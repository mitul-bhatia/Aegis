"""
Aegis — Slack & Discord Notifications

Sends webhook notifications when scans reach notable states.
Both channels are optional — configure via environment variables:

  SLACK_WEBHOOK_URL   = https://hooks.slack.com/services/...
  DISCORD_WEBHOOK_URL = https://discord.com/api/webhooks/...

If neither is set, notifications are silently skipped.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import requests

import config

logger = logging.getLogger(__name__)

# ── Severity colours ──────────────────────────────────────
# Used as attachment/embed colours in Slack and Discord.
_SEVERITY_COLOURS = {
    "CRITICAL": {"slack": "#FF0000", "discord": 0xFF0000},
    "HIGH":     {"slack": "#FF6600", "discord": 0xFF6600},
    "MEDIUM":   {"slack": "#FFA500", "discord": 0xFFA500},
    "LOW":      {"slack": "#3AA3E3", "discord": 0x3AA3E3},
}

_STATUS_EMOJI = {
    "fixed":             "🛡️",
    "failed":            "❌",
    "exploit_confirmed": "🚨",
    "awaiting_approval": "⚠️",
    "false_positive":    "📊",
    "clean":             "✅",
}


@dataclass
class ScanEvent:
    scan_id: int
    repo_name: str
    status: str
    vulnerability_type: Optional[str]
    severity: Optional[str]
    vulnerable_file: Optional[str]
    pr_url: Optional[str]
    error_message: Optional[str]
    scan_url: str  # link back to Aegis UI


# ── Public entry point ────────────────────────────────────

def notify_scan_event(event: ScanEvent) -> None:
    """
    Fire notifications to all configured channels for a scan event.
    Called after every terminal or notable status change.
    """
    # Only notify for states worth alerting on
    notable = {
        "fixed", "failed", "exploit_confirmed", "awaiting_approval",
        "false_positive",
    }
    if event.status not in notable:
        return

    slack_url = getattr(config, "SLACK_WEBHOOK_URL", "")
    discord_url = getattr(config, "DISCORD_WEBHOOK_URL", "")

    if slack_url:
        _send_slack(event, slack_url)

    if discord_url:
        _send_discord(event, discord_url)

    if not slack_url and not discord_url:
        logger.debug("No notification webhooks configured — skipping")


# ── Slack ─────────────────────────────────────────────────

def _send_slack(event: ScanEvent, webhook_url: str) -> None:
    title, body = _build_message(event)
    severity = (event.severity or "MEDIUM").upper()
    colour = _SEVERITY_COLOURS.get(severity, _SEVERITY_COLOURS["MEDIUM"])["slack"]

    fields = [
        {"title": "Repository", "value": event.repo_name, "short": True},
        {"title": "Status",     "value": event.status.replace("_", " ").title(), "short": True},
    ]
    if event.vulnerability_type:
        fields.append({"title": "Vulnerability", "value": event.vulnerability_type, "short": True})
    if event.severity:
        fields.append({"title": "Severity", "value": severity, "short": True})
    if event.vulnerable_file:
        fields.append({"title": "File", "value": f"`{event.vulnerable_file}`", "short": False})

    actions = [{"type": "button", "text": "View in Aegis", "url": event.scan_url}]
    if event.pr_url:
        actions.append({"type": "button", "text": "Review PR", "url": event.pr_url})

    payload = {
        "attachments": [{
            "color": colour,
            "title": title,
            "text": body,
            "fields": fields,
            "actions": actions,
            "footer": "Aegis Security",
            "mrkdwn_in": ["text"],
        }]
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=8)
        if resp.ok:
            logger.info(f"Slack notification sent for scan #{event.scan_id}")
        else:
            logger.warning(f"Slack notification failed: {resp.status_code} {resp.text[:100]}")
    except requests.RequestException as e:
        logger.warning(f"Slack notification error: {e}")


# ── Discord ───────────────────────────────────────────────

def _send_discord(event: ScanEvent, webhook_url: str) -> None:
    title, body = _build_message(event)
    severity = (event.severity or "MEDIUM").upper()
    colour = _SEVERITY_COLOURS.get(severity, _SEVERITY_COLOURS["MEDIUM"])["discord"]

    fields = [
        {"name": "Repository", "value": event.repo_name, "inline": True},
        {"name": "Status",     "value": event.status.replace("_", " ").title(), "inline": True},
    ]
    if event.vulnerability_type:
        fields.append({"name": "Vulnerability", "value": event.vulnerability_type, "inline": True})
    if event.severity:
        fields.append({"name": "Severity", "value": severity, "inline": True})
    if event.vulnerable_file:
        fields.append({"name": "File", "value": f"`{event.vulnerable_file}`", "inline": False})

    # Discord embed links go in the description
    links = [f"[View in Aegis]({event.scan_url})"]
    if event.pr_url:
        links.append(f"[Review PR]({event.pr_url})")
    description = body + "\n\n" + " · ".join(links)

    payload = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": colour,
            "fields": fields,
            "footer": {"text": "Aegis Security"},
        }]
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=8)
        if resp.ok:
            logger.info(f"Discord notification sent for scan #{event.scan_id}")
        else:
            logger.warning(f"Discord notification failed: {resp.status_code} {resp.text[:100]}")
    except requests.RequestException as e:
        logger.warning(f"Discord notification error: {e}")


# ── Message builder ───────────────────────────────────────

def _build_message(event: ScanEvent) -> tuple[str, str]:
    """Return (title, body) for the notification."""
    emoji = _STATUS_EMOJI.get(event.status, "🔔")

    if event.status == "fixed":
        title = f"{emoji} Vulnerability Fixed — {event.repo_name}"
        body = (
            f"Aegis patched **{event.vulnerability_type}** in `{event.vulnerable_file}`. "
            f"A PR is ready for review."
        )
    elif event.status == "exploit_confirmed":
        title = f"{emoji} Exploitable Vulnerability Found — {event.repo_name}"
        body = (
            f"**{event.vulnerability_type}** in `{event.vulnerable_file}` "
            f"was confirmed exploitable in a Docker sandbox. Patching in progress."
        )
    elif event.status == "awaiting_approval":
        title = f"{emoji} CRITICAL Patch Needs Approval — {event.repo_name}"
        body = (
            f"Aegis patched a **CRITICAL {event.vulnerability_type}** "
            f"in `{event.vulnerable_file}`. Human approval required before PR creation."
        )
    elif event.status == "failed":
        title = f"{emoji} Scan Failed — {event.repo_name}"
        body = event.error_message or "The pipeline encountered an error. Human review required."
    elif event.status == "false_positive":
        title = f"{emoji} False Positive — {event.repo_name}"
        body = (
            f"Aegis flagged **{event.vulnerability_type}** but could not confirm "
            f"it was exploitable in the sandbox."
        )
    else:
        title = f"{emoji} Scan Update — {event.repo_name}"
        body = f"Scan #{event.scan_id} status: {event.status}"

    return title, body
