"""
Aegis LangGraph State Machine

Defines the pipeline as a directed graph with conditional routing.
Each node is a function from nodes.py. Edges define what runs next
based on the current state.

Graph topology:

  pre_process
      │
      ▼
   finder ──── no findings ──► END (clean)
      │
      ▼
  exploiter ── no confirmed ──► END (false_positive)
      │         docker down ──► END (failed)
      ▼
  engineer ─── patch failed ──► next vuln or END
      │
      ▼
  safety_validator ── regression/new vuln ──► engineer (retry)
      │
      ▼
  approval_gate ── CRITICAL ──► END (await human)
      │
      ▼
  pr_creator
      │
      ├── more vulns? ──► engineer (loop)
      │
      └── all done? ──► END
"""

from langgraph.graph import StateGraph, END

from pipeline.state import AegisPipelineState
from pipeline.nodes import (
    pre_process_node,
    finder_node,
    exploiter_node,
    engineer_node,
    pr_creator_node,
    approval_gate_node,
)
from pipeline.safety_validator import safety_validator_node


# ── Routing functions ─────────────────────────────────────
# Each returns a string key that maps to the next node name.

def route_after_pre_process(state: AegisPipelineState) -> str:
    """Skip to END if no code files changed."""
    if state.get("pipeline_status") == "clean":
        return "end"
    return "finder"


def route_after_finder(state: AegisPipelineState) -> str:
    """Skip to END if Finder found nothing."""
    if not state.get("vulnerability_findings"):
        return "end"
    return "exploiter"


def route_after_exploiter(state: AegisPipelineState) -> str:
    """Skip to END if no exploits confirmed, or Docker was unavailable."""
    status = state.get("pipeline_status", "")
    if status in ("false_positive", "failed", "clean"):
        return "end"
    if not state.get("confirmed_vulnerabilities"):
        return "end"
    return "engineer"


def route_after_engineer(state: AegisPipelineState) -> str:
    """
    After the Engineer finishes one vulnerability:
    - If patch succeeded → go to safety validator
    - If patch failed → move to next vuln (or end if all done)
    """
    confirmed = state.get("confirmed_vulnerabilities", [])
    idx = state.get("current_vuln_index", 0)

    # Patch succeeded — run safety checks
    if state.get("verification_passed"):
        return "safety_validator"

    # Patch failed — check if there are more vulns to try
    # idx was already incremented by engineer_node on failure
    if idx < len(confirmed):
        return "engineer"

    return "end"


def route_after_safety(state: AegisPipelineState) -> str:
    """
    If regression detected, loop back to engineer to try again.
    Otherwise, proceed to the approval gate.
    """
    if state.get("rescan_needed"):
        return "engineer"
    return "approval_gate"


def route_after_approval(state: AegisPipelineState) -> str:
    """
    If awaiting approval (CRITICAL) → end (wait for human)
    Otherwise → open a PR
    """
    if state.get("awaiting_approval"):
        return "end"
    return "pr_creator"


def route_after_pr_creator(state: AegisPipelineState) -> str:
    """
    After opening a PR:
    - If more confirmed vulns remain → loop back to engineer
    - Otherwise → done
    """
    confirmed = state.get("confirmed_vulnerabilities", [])
    idx = state.get("current_vuln_index", 0)

    if idx < len(confirmed):
        return "engineer"  # fix next vulnerability

    return "end"


# ── Build the graph ───────────────────────────────────────

def build_aegis_graph():
    """
    Construct and compile the Aegis LangGraph pipeline.
    Returns a compiled graph ready to invoke.
    """
    graph = StateGraph(AegisPipelineState)

    # Register all nodes
    graph.add_node("pre_process", pre_process_node)
    graph.add_node("finder",      finder_node)
    graph.add_node("exploiter",   exploiter_node)
    graph.add_node("engineer",    engineer_node)
    graph.add_node("safety_validator", safety_validator_node)
    graph.add_node("approval_gate", approval_gate_node)
    graph.add_node("pr_creator",  pr_creator_node)

    # Entry point
    graph.set_entry_point("pre_process")

    # Conditional edges — each routing function returns the next node name
    graph.add_conditional_edges(
        "pre_process",
        route_after_pre_process,
        {"finder": "finder", "end": END},
    )
    graph.add_conditional_edges(
        "finder",
        route_after_finder,
        {"exploiter": "exploiter", "end": END},
    )
    graph.add_conditional_edges(
        "exploiter",
        route_after_exploiter,
        {"engineer": "engineer", "end": END},
    )
    graph.add_conditional_edges(
        "engineer",
        route_after_engineer,
        {"safety_validator": "safety_validator", "engineer": "engineer", "end": END},
    )
    graph.add_conditional_edges(
        "safety_validator",
        route_after_safety,
        {"approval_gate": "approval_gate", "engineer": "engineer"},
    )
    graph.add_conditional_edges(
        "approval_gate",
        route_after_approval,
        {"pr_creator": "pr_creator", "end": END},
    )
    graph.add_conditional_edges(
        "pr_creator",
        route_after_pr_creator,
        {"engineer": "engineer", "end": END},
    )

    return graph.compile()


# Compile once at import time — reused for every pipeline run
aegis_pipeline = build_aegis_graph()
