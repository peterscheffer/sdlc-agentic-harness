---
description: Advance the project through the LangGraph SDLC pipeline.
---

First, save the full conversation context from this session to a timestamped file in the discussions/ directory using the Bash tool:
mkdir -p discussions
CONTEXT_FILE="discussions/$(date +%Y%m%d_%H%M%S)-context.md"
cat > "$CONTEXT_FILE" << 'EOF'
[Write the COMPLETE conversation context here — include ALL user messages, assistant responses, tool calls, reasoning, technical decisions, and requirements from the entire session so far. Be thorough and preserve as much detail as possible.]
EOF

Then use the Bash tool to run this exact command:
python3 .scripts/langgraph_sdlc.py --stage $ARGUMENTS --context "$CONTEXT_FILE"

Then read the printed output and summarize the state changes and next steps for the developer. Do NOT automatically write code or skip ahead to the next stage yourself. Hold the line here and wait for human review.
