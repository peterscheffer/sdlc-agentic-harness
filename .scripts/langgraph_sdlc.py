#!/usr/bin/env python3
import argparse
import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from utils.state import (
    load_state, save_state, init_state,
    validate_stage_transition, get_expected_next_stages, STATE_FILE,
)
from utils.config import load_config
from utils.git import get_current_branch

from nodes.planning import execute_planning
from nodes.ui_design import execute_ui_design
from nodes.architecture import execute_architecture
from nodes.requirements import execute_requirements
from nodes.coding import execute_coding
from nodes.testing import execute_testing
from nodes.review import execute_review
from nodes.pr import execute_pr


def _prd_update(state, config, stage_id, conversation_context, require_complete=True):
    if stage_id not in ("planning", "review", "pr"):
        if require_complete:
            stage_entry = state.stages.get(stage_id)
            if not stage_entry or stage_entry.status != "complete":
                return
        try:
            from utils.prd_updater import update_prd_if_needed
            updated = update_prd_if_needed(state, config, stage_id, conversation_context)
            if updated:
                print(f"\n[{stage_id}] PRD updated with new information.")
        except Exception as e:
            print(f"\n[{stage_id}] PRD update skipped: {e}")


def cmd_status():
    try:
        state = load_state()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"--- SDLC Pipeline Status ---")
    print(f"Pipeline ID: {state.pipeline_id or 'N/A'}")
    print(f"Intent: {state.intent or 'N/A'}")
    print(f"Current Stage: {state.current_stage}")
    print(f"Completed Stages: {state.completed_stages}")
    print(f"State file: {STATE_FILE}")

    print(f"\nStage Details:")
    for stage_id in ["planning", "ui-design", "architecture", "requirements", "coding", "testing", "review", "pr"]:
        entry = state.stages.get(stage_id)
        if entry:
            status_icon = "\u2713" if entry.status == "complete" else \
                          "\u26a0" if entry.status == "skipped" else \
                          "\u2717" if entry.status == "failed" else \
                          "\u2014"
            print(f"  {status_icon} {stage_id}: {entry.status}")
            if entry.reason:
                print(f"       Reason: {entry.reason}")
            if entry.recommendation:
                print(f"       Recommendation: {entry.recommendation}")

    if state.pr_url:
        print(f"\nPR URL: {state.pr_url}")
    return 0


def cmd_reset(args):
    try:
        state = load_state()
    except ValueError:
        state = None

    if state and not args.force:
        print(
            "This will clear all pipeline state. Existing sdlc/ artefacts will not be deleted.\n"
            "Are you sure? (yes/no)"
        )
        try:
            response = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nReset cancelled.")
            return 1
        if response != "yes":
            print("Reset cancelled.")
            return 0

    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    print("Pipeline state cleared. Run /sdlc planning '<intent>' to start fresh.")
    return 0


def _read_context_file(path: str) -> str:
    if not path:
        return ""
    if not os.path.exists(path):
        print(f"[context] Warning: Context file not found: {path}")
        return ""
    try:
        with open(path) as f:
            return f.read()
    except Exception as e:
        print(f"[context] Warning: Could not read context file {path}: {e}")
        return ""


def _run_autopilot(state, config, conversation_context):
    from utils.state import StageEntry

    print(f"\n{'='*60}")
    print(f"[autopilot] Pipeline auto-pilot engaged. Running remaining stages...")
    print(f"{'='*60}")

    while True:
        expected = get_expected_next_stages(state)
        if not expected or expected[0] == "complete":
            break
        next_stage = expected[0]

        print(f"\n{'='*50}")
        print(f"[autopilot] Running stage: {next_stage}")
        print(f"{'='*50}")

        if next_stage == "coding":
            state = execute_coding(state, config, conversation_context=conversation_context)
        elif next_stage == "testing":
            state = execute_testing(state, config)
        elif next_stage == "review":
            state = execute_review(state, config, conversation_context=conversation_context)
        elif next_stage == "pr":
            rec = state.stages.get("review", StageEntry()).recommendation
            if rec == "FAIL":
                print(f"\n[autopilot] Review recommended FAIL. Cannot auto-submit PR.")
                print(f"[autopilot] Halting pipeline. Run '/pr' or '/pr --force' manually.")
                state.stages["pr"].status = "failed"
                state.stages["pr"].reason = "Autopilot halted: review recommendation is FAIL"
                save_state(state)
                _print_metrics(state, next_stage)
                return state
            state = execute_pr(state, config, force=False)

        save_state(state)
        _prd_update(state, config, next_stage, conversation_context)
        _print_metrics(state, next_stage)

        if state.stages[next_stage].status != "complete":
            print(f"\n[autopilot] \u2717 Stage '{next_stage}' FAILED.")
            print(f"[autopilot] Pipeline halted. Fix the issue and continue manually.")
            print(f"[autopilot] Run '/sdlc status' to see the current state.")
            return state

        print(f"[autopilot] \u2713 Stage '{next_stage}' completed.")

    print(f"\n{'='*60}")
    print(f"[autopilot] \u2713 All stages completed. Pipeline finished!")
    print(f"{'='*60}")
    return state


def execute_stage(stage_id: str, intent: str = "", force: bool = False, conversation_context: str = "", autopilot: bool = False):
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    try:
        state = load_state()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if state.current_stage == "INIT" and stage_id != "planning":
        print("No pipeline in progress. Start with: /sdlc planning '<intent>'")
        sys.exit(1)

    # --- Cross-stage workflow: re-enter planning with new intent ---
    if stage_id == "planning" and state.current_stage != "INIT" and intent:
        state = init_state(intent, get_current_branch())
        state = execute_planning(state, config, intent, conversation_context=conversation_context)
        save_state(state)
        _print_metrics(state, stage_id)
        return 0

    # --- Cross-stage workflow: re-enter coding from review ---
    if stage_id == "coding" and state.current_stage == "review":
        state.stages["coding"].status = "not_started"
        state.stages["coding"].iterations = None
        state.current_stage = "coding"
        if "coding" in state.completed_stages:
            state.completed_stages.remove("coding")
        state = execute_coding(state, config, conversation_context=conversation_context)
        _prd_update(state, config, "coding", conversation_context)
        save_state(state)
        _print_metrics(state, stage_id)
        return 0

    # --- Normal transition validation ---
    transition_error = validate_stage_transition(state, stage_id)
    if transition_error:
        print(transition_error)
        print("State file not modified.")
        sys.exit(1)

    branch = get_current_branch()

    _prd_update(state, config, stage_id, conversation_context, require_complete=False)

    if stage_id == "planning":
        if state.current_stage == "INIT":
            state = init_state(intent, branch)
            state.current_stage = "INIT"
        state = execute_planning(state, config, intent, conversation_context=conversation_context)

    elif stage_id == "ui-design":
        state = execute_ui_design(state, config, conversation_context=conversation_context)

    elif stage_id == "architecture":
        state = execute_architecture(state, config, conversation_context=conversation_context)

    elif stage_id == "requirements":
        state = execute_requirements(state, config, conversation_context=conversation_context)

    elif stage_id == "coding":
        state = execute_coding(state, config, conversation_context=conversation_context)

    elif stage_id == "testing":
        state = execute_testing(state, config)

    elif stage_id == "review":
        state = execute_review(state, config, conversation_context=conversation_context)

    elif stage_id == "pr":
        state = execute_pr(state, config, force=force)

    save_state(state)

    _prd_update(state, config, stage_id, conversation_context)

    _print_metrics(state, stage_id)

    if autopilot and state.stages[stage_id].status == "complete":
        state = _run_autopilot(state, config, conversation_context)
        save_state(state)

    return 0


def _print_metrics(state, stage_id: str):
    print(f"\n--- Stage Execution Metrics ---")
    stage_entry = state.stages.get(stage_id)
    if stage_entry:
        print(f"Updated System Stage Status:  {stage_entry.status.upper()}")
        if stage_entry.iterations:
            print(f"Iterations: {stage_entry.iterations}")
    else:
        print(f"Updated System Stage Status:  {state.current_stage}")
    print(f"Next Human Gated Action Required: {_get_next_command(state)}")
    print(f"-------------------------------")


def _get_next_command(state) -> str:
    expected = get_expected_next_stages(state)
    if expected and expected[0] != "complete":
        return f"Run `/sdlc {expected[0]}`"
    if "pr" in state.completed_stages:
        return "Pipeline complete. All artefacts committed to sdlc/."
    return "Run `/sdlc status`"


def main():
    parser = argparse.ArgumentParser(
        description="LangGraph-driven SDLC Pipeline - Orchestration Engine"
    )

    parser.add_argument("--stage", required=False,
                        choices=["planning", "ui-design", "architecture",
                                 "requirements", "coding", "testing", "review", "pr"],
                        help="The target execution stage.")
    parser.add_argument("--feature", "--intent", required=False, dest="feature",
                        help="The intent or feature description (for planning).")
    parser.add_argument("--force", action="store_true",
                        help="Skip confirmation (for reset) or force PR submission.")
    parser.add_argument("--context", required=False,
                        help="Path to a file containing prior conversation context.")
    parser.add_argument("--autopilot", "-a", action="store_true",
                        help="After the requested stage succeeds, automatically run all remaining stages.")

    args, remaining = parser.parse_known_args()

    conversation_context = _read_context_file(args.context or "")

    if remaining and remaining[0] in ("status", "reset", "stage"):
        subcmd = remaining[0]
        if subcmd == "status":
            return cmd_status()
        elif subcmd == "reset":
            return cmd_reset(args)
        elif subcmd == "stage":
            subparser = argparse.ArgumentParser()
            subparser.add_argument("--stage", required=True,
                                    choices=["planning", "ui-design", "architecture",
                                             "requirements", "coding", "testing", "review", "pr"])
            subparser.add_argument("--feature", required=False)
            subparser.add_argument("--force", action="store_true")
            subparser.add_argument("--context", required=False)
            subparser.add_argument("--autopilot", action="store_true")
            subargs, _ = subparser.parse_known_args(remaining[1:])
            ctx = _read_context_file(subargs.context or "")
            return execute_stage(subargs.stage, subargs.feature or "", subargs.force,
                                 conversation_context=ctx, autopilot=subargs.autopilot)

    if args.stage:
        return execute_stage(args.stage, args.feature or "", args.force,
                             conversation_context=conversation_context, autopilot=args.autopilot)

    print("Usage:")
    print("  python3 .scripts/langgraph_sdlc.py --stage <stage> [--feature <intent>] [--force] [--context <file>] [--autopilot]")
    print("  python3 .scripts/langgraph_sdlc.py status")
    print("  python3 .scripts/langgraph_sdlc.py reset [--force]")
    print("  python3 .scripts/langgraph_sdlc.py stage --stage <stage> [--feature <intent>] [--force] [--context <file>] [--autopilot]")
    print("")
    print("Stages: planning, ui-design, architecture, requirements, coding, testing, review, pr")
    print("")
    print("Flags:")
    print("  --autopilot, -a   Run all remaining stages automatically after the requested stage completes.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
