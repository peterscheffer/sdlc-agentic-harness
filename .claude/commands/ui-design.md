---
description: Assist user in proceeding through the UI-Design stage of the SDLC pipeline.
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
   python3 .scripts/sdlc_harness.py --stage ui-design --context "$CONTEXT_FILE"
   ```

## Phase 3.5: Stitch Design Retrieval (MCP)
Once the script has written `sdlc/ui-design/DESIGN.md` and its gates passed, materialise the design as Stitch screen exports. These exports are the machine-verifiable UI spec that the coding and testing stages are gated against (via the `stitch-ui` spec profile), so this phase must complete before the pipeline can pass those stages.

1. **Check the Stitch MCP connection** by calling the `mcp__stitch__list_projects` tool. If the call fails (not connected, or an auth error such as "Incompatible auth server"), skip to step 6 (fallback).
2. **Create a Stitch project**: call `mcp__stitch__create_project` with a title from the PRD. Note the returned project ID.
3. **Upload the design spec and build the design system**: base64-encode `sdlc/ui-design/DESIGN.md` (`base64 -i sdlc/ui-design/DESIGN.md`), call `mcp__stitch__upload_design_md`, then immediately call `mcp__stitch__create_design_system_from_design_md` with the returned screen instance. Note the design system asset ID (`mcp__stitch__get_project` / `mcp__stitch__list_design_systems` if needed).
4. **Generate each screen**: for every screen/page listed in DESIGN.md's `## Screens` (or `## Components`) section, call `mcp__stitch__generate_screen_from_text` with that screen's description as the prompt, the design system asset from step 3, and the device type the user chose in Phase 1. These calls take minutes — do not retry on timeout; poll with `mcp__stitch__get_screen` instead.
5. **Persist the exports locally**: for each generated screen, retrieve it with `mcp__stitch__get_screen` and write its generated HTML/code to `sdlc/ui-design/stitch/<screen-slug>/code.html`. Also write `sdlc/ui-design/stitch/manifest.json` recording `{ "projectId": ..., "screens": [{"id": ..., "name": ..., "path": ...}] }` so later stages and re-runs can trace exports back to Stitch.
6. **Fallback (no working Stitch MCP)**: tell the user the Stitch MCP connection is unavailable and that they must either (a) fix the connection (re-authenticate the `stitch` MCP server) and re-run this phase, or (b) design the screens in the Stitch web app from `sdlc/ui-design/DESIGN.md` and manually save each screen's exported `code.html` under `sdlc/ui-design/stitch/<screen-slug>/code.html`. The requirements-stage gate for the `stitch-ui` profile blocks until these exports exist.
7. **Validate the exports deterministically**:
   ```bash
   python3 .scripts/utils/design_tokens.py validate sdlc/ui-design/stitch
   ```
   This must exit 0 (at least one export with an extractable design-token set). If it fails, the exports are incomplete — repeat retrieval before handing over.

## Phase 4. Output Synthesis & Handover
Read the stdout/stderr printed by the Python script.
1. **Summarize Changes:** Outline the UI design artefacts generated — DESIGN.md sections, the Stitch screen exports retrieved into `sdlc/ui-design/stitch/`, and the design-token validation result.
2. **Read Generated Artefacts:** Use your file-reading tool to open `sdlc/ui-design/DESIGN.md` to prepare for the next stage.
3. **Clear Context:** From this point forward, treat the prior UI/UX discussion as deprecated noise to optimize current memory constraints.
4. **Trigger Next Stage:** Prompt the user that the ui-design stage is complete and instruct them on how to proceed.
   _Example message to user:_
   "UI design specification generated. To begin the Requirements stage with the design and architecture baseline, run: /requirements"
5. CRITICAL: Hold the line here. Do NOT automatically begin generating code, components, or UI mockups yourself. Wait for human review and the next explicit command invocation.
