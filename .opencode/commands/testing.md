---
description: Assist user in proceeding through the Testing stage of the SDLC pipeline.
---

## Phase 0: Baseline State Initialization
Before interacting with the user, you must establish the project's current state.
1. Use your file-reading tool to open and read:
   - `sdlc/planning/PRD.md`
   - `sdlc/requirements/REQUIREMENTS.md`
   - All `.feature` files under `sdlc/requirements/`
   - The source code files that were generated or modified in the coding stage
2. Absorb the product requirements, Gherkin scenarios, and current implementation.
3. Do **NOT** re-interview the user on information already captured in prior artefacts.

## Phase 1: Test Strategy Discovery (Dynamic Questioning)
Your objective is to interview the user to determine the testing scope and focus areas.

* **Goal:** Collect enough direction to run the correct tests and validate behaviour.
* **Execution:** Ask **one or two targeted questions at a time**. Do not overwhelm the user.
* **Scope:** Focus on testing decisions:
  * **Test Scope:** Run all tests or focus on specific feature areas?
  * **Edge Cases:** Are there specific edge cases or failure scenarios to prioritise?
  * **Coverage Goals:** Are there minimum coverage thresholds or critical paths that must pass?
  * **Environment:** Any special environment setup or configuration needed for tests?

## Phase 2: The Gate (Validation)
Iterate on the testing questions until you have a clear testing direction. Do **NOT** proceed to the bash commands in Phase 3 until you explicitly meet this condition:
* You have a defined test scope **AND** the user explicitly indicates they are ready to proceed (e.g., "I'm ready", "Run the tests", "Verify compliance").

## Phase 3: Context Export & Script Execution
Once the gate in Phase 2 is passed, execute the following steps exactly using your Bash tool:

1. Ensure the testing discussions directory exists:
   ```bash
   mkdir -p discussions/testing
   ```
2. Save the full testing conversation context and decisions to a timestamped file:
   ```bash
   CONTEXT_FILE="discussions/testing/$(date +%Y%m%d_%H%M%S)-testing-context.md"
   cat > "$CONTEXT_FILE" << 'EOF'
   [Insert complete chronological testing conversation history, chosen test scope, and focus areas here]
   EOF
   ```
3. Execute the LangGraph pipeline execution script for the testing stage:
   ```bash
   python3 .scripts/langgraph_sdlc.py --stage testing --context "$CONTEXT_FILE"
   ```

## Phase 4. Output Synthesis & Handover
Read the stdout/stderr printed by the Python script.
1. **Summarize Changes:** Outline the test results — how many tests passed/failed, Gherkin compliance status, and any issues found.
2. **Clear Context:** From this point forward, treat the prior testing discussion as deprecated noise to optimize current memory constraints.
3. **Trigger Next Stage:** Prompt the user that the testing stage is complete and instruct them on how to proceed.
   _Example message to user:_
   "Testing complete. All tests pass and Gherkin compliance is verified. To review the changes and prepare the PR, run: /review"
4. CRITICAL: Hold the line here. Do NOT automatically fix failing tests, modify code, or skip ahead to the next stage yourself. Wait for human review and the next explicit command invocation.
