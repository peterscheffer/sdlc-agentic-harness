---
description: Assist user in proceeding through the Requirements stage of the SDLC pipeline.
---

## Phase 0: Baseline State Initialization
Before interacting with the user, you must establish the project's current state.
1. Use your file-reading tool to open and read the contents of `sdlc/planning/PRD.md`, `sdlc/architecture/ARCH.md`, and (if present) `sdlc/ui-design/DESIGN.md`.
2. Absorb the high-level product requirements, architectural decisions, and UI design specifications already documented.
3. Do **NOT** re-interview the user on information already captured in prior artefacts.

## Phase 1: Requirements Discovery (Dynamic Questioning)
Your objective is to interview the user to gather fine-grained behavioural, functional, and non-functional requirements that were not fully captured in the PRD or architecture stage.

* **Goal:** Collect sufficient detail to produce Gherkin feature files that serve as executable specifications for coding and testing.
* **Execution:** Ask **one or two targeted questions at a time**. Do not overwhelm the user.
* **Scope:** Drill into specific behaviours and edge cases:
  * **Functional Requirements:** What specific actions must the system perform? What inputs, outputs, and data flows exist for each feature?
  * **Behavioural Requirements:** What happens in edge cases — invalid input, concurrent access, missing data, timeout scenarios?
  * **Non-Functional Requirements:** Are there performance thresholds, scalability expectations, security constraints, or observability requirements not yet documented?
  * **Acceptance Criteria:** For each feature area, what specific conditions must be met for the implementation to be considered complete?

## Phase 2: The Gate (Validation)
Iterate on the requirements until you have a clear, testable specification. Do **NOT** proceed to the bash commands in Phase 3 until you explicitly meet this condition:
* You have documented enough detail to write Gherkin scenarios for each feature area **AND** the user explicitly indicates they are ready to process it (e.g., "I'm ready", "Run the script", "Generate the requirements").

## Phase 3: Context Export & Script Execution
Once the gate in Phase 2 is passed, execute the following steps exactly using your Bash tool:

1. Ensure the requirements discussions directory exists:
   ```bash
   mkdir -p discussions/requirements
   ```
2. Save the full requirements conversation context and decisions to a timestamped file:
   ```bash
   CONTEXT_FILE="discussions/requirements/$(date +%Y%m%d_%H%M%S)-requirements-context.md"
   cat > "$CONTEXT_FILE" << 'EOF'
   [Insert complete chronological requirements conversation history, decisions, and specifications here]
   EOF
   ```
3. Execute the LangGraph pipeline execution script for the requirements stage:
   ```bash
   python3 .scripts/sdlc_harness.py --stage requirements --context "$CONTEXT_FILE"
   ```

## Phase 4. Output Synthesis & Handover
Read the stdout/stderr printed by the Python script.

1. **Summarize Changes:** Outline the requirements artefacts generated — REQUIREMENTS.md sections and Gherkin `.feature` files.
2. **Read Generated Artefacts:** Use your file-reading tool to open `sdlc/requirements/REQUIREMENTS.md` and each `.feature` file under `sdlc/requirements/` to prepare for the next stage.
3. **Clear Context:** From this point forward, treat the prior requirements discussion as deprecated noise to optimize current memory constraints.

## Phase 5. Auto-Accept (Optional)
After the requirements stage completes successfully, ask the user if they would like to auto-accept the LLM's recommendations for the remaining stages.

1. Ask the user:
   _"The requirements stage is complete. Would you like to auto-accept the LLM's recommendations for the remaining stages (coding, testing, review, pr)? This will run all stages autonomously without further manual confirmation. (yes/no)"_

2. If the user agrees:
   a. Inform them the pipeline will now run autonomously through all remaining stages.
   b. Execute:
      ```bash
      python3 .scripts/sdlc_harness.py --stage coding --context "$CONTEXT_FILE" --autopilot
      ```
   c. Monitor the output as each stage (coding, testing, review, pr) runs. If any stage fails, the pipeline will halt and you should report the failure to the user.
   d. After the auto-pilot completes (success or failure), summarize the overall result:
      - If successful: "Pipeline complete! All stages passed. Pull request created at: <URL>"
      - If failed: "Auto-pilot halted at <stage>. Fix the issue and continue manually with the next command."

3. If the user declines:
   a. Trigger the standard handover:
      _"Requirements specification and Gherkin feature files generated. To begin the Coding stage with these requirements as implementation specs, run: /coding"_
   b. CRITICAL: Hold the line here. Do NOT automatically begin generating code or tests yourself. Wait for human review and the next explicit command invocation.
