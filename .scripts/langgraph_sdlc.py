#!/usr/bin/env python3
import argparse
import json
import os
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END

# 1. Define the Graph State Schema
class SDLCState(TypedDict):
    current_stage: str
    next_stage: str
    target_feature: Optional[str]

# 2. Local State Persistence Mechanics
STATE_FILE = ".sdlc_state.json"

def load_persisted_state() -> SDLCState:
    """Loads the state dictionary from disk if it exists; otherwise defaults."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"current_stage": "INIT", "next_stage": "architect", "target_feature": None}

def save_persisted_state(state: SDLCState):
    """Saves the mutated state back to disk."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# 3. Define the Graph Nodes (Your original logic)
def run_architect_stage(state: SDLCState) -> dict:
    print("\n[LangGraph Node: Architect] Analyzing code footprint and requirements...")
    # Real-world: Ingests CONSTITUTION.md, targets files, creates your atomic specs
    return {"current_stage": "PLANNING_COMPLETE", "next_stage": "coder"}

def run_coder_stage(state: SDLCState) -> dict:
    print("\n[LangGraph Node: Coder] Booting local context-isolated Ralph code execution...")
    # Real-world: Multi-iteration loop executing code generation and validation blocks
    return {"current_stage": "BUILD_COMPLETE", "next_stage": "verify"}

def run_verify_stage(state: SDLCState) -> dict:
    print("\n[LangGraph Node: Verify] Evaluating systemic drift and integration tests...")
    # Real-world: Executes dependency structural validation and Playwright/linter runs
    return {"current_stage": "VERIFICATION_SUCCESS", "next_stage": "complete"}

# 4. Assemble the LangGraph State Machine
workflow = StateGraph(SDLCState)

# Add our functional components as nodes
workflow.add_node("architect", run_architect_stage)
workflow.add_node("coder", run_coder_stage)
workflow.add_node("verify", run_verify_stage)

# Establish the routing constraints
def route_from_start(state: SDLCState) -> str:
    # Use persisted current_stage to decide which node to run next
    stage_map = {
        "INIT": "architect",
        "PLANNING_COMPLETE": "coder",
        "BUILD_COMPLETE": "verify",
    }
    return stage_map.get(state.get("current_stage", "INIT"), END)

workflow.add_conditional_edges(START, route_from_start)
workflow.add_edge("architect", END)
workflow.add_edge("coder", END)
workflow.add_edge("verify", END)

# Compile our executable graph
app = workflow.compile()

# 5. CLI Execution Handler
def main():
    parser = argparse.ArgumentParser(description="LangGraph-driven SDLC State Machine Core")
    parser.add_argument("--stage", required=True, choices=["planning", "coder", "verify"], 
                        help="The target execution stage invoked via OpenCode slash command.")
    parser.add_argument("--feature", required=False, help="The prompt or feature description passed in on initialization.")
    
    args = parser.parse_args()
    
    # Ingest historical context from disk
    current_state = load_persisted_state()
    
    # Capture feature payload if provided during the initial planning step
    if args.feature:
        current_state["target_feature"] = args.feature

    print(f"─── LangGraph Activation Initialized ───")
    print(f"Target Parameter Passed From Slash Command: '{args.stage}'")
    print(f"Current Persistent Memory State: {current_state['current_stage']}")

    config = {"configurable": {"thread_id": "1"}}
    final_output = app.invoke(current_state, config)
    
    # Save output adjustments cleanly to disk
    save_persisted_state(final_output)
    
    print(f"\n─── Stage Execution Metrics ───")
    print(f"Updated System Stage Status:  {final_output['current_stage']}")
    print(f"Next Human Gated Action Required: Run `/sdlc {final_output['next_stage']}`")
    print(f"────────────────────────────────────────")

if __name__ == "__main__":
    main()
