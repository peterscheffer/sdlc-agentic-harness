---
description: Assist user in proceeding through the Review stage of the SDLC pipeline.
---

## Phase 0: Baseline State Initialization
Before interacting with the user, you must establish the project's current state.
1. Use your file-reading tool to open and read:
   - `sdlc/planning/PRD.md`
   - `sdlc/architecture/ARCH.md`
2. Examine the current code changes using:
   ```bash
   git diff --stat
   ```
3. Absorb the changes made during coding and testing stages.
4. Do **NOT** re-interview the user on information already captured in prior artefacts.

## Phase 1: Review Focus Discovery (Dynamic Questioning)
Your objective is to interview the user to determine the focus areas for the code review.

* **Goal:** Collect enough direction to produce a focused, actionable review.
* **Execution:** Ask **one or two targeted questions at a time**. Do not overwhelm the user.
* **Scope:** Focus on review priorities:
  * **Correctness:** Does the implementation match the requirements and architecture?
  * **Security:** Are there any security concerns (input validation, auth, data leakage)?
  * **Performance:** Are there performance-sensitive areas that need attention?
  * **Maintainability:** Code style, documentation, test coverage, adherence to project conventions.

## Phase 2: The Gate (Validation)
Iterate on the review questions until you have a clear review direction. Do **NOT** proceed to the bash commands in Phase 3 until you explicitly meet this condition:
* You have a defined review focus **AND** the user explicitly indicates they are ready to proceed (e.g., "I'm ready", "Run the review", "Review the code").

## Phase 3: Context Export & Script Execution
Once the gate in Phase 2 is passed, execute the following steps exactly using your Bash tool. **This stage uses gemma4:31b which is slow — use a 900000ms timeout.**

1. Ensure the review discussions directory exists:
   ```bash
   mkdir -p discussions/review
   ```
2. Save the full review conversation context and decisions to a timestamped file:
   ```bash
   CONTEXT_FILE="discussions/review/$(date +%Y%m%d_%H%M%S)-review-context.md"
   cat > "$CONTEXT_FILE" << 'EOF'
   [Insert complete chronological review conversation history, focus areas, and priorities here]
   EOF
   ```
3. Execute the LangGraph pipeline execution script for the review stage:
   ```bash
   python3 .scripts/langgraph_sdlc.py --stage review --context "$CONTEXT_FILE"
   ```

## Phase 4. Output Synthesis & Handover
Read the stdout/stderr printed by the Python script.
1. **Summarize Changes:** Outline the review findings — issues identified, PRINCIPLES compliance, and any recommended changes.
2. **Read Review Output:** Use your file-reading tool to open the generated review artefact for details.
3. **Clear Context:** From this point forward, treat the prior review discussion as deprecated noise to optimize current memory constraints.
4. **Trigger Next Stage:** Prompt the user that the review stage is complete and instruct them on how to proceed.
   _Example message to user:_
   "Code review complete. All issues documented and PRINCIPLES compliance verified. To create the pull request, run: /pr"
5. CRITICAL: Hold the line here. Do NOT automatically fix review issues, modify code, or skip ahead to the next stage yourself. Wait for human review and the next explicit command invocation.
