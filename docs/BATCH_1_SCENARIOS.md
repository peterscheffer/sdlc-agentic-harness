# Batch 1: SDLC Pipeline Stages 1–3 & State Management
## Cucumber Scenarios for AI Builder

---

## Feature 1: Pipeline State Management

```gherkin
Feature: Pipeline State Persistence and Resumption
  As a solo developer
  I want my pipeline state to survive terminal restarts and context wipes
  So that I can resume work without losing progress

  Background:
    Given the project has a valid sdlc.config.json
    And the project has a valid .gitignore with .sdlc_state.json listed
    And no .sdlc_state.json exists yet

  Scenario: Initialize fresh pipeline on first /sdlc command
    When I run "/sdlc planning 'add user authentication'"
    Then a new .sdlc_state.json file is created
    And the file contains:
      | field | value |
      | pipeline_id | <a valid UUID> |
      | intent | add user authentication |
      | current_stage | planning |
      | started_at | <ISO 8601 timestamp> |
    And the file is valid JSON matching the sdlc-state/v1 schema

  Scenario: Persist state to .sdlc_state.json after planning stage completes
    Given I have run "/sdlc planning 'add user auth'" and it completed successfully
    And sdlc/planning/PRD.md exists
    When I examine .sdlc_state.json
    Then the state contains:
      | field | value |
      | current_stage | planning |
      | completed_stages | ["planning"] |
      | stages.planning.status | complete |
      | stages.planning.artefact | sdlc/planning/PRD.md |
      | stages.planning.gate_results.prd_exists | true |

  Scenario: Resume pipeline after terminal restart
    Given I have completed the planning stage with .sdlc_state.json written
    And I close my terminal and open a new one
    When I run "/sdlc architecture"
    Then the pipeline reads .sdlc_state.json and resumes from the last completed stage
    And a new ARCH.md is generated using the existing PRD.md

  Scenario: Reject stage invocation out of order
    Given .sdlc_state.json shows current_stage = "planning" and completed_stages = ["planning"]
    When I run "/sdlc testing"
    Then the command fails with error:
      """
      Error: Cannot advance to testing. Completed stages: [planning]. 
      Expected next stage: ui-design or architecture.
      """
    And .sdlc_state.json is not modified

  Scenario: Reset pipeline state on /sdlc reset with confirmation
    Given .sdlc_state.json exists with completed_stages = ["planning", "architecture"]
    When I run "/sdlc reset"
    Then the CLI prompts:
      """
      This will clear all pipeline state. Existing sdlc/ artefacts will not be deleted.
      Are you sure? (yes/no)
      """
    And I type "yes"
    Then .sdlc_state.json is deleted (or reset to empty)
    And the next "/sdlc planning" command starts a fresh pipeline_id

  Scenario: Cancel reset on /sdlc reset without confirmation
    Given .sdlc_state.json exists
    When I run "/sdlc reset"
    And I type "no"
    Then .sdlc_state.json is unchanged
    And the pipeline continues in its current state

  Scenario: Retrieve current pipeline status with /sdlc status
    Given .sdlc_state.json shows current_stage = "architecture"
    When I run "/sdlc status"
    Then the output displays:
      """
      Pipeline ID: <uuid>
      Intent: <original intent>
      Current Stage: architecture
      Completed Stages: [planning]
      """
    And the output is human-readable but parseable

  Scenario: Allow developer to view state file location
    When I run "/sdlc status"
    Then the output includes:
      """
      State file: .sdlc_state.json
      """
```

---

## Feature 2: Planning Stage

```gherkin
Feature: Planning Stage – PRD Generation and Validation
  As the SDLC pipeline
  I want to parse developer intent and generate a structured PRD
  So that all subsequent stages have clear requirements

  Background:
    Given the project has a valid sdlc.config.json with default planning model configured
    And PRINCIPLES.md exists (or is absent, both cases covered)
    And the planning model is available and responding

  Scenario: Generate PRD.md from developer intent
    Given no .sdlc_state.json exists (fresh pipeline)
    When I run "/sdlc planning 'implement JWT-based authentication'"
    Then the planning stage executes
    And sdlc/planning/PRD.md is created
    And the file contains at least 100 words of structured content
    And the planning stage halts (does not advance to next stage automatically)

  Scenario: PRD.md contains all required sections
    Given planning stage has executed and sdlc/planning/PRD.md exists
    When I examine the PRD.md file
    Then it contains these H2 headings in order:
      | heading |
      | ## Summary |
      | ## Goals |
      | ## Non-Goals |
      | ## Tasks |
      | ## Acceptance Criteria |
      | ## Affected Files |

  Scenario: PRD.md has at least one task defined
    Given sdlc/planning/PRD.md has been generated
    When I check the Tasks section
    Then at least one checkbox task is defined:
      """
      - [ ] <task description>
      """

  Scenario: Planning gate check: PRD.md exists
    Given planning stage has executed
    When gate checks run
    Then the gate check "prd_exists" returns true
    And the check is recorded in .sdlc_state.json at stages.planning.gate_results.prd_exists

  Scenario: Planning gate check: PRD.md schema is valid
    Given sdlc/planning/PRD.md exists
    When gate checks run
    Then the schema validator checks for all required H2 headings
    And the gate check "prd_schema_valid" returns true
    And the check is recorded in .sdlc_state.json

  Scenario: Planning gate check: at least one task is defined
    Given sdlc/planning/PRD.md exists
    When gate checks run
    Then the validator scans the Tasks section for at least one checkbox
    And the gate check "tasks_defined" returns true

  Scenario: Fail planning stage if PRD.md is not generated
    Given the planning model fails to respond or times out after 3 retries
    When the planning stage executes
    Then the stage fails with error message:
      """
      Planning stage failed: PRD.md was not generated.
      Retry with: /sdlc planning '<intent>'
      """
    And .sdlc_state.json.stages.planning.status = "failed"
    And current_stage remains "planning"

  Scenario: Fail planning gate if PRD.md lacks required sections
    Given sdlc/planning/PRD.md exists but is missing the "## Tasks" section
    When gate checks run
    Then the gate check "prd_schema_valid" returns false
    And the stage fails with error:
      """
      PRD.md is missing required section: ## Tasks
      """

  Scenario: Fail planning gate if no tasks are defined
    Given sdlc/planning/PRD.md exists with a Tasks section but no checkbox items
    When gate checks run
    Then the gate check "tasks_defined" returns false
    And the stage fails with error:
      """
      PRD.md contains no tasks. At least one task is required.
      """

  Scenario: Update .sdlc_state.json on successful planning completion
    Given planning stage has passed all gate checks
    When the stage completes
    Then .sdlc_state.json is updated:
      | field | value |
      | stages.planning.status | complete |
      | stages.planning.completed_at | <ISO 8601 timestamp> |
      | stages.planning.artefact | sdlc/planning/PRD.md |
      | stages.planning.gate_results.prd_exists | true |
      | stages.planning.gate_results.prd_schema_valid | true |
      | stages.planning.gate_results.tasks_defined | true |
      | completed_stages | ["planning"] |

  Scenario: Display gate check results to developer
    Given planning stage has completed
    When the OpenCode command finishes
    Then the output displays:
      """
      [planning] ✓ PRD.md written to sdlc/planning/PRD.md
      [planning] ✓ Gate checks passed (3/3)
      Review sdlc/planning/PRD.md, then run: /sdlc ui-design  (or /sdlc architecture to skip UI)
      """

  Scenario: Log all LLM calls for auditability
    Given planning stage executes
    When the LangGraph planning node calls the LLM
    Then the request and response are logged to sdlc/logs/planning_<timestamp>.log
    And the log file is human-readable and includes: timestamp, model name, prompt tokens, completion tokens

  Scenario: No API keys or secrets are logged
    Given planning stage logs an LLM call
    When I examine sdlc/logs/planning_<timestamp>.log
    Then no API keys, auth tokens, or sensitive credentials appear in the file
```

---

## Feature 3: UI Design Stage (Optional)

```gherkin
Feature: UI Design Stage – Optional Stitch DESIGN.md Generation
  As the SDLC pipeline
  I want to optionally generate a DESIGN.md spec for UI changes
  So that the architecture stage has clear component requirements

  Background:
    Given the project has a valid sdlc.config.json with ui-design model configured
    And sdlc/planning/PRD.md has been generated and passed gate checks
    And the ui-design model is available

  Scenario: Skip ui-design automatically if PRD has no UI keywords
    Given sdlc/planning/PRD.md contains no mentions of: component, page, view, screen, UI, frontend, form, modal, layout
    When I run "/sdlc architecture"
    Then the ui-design stage is automatically skipped
    And .sdlc_state.json.stages.ui-design.status = "skipped"
    And .sdlc_state.json.stages.ui-design.reason = "No UI keywords found in PRD"

  Scenario: Automatically run ui-design if PRD contains UI keywords
    Given sdlc/planning/PRD.md contains "Add a new dashboard component"
    When I run "/sdlc ui-design"
    Then the ui-design stage executes
    And sdlc/ui-design/DESIGN.md is generated

  Scenario: Generate DESIGN.md conforming to Google Stitch specification
    Given the ui-design stage has executed
    When I examine sdlc/ui-design/DESIGN.md
    Then the file conforms to the Google Stitch DESIGN.md specification
    And the file is valid Markdown with proper heading structure

  Scenario: DESIGN.md contains required Stitch sections
    Given sdlc/ui-design/DESIGN.md exists
    When gate checks run
    Then the file contains these required H2 sections:
      | section |
      | ## Overview |
      | ## Components or ## Screens |
    And at least one of Components or Screens is present

  Scenario: UI design gate check: DESIGN.md exists
    Given ui-design stage has executed
    When gate checks run
    Then the gate check "design_md_exists" returns true
    And the check is recorded in .sdlc_state.json.stages.ui-design.gate_results

  Scenario: UI design gate check: DESIGN.md schema is valid
    Given sdlc/ui-design/DESIGN.md exists
    When gate checks run
    Then the schema validator checks for required Stitch sections
    And the gate check "design_schema_valid" returns true

  Scenario: Fail ui-design gate if DESIGN.md is missing
    Given the ui-design model fails to generate a file
    When gate checks run
    Then the stage fails with error:
      """
      UI Design stage failed: DESIGN.md was not generated.
      Retry with: /sdlc ui-design
      """

  Scenario: Fail ui-design gate if DESIGN.md lacks required sections
    Given sdlc/ui-design/DESIGN.md exists but is missing "## Components"
    When gate checks run
    Then the stage fails with error:
      """
      DESIGN.md is missing required Stitch section: ## Components or ## Screens
      """

  Scenario: Developer can force-skip ui-design
    Given sdlc/planning/PRD.md contains UI keywords
    When I run "/sdlc architecture"
    Then the ui-design stage is skipped
    And .sdlc_state.json.stages.ui-design.status = "skipped"
    And .sdlc_state.json.stages.ui-design.reason = "Skipped by developer"

  Scenario: Developer can force-run ui-design
    Given sdlc/planning/PRD.md contains NO UI keywords
    When I run "/sdlc ui-design"
    Then the ui-design stage executes
    And DESIGN.md is generated regardless of PRD content

  Scenario: Update .sdlc_state.json on successful ui-design completion
    Given ui-design stage has passed all gate checks
    When the stage completes
    Then .sdlc_state.json is updated:
      | field | value |
      | stages.ui-design.status | complete |
      | stages.ui-design.completed_at | <ISO 8601 timestamp> |
      | stages.ui-design.artefact | sdlc/ui-design/DESIGN.md |
      | stages.ui-design.gate_results.design_md_exists | true |
      | stages.ui-design.gate_results.design_schema_valid | true |

  Scenario: Display ui-design completion to developer
    Given ui-design stage has completed successfully
    When the OpenCode command finishes
    Then the output displays:
      """
      [ui-design] ✓ DESIGN.md written to sdlc/ui-design/DESIGN.md
      [ui-design] ✓ Gate checks passed (2/2)
      To proceed with architecture, run: /sdlc architecture
      """
```

---

## Feature 4: Architecture Stage

```gherkin
Feature: Architecture Stage – Design Review and PRINCIPLES Validation
  As the SDLC pipeline
  I want to generate an architecture spec and validate it against project guardrails
  So that code generation follows the project's rules consistently

  Background:
    Given sdlc/planning/PRD.md has been generated and passed gate checks
    And PRINCIPLES.md exists at the project root (or is absent, both valid)
    And the project has a valid sdlc.config.json with architecture model configured
    And the architecture model is available

  Scenario: Generate ARCH.md from PRD and prior stages
    Given I have completed the planning stage
    When I run "/sdlc architecture"
    Then the architecture stage executes
    And sdlc/architecture/ARCH.md is generated
    And the file references the PRD intent and requirements

  Scenario: ARCH.md contains all required sections
    Given sdlc/architecture/ARCH.md exists
    When I examine the file structure
    Then it contains these H2 headings in order:
      | heading |
      | ## Overview |
      | ## Target Files |
      | ## Design Decisions |
      | ## PRINCIPLES Compliance |
      | ## Risks |

  Scenario: ARCH.md Target Files section lists files with actions
    Given sdlc/architecture/ARCH.md has been generated
    When I examine the Target Files section
    Then it contains a table with columns: File, Action, Description
    And each row specifies CREATE, MODIFY, or DELETE as the action
    And at least one target file is listed

  Scenario: Validate ARCH.md against PRINCIPLES.md rules
    Given PRINCIPLES.md exists with at least one rule
    And sdlc/architecture/ARCH.md has been generated
    When the architecture validator runs
    Then it checks each rule in PRINCIPLES.md against ARCH.md and target files
    And a "PRINCIPLES Compliance" table is added to ARCH.md
    And each rule shows status: PASS, WARN, or FAIL

  Scenario: Pass architecture gate if only warning-severity PRINCIPLES violations
    Given PRINCIPLES.md contains a rule with severity: warning
    And the architecture violates that rule
    When gate checks run
    Then the gate check passes
    And the violation is recorded in ARCH.md with status WARN
    And the stage does not fail

  Scenario: Fail architecture gate if any error-severity PRINCIPLES violations
    Given PRINCIPLES.md contains a rule with severity: error
    And the architecture violates that rule
    When gate checks run
    Then the gate check fails
    And the stage fails with error:
      """
      Architecture violates PRINCIPLES.md rule: <rule_id>
      <rule description>
      """
    And .sdlc_state.json.stages.architecture.status = "failed"

  Scenario: Architecture gate check: ARCH.md exists
    Given architecture stage has executed
    When gate checks run
    Then the gate check "arch_exists" returns true
    And the check is recorded in .sdlc_state.json.stages.architecture.gate_results

  Scenario: Architecture gate check: ARCH.md schema is valid
    Given sdlc/architecture/ARCH.md exists
    When gate checks run
    Then the schema validator checks for all required H2 headings
    And the gate check "arch_schema_valid" returns true

  Scenario: Architecture gate check: zero error-severity PRINCIPLES violations
    Given PRINCIPLES.md exists with error-severity rules
    When gate checks run
    Then the validator counts PRINCIPLES violations by severity
    And the gate check "principles_errors_zero" returns true only if error count = 0
    And false otherwise

  Scenario: Fail architecture stage if ARCH.md is not generated
    Given the architecture model fails to respond after 3 retries
    When the architecture stage executes
    Then the stage fails with error:
      """
      Architecture stage failed: ARCH.md was not generated.
      Retry with: /sdlc architecture
      """

  Scenario: Fail architecture gate if ARCH.md lacks required sections
    Given sdlc/architecture/ARCH.md exists but is missing "## Design Decisions"
    When gate checks run
    Then the stage fails with error:
      """
      ARCH.md is missing required section: ## Design Decisions
      """

  Scenario: Handle missing PRINCIPLES.md gracefully
    Given no PRINCIPLES.md file exists
    When the architecture stage executes
    Then a warning is logged:
      """
      Warning: PRINCIPLES.md not found. Skipping PRINCIPLES compliance checks.
      """
    And the PRINCIPLES Compliance section of ARCH.md states:
      """
      No PRINCIPLES.md found. Compliance checks skipped.
      """
    And the stage does not fail; gate checks pass

  Scenario: Update .sdlc_state.json on successful architecture completion
    Given architecture stage has passed all gate checks
    When the stage completes
    Then .sdlc_state.json is updated:
      | field | value |
      | stages.architecture.status | complete |
      | stages.architecture.completed_at | <ISO 8601 timestamp> |
      | stages.architecture.artefact | sdlc/architecture/ARCH.md |
      | stages.architecture.gate_results.arch_exists | true |
      | stages.architecture.gate_results.arch_schema_valid | true |
      | stages.architecture.gate_results.principles_errors_zero | true |
      | completed_stages | ["planning", "architecture"] or ["planning", "ui-design", "architecture"] |

  Scenario: Display architecture completion to developer
    Given architecture stage has completed successfully
    When the OpenCode command finishes
    Then the output displays:
      """
      [architecture] ✓ ARCH.md written to sdlc/architecture/ARCH.md
      [architecture] ✓ Gate checks passed (3/3)
      Review sdlc/architecture/ARCH.md, then run: /sdlc coding
      """

  Scenario: Display architecture violations (warning or error) clearly
    Given architecture stage has completed with PRINCIPLES violations
    When the OpenCode command finishes
    Then the output includes a summary:
      """
      [architecture] ⚠ PRINCIPLES violations detected:
      - ARCH-001: Hexagonal layers respected [WARN]
      - QUAL-002: All exports typed [ERROR]
      """
    And if any ERRORs are present, the stage fails

  Scenario: Log all LLM calls for auditability
    Given architecture stage executes
    When the LangGraph architecture node calls the LLM
    Then the request and response are logged to sdlc/logs/architecture_<timestamp>.log
    And the log includes: timestamp, model name, token counts, PRINCIPLES rules checked
```

---

## Summary of Batch 1 Coverage

**Total Scenarios: 57**

| Feature | Scenario Count | Key Coverage |
|---------|---|---|
| Pipeline State Management | 10 | Init, persist, resume, reset, status, out-of-order rejection |
| Planning Stage | 14 | PRD generation, all 3 gate checks, failures, logging |
| UI Design Stage | 14 | Optional skipping, keyword detection, Stitch schema, gate checks |
| Architecture Stage | 19 | ARCH.md generation, PRINCIPLES validation, error/warning severity handling |

**Batch 1 Completeness:**
- ✅ All state management scenarios (init, persist, resume, reset)
- ✅ All planning stage scenarios (happy path, all gate checks, failures)
- ✅ All ui-design stage scenarios (optional logic, keyword detection, schema validation)
- ✅ All architecture stage scenarios (ARCH.md generation, PRINCIPLES validation, error handling)
- ✅ Logging and auditability for Batch 1 stages
- ✅ Developer-facing output and error messages
- ✅ Edge cases: missing files, schema violations, PRINCIPLES violations

**Ready for Batch 2?** Batch 2 will cover:
- Coding Stage (Ralph loop with iteration, context clearing, max iterations)
- Testing Stage (test execution, coverage checks)
- Error handling and retry logic across all stages

*End of Batch 1.*
