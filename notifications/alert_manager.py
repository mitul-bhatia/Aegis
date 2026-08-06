"""
Aegis — Multi-Channel Notification Alert Manager

Sends security scan alerts and PR creation digests to:
- Slack Webhooks (Block Kit)
- Discord Webhooks (Embeds)
- Email via Resend/SendGrid REST API
"""

import logging
import requests
import config

logger = logging.getLogger(__name__)


def send_scan_alert(
    repo_name: str,
    vulnerability_type: str,
    severity: str,
    vulnerable_file: str,
    pr_url: str = None,
    slack_url: str = None,
    discord_url: str = None,
):
    """
    Dispatch vulnerability fix alert across active notification channels.
    """
    slack_target = slack_url or config.SLACK_WEBHOOK_URL
    discord_target = discord_url or config.DISCORD_WEBHOOK_URL

    title = f"🛡️ Aegis Security Fix Applied: {repo_name}"
    message = (
        f"*Vulnerability:* {vulnerability_type}\n"
        f"*Severity:* {severity}\n"
        f"*File:* `{vulnerable_file}`\n"
        f"*Pull Request:* {pr_url if pr_url else 'Pending approval'}"
    )

    # 1. Slack Webhook Notification
    if slack_target:
        try:
            payload = {
                "text": title,
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": title, "emoji": True},
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Repository:*\n{repo_name}"},
                            {"type": "mrkdwn", "text": f"*Severity:*\n{severity}"},
                            {"type": "mrkdwn", "text": f"*Vulnerability:*\n{vulnerability_type}"},
                            {"type": "mrkdwn", "text": f"*File:*\n`{vulnerable_file}`"},
                        ],
                    },
                ],
            }
            if pr_url:
                payload["blocks"].append({
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Pull Request 🚀"},
                            "url": pr_url,
                            "style": "primary",
                        }
                    ],
                })

            requests.post(slack_target, json=payload, timeout=5)
            logger.info(f"Slack alert sent for {repo_name}")
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")

    # 2. Discord Webhook Notification
    if discord_target:
        try:
            color = 15158332 if severity.upper() in ("CRITICAL", "HIGH", "ERROR") else 3447003
            payload = {
                "username": "Aegis Security Swarm",
                "embeds": [
                    {
                        "title": title,
                        "description": message,
                        "color": color,
                        "url": pr_url or config.FRONTEND_URL,
                        "footer": {"text": "Aegis Automated Defensibility Layer"},
                    }
                ],
            }
            requests.post(discord_target, json=payload, timeout=5)
            logger.info(f"Discord alert sent for {repo_name}")
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
