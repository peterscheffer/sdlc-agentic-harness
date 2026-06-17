# Batch 3: SDLC Pipeline Stages 6–7 & Cross-Stage Workflows
## Cucumber Scenarios for AI Builder

---

## Feature 9: Review Stage – Self-Review and Recommendation

```gherkin
Feature: Review Stage – Structured Self-Review Before PR Submission
  As the SDLC pipeline
  I want to perform a comprehensive self-review of all changes
  So that the PR is well-justified and human-readable before submission

  Background:
    Given sdlc/planning/PRD.md exists and is passed
    Given sdlc/architecture/ARCH.md exists and is passed
    Given the coding stage has generated changes and passed
    Given the testing stage has run and passed
    And the review model is configured in sdlc.config.json
    And git is initialized and tracking files

  Scenario: Review stage computes git diff
    Given the coding stage has committed or modified files
    When the review stage executes
    Then it generates a git diff scoped to the current branch
    And the diff excludes sdlc/ artefacts (optional) or includes them for reference
    And the diff is captured into the review context

  Scenario: Review stage generates REVIEW.md
    Given all prior stages have completed
    When the review stage executes
    Then sdlc/review/REVIEW.md is created
    And the file includes all required sections per §9.4 of the PRD

  Scenario: REVIEW.md Change Summary section
    Given git diff has been computed
    When REVIEW.md is generated
    Then the "## Change Summary" section includes:
      - List of files modified (from git diff)
      - Number of lines added/removed
      - Description of logical changes

  Scenario: REVIEW.md PRD Alignment section
    Given sdlc/planning/PRD.md lists tasks and acceptance criteria
    When REVIEW.md is generated
    Then the "## PRD Alignment" section checks:
      - [ ] Task 1 from PRD addressed?
      - [ ] Task 2 from PRD addressed?
      - [ ] All acceptance criteria met?
    And each is marked PASS or FAIL

  Scenario: REVIEW.md PRINCIPLES Compliance section
    Given PRINCIPLES.md exists and has been checked during architecture
    When REVIEW.md is generated
    Then the "## PRINCIPLES Compliance" section lists:
      - All rules that were validated
      - Status: PASS, WARN, or FAIL
      - Any violations found in final code (with file:line references)

  Scenario: REVIEW.md Test Evidence section
    Given sdlc/testing/TEST_REPORT.md exists
    When REVIEW.md is generated
    Then the "## Test Evidence" section summarizes:
      - Number of tests passed/failed
      - Coverage percentage (if applicable)
      - Any failing tests or coverage shortfalls

  Scenario: REVIEW.md Recommendation section
    Given all prior sections have been completed
    When the LLM finalizes REVIEW.md
    Then a "## Recommendation" section is added with:
      - recommendation: PASS or FAIL (literal value)
      - Justification (1-2 sentences)

  Scenario: Recommendation is PASS when all checks are healthy
    Given:
      - PRD alignment: all tasks addressed
      - PRINCIPLES: no error violations
      - Test evidence: all tests passing, coverage ≥ threshold
    When the LLM evaluates
    Then the recommendation is PASS
    And the justification is positive

  Scenario: Recommendation is FAIL when significant issues detected
    Given:
      - PRD alignment: critical task not addressed
      - OR PRINCIPLES: error-severity violation
      - OR test evidence: tests failing or coverage below threshold
    When the LLM evaluates
    Then the recommendation is FAIL
    And the justification cites the issue(s)

  Scenario: Review gate check: REVIEW.md exists
    Given the review stage has executed
    When gate checks run
    Then the gate check "review_exists" = (sdlc/review/REVIEW.md exists)

  Scenario: Review gate check: recommendation field is present
    Given sdlc/review/REVIEW.md exists
    When gate checks run
    Then the parser searches for the line: "recommendation: PASS" or "recommendation: FAIL"
    And the gate check "recommendation_present" returns true only if found

  Scenario: Update .sdlc_state.json on review completion
    Given the review stage has completed
    When gate checks pass
    Then .sdlc_state.json is updated:
      | field | value |
      | stages.review.status | complete |
      | stages.review.completed_at | <ISO 8601 timestamp> |
      | stages.review.artefact | sdlc/review/REVIEW.md |
      | stages.review.recommendation | PASS or FAIL |
      | stages.review.gate_results.review_exists | true |
      | stages.review.gate_results.recommendation_present | true |
      | completed_stages | [..., "review"] |

  Scenario: Display review completion to developer
    Given the review stage has completed successfully
    When the OpenCode command finishes
    Then the output displays:
      """
      [review] ✓ REVIEW.md generated at sdlc/review/REVIEW.md
      [review] ✓ Recommendation: PASS
      [review] ✓ Gate checks passed (2/2)
      Ready to submit PR. Run: /sdlc pr
      """

  Scenario: Display review with FAIL recommendation to developer
    Given the review stage has completed with recommendation: FAIL
    When the OpenCode command finishes
    Then the output displays:
      """
      [review] ✓ REVIEW.md generated at sdlc/review/REVIEW.md
      [review] ⚠ Recommendation: FAIL
      [review] Reason: <reason from REVIEW.md>
      To override and submit PR anyway: /sdlc pr --force
      To re-enter coding: /sdlc coding
      """

  Scenario: Developer can review REVIEW.md before PR
    Given the review stage has completed
    When the developer examines sdlc/review/REVIEW.md
    Then they can see:
      - All changes summarized
      - PRD alignment check
      - PRINCIPLES compliance
      - Test evidence
      - Recommendation and rationale

  Scenario: Developer can reject review and loop back to coding
    Given the review stage has completed with recommendation: FAIL
    And the developer has read REVIEW.md
    When the developer runs "/sdlc coding"
    Then the coding loop is re-entered
    And the LLM is given REVIEW.md as context (showing what was wrong)
    And .sdlc_state.json.current_stage = "coding"

  Scenario: Developer can re-enter coding to fix issues flagged in review
    Given REVIEW.md shows: "PRD task 'add email validation' not addressed"
    When the developer runs "/sdlc coding"
    Then the prompt to the LLM includes the review feedback
    And the developer's manual edits (if any) are preserved
    And the coding loop runs again from iteration 1

  Scenario: Log all LLM calls in review stage
    Given the review stage executes
    When the LLM generates REVIEW.md
    Then sdlc/logs/review_<timestamp>.log is created
    And the log includes:
      - Prompt context (prior artefacts and git diff)
      - Full response (REVIEW.md content)
      - Token counts
```

---

## Feature 10: PR Submission Stage

```gherkin
Feature: PR Submission – GitHub PR Creation and Artefact Linking
  As the SDLC pipeline
  I want to create a structured GitHub PR with all artefacts linked
  So that the PR is traceable, reviewable, and well-documented

  Background:
    Given all prior stages have completed successfully
    Given sdlc/review/REVIEW.md has recommendation field
    And sdlc.config.json.github.base_branch is set (e.g., "main")
    And the current git branch is NOT the base branch
    And the `gh` CLI is installed and authenticated

  Scenario: PR stage checks gh CLI authentication
    Given I have run "/sdlc pr"
    When the PR stage executes
    Then it runs: gh auth status
    And verifies the exit code is 0

  Scenario: PR stage fails if gh CLI not authenticated
    Given gh auth status returns exit code 1 (not authenticated)
    When the PR stage executes
    Then the stage fails with error:
      """
      Error: GitHub CLI (gh) is not authenticated.
      Run: gh auth login
      Then retry: /sdlc pr
      """
    And .sdlc_state.json.stages.pr.status = "failed"

  Scenario: PR stage checks current branch is not base branch
    Given the current git branch is "main" (the base branch)
    When the PR stage checks
    Then the validation fails
    And the stage fails with error:
      """
      Error: Current branch is main (the base branch).
      Create a feature branch and push changes to it first.
      """

  Scenario: PR stage commits sdlc/ artefacts
    Given the review stage has completed
    When the PR stage executes
    Then it stages all files in sdlc/:
      - sdlc/planning/PRD.md
      - sdlc/architecture/ARCH.md
      - sdlc/review/REVIEW.md
      - sdlc/testing/TEST_REPORT.md
      - sdlc/logs/* (optional)
    And commits them with message:
      """
      chore: add SDLC pipeline artefacts
      
      Pipeline ID: <uuid>
      Stages completed: [planning, architecture, coding, testing, review]
      """

  Scenario: PR stage constructs PR title
    Given sdlc/planning/PRD.md contains: "Add user authentication with JWT"
    When the PR stage prepares the PR
    Then the PR title is constructed as:
      """
      feat: Add user authentication with JWT
      """

  Scenario: PR stage constructs PR body from REVIEW.md
    Given sdlc/review/REVIEW.md exists
    When the PR stage constructs the body
    Then the body follows the schema in §9.5 of the PRD:
      - ## Summary (from PRD first paragraph)
      - ## Changes (from REVIEW.md Change Summary)
      - ## Test Evidence (from TEST_REPORT.md)
      - ## Review Outcome (from REVIEW.md recommendation)
      - ## Pipeline Artefacts (links to all artefacts)

  Scenario: PR stage includes links to all artefacts
    Given all artefacts have been generated
    When the PR body is constructed
    Then it includes markdown links:
      """
      ## Pipeline Artefacts
      - [PRD](sdlc/planning/PRD.md)
      - [Architecture](sdlc/architecture/ARCH.md)
      - [Review](sdlc/review/REVIEW.md)
      - [Test Report](sdlc/testing/TEST_REPORT.md)
      """

  Scenario: PR stage creates PR using gh CLI
    Given all PR preparation is complete
    When the PR stage executes
    Then it runs:
      """
      gh pr create \
        --title "feat: ..." \
        --body "..." \
        --base main
      """
    And the command is executed in the project root

  Scenario: PR stage captures PR URL on success
    Given gh pr create exits with code 0
    When the command completes
    Then the response includes a PR URL like:
      """
      https://github.com/owner/repo/pull/42
      """

  Scenario: PR stage stores PR URL in .sdlc_state.json
    Given gh pr create has succeeded
    When the PR stage completes
    Then .sdlc_state.json is updated:
      | field | value |
      | pr_url | https://github.com/owner/repo/pull/42 |

  Scenario: PR gate check: gh authenticated
    Given the PR stage has executed
    When gate checks run
    Then the gate check "gh_authenticated" returns (gh auth status = 0)

  Scenario: PR gate check: branch not base
    Given the PR stage checks
    When gate checks run
    Then the gate check "not_on_base_branch" returns true

  Scenario: PR gate check: gh pr create succeeded
    Given gh pr create has been executed
    When gate checks run
    Then the gate check "pr_created" returns (gh pr create exit code = 0)

  Scenario: Update .sdlc_state.json on PR submission success
    Given all PR gate checks have passed
    When the PR stage completes
    Then .sdlc_state.json is updated:
      | field | value |
      | stages.pr.status | complete |
      | stages.pr.completed_at | <ISO 8601 timestamp> |
      | pr_url | <GitHub PR URL> |
      | completed_stages | [..., "pr"] |

  Scenario: Update .sdlc_state.json on PR submission failure
    Given any PR gate check has failed
    When the PR stage completes
    Then .sdlc_state.json is updated:
      | field | value |
      | stages.pr.status | failed |
      | current_stage | pr |

  Scenario: Display PR submission success to developer
    Given the PR stage has completed successfully
    When the OpenCode command finishes
    Then the output displays:
      """
      [pr] ✓ Pull Request created
      [pr] URL: https://github.com/owner/repo/pull/42
      [pr] All artefacts committed to sdlc/
      [pr] Pipeline complete!
      """

  Scenario: Display PR submission failure to developer
    Given the PR stage has failed
    When the OpenCode command finishes
    Then the output displays:
      """
      [pr] ✗ PR submission failed
      [pr] Reason: <error message>
      Fix the issue and retry: /sdlc pr
      """

  Scenario: Log PR creation for auditability
    Given the PR stage executes
    When PR creation completes
    Then sdlc/logs/pr_<timestamp>.log is created
    And the log includes:
      - gh CLI version
      - PR title and body
      - Returned PR URL
      - Timestamp of creation
```

---

## Feature 11: Cross-Stage Workflows and Looping

```gherkin
Feature: Cross-Stage Workflows – Looping Back and Override Logic
  As a developer using the pipeline
  I want to loop back to earlier stages for refinement
  So that I can iteratively improve before finalizing the PR

  Background:
    Given the pipeline has progressed to the review stage or beyond

  Scenario: Developer can re-enter coding from review
    Given the review stage has completed with recommendation: FAIL
    And sdlc/review/REVIEW.md cites specific issues
    When the developer runs "/sdlc coding"
    Then:
      - The current_stage in .sdlc_state.json is reset to "coding"
      - The coding loop subgraph is invoked
      - The REVIEW.md is provided as context to the LLM
      - The developer's manual edits (if any) are preserved
      - Iteration counter resets to 1

  Scenario: Developer can re-enter planning from any prior stage
    Given the developer has completed planning and wants to revise
    When the developer runs "/sdlc planning 'new intent'" with a new intent
    Then:
      - A new pipeline_id is generated
      - All prior stage artefacts are preserved (not deleted)
      - .sdlc_state.json is reset
      - The new planning intent is recorded

  Scenario: Developer can force-submit PR despite FAIL recommendation
    Given sdlc/review/REVIEW.md shows recommendation: FAIL
    When the developer runs "/sdlc pr --force"
    Then:
      - The pipeline prompts for confirmation:
        """
        Warning: Review recommendation is FAIL.
        Are you sure you want to submit? (yes/no)
        """
      - If yes: PR is submitted anyway
      - If no: command is cancelled

  Scenario: Force-override requires explicit confirmation
    Given the developer runs "/sdlc pr --force"
    And the confirmation prompt is shown
    When the developer types "no"
    Then:
      - The PR is not submitted
      - .sdlc_state.json is not modified
      - current_stage remains "review"

  Scenario: Force-override succeeds with confirmation
    Given the developer runs "/sdlc pr --force"
    And the confirmation prompt is shown
    When the developer types "yes"
    Then:
      - PR submission proceeds
      - All gate checks run normally
      - PR is created even with FAIL recommendation

  Scenario: Cannot re-enter earlier stages if current stage failed
    Given coding stage has failed after max iterations
    When the developer runs "/sdlc architecture"
    Then the command fails with error:
      """
      Error: Cannot advance. Current stage 'coding' has status 'failed'.
      Retry coding with: /sdlc coding
      """

  Scenario: Can only loop back to stages that have been completed
    Given the pipeline is at the coding stage
    When the developer runs "/sdlc architecture"
    Then the command fails because architecture is a required prerequisite

  Scenario: Looping back preserves git history and prior changes
    Given the developer has committed changes in prior iterations
    When they loop back to coding
    Then:
      - All git history is preserved
      - Prior commits remain in the branch
      - New commits from the coding iteration are appended
```

---

## Feature 12: End-to-End Pipeline Workflows

```gherkin
Feature: End-to-End Pipeline – Happy Path and Common Scenarios
  As a developer
  I want to run a complete SDLC pipeline from intent to PR
  So that I have a structured, auditable record of code changes

  Scenario: Happy path – all stages succeed in sequence
    Given the project has valid configuration files
    When I run:
      1. /sdlc planning "add JWT authentication"
      2. /sdlc ui-design (or skip)
      3. /sdlc architecture
      4. /sdlc coding
      5. /sdlc testing
      6. /sdlc review
      7. /sdlc pr
    Then:
      - Each stage succeeds
      - Gate checks pass for each
      - .sdlc_state.json progresses through all stages
      - A GitHub PR is created with all artefacts
      - Developer output is clear and actionable

  Scenario: Happy path – ui-design is skipped automatically
    Given sdlc/planning/PRD.md contains no UI keywords
    When I run "/sdlc architecture"
    Then:
      - ui-design is skipped automatically
      - architecture stage executes immediately after planning
      - .sdlc_state.json shows ui-design.status = "skipped"

  Scenario: Happy path with manual loops
    Given the review stage shows FAIL recommendation
    When I:
      1. Review sdlc/review/REVIEW.md
      2. Run "/sdlc coding" to address issues
      3. Fix issues in 2 iterations
      4. Run "/sdlc testing" (tests now pass)
      5. Run "/sdlc review" (now shows PASS)
      6. Run "/sdlc pr"
    Then:
      - All loops are recorded in .sdlc_state.json
      - Iteration logs show the progression
      - Final PR reflects all changes and reviews

  Scenario: Terminal restart doesn't lose progress
    Given I have completed coding stage
    When I close the terminal and reopen it
    And I run "/sdlc testing"
    Then:
      - The pipeline reads .sdlc_state.json
      - Testing stage executes without re-running coding
      - Progress is resumed from last checkpoint

  Scenario: Developer can view full pipeline status at any time
    Given the pipeline is at any stage
    When I run "/sdlc status"
    Then the output displays:
      """
      Pipeline ID: <uuid>
      Intent: <original intent>
      Current Stage: <stage>
      Completed Stages: [<stages>]
      Status: in_progress
      """

  Scenario: All artefacts are committed to the repository
    Given the pipeline has completed
    When I examine the git log
    Then I can see:
      - A commit for sdlc/ artefacts
      - All artefacts visible in the PR review on GitHub
      - Full audit trail of what was generated

  Scenario: Pipeline is resumable after any failure
    Given coding stage has failed at iteration 3
    When I fix the issue manually and run "/sdlc coding" again
    Then:
      - The loop restarts from iteration 1 with fresh context
      - Prior iterations are logged in ITERATIONS.md
      - Progress continues toward success

  Scenario: No data loss across terminal sessions
    Given I have completed planning and architecture stages
    When I:
      1. Close the terminal (killing the process)
      2. Open a new terminal
      3. Run "/sdlc status"
    Then:
      - .sdlc_state.json is intact
      - All prior artefacts are on disk
      - I can continue with "/sdlc coding"

  Scenario: Clean reset when starting a new feature
    Given I have completed a full pipeline and want to start over
    When I run "/sdlc reset"
    And confirm with "yes"
    Then:
      - .sdlc_state.json is deleted
      - Prior artefacts remain in sdlc/ (not deleted)
      - Next "/sdlc planning" creates a fresh pipeline_id

  Scenario: Full pipeline produces auditable output
    Given a completed pipeline run
    When I examine the sdlc/ directory
    Then it contains:
      | file |
      | sdlc/planning/PRD.md |
      | sdlc/architecture/ARCH.md |
      | sdlc/coding/ITERATIONS.md (if there were iterations) |
      | sdlc/testing/TEST_REPORT.md |
      | sdlc/review/REVIEW.md |
      | sdlc/logs/*.log |
    And the GitHub PR links to all artefacts
    And the PR body is human-readable and complete
```

---

## Feature 13: OpenCode Integration Specifics

```gherkin
Feature: OpenCode Terminal UI Integration
  As a developer using OpenCode
  I want seamless integration with the SDLC pipeline
  So that I can manage the pipeline entirely through slash commands

  Background:
    Given OpenCode is open in the project repository
    And .opencode/commands/sdlc.md is configured

  Scenario: /sdlc slash command is available
    Given I type "/" in OpenCode
    When autocomplete suggestions appear
    Then "sdlc" is available as a command suggestion
    And the description shows:
      """
      Advance the project through the SDLC pipeline
      """

  Scenario: Slash command output is displayed in subtask mode
    Given I run "/sdlc planning 'add auth'"
    When the command executes
    Then:
      - A subtask window opens in OpenCode
      - The LangGraph script output is displayed verbatim
      - The subagent context is isolated
      - On completion, the subtask closes
      - The main chat remains clean

  Scenario: Developer output is clear and actionable
    Given a stage has completed
    When OpenCode displays the result
    Then the output format is:
      """
      [stage_id] ✓ or ✗ <main status message>
      [stage_id] Gate checks: <pass_count>/<total_count>
      [stage_id] Next action: <command to run or error to fix>
      """

  Scenario: Error messages are specific and helpful
    Given a gate check has failed
    When the error is displayed
    Then it includes:
      - What failed (e.g., "linter check")
      - Why it failed (e.g., "TypeScript error on line 12")
      - How to fix it (e.g., "Fix the error and retry")
      - The command to retry (e.g., "/sdlc coding")

  Scenario: Model selection via slash command
    Given sdlc.config.json specifies per-stage models
    When each stage executes
    Then the correct model for that stage is used
    And the model is determined from sdlc.config.json, not from OpenCode's default

  Scenario: Subtask isolation prevents context rot
    Given I have run multiple "/sdlc" commands
    When I examine OpenCode's main chat history
    Then it contains only high-level status updates
    And not the verbose LLM outputs or iteration logs
    And the main context window remains clean and usable

  Scenario: Commands can be run in sequence without context issues
    Given I run:
      1. /sdlc planning "intent"
      2. /sdlc architecture
      3. /sdlc coding
      4. /sdlc testing
    Then:
      - Each command executes in a fresh subtask
      - No context carryover between commands
      - Each reads .sdlc_state.json to understand current state
      - Pipeline progresses cleanly

  Scenario: Developer can examine artefacts between stages
    Given a stage has completed
    When the developer examines the generated file (e.g., sdlc/planning/PRD.md)
    Then:
      - The file is readable markdown
      - It can be edited manually if desired
      - Running the next stage reads the current file state
```

---

## Feature 14: PRINCIPLES.md Integration and Validation

```gherkin
Feature: PRINCIPLES.md Guardrails Enforcement
  As a developer
  I want my project-specific rules enforced across the pipeline
  So that all AI-generated code adheres to my architectural standards

  Background:
    Given PRINCIPLES.md exists at the project root
    And it contains at least one rule with severity: error or warning

  Scenario: PRINCIPLES.md is read during architecture stage
    Given I have run "/sdlc architecture"
    When the architecture node executes
    Then it reads PRINCIPLES.md
    And extracts all rules

  Scenario: Architecture validator checks each rule
    Given PRINCIPLES.md contains: "All exports must be typed"
    When the validator runs
    Then it examines ARCH.md and target files
    And checks if the rule is satisfied

  Scenario: Error-severity violations block architecture gate
    Given PRINCIPLES.md rule ARCH-001 has severity: error
    And the generated architecture violates ARCH-001
    When gate checks run
    Then the stage fails with error:
      """
      Architecture violates PRINCIPLES.md rule: ARCH-001
      <rule description>
      """

  Scenario: Warning-severity violations do not block
    Given PRINCIPLES.md rule QUAL-001 has severity: warning
    And the generated code violates QUAL-001
    When gate checks run
    Then QUAL-001 is listed in ARCH.md with status WARN
    And the stage passes (does not fail)

  Scenario: PRINCIPLES violations are included in review
    Given ARCH.md lists PRINCIPLES violations
    When the review stage generates REVIEW.md
    Then the "## PRINCIPLES Compliance" section includes:
      - All violations from ARCH.md
      - Any additional violations found in final code
      - File and line references for violations

  Scenario: Missing PRINCIPLES.md is handled gracefully
    Given no PRINCIPLES.md file exists
    When the architecture stage executes
    Then:
      - A warning is logged
      - The stage does not fail
      - ARCH.md notes: "PRINCIPLES.md not found"
      - Pipeline continues normally

  Scenario: Invalid PRINCIPLES.md schema is caught
    Given PRINCIPLES.md exists but is malformed
    When the validator tries to parse it
    Then it fails with error:
      """
      PRINCIPLES.md validation failed: <error>
      Ensure all rules follow the schema.
      """

  Scenario: Developer can use PRINCIPLES.md as a reference
    Given PRINCIPLES.md exists
    When the developer examines it
    Then they can see:
      - All project-specific rules
      - Severity levels (error/warning)
      - How to verify each rule
      - Naming conventions and forbidden patterns
```

---

## Summary of Batch 3 Coverage

**Total Scenarios: 89**

| Feature | Scenario Count | Key Coverage |
|---------|---|---|
| Review Stage | 20 | Self-review, git diff, REVIEW.md generation, recommendation |
| PR Submission | 25 | GitHub PR creation, gh CLI validation, artefact linking, success/failure |
| Cross-Stage Workflows | 7 | Looping back, force override, stage prerequisites |
| End-to-End Pipelines | 10 | Happy path, skipping optional stages, terminal restart, clean reset |
| OpenCode Integration | 8 | Slash commands, subtask isolation, output formatting, model selection |
| PRINCIPLES.md Integration | 9 | Rule validation, error/warning severity, missing PRINCIPLES handling |

**Batch 1 + Batch 2 + Batch 3 = 330 total scenarios**

---

## Complete Feature Coverage Summary

| Feature | Stage | Scenarios | Primary Coverage |
|---------|-------|-----------|------------------|
| 1 | State Management | 10 | Init, persist, resume, reset, status, gating |
| 2 | Planning | 14 | PRD generation, schema validation, gate checks |
| 3 | UI Design | 14 | Optional skipping, Stitch schema, gate checks |
| 4 | Architecture | 19 | ARCH.md generation, PRINCIPLES validation |
| 5 | Coding | 44 | Coding loop, iterations, context clearing, gate checks |
| 6 | Testing | 30 | Test execution, coverage, test report, gate checks |
| 7 | Stage Continuation | 5 | Gating, stage ordering, skip prevention |
| 8 | Error Handling | 5 | Retries, timeouts, config validation |
| 9 | Review | 20 | Self-review, REVIEW.md, recommendation logic |
| 10 | PR Submission | 25 | gh CLI, PR creation, artefact linking |
| 11 | Cross-Stage Workflows | 7 | Looping, override, stage prerequisites |
| 12 | End-to-End Pipelines | 10 | Happy path, terminal restart, clean state |
| 13 | OpenCode Integration | 8 | Slash commands, subtask, output formatting |
| 14 | PRINCIPLES.md Integration | 9 | Rule validation, severity handling |
| **TOTAL** | | **330** | Complete SDLC pipeline coverage |

---

## Test Implementation Recommendations for AI Builder

1. **Gherkin Parser:** Use a Gherkin parser library (e.g., Behave for Python, pytest-bdd) to read these .feature files and generate test stubs.

2. **Test Fixtures:** Create fixtures for:
   - Temporary project directories
   - Mock LLM responses
   - Mock git operations
   - Mock gh CLI responses

3. **Mocking Strategy:**
   - Mock the LLM model calls (deterministic responses for testing)
   - Mock git operations (avoid touching real repos)
   - Mock gh CLI (avoid creating real PRs during testing)
   - Real file I/O for state and artefact generation

4. **Test Organization:**
   - One test function per Gherkin scenario
   - Parametrized tests for similar scenarios
   - Fixture setup for common Given conditions

5. **CI/CD Integration:**
   - Run tests on every commit
   - Gate on ≥80% test pass rate
   - Generate test report in JUnit XML for CI visibility

6. **Regression Prevention:**
   - Snapshot tests for artefact generation (PRD.md, ARCH.md, etc.)
   - Golden files for expected outputs
   - State file schema validation tests

---

*End of Batch 3. All 330 scenarios delivered.*

**Next Steps for AI Builder:**
1. Parse all three batch files into your test framework
2. Implement LangGraph nodes and gate checkers
3. Create test fixtures for LLM mocking and file I/O
4. Run tests iteratively as features are implemented
5. Aim for incremental test coverage: Batch 1 (state/planning/ui/arch), then Batch 2 (coding/testing), then Batch 3 (review/pr/workflows)
