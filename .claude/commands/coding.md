---
description: Assist user in proceeding through the Coding stage of the SDLC pipeline.
---

## Phase 0: Baseline State Initialization
Before interacting with the user, you must establish the project's current state.
1. Use your file-reading tool to open and read:
   - `sdlc/planning/PRD.md`
   - `sdlc/architecture/ARCH.md`
   - `sdlc/requirements/REQUIREMENTS.md`
   - All `.feature` files under `sdlc/requirements/`
2. Absorb the product requirements, architectural blueprint, functional specifications, and Gherkin scenarios.
3. Do **NOT** re-interview the user on information already captured in prior artefacts.

## Phase 1: Implementation Discovery (Dynamic Questioning)
Your objective is to interview the user to clarify the implementation approach before generating code.

* **Goal:** Collect enough direction to produce well-structured, correct code.
* **Execution:** Ask **one or two targeted questions at a time**. Do not overwhelm the user.
* **Scope:** Focus on implementation decisions:
  * **Implementation Order:** Which features should be built first? Is there a dependency order?
  * **File Structure:** Any preferences for module organisation, naming conventions, or directory layout?
  * **Dependencies:** Are there specific libraries, SDKs, or third-party services to integrate?
  * **Testing Approach:** Unit tests first? Integration tests alongside? Any specific test framework preferences?

## Phase 2: The Gate (Validation)
Iterate on the implementation questions until you have a clear coding direction. Do **NOT** proceed to the bash commands in Phase 3 until you explicitly meet this condition:
* You have a clear implementation plan **AND** the user explicitly indicates they are ready to proceed (e.g., "I'm ready", "Run the script", "Generate the code").

## Phase 3: Context Export & Script Execution
Once the gate in Phase 2 is passed, execute the following steps exactly using your Bash tool:

1. Ensure the coding discussions directory exists:
   ```bash
   mkdir -p discussions/coding
   ```
2. Save the full implementation conversation context and decisions to a timestamped file:
   ```bash
   CONTEXT_FILE="discussions/coding/$(date +%Y%m%d_%H%M%S)-coding-context.md"
   cat > "$CONTEXT_FILE" << 'EOF'
   [Insert complete chronological implementation conversation history, chosen approach, file structure decisions, and dependency choices here]
   EOF
   ```
3. Execute the LangGraph pipeline execution script for the coding stage:
   ```bash
   python3 .scripts/langgraph_sdlc.py --stage coding --context "$CONTEXT_FILE"
   ```

## Phase 4. Output Synthesis & Handover
Read the stdout/stderr printed by the Python script.
1. **Summarize Changes:** Outline the files that were created or modified and any key implementation decisions made by the script.
2. **Read Generated Code:** Use your file-reading tool to open the generated target files and verify correctness.
3. **Clear Context:** From this point forward, treat the prior implementation discussion as deprecated noise to optimize current memory constraints.
4. **Trigger Next Stage:** Prompt the user that the coding stage is complete and instruct them on how to proceed.
   _Example message to user:_
   "Code generation complete. All target files have been created or updated. To run tests and verify compliance, run: /testing"
5. CRITICAL: Hold the line here. Do NOT automatically run tests, modify code, or skip ahead to the next stage yourself. Wait for human review and the next explicit command invocation.
