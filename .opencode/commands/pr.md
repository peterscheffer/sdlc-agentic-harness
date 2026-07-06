---
description: Assist user in creating a Pull Request through the PR stage of the SDLC pipeline.
---

## Phase 0.0: Auto-Accept Detection (Dark Factory Mode)
Before any interactive phase, determine whether this run is in auto-accept mode:
1. Run:
   ```bash
   python3 -c "import json,os;print(json.load(open('.sdlc_state.json')).get('auto_accept',False) if os.path.exists('.sdlc_state.json') else False)"
   ```
2. Auto-accept is active if that prints `True`, OR the user's invocation includes `--auto-accept`.
3. If auto-accept is active: **SKIP every interactive questioning phase in this skill.** Answer each discovery question yourself using best-practice defaults inferred from the PRD, prior artefacts, and the repository. Record every decision you made in the context file under a heading `## Auto-Accepted Decisions`. Then proceed directly to the context-export and script-execution phase, appending `--auto-accept` to the `python3` command. Do not ask the user anything.


## Phase 0: Baseline State Initialization
Before interacting with the user, you must establish the project's current state.
1. Use your file-reading tool to open and read `sdlc/planning/PRD.md`.
2. Examine the current code changes using:
   ```bash
   git diff --stat
   ```
3. Read any review artefacts generated during the review stage.
4. Do **NOT** re-interview the user on information already captured in prior artefacts.

## Phase 1: PR Details Discovery (Dynamic Questioning)
Your objective is to gather the necessary details for the pull request.

* **Goal:** Collect the information needed to create a well-documented PR.
* **Execution:** Ask **one or two targeted questions at a time**. Do not overwhelm the user.
* **Scope:** Focus on PR logistics:
  * **PR Title & Description:** What should the PR title and summary be?
  * **Reviewers:** Any specific reviewers to request?
  * **Branch Strategy:** Target branch, branch naming conventions.
  * **Additional Context:** Any related issues, tickets, or notes to include?

## Phase 2: The Gate (Validation)
Iterate on the PR details until everything is clear. Do **NOT** proceed to the bash commands in Phase 3 until you explicitly meet this condition:
* You have all PR details **AND** the user explicitly confirms they are ready to submit (e.g., "I'm ready", "Create the PR", "Submit it").

## Phase 3: Context Export & Script Execution
Once the gate in Phase 2 is passed, execute the following steps exactly using your Bash tool:

1. Ensure the pr discussions directory exists:
   ```bash
   mkdir -p discussions/pr
   ```
2. Save the full PR conversation context and decisions to a timestamped file:
   ```bash
   CONTEXT_FILE="discussions/pr/$(date +%Y%m%d_%H%M%S)-pr-context.md"
   cat > "$CONTEXT_FILE" << 'EOF'
   [Insert complete chronological PR conversation history, title, description, and reviewer choices here]
   EOF
   ```
3. Execute the LangGraph pipeline execution script for the pr stage:
   ```bash
   python3 .scripts/sdlc_harness.py --stage pr --context "$CONTEXT_FILE" --force
   ```

## Phase 4. Output Synthesis & Completion
Read the stdout/stderr printed by the Python script.
1. **Summarize PR:** Print the PR URL, title, and summary for the user.
2. **Clear Context:** From this point forward, treat the prior PR discussion as deprecated noise.
3. **Declare Completion:** Confirm that the SDLC pipeline is complete for this feature cycle.
   _Example message to user:_
   "Pull request created successfully. The SDLC pipeline is complete for this feature. The next feature cycle can begin with /plan."
