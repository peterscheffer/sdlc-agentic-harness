---
description: Assist user in proceeding through the UI-Design stage of the SDLC pipeline.
---

## Phase 0: Baseline State Initialization
Before interacting with the user, you must establish the project's current state.
1. Use your file-reading tool to open and read the contents of `sdlc/planning/PRD.md` and `sdlc/architecture/ARCH.md`.
2. Absorb the functional requirements, architectural decisions, and technical constraints already documented.
3. Do **NOT** re-interview the user on information already captured in prior artefacts.

## Phase 1: UI/UX Discovery (Dynamic Questioning)
Your objective is to interview the user to gather the visual and interaction design requirements necessary to produce a UI design specification.

* **Goal:** Collect sufficient detail to produce a wireframe-level UI design document.
* **Execution:** Ask **one or two targeted questions at a time**. Do not overwhelm the user.
* **Scope:** Focus on visual and interaction design choices:
  * **Visual Style:** Colour palette, typography, spacing, branding guidelines, dark/light mode preference.
  * **Layout:** Page structure, navigation patterns, responsive breakpoints, mobile vs desktop priority.
  * **Components:** Component library (Material, Shadcn, custom), form patterns, data display (tables, cards, charts).
  * **User Flow:** Key user journeys, error states, loading states, empty states.

## Phase 2: The Gate (Validation)
Iterate on the design questions until you have a clear UI direction. Do **NOT** proceed to the bash commands in Phase 3 until you explicitly meet this condition:
* You have a coherent UI/UX direction **AND** the user explicitly indicates they are ready to process it (e.g., "I'm ready", "Run the script", "Generate the design").

## Phase 3: Context Export & Script Execution
Once the gate in Phase 2 is passed, execute the following steps exactly using your Bash tool:

1. Ensure the ui-design discussions directory exists:
   ```bash
   mkdir -p discussions/ui-design
   ```
2. Save the full UI/UX conversation context and decisions to a timestamped file:
   ```bash
   CONTEXT_FILE="discussions/ui-design/$(date +%Y%m%d_%H%M%S)-ui-design-context.md"
   cat > "$CONTEXT_FILE" << 'EOF'
   [Insert complete chronological UI/UX conversation history, chosen design direction, layout decisions, and component preferences here]
   EOF
   ```
3. Execute the LangGraph pipeline execution script for the ui-design stage:
   ```bash
   python3 .scripts/langgraph_sdlc.py --stage ui-design --context "$CONTEXT_FILE"
   ```

## Phase 4. Output Synthesis & Handover
Read the stdout/stderr printed by the Python script.
1. **Summarize Changes:** Outline the UI design artefacts generated — DESIGN.md sections, wireframes, or component specifications.
2. **Read Generated Artefacts:** Use your file-reading tool to open `sdlc/ui-design/DESIGN.md` to prepare for the next stage.
3. **Clear Context:** From this point forward, treat the prior UI/UX discussion as deprecated noise to optimize current memory constraints.
4. **Trigger Next Stage:** Prompt the user that the ui-design stage is complete and instruct them on how to proceed.
   _Example message to user:_
   "UI design specification generated. To begin the Requirements stage with the design and architecture baseline, run: /requirements"
5. CRITICAL: Hold the line here. Do NOT automatically begin generating code, components, or UI mockups yourself. Wait for human review and the next explicit command invocation.
