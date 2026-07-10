---
description: Assist user in proceeding through the Requirements stage of the SDLC pipeline.
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
1. Use your file-reading tool to open and read the contents of `sdlc/planning/PRD.md`, `sdlc/architecture/ARCH.md`, and (if present) `sdlc/ui-design/DESIGN.md`.
2. Absorb the high-level product requirements, architectural decisions, and UI design specifications already documented.
3. Do **NOT** re-interview the user on information already captured in prior artefacts.

## Phase 1: Requirements Discovery (Dynamic Questioning)
Your objective is to interview the user to gather fine-grained behavioural, functional, and non-functional requirements that were not fully captured in the PRD or architecture stage.

* **Goal:** Collect sufficient detail to produce machine-verifiable specifications (Gherkin scenarios, enumerated test cases, and/or an OpenAPI contract — depending on the spec profiles chosen in Phase 1.5) that serve as executable specs for coding and testing.
* **Execution:** Ask **one or two targeted questions at a time**. Do not overwhelm the user.
* **Scope:** Drill into specific behaviours and edge cases. The solution may be a UI, a service, an API, an integration, or a data layer — adapt your questions accordingly:
  * **Functional Requirements:** What specific actions must the system perform? What inputs, outputs, and data flows exist for each feature?
  * **Behavioural Requirements:** What happens in edge cases — invalid input, concurrent access, missing data, timeout scenarios?
  * **Non-Functional Requirements:** Are there performance thresholds, scalability expectations, security constraints, or observability requirements not yet documented?
  * **Acceptance Criteria:** For each feature area, what specific conditions must be met for the implementation to be considered complete?
  * **For APIs/integrations:** What endpoints, request/response schemas, status codes, and error contracts are expected?
  * **For data layers:** What schemas, constraints, and data-quality expectations apply?

## Phase 1.5: Spec Profile Recommendation & Toolchain Confirmation
Decide, with the user, HOW the solution will be specified and verified. Verification is deterministic: each spec profile has a code-based verifier that gives an exact pass/fail; the LLM is only used where determinism is impossible.

1. Read the solution classification produced at planning:
   ```bash
   python3 -c "import json,os;s=json.load(open('.sdlc_state.json')) if os.path.exists('.sdlc_state.json') else {};print(json.dumps(s.get('solution_classification')))"
   ```
2. Present the recommended spec profile(s) with a one-sentence best-practice rationale, and explain each profile's verification mechanism:
   * `gherkin-bdd` — Gherkin feature files, executed by a real BDD runner (behave / cucumber-js / cucumber-jvm). Best for user-facing flows and behavioural scenarios.
   * `var-spec` — plain-Markdown "oaths" (no Given/When/Then dialect; claim sentences are matched and verified directly against a stimulus/sensor step), executed by the Vár adapter (pytest-var / var-cli / var-junit). An alternative to `gherkin-bdd` for the same kind of user-facing behavioural scenarios — prefer it when the team wants the spec itself to double as rendered documentation. Note: JVM tooling is less mature (no `var init` CLI yet); default to `gherkin-bdd` on Java/Kotlin projects unless the user asks for `var-spec` specifically.
   * `unit-tests` — requirements enumerated as concrete test cases, run by the project's test framework (pytest / jest / vitest / JUnit). Best for business logic, services, integrations, and data transformations.
   * `openapi-contract` — an OpenAPI document, contract-tested against the running service with schemathesis. Best for REST APIs.
   Multiple profiles can be combined (e.g. a web app with an API: `gherkin-bdd` + `openapi-contract` + `unit-tests`). Don't combine `gherkin-bdd` and `var-spec` in the same run — they cover the same scenarios. All selected profiles must pass for the testing gate to pass.
3. Ask the user to confirm the recommendation or override it. (In auto-accept mode: adopt the recommendation silently.)
4. Detect the project toolchain (inspect `pyproject.toml` / `requirements.txt` / `package.json` / `tsconfig.json` / `pom.xml` / `build.gradle`) and confirm the runner per profile (e.g. behave vs cucumber-js, pytest vs jest vs vitest). (In auto-accept mode: adopt the detected toolchain silently.)
5. If a chosen runner is not installed, tell the user the exact install command (e.g. `pip install behave`, `npm install --save-dev @cucumber/cucumber`) BEFORE running the harness — the coding stage will fail fast without it.

## Phase 2: The Gate (Validation)
Iterate on the requirements until you have a clear, testable specification. Do **NOT** proceed to the bash commands in Phase 3 until you explicitly meet this condition:
* You have documented enough detail to write the selected spec artifacts for each feature area, the spec profiles are confirmed, **AND** the user explicitly indicates they are ready to process it (e.g., "I'm ready", "Run the script", "Generate the requirements").

## Phase 3: Context Export & Script Execution
Once the gate in Phase 2 is passed, execute the following steps exactly using your Bash tool:

1. Ensure the requirements discussions directory exists:
   ```bash
   mkdir -p discussions/requirements
   ```
2. Save the full requirements conversation context and decisions to a timestamped file. The file MUST end with the machine-readable spec-profile footer (exactly these line formats — the harness parses them):
   ```bash
   CONTEXT_FILE="discussions/requirements/$(date +%Y%m%d_%H%M%S)-requirements-context.md"
   cat > "$CONTEXT_FILE" << 'EOF'
   [Insert complete chronological requirements conversation history, decisions, and specifications here]

   SPEC_PROFILES: <comma-separated confirmed profiles, e.g. gherkin-bdd, unit-tests>
   SPEC_TOOLCHAIN: <profile>=<runner>; <profile>=<runner>  (e.g. gherkin-bdd=behave; unit-tests=pytest)
   EOF
   ```
3. Execute the LangGraph pipeline execution script for the requirements stage:
   ```bash
   python3 .scripts/sdlc_harness.py --stage requirements --context "$CONTEXT_FILE"
   ```

## Phase 4. Output Synthesis & Handover
Read the stdout/stderr printed by the Python script.

1. **Summarize Changes:** Outline the requirements artefacts generated — REQUIREMENTS.md sections plus the spec artifacts for each selected profile (`.feature` files, `TEST_CASES.md`, and/or `openapi.yaml` under `sdlc/requirements/`).
2. **Read Generated Artefacts:** Use your file-reading tool to open `sdlc/requirements/REQUIREMENTS.md` and each generated spec artifact under `sdlc/requirements/` to prepare for the next stage.
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
