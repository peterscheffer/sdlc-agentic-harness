# Product Requirements Document
## [PROJECT_NAME] — [One-line project descriptor]

| Field | Value |
|-------|-------|
| **Version** | 0.1.0-draft |
| **Status** | Draft |
| **Last Updated** | YYYY-MM-DD |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Goals](#3-goals)
4. [Non-Goals](#4-non-goals)
5. [User Persona](#5-user-persona)
6. [System Architecture Overview](#6-system-architecture-overview)
7. [Stage / Feature Definitions](#7-stage--feature-definitions)
8. [External Integrations](#8-external-integrations)
9. [Data Schemas](#9-data-schemas)
10. [Repository Structure](#10-repository-structure)
11. [Technical Stack](#11-technical-stack)
12. [Non-Functional Requirements](#12-non-functional-requirements)
13. [Error Handling](#13-error-handling)
14. [Open Questions](#14-open-questions)

---

## 1. Executive Summary

[2–3 sentences describing what the project is, who it is for, and the core value it delivers. Avoid technical detail here — focus on the "why" and the outcome.]

---

## 2. Problem Statement

[Describe the pain points or gaps this project addresses. Use a short paragraph or bullet list. Be specific: what does the user currently have to do manually, badly, or not at all?]

- [Pain point one]
- [Pain point two]
- [Pain point three]

---

## 3. Goals

| ID | Goal |
|----|------|
| G1 | [Primary goal — what the system must achieve] |
| G2 | [Second goal] |
| G3 | [Third goal] |
| G4 | [Add rows as needed] |

---

## 4. Non-Goals

| ID | Non-Goal |
|----|----------|
| NG1 | [Something explicitly out of scope for this version] |
| NG2 | [Another explicit exclusion] |
| NG3 | [Add rows as needed] |

---

## 5. User Persona

**[Persona Name / Role]**

- [Who they are — job title, context, skill level]
- [What tools or workflows they currently use]
- [What they care about most — outcomes, not features]
- [Any key constraints or preferences, e.g. "no GUI required"]

---

## 6. System Architecture Overview

```
[Insert ASCII diagram or high-level block diagram here]

Example structure to adapt:
┌─────────────────────────┐
│  Entry Point / Interface │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Core Processing Layer   │
└────────────┬────────────┘
             │
   ┌─────────┼─────────┐
   ▼         ▼         ▼
[Output A] [Output B] [Output C]
```

[1–2 sentences explaining how the major components interact and what the data flow looks like.]

---

## 7. Stage / Feature Definitions

### 7.1 Overview

| Order | ID | Required | Output / Artefact |
|-------|----|----------|-------------------|
| 1 | `[stage-or-feature-id]` | Yes / No | `[path/to/output-file or description]` |
| 2 | `[stage-or-feature-id]` | Yes / No | `[path/to/output-file or description]` |
| 3 | `[stage-or-feature-id]` | Yes / No | `[Add rows as needed]` |

[One sentence stating any overarching constraint, e.g. ordering rules, gate requirements, or skip conditions.]

---

### 7.2 [Stage / Feature Name]

**Purpose:** [One sentence stating the job this stage or feature does.]

**Inputs:**
- [Input one — file, user action, data source]
- [Input two]

**Behaviour:**
- [What happens when this stage/feature runs — key logic, LLM calls, subprocess calls, etc.]
- [How it decides it is "done"]

**Gate checks / Completion criteria:**
- [ ] [Check one — e.g. output file exists]
- [ ] [Check two — e.g. command exits with code 0]

**Expected output:**
```
[Optional: example terminal output or return value the developer will see]
```

---

### 7.3 [Stage / Feature Name]

> *(Copy the 7.2 block for each additional stage or feature. Remove this note when done.)*

---

## 8. External Integrations

### 8.1 [Integration Name]

**Purpose:** [Why this integration is needed.]

**Invocation:**
```
[Command, API call, or config snippet showing how the integration is triggered]
```

**Reference / Docs:** [URL or internal doc link]

### 8.2 [Integration Name]

| Command / Action | Description |
|-----------------|-------------|
| `[command one]` | [What it does] |
| `[command two]` | [What it does] |

> *(Add or remove subsections per integration. Remove this note when done.)*

---

## 9. Data Schemas

### 9.1 [Artefact / Document Name] Schema

`[path/to/file]` MUST contain the following sections. [State what validates it — heading detection, JSON schema, Pydantic, etc.]

```markdown
## [Required section one]
[Description of expected content]

## [Required section two]
[Description of expected content]
```

---

### 9.2 [Config / State File] Schema

`[filename]` lives at [location] and [must/should] be [committed / gitignored].

```json
{
  "$schema": "[schema-id/v1]",
  "[field_one]": "<description of value>",
  "[field_two]": "<description of value>",
  "[nested_object]": {
    "[sub_field]": "<description>"
  }
}
```

[Any notes on required fields, forward-compatibility, or fallback behaviour.]

---

### 9.3 [Additional Schema]

> *(Copy 9.1 or 9.2 block for each schema. Remove this note when done.)*

---

## 10. Repository Structure

```
<project-root>/
│
├── [top-level-dir]/
│   └── [file]                    # [Purpose]
│
├── [source-dir]/
│   ├── [file-or-module].py       # [Purpose]
│   └── [subdirectory]/
│       └── [file].py             # [Purpose]
│
├── [output-dir]/                 # [Generated artefacts — committed / gitignored?]
│   └── [subdirectory]/
│
├── [CONFIG_FILE]                 # [Purpose — committed / gitignored?]
└── README.md
```

[Any notes about which files must be committed, gitignored, or excluded from distribution.]

---

## 11. Technical Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| [Component name] | [Library / tool / language] | [Any version constraints or rationale] |
| [Component name] | [Library / tool / language] | [Notes] |
| [Component name] | [Library / tool / language] | [Notes] |
| Runtime | [Language + version] | |
| Distribution | [How it is installed / run] | |

---

## 12. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | [Performance, reliability, or observability requirement] |
| NFR-2 | [Security requirement — e.g. no secrets written to disk] |
| NFR-3 | [Portability or platform support requirement] |
| NFR-4 | [Code quality requirement — e.g. test coverage, type annotations] |
| NFR-5 | [Versioning / distribution requirement] |

---

## 13. Error Handling

| Scenario | Behaviour |
|----------|-----------|
| [Error condition one] | [What the system does — retry, fail fast, warn, prompt user] |
| [Error condition two] | [Behaviour] |
| [Missing required file or config] | [Behaviour] |
| [External command / API failure] | [Behaviour] |
| [Invalid or corrupted state] | [Behaviour] |

---

## 14. Open Questions

| ID | Question | Priority |
|----|----------|----------|
| OQ-1 | **[Topic]** — [The specific question that needs an answer before or after launch.] | High / Medium / Low |
| OQ-2 | **[Topic]** — [Question] | High / Medium / Low |
| OQ-3 | **[Topic]** — [Question] | High / Medium / Low |

---

*End of document. Version [X.Y.Z-draft].*
