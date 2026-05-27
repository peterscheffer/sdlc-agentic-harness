---
description: Assist user in proceeding through planning stage of the SDLC pipeline.
---

## Phase 1: High-Level Discovery (Dynamic Questioning)
Your first objective is to interview the user to gather high-level information about the purpose of the software product they want to build. 

* **Goal:** Collect sufficient information and requirements to populate a Product Requirement Document (PRD) to prepare for the ui-design stage or the architecture stage.
* **Execution:** Ask **one or two targeted questions at a time**. Do not overwhelm the user with a massive list. 
* **Scope:** Keep it high-level (core features, target audience, primary pain points, high-level requirements).

## Phase 2: The Gate (Validation)
Iterate on the questions until you have a clear picture. Do **NOT** proceed to the bash commands in Phase 3 until you explicitly meet this condition:
* You have enough information for a first-cut PRD **AND** the user explicitly indicates they are ready to proceed (e.g., "I'm ready", "Run the script", "Let's go").

## Phase 3: Context Export & Script Execution
Once the gate in Phase 2 is passed, execute the following steps exactly using the Bash tool:

1. Ensure the target directory exists:
   ```bash
   mkdir -p discussions
   ```
2. CONTEXT_FILE="discussions/$(date +%Y%m%d_%H%M%S)-planning-context.md"
   ```bash
   cat > "$CONTEXT_FILE" << 'EOF'
   [Insert complete chronological conversation history and synthesized requirements here]
   EOF   
   ```
3. Execute the LangGraph pipeline execution script for the planning stage:
   ```bash
   python3 .scripts/langgraph_sdlc.py --stage planning --context "$CONTEXT_FILE"
   ```

## Phase 4. Output Synthesis & Handover
Read the stdouts/stderr printed by the Python script.
* Summarize the state changes returned by the script.
* Outline the explicit next steps for the developer.
* CRITICAL: Do NOT automatically write code, modify files, or skip ahead to the architecture stage yourself. Hold the line here and wait for human review.

## Phase 4: Output Synthesis & Next Stage Handoff
Read the printed output from the Python script. 

1. Summarize the state changes and next steps for the developer.
2. **Clear Context:** From this point forward, treat the prior conversation history as deprecated noise. 
3. **Pivot Context:** Read the contents of that PRD file using your file-reading tool to prepare for the next stage - 'sdlc/planning/PRD.md'.
4. **Trigger Next Stage:** Prompt the user that the planning stage is complete and explicitly instruct them to run the next command file when they are ready:
   
   *Example message to user:* 
   "Planning context exported and state updated. To begin the architecture stage with the clean PRD baseline, run: `/architecture` or `source .claudecmd/architecture.md`"