# KiCad Component Factory
## Software Architecture Specification

**Status:** Proposed implementation baseline  
**Document version:** 0.1  
**Date:** July 13, 2026  
**Owner:** Garth Benson  
**Primary audience:** Codex and engineers implementing the application  
**Working application name:** KiCad Component Factory (KCF)  
**Target toolchain:** KiCad 10, Python 3.12+, private Git repository

---

## 1. Purpose

KiCad Component Factory is a local-first, Git-centered application that creates, validates, reviews, and releases KiCad library components from engineering source material. A component release consists primarily of a schematic symbol, PCB footprint, optional 3D model association, source evidence, and machine-readable metadata.

The application uses AI for document interpretation and engineering assistance, but it does not allow an AI model to directly author or release arbitrary KiCad files. Model output is treated as untrusted proposed data. Deterministic code converts an approved canonical component specification into KiCad artifacts, and automated plus human validation gates control release.

This document is intended to be sufficiently specific for Codex to implement the first production-quality version without requiring major architectural decisions during coding.

## 2. Goals

The system shall:

- Reduce the time needed to create repetitive KiCad symbols and footprints.
- Preserve the source and reasoning behind every pin, dimension, pad, and model association.
- Produce deterministic and reproducible KiCad library files.
- Use Git as the authoritative release history and collaboration mechanism.
- Permit local use without requiring a central application server.
- Support hosted or local AI models through interchangeable adapters.
- Stop and request engineering review when evidence is incomplete or conflicting.
- Generate visual and machine-readable review artifacts for each proposed component.
- Scale from a single engineer to a small engineering team without rewriting the core.

## 3. Non-goals for the first release

The first release will not:

- Automatically design complete machine schematics or wiring diagrams.
- Automatically select parts for an electrical design.
- Release safety-critical or mains-voltage components without human approval.
- Replace KiCad ERC, DRC, or engineering review.
- Train a custom foundation model.
- Provide a public multi-tenant SaaS service.
- Implement a complete product-lifecycle-management system.
- Guarantee extraction from every possible datasheet format.
- Modify a user's existing production library without an explicit release command.

The architecture should leave room for future generation of complete reference schematics, wiring harness artifacts, and e-box assemblies, but those features are outside the MVP.

## 4. Terminology

| Term | Meaning |
|---|---|
| Component | One manufacturer part number or an explicitly defined generic library item. |
| Symbol | KiCad schematic-library representation stored in a `.kicad_sym` library. |
| Footprint | KiCad PCB representation stored as a `.kicad_mod` file in a `.pretty` directory. |
| Canonical specification | Versioned YAML/JSON description from which KiCad artifacts are generated. |
| Evidence | Source location supporting an extracted fact, such as a PDF page, table, drawing callout, or approved engineering assumption. |
| Job | One workflow instance used to create or revise a component. |
| Release | A component state committed to the protected main branch after all required gates pass. |
| Agent | A constrained AI-backed operation that accepts and returns typed structured data. |
| Generator | Deterministic code that converts approved structured data into files. |
| Validator | Deterministic or AI-assisted check that reports findings without silently changing released data. |
| Collaboration adapter | Optional integration, such as Slack, that projects workflow events into a team communication tool and submits authenticated commands back to application services. |
| Review question | A persisted request for human input raised by an agent, validator, or reviewer. Questions may be blocking or non-blocking depending on the transition being attempted. |

## 5. Architectural principles

### 5.1 Git is the release system of record

The private Git repository contains released source specifications, generated KiCad files, review evidence, and release manifests. The local workflow database is operational state only and can be rebuilt from the repository where practical.

### 5.2 The canonical specification is authoritative

The canonical component YAML is the source of truth for generated geometry and metadata. Generated KiCad files are committed because KiCad must consume them directly, but CI regenerates the files and fails if committed output differs.

### 5.3 AI output is untrusted input

AI services may extract, classify, suggest, and review. They shall not:

- Write directly to the protected branch.
- Execute arbitrary shell commands.
- Select their own release state.
- Invent missing dimensions without an explicit, labeled engineering assumption.
- Modify a canonical specification after human approval without reopening the approval gate.

### 5.4 Geometry and syntax are deterministic

Pin coordinates, pad coordinates, shapes, clearances, UUIDs, file ordering, and S-expression serialization are produced by deterministic application code. The same approved specification and generator version must produce byte-identical output, except where a documented migration changes the format.

### 5.5 Human approval is a first-class workflow state

Approval is not represented by a comment in a prompt. It is a persisted event with actor, timestamp, specification hash, and scope.

### 5.6 Local-first and adapter-driven

The core application runs locally and accesses the local Git repository and KiCad installation. Model providers, Git hosting, PDF extraction, and KiCad command execution are ports with replaceable adapters.

### 5.7 Fail closed

When a required fact is absent, ambiguous, unsupported, or contradicted, the workflow enters a blocked state. It does not produce a releasable component from guessed values.

## 6. Assumptions and selected defaults

These defaults should be implemented but remain configurable:

| Area | Default decision |
|---|---|
| User model | One local user initially; actor identity taken from Git configuration. |
| Repository | Existing or newly initialized private Git repository. |
| Git host | Optional GitHub integration; local Git works without it. |
| Operating system | macOS first, with paths and subprocess handling written portably for Windows and Linux. |
| KiCad | KiCad 10 available locally; exact executable path configurable. |
| Backend | Python 3.12+, FastAPI application and reusable domain package. |
| Frontend | React and TypeScript, served by the local backend in production. |
| CLI | Typer-based CLI using the same application services as the web API. |
| Operational database | SQLite with SQLAlchemy and Alembic. |
| Canonical format | YAML for human review, validated through Pydantic models and exported JSON Schema. |
| AI | Provider-neutral interface; one hosted provider adapter first, local inference later. |
| Job execution | In-process asynchronous worker for MVP; queue interface allows later replacement. |
| Collaboration | Optional Slack adapter for review notifications, hash-bound approve/deny actions, agent questions, and workflow status; CLI and web workflows remain fully usable without Slack. |
| Authentication | Loopback-only local service by default; no login in MVP. |
| 3D models | Referenced or copied according to repository policy; never fabricated by the model. |

## 7. System context

![System context](kicad_architecture_work/system_context.png)

The engineer interacts through a browser or CLI. The local application owns workflow state and file generation. It may call a hosted or local model provider, invokes the local KiCad toolchain for validation and rendering, and writes changes only to a job-specific Git branch.

External dependencies are not permitted to bypass the application-service layer.

When configured, collaboration tools such as Slack receive notifications derived from persisted workflow events and may submit authenticated commands to the application. They are not systems of record for approvals, questions, release state, or generated artifacts.

## 8. High-level architecture

![Logical component architecture](kicad_architecture_work/component_architecture.png)

The application follows a hexagonal architecture with a domain core, application services, and infrastructure adapters.

### 8.1 Domain layer

The domain layer contains no FastAPI, database, Git, model-provider, or KiCad imports. It defines:

- Component identity and lifecycle.
- Canonical component specification models.
- Evidence and confidence models.
- Symbol and footprint plans.
- Validation findings and severities.
- Workflow states and allowed transitions.
- Approval records.
- Release manifests.
- Domain exceptions.

### 8.2 Application layer

Application services implement use cases:

- Create a component job.
- Attach and hash source documents.
- Extract facts from source documents.
- Resolve ambiguities and edit the canonical specification.
- Create, route, answer, and resolve review questions.
- Approve a specification.
- Generate KiCad artifacts.
- Validate artifacts.
- Render review images.
- Approve or reject a release candidate.
- Notify reviewers of required actions through optional collaboration channels.
- Query workflow status for in-progress jobs and parts.
- Commit, tag, and optionally open a pull request.
- Regenerate and validate the entire repository.

### 8.3 Infrastructure layer

Infrastructure adapters include:

- Filesystem and content-addressed source storage.
- SQLite repositories for jobs, events, and approvals.
- Git command adapter.
- Optional GitHub API adapter.
- PDF text and page-image extraction.
- Model provider adapter.
- KiCad CLI adapter.
- SVG/PNG rendering adapter.
- Collaboration notification adapter.
- Slack adapter for interactive review commands and status queries.
- Clock and identity providers.

### 8.4 Interface layer

The interface layer includes:

- Versioned REST API.
- Server-sent events for job progress.
- Browser application.
- Command-line interface.
- CI entry points.

## 9. Repository model

### 9.1 Recommended repository layout

```text
kicad-component-library/
├── .kcf/
│   ├── config.yaml
│   ├── config.example.yaml
│   ├── config.local.yaml          # local, gitignored
│   ├── schema-version
│   ├── slack.example.yaml
│   └── policies/
│       ├── library-style.yaml
│       ├── risk-rules.yaml
│       └── source-retention.yaml
├── components/
│   └── <manufacturer_slug>/
│       └── <part_slug>/
│           ├── component.yaml
│           ├── source-manifest.yaml
│           ├── evidence/
│           │   ├── pinout.json
│           │   ├── dimensions.json
│           │   └── review-notes.md
│           ├── sources/
│           │   └── <stored source files when permitted>
│           ├── review/
│           │   ├── symbol.svg
│           │   ├── footprint.svg
│           │   ├── footprint-layers.svg
│           │   ├── model.png
│           │   └── validation-report.json
│           └── release.yaml
├── libraries/
│   ├── Company_Electrical.kicad_sym
│   ├── Company_Electrical.pretty/
│   │   └── <footprint-name>.kicad_mod
│   └── Company_Electrical.3dshapes/
│       └── <approved models>
├── test-projects/
│   └── <component-key>/
│       ├── component-test.kicad_pro
│       ├── component-test.kicad_sch
│       └── component-test.kicad_pcb
├── schemas/
│   ├── component.schema.json
│   ├── validation-report.schema.json
│   └── release.schema.json
├── tools/
│   └── repository-specific scripts if required
├── .github/workflows/
│   ├── component-check.yml
│   └── library-regression.yml
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

### 9.1.1 Public application repository and private library repositories

KCF should support a public or broadly shared application repository while making it easy to initialize a private component-library repository or private fork for real engineering work.

The application repository may contain source code, schemas, tests, documentation, example fixtures, and redacted example configuration. The private library repository contains company component specifications, review evidence, generated KiCad libraries, source manifests, release manifests, and any permitted source documents.

Secrets are never committed. Slack bot tokens, Slack signing secrets, hosted model credentials, webhook URLs, and internal API keys must come from environment variables, a local gitignored configuration file, an operating-system secret store, or a CI secret manager.

Recommended gitignored local files include:

- `.kcf/config.local.yaml`
- `.kcf/secrets/`
- `.kcf/runtime/`
- `.env`
- `.env.*`
- `*.sqlite`
- `*.sqlite3`

Committed setup files should use safe templates such as `.env.example`, `.kcf/config.example.yaml`, and `.kcf/slack.example.yaml`. A bootstrap command such as `kcf init-library --private` should create the private repository layout, copy safe templates, install a conservative `.gitignore`, and leave credentials unset.

### 9.2 Source retention policy

The source manifest is always committed. Source files are committed only when company policy and licensing permit. A manifest entry must contain:

- Original filename.
- Media type.
- SHA-256 hash.
- Source type.
- Manufacturer and part number, if applicable.
- Document revision and publication date when known.
- Retrieval date.
- Original URL or internal reference.
- Storage mode: `embedded`, `external`, or `restricted`.
- Page count and extracted page-image hashes for PDFs.

The system must continue to validate evidence references even when a source is external. A release cannot claim reproducibility if the source is unavailable; such releases must explicitly record the limitation.

### 9.2.1 Review-response retention policy

Human review responses, Slack message metadata, agent questions, and reviewer comments are workflow evidence and can contain sensitive engineering context. Retention must be policy-driven.

Supported review-response storage modes should include:

- `summary_only`: commit the decision, actor, timestamp, approved hash, and concise reason; this is the default.
- `external`: commit a reference such as a Slack workspace/channel/message timestamp or permalink without full message text.
- `embedded`: commit the full review text or thread export when company policy permits.
- `restricted`: keep the response in the local operational database or another private store and commit only a limitation or external reference.

Release manifests must not claim that restricted review content is reproducible from Git alone.

### 9.3 Branching strategy

- Protected branch: `main`.
- New component branch: `parts/<manufacturer-slug>-<part-slug>`.
- Revision branch: `parts/<manufacturer-slug>-<part-slug>-rev-<n>`.
- Generator or schema changes: normal feature branches.
- The application never force-pushes.
- Automatic commits are permitted only on the active part branch.
- Pushing and opening a pull request require explicit user commands.

### 9.4 Committed generated artifacts

Generated KiCad files and review renders are committed. This is intentional because:

- Engineers need the library without running KCF.
- Pull requests need human-readable diffs and previews.
- Released commits must be directly usable.

CI must regenerate artifacts into a temporary directory and compare them to the committed versions. Any difference fails the build with a deterministic-drift finding.

### 9.5 Release identity

Each release manifest contains:

- Component key.
- Manufacturer part number.
- Component specification SHA-256.
- Source-manifest SHA-256.
- Generator package version.
- Schema version.
- KiCad target version.
- Validation-report SHA-256.
- Approver identity and timestamp.
- Git commit identifier when available.
- Risk classification.
- Known limitations.

## 10. Git-centered release flow

![Git-centered release flow](kicad_architecture_work/git_release_flow.png)

A standard release proceeds as follows:

1. Create or select a part branch.
2. Add source documents and source manifest.
3. Run extraction agents and save proposed structured outputs.
4. Resolve findings and approve the canonical specification.
5. Generate symbol, footprint, test project, and review artifacts.
6. Run local validation.
7. Commit the complete candidate to the part branch.
8. Push and open a pull request when requested.
9. CI regenerates and validates independently.
10. A human reviewer approves the pull request.
11. Merge to `main` creates the released component history.
12. Optional library tags identify coherent library releases.

No model API is required during repository-wide CI. CI validates committed structured data and deterministically regenerates outputs. This prevents builds from depending on model availability or nondeterministic responses.

## 11. Workflow state machine

![Workflow state machine](kicad_architecture_work/workflow_state_machine.png)

### 11.1 States

| State | Meaning |
|---|---|
| `DRAFT` | Job exists; identity may still be incomplete. |
| `SOURCES_READY` | Required sources are attached, hashed, and indexed. |
| `EXTRACTED` | Proposed facts and plans exist but are not approved. |
| `SPEC_APPROVED` | Human-approved canonical specification hash is recorded. |
| `GENERATED` | Artifacts were generated from the approved specification. |
| `VALIDATED` | All required deterministic validations passed. |
| `REVIEW_APPROVED` | Human release review approved the exact candidate hash. |
| `RELEASED` | Candidate was committed to the protected release history. |
| `BLOCKED` | Required evidence is missing, conflicting, or unsupported. |
| `CHANGES_REQUESTED` | A validator or reviewer rejected the current candidate. |
| `CANCELLED` | User intentionally abandoned the job. |

### 11.2 Transition rules

- A transition is executed only by an application command.
- Every transition appends an immutable workflow event.
- Transition guards operate on hashes, not mutable object references.
- Editing an approved specification invalidates later generation, validation, and approval states.
- Changing a source invalidates extraction and every downstream state.
- Changing a generator version invalidates generated artifacts and validation, but not approved source facts.
- Changing a style policy invalidates generation and validation for affected components.
- Unresolved blocking questions prevent transitions whose guards depend on the missing answer.
- Non-blocking questions may remain open while unrelated extraction, generation, rendering, or validation work continues.
- Release requires a clean Git worktree except for files explicitly included in the candidate commit.

### 11.3 Questions and required actions

Questions are first-class workflow records, not prompt comments or transient chat messages. Agents, deterministic validators, reviewers, and application services may create questions when additional human input would improve or unblock a job.

Each question must contain:

- Question identifier.
- Job identifier and component key.
- Originator type: agent, validator, reviewer, or system.
- Blocking flag and the transition or guard it blocks, if any.
- Prompt text and structured answer schema when applicable.
- Related finding, evidence reference, source hash, specification hash, or candidate hash.
- Assignee role or reviewer identity when known.
- Creation time, due time when applicable, and current status.

Question statuses are:

| Status | Meaning |
|---|---|
| `OPEN` | The question is waiting for an answer. |
| `ANSWERED` | A human has provided a response. |
| `RESOLVED` | The answer was applied, rejected, or converted into a finding or assumption. |
| `EXPIRED` | The question exceeded its configured response window. |
| `CANCELLED` | The question no longer applies because the job changed. |

Answers submitted through Slack, CLI, or the web UI execute the same application command and append immutable events. A Slack answer may include message metadata, but the persisted workflow record remains authoritative.

### 11.4 Workflow status summaries

The application shall expose a status summary for in-progress parts through CLI, REST API, web UI, and optional collaboration adapters. The same application query should power all interfaces.

A status summary includes:

- Component key and manufacturer part number.
- Current workflow state.
- Active Git branch.
- Latest persisted event and timestamp.
- Open blocking findings.
- Open blocking and non-blocking questions.
- Current required human actions.
- Validation status.
- Review bundle paths or links.
- Current specification hash and candidate hash when available.
- Next recommended command or action.

Slack commands such as `/kcf status` may display this summary, but Slack is only a projection of application state.

### 11.5 Collaboration and Slack review operations

Collaboration integrations are optional adapters over workflow events and application commands. Slack is the first recommended collaboration adapter because it can deliver review notifications, collect hash-bound approvals or denials, ask and answer questions, and show status for in-progress parts.

Slack interactions must obey these rules:

- Slack is not the system of record for approvals, release state, or questions.
- Inbound Slack requests must verify the signing secret, timestamp, and replay window.
- Bot tokens and signing secrets must come from environment variables, local gitignored config, or a secret manager.
- Slack user IDs must be mapped to application actors and roles before they can approve or deny.
- Approval and denial actions must include the exact specification hash or candidate hash being acted on.
- If the referenced hash no longer matches current job state, the command fails closed and asks the reviewer to refresh.
- Slack approval, denial, and answer actions call the same application services used by CLI and web interfaces.
- Slack raw payloads and full message text are not committed unless review-response retention policy explicitly permits it.
- Notification delivery failure does not change workflow state; it creates a warning or delivery event.

A standard Slack review thread may receive messages for job creation, sources ready, extraction completed, questions opened, specification ready for approval, artifacts generated, validation completed, release candidate ready, approval or denial recorded, and pull request opened.

## 12. Canonical component specification

### 12.1 Schema design

The canonical specification shall be represented by versioned Pydantic models and serialized as stable YAML. The serializer must preserve a documented field order and use normalized numeric formatting.

Top-level structure:

```yaml
schema_version: "1.0"
component_key: "phoenix-contact-1715721"
identity: {}
classification: {}
symbol: {}
footprint: {}
model_3d: {}
sources: []
evidence: {}
assumptions: []
policies: {}
release_constraints: {}
```

### 12.2 Example specification

```yaml
schema_version: "1.0"
component_key: "example-mfr-abc123"

identity:
  manufacturer: "Example Manufacturer"
  manufacturer_part_number: "ABC123"
  library_name: "Company_Electrical"
  symbol_name: "ABC123"
  footprint_name: "TerminalBlock_ABC123_1x03_P5.08mm"
  description: "Three-position through-hole terminal block"
  datasheet_description: "PCB terminal block, 3 positions"
  keywords: ["terminal block", "5.08 mm", "through hole"]

classification:
  family: "terminal_block"
  risk_level: "medium"
  safety_related: false
  mains_rated: false

symbol:
  reference_prefix: "J"
  representation: "single_unit"
  body:
    width_grid_units: 6
    height_grid_units: 6
  pins:
    - number: "1"
      name: "1"
      electrical_type: "passive"
      orientation: "right"
      group: "terminals"
    - number: "2"
      name: "2"
      electrical_type: "passive"
      orientation: "right"
      group: "terminals"
    - number: "3"
      name: "3"
      electrical_type: "passive"
      orientation: "right"
      group: "terminals"

footprint:
  technology: "through_hole"
  origin_strategy: "pad_1"
  pitch_mm: 5.08
  body:
    width_mm: 15.24
    depth_mm: 10.20
    height_mm: 12.00
  pads:
    - number: "1"
      x_mm: 0.00
      y_mm: 0.00
      shape: "rect"
      size_x_mm: 2.40
      size_y_mm: 2.40
      drill_mm: 1.30
    - number: "2"
      x_mm: 5.08
      y_mm: 0.00
      shape: "circle"
      size_x_mm: 2.40
      size_y_mm: 2.40
      drill_mm: 1.30
    - number: "3"
      x_mm: 10.16
      y_mm: 0.00
      shape: "circle"
      size_x_mm: 2.40
      size_y_mm: 2.40
      drill_mm: 1.30
  courtyard:
    method: "body_plus_clearance"
    clearance_mm: 0.50
  mechanical_regions:
    - type: "wire_entry"
      description: "Keep clear for conductor insertion"
      geometry_ref: "wire-entry-1"

model_3d:
  status: "provided"
  path: "${KIPRJMOD}/../libraries/Company_Electrical.3dshapes/ABC123.step"
  source_hash: "sha256:..."
  transform:
    offset_mm: [0.0, 0.0, 0.0]
    rotation_deg: [0.0, 0.0, 0.0]
    scale: [1.0, 1.0, 1.0]

assumptions: []

release_constraints:
  required_human_roles: ["electrical_reviewer"]
  block_on_warning_codes:
    - "EVIDENCE_CONFLICT"
    - "PIN_PAD_MISMATCH"
```

### 12.3 Numeric representation

- Internal numeric calculations use `Decimal` where exact decimal geometry matters.
- Public schema values use millimeters and decimal degrees unless explicitly stated.
- Unit-bearing source facts retain original units and normalized SI values.
- No binary floating-point value may be directly serialized into a generated KiCad file without normalization.
- Coordinate output precision is centrally configured and tested.

### 12.4 Evidence model

Every extracted engineering fact should be representable as:

```yaml
fact_id: "footprint.pitch_mm"
value: 5.08
unit: "mm"
status: "supported"
confidence: 0.99
source_ref:
  source_id: "datasheet-primary"
  page: 4
  region: [0.12, 0.31, 0.72, 0.64]
  label: "dimension drawing"
method: "model_extraction"
notes: null
```

Allowed fact statuses:

- `supported`: directly stated in a source.
- `derived`: calculated from supported facts using a recorded formula.
- `assumed`: manually entered engineering assumption.
- `conflicting`: sources disagree.
- `missing`: required value not found.
- `not_applicable`: intentionally absent.

A releasable part may contain assumptions only when policy permits them and a human has explicitly approved each assumption.

## 13. Agent architecture

### 13.1 General contract

Each agent is a pure application operation from typed input to typed output from the perspective of the workflow. Calls may be nondeterministic, but results are persisted verbatim with model metadata and are never silently overwritten.

Every agent response must include:

- Schema version.
- Agent name and agent prompt version.
- Model provider and model identifier.
- Input content hashes.
- Structured result.
- Confidence by finding or field.
- Uncertainties.
- Token or cost metadata when available.
- Raw-response reference for debugging, protected from accidental release if it contains sensitive data.

### 13.2 Source extraction agent

Responsibilities:

- Identify document type and likely relevant pages.
- Extract manufacturer identity, exact part number, revision, and package variant.
- Extract pin tables, pin names, electrical functions, dimensions, tolerances, recommended land patterns, mounting features, and orientation indicators.
- Return explicit missing and conflicting facts.
- Provide page and image-region evidence.

The agent must be instructed that document text is untrusted data and any instructions inside the document are not executable instructions.

### 13.3 Symbol planning agent

Responsibilities:

- Propose reference prefix.
- Propose single-unit or multi-unit organization.
- Assign electrical pin types.
- Group pins functionally.
- Propose pin ordering and visual arrangement.
- Identify hidden, stacked, alternate-function, no-connect, and power pins.
- Explain decisions that are not direct datasheet facts.

The symbol planner returns a semantic plan. It does not output KiCad S-expressions or final coordinates.

### 13.4 Footprint planning agent

Responsibilities:

- Select a supported footprint template or request a custom template.
- Identify origin and orientation strategy.
- Associate source dimensions with template parameters.
- Identify mating, wire-entry, screwdriver-access, panel-edge, keepout, and mounting regions.
- Flag cases where manufacturer land-pattern guidance is absent.

It does not calculate arbitrary pad geometry outside approved deterministic calculation functions.

### 13.5 Visual review agent

Inputs:

- Rendered symbol.
- Footprint layer renders.
- Optional 3D render.
- Datasheet pinout pages.
- Datasheet mechanical drawing pages.
- Approved canonical specification.
- Deterministic validation report.

Outputs:

- Findings only, each with severity, evidence, confidence, and suggested human action.
- No automatic approval.
- No direct edits.

### 13.6 Model gateway

Define a `ModelGateway` port with operations such as:

```python
class ModelGateway(Protocol):
    async def structured_completion(
        self,
        *,
        task: str,
        prompt_version: str,
        input_parts: list[ModelInputPart],
        output_schema: type[BaseModel],
        request_metadata: dict[str, str],
    ) -> ModelResult: ...
```

The provider adapter must enforce structured output validation and retry only for transport errors or schema-repair attempts. It must not endlessly retry low-confidence engineering content.

## 14. Deterministic generation

### 14.1 Generator responsibilities

The generator package shall:

- Convert canonical symbol plans to KiCad symbol-library objects.
- Convert canonical footprint plans to footprint objects.
- Generate stable UUIDs from component key plus semantic object path.
- Serialize objects in stable order.
- Merge symbols into a library without reformatting unrelated symbols.
- Write one footprint file per footprint.
- Associate approved 3D models using portable paths.
- Generate component test projects.
- Generate review metadata and traceability comments where supported.

### 14.2 Generator module structure

```text
src/kcf/generation/
├── models.py
├── symbol_builder.py
├── footprint_builder.py
├── geometry.py
├── uuid.py
├── naming.py
├── serializer/
│   ├── symbol_sexpr.py
│   ├── footprint_sexpr.py
│   └── common.py
├── test_project.py
└── merge.py
```

### 14.3 Stable UUID strategy

Use UUID version 5 with a fixed application namespace:

```text
uuid5(KCF_NAMESPACE, "<component_key>/<artifact>/<semantic_path>")
```

Examples:

```text
example-mfr-abc123/symbol/unit-a/pin-1
example-mfr-abc123/footprint/pad-1
example-mfr-abc123/footprint/fab/outline/top
```

Renaming display text should not change UUIDs unless the semantic identity changes. The generator must include migration tests before changing UUID construction.

### 14.4 Template-based footprint generation

The MVP supports a template registry rather than arbitrary free-form footprints. Initial templates:

- Single-row through-hole connector.
- Dual-row through-hole connector.
- Single-row SMD connector.
- Rectangular module with perimeter connectors.
- Terminal block with parametric position count.
- Relay with explicit pad coordinate table.
- Generic custom-coordinate footprint for reviewed exceptional cases.

Each template defines required parameters, allowed ranges, geometry functions, and template-specific validators.

### 14.5 Library merge behavior

Symbol generation must not rewrite an entire large symbol library with uncontrolled formatting changes. Implement one of these approaches, in order of preference:

1. Parse the library into a typed syntax tree and replace only the named symbol while preserving stable serializer formatting.
2. Maintain one generated symbol library per component family and combine them during release.
3. If a whole-library rewrite is unavoidable, use a canonical serializer and add a one-time migration commit.

The implementation must have regression fixtures for comments, properties, multi-unit symbols, stacked pins, and existing unrelated symbols.

## 15. Validation architecture

### 15.1 Finding model

All validators emit a common finding structure:

```yaml
code: "PIN_PAD_MISMATCH"
severity: "error"
message: "Symbol pin 4 has no connectable footprint pad."
artifact: "example-mfr-abc123"
path: "symbol.pins[3].number"
evidence_refs: ["pin-table-page-3"]
validator: "pin_pad_parity"
validator_version: "1.0.0"
waivable: false
```

Severities:

- `info`: useful context.
- `warning`: review required depending on policy.
- `error`: blocks validation.
- `critical`: blocks validation and requires explicit engineering resolution.

### 15.2 Validation stages

#### Stage A: schema validation

- YAML parses successfully.
- Schema version is supported.
- Required fields are present.
- Enums and numeric ranges are valid.
- References resolve.

#### Stage B: evidence validation

- Required engineering facts have supporting evidence.
- Evidence points to an available source or documented external source.
- Source hash matches.
- Conflicting facts are resolved.
- Assumptions are explicitly approved.

#### Stage C: semantic validation

- Symbol pin numbers are unique unless stacking is intentional.
- Footprint pad numbers are valid.
- Symbol-to-pad parity is correct.
- Electrical pin types are permitted by policy.
- Reference prefix and naming follow style policy.
- Units, variants, and package identity are consistent.

#### Stage D: geometry validation

- Pad sizes exceed drills by policy-required annular ring.
- Pads do not unintentionally overlap.
- Courtyard is closed and contains required body geometry.
- Silkscreen does not cross forbidden pad regions beyond configured policy.
- Origin and pin-1 marker agree with the specification.
- Body dimensions and pad coordinates are within tolerance of supported source facts.
- Mechanical access regions are represented when required.

#### Stage E: KiCad tool validation

The KiCad adapter should detect supported CLI capabilities at startup. Validation should include all available operations needed to prove that generated files load and can be exported. The adapter must capture command, version, exit code, standard output, and standard error.

Expected checks include:

- Parse or export symbol library.
- Parse or export footprint.
- Open or process generated test schematic.
- Run ERC on the test schematic.
- Run DRC and schematic-parity checks on the test PCB when supported.
- Export SVG or other review formats.
- Render or export a 3D view when supported by the available toolchain.

Exact flags belong in the KiCad adapter and must be covered by integration tests against the pinned KiCad version.

#### Stage F: deterministic drift validation

- Generate all artifacts in a clean temporary directory.
- Compare against committed artifacts.
- Normalize only explicitly allowed environment-dependent fields.
- Fail if any unexplained difference exists.

#### Stage G: visual review

- Produce standardized renders at fixed scale and orientation.
- Run optional AI visual review.
- Require human approval for configured risk classes.

### 15.3 Policy engine

Validation behavior is controlled by repository policy files. Example:

```yaml
policy_version: "1.0"
coordinate_precision_mm: 0.001
minimum_annular_ring_mm: 0.15
courtyard_clearance_mm:
  default: 0.50
  terminal_block: 1.00
human_review:
  low: ["visual"]
  medium: ["electrical", "mechanical"]
  high: ["electrical", "mechanical", "independent"]
block_on_assumptions:
  safety_related: true
  mains_rated: true
```

Policy files are versioned in Git. A release manifest records the policy commit or hash used for validation.

## 16. Test-project generation

Every component candidate receives a generated test project.

### 16.1 Test schematic

The test schematic shall:

- Instantiate every unit of the symbol.
- Expose every pin.
- Apply no-connect markers only when the component specification explicitly marks pins as intentionally unused in the fixture.
- Assign the generated footprint.
- Include identifying text with the component key and specification hash.

### 16.2 Test PCB

The test PCB shall:

- Place the generated footprint at a known origin.
- Include a board outline large enough for the component and access regions.
- Include reference dimensions or markers useful for visual inspection.
- Preserve the intended top-side orientation.
- Include the 3D model association when present.

### 16.3 Fixture purpose

The fixture is not an application circuit. It proves integration between symbol, footprint, pad mapping, KiCad parsing, and 3D association.

## 17. Persistence and audit log

### 17.1 SQLite data model

Suggested tables:

```text
jobs
job_sources
agent_runs
workflow_events
approvals
validation_runs
validation_findings
generation_runs
artifacts
repository_operations
settings
```

### 17.2 Event records

Every material operation appends an event:

```json
{
  "event_id": "...",
  "job_id": "...",
  "event_type": "SPEC_APPROVED",
  "actor": "Garth Benson <garthbenson@gmail.com>",
  "occurred_at": "2026-07-13T22:00:00-05:00",
  "input_hashes": {"component_yaml": "sha256:..."},
  "output_hashes": {},
  "metadata": {"approval_scope": "symbol_and_footprint"}
}
```

Events are immutable. Corrections are represented by later events.

### 17.3 Rebuildability

The database is not the sole location for released facts. The application should be able to import a component directory and reconstruct its released state, validation history summary, and manifest from Git content.

## 18. API design

Use `/api/v1` from the first implementation.

### 18.1 Core endpoints

```text
POST   /api/v1/jobs
GET    /api/v1/jobs
GET    /api/v1/jobs/{job_id}
DELETE /api/v1/jobs/{job_id}

POST   /api/v1/jobs/{job_id}/sources
GET    /api/v1/jobs/{job_id}/sources
POST   /api/v1/jobs/{job_id}/sources/index

POST   /api/v1/jobs/{job_id}/extract
GET    /api/v1/jobs/{job_id}/extractions

GET    /api/v1/jobs/{job_id}/specification
PUT    /api/v1/jobs/{job_id}/specification
POST   /api/v1/jobs/{job_id}/specification/approve

POST   /api/v1/jobs/{job_id}/generate
POST   /api/v1/jobs/{job_id}/validate
GET    /api/v1/jobs/{job_id}/validation

POST   /api/v1/jobs/{job_id}/review/approve
POST   /api/v1/jobs/{job_id}/review/reject

POST   /api/v1/jobs/{job_id}/git/commit
POST   /api/v1/jobs/{job_id}/git/push
POST   /api/v1/jobs/{job_id}/git/pull-request
POST   /api/v1/jobs/{job_id}/release

GET    /api/v1/jobs/{job_id}/events
GET    /api/v1/jobs/{job_id}/stream
GET    /api/v1/system/capabilities
GET    /api/v1/system/health
```

### 18.2 Idempotency

Commands that create agent runs, generation runs, validation runs, commits, or releases accept an idempotency key. The application must not create duplicate releases or duplicate commits when a client retries after a network interruption.

### 18.3 Optimistic concurrency

Specification updates require an expected specification hash or ETag. A stale browser tab must receive a conflict response rather than overwrite newer edits.

### 18.4 Progress events

Use server-sent events for progress. Event payloads contain stable event types and user-readable messages but no chain-of-thought or hidden model reasoning.

## 19. CLI design

The CLI is a first-class interface and should be implemented before or alongside the browser UI.

```text
kcf init <repository>
kcf doctor
kcf part create --manufacturer <name> --mpn <part-number>
kcf part add-source <component-key> <file>
kcf part extract <component-key>
kcf part show <component-key>
kcf part edit <component-key>
kcf part approve-spec <component-key>
kcf part generate <component-key>
kcf part validate <component-key>
kcf part render <component-key>
kcf part approve-release <component-key>
kcf part commit <component-key>
kcf part push <component-key>
kcf part open-pr <component-key>
kcf repo validate
kcf repo regenerate --check
kcf repo migrate
```

`kcf doctor` shall report:

- Repository status.
- Configuration validity.
- Git version and identity.
- KiCad executable location and version.
- Supported KiCad capabilities.
- Database status.
- Model-provider configuration without exposing secrets.
- Write permissions.

## 20. Browser interface

### 20.1 Primary screens

1. Repository dashboard.
2. Component job list.
3. New-component wizard.
4. Source document viewer with evidence overlays.
5. Canonical specification editor.
6. Symbol and footprint preview.
7. Validation findings panel.
8. Git diff and commit screen.
9. Release approval screen.
10. Settings and capability diagnostics.

### 20.2 Review experience

The central review screen should show:

- Datasheet page and selected evidence region.
- Extracted fact and confidence.
- Approved canonical value.
- Symbol render.
- Footprint render by layer.
- 3D render when available.
- Validator findings.
- Git diff for the current candidate.

A reviewer should be able to navigate from a pad or pin directly to its supporting evidence.

### 20.3 Editing rules

- Form editors write only canonical schema fields.
- Raw YAML editing may be offered in an advanced mode with schema validation.
- The browser never edits generated KiCad syntax directly in the MVP.
- Any edit invalidates affected approvals immediately.

## 21. Git adapter

### 21.1 Required operations

Define a repository port supporting:

- Discover repository root.
- Read status and current branch.
- Create and switch branch.
- Stage explicit paths.
- Show diff and staged diff.
- Commit with controlled message.
- Obtain commit identifiers.
- Check ancestry and branch protection assumptions.
- Push only after explicit command.
- Detect untracked or unrelated modifications.

### 21.2 Shell safety

- Invoke Git with argument arrays, never shell interpolation.
- Validate branch and path inputs.
- Restrict operations to the configured repository root.
- Never run hooks from untrusted repositories unless the user explicitly enables them.
- Never perform reset, clean, rebase, or force push automatically.
- Redact credentials from logs.

### 21.3 Commit format

Recommended commit message:

```text
Add Example Manufacturer ABC123 component

Component-Key: example-mfr-abc123
Spec-SHA256: <hash>
Generator-Version: <version>
Validation-Report-SHA256: <hash>
```

## 22. GitHub integration

GitHub support is optional and implemented behind a hosting-provider interface.

MVP capabilities:

- Detect repository remote.
- Open a pull request from the active part branch.
- Add a generated PR body summarizing evidence, assumptions, renders, and validation.
- Read CI status.
- Link the local job to the PR.

The local application must remain fully usable with no GitHub token and with a non-GitHub remote.

## 23. Configuration

### 23.1 Repository configuration

Example `.kcf/config.yaml`:

```yaml
config_version: "1.0"
repository_id: "company-electrical-library"

libraries:
  symbol_library: "libraries/Company_Electrical.kicad_sym"
  footprint_directory: "libraries/Company_Electrical.pretty"
  model_directory: "libraries/Company_Electrical.3dshapes"

kicad:
  target_major_version: 10
  executable: null
  auto_discover: true

git:
  protected_branch: "main"
  part_branch_prefix: "parts/"
  allow_automatic_commit: true
  allow_automatic_push: false

models:
  default_provider: "hosted"
  extraction_model: "configured-by-environment"
  planning_model: "configured-by-environment"
  visual_review_model: "configured-by-environment"

storage:
  operational_database: ".kcf/local/kcf.sqlite3"
  raw_model_responses: ".kcf/local/model-runs"

policies:
  style: ".kcf/policies/library-style.yaml"
  risk: ".kcf/policies/risk-rules.yaml"
  source_retention: ".kcf/policies/source-retention.yaml"
```

Local secrets and runtime state must be ignored by Git.

### 23.2 Environment variables

Use environment variables or OS secret storage for:

- Model API credentials.
- GitHub token.
- Optional telemetry endpoint credentials.

Do not place secrets in repository YAML, logs, generated reports, or model prompts.

## 24. Security model

### 24.1 Threats

Important threats include:

- Prompt injection embedded in a datasheet or source webpage.
- Malicious or malformed PDF content.
- Path traversal in uploaded filenames.
- Arbitrary command injection through part numbers or branch names.
- Model hallucination of dimensions or pin functions.
- Accidental release of confidential source documents.
- API keys written to Git.
- A model or plugin modifying unrelated files.
- Supply-chain compromise of Python or frontend dependencies.

### 24.2 Controls

- Treat all source text as quoted data, not instructions.
- Store uploads under generated identifiers, not original paths.
- Enforce file-type and size limits.
- Hash all inputs.
- Use subprocess argument arrays and timeouts.
- Restrict filesystem operations to configured roots.
- Require evidence for release-critical facts.
- Require human approvals based on risk policy.
- Run AI calls with least-necessary document pages and fields.
- Add secret scanning to CI.
- Pin dependencies with lock files.
- Produce a software bill of materials for releases when practical.
- Disable network access in deterministic CI generation jobs unless required for dependency installation.

### 24.3 Data privacy

Raw model requests and responses remain local operational data by default and are not committed. The UI must show which source pages will be transmitted before a hosted-model call when repository policy requires confirmation.

## 25. Reliability and recovery

- Every long operation writes a run record before execution.
- Temporary generation occurs outside released directories and is atomically promoted after success.
- Interrupted jobs can resume from the last valid state.
- Model calls are retryable for transport failure but not blindly repeated for engineering ambiguity.
- Git operations are transactional at the application level: stage explicit files, show diff, then commit.
- A failed commit or push leaves the generated candidate intact for inspection.
- The application creates no hidden background release process.

## 26. Observability

### 26.1 Structured logs

Log fields should include:

- Timestamp.
- Level.
- Request or command identifier.
- Job identifier.
- Component key.
- Operation.
- Duration.
- Result status.
- External command exit code.
- Model run identifier.

Do not log secrets, complete confidential document text, or hidden model reasoning.

### 26.2 Metrics

Useful local metrics:

- Jobs by state.
- Extraction success and blocked rate.
- Average time from draft to release.
- Validation failures by code.
- Model cost by agent type.
- Regeneration drift incidents.
- Components by risk level and review status.

Telemetry is opt-in and disabled by default.

## 27. Testing strategy

### 27.1 Unit tests

Required unit-test areas:

- Pydantic schemas and migrations.
- Stable YAML serialization.
- UUID construction.
- Geometry functions.
- Naming and slugging.
- Symbol and footprint serializers.
- Workflow transition guards.
- Evidence resolution.
- Policy evaluation.
- Git command construction.

### 27.2 Golden-file tests

Maintain fixtures for:

- Simple two-pin component.
- Parametric terminal block.
- Multi-unit relay.
- Module with grouped connectors.
- Through-hole and SMD pads.
- Mounting holes and mechanical pads.
- Stacked pins.
- Alternate pin names.
- 3D model transforms.

Golden files must be intentionally updated through a documented command that shows diffs.

### 27.3 Property-based tests

Use property-based tests for geometry and serialization invariants, including:

- Pad coordinate sequences for arbitrary supported pin counts.
- Courtyard containment.
- UUID stability.
- Round-trip parse and serialize behavior.
- No duplicate semantic identifiers.

### 27.4 Integration tests

Run against an installed pinned KiCad version:

- Generate component.
- Parse and export artifacts through KiCad.
- Run ERC and DRC on generated fixture.
- Validate output hashes.
- Verify review renders exist and are non-empty.

### 27.5 End-to-end tests

A full test should:

1. Initialize a temporary Git repository.
2. Create a job.
3. Attach fixture source data.
4. Import a deterministic mocked extraction response.
5. Approve the specification.
6. Generate and validate artifacts.
7. Commit a part branch.
8. Regenerate and confirm no drift.
9. Approve and simulate merge to main.
10. Import the released component into a fresh operational database.

### 27.6 Model evaluation tests

Agent prompts require a fixture set with expected facts and acceptable uncertainty behavior. Evaluation should emphasize false-confidence prevention rather than exact wording.

## 28. CI architecture

### 28.1 Pull-request checks

The component check workflow shall:

1. Check out the repository.
2. Install the pinned application package and dependencies.
3. Install or select the pinned KiCad toolchain.
4. Validate all changed component schemas.
5. Regenerate changed artifacts into a clean directory.
6. Fail on deterministic drift.
7. Run component-level validators.
8. Run generated fixture ERC and DRC.
9. Produce review renders and validation reports as build artifacts.
10. Summarize findings in the check output.

### 28.2 Main-branch checks

The library regression workflow shall:

- Validate the complete repository.
- Regenerate every component or a cache-safe affected set.
- Confirm no duplicate library names or footprint names.
- Confirm all release manifests and hashes.
- Build a distributable library archive.
- Optionally tag and publish internal releases.

### 28.3 No model dependency in CI

CI shall not invoke an AI model to decide whether committed components are valid. AI-produced extraction data is reviewed and committed before CI. CI uses deterministic schemas and validators only.

## 29. Package and source-code layout

```text
kicad-component-factory/
├── src/kcf/
│   ├── domain/
│   │   ├── component.py
│   │   ├── evidence.py
│   │   ├── workflow.py
│   │   ├── validation.py
│   │   ├── release.py
│   │   └── policies.py
│   ├── application/
│   │   ├── commands/
│   │   ├── queries/
│   │   ├── services/
│   │   └── ports/
│   ├── generation/
│   ├── validation/
│   ├── agents/
│   ├── infrastructure/
│   │   ├── database/
│   │   ├── filesystem/
│   │   ├── git/
│   │   ├── github/
│   │   ├── kicad/
│   │   ├── models/
│   │   └── documents/
│   ├── api/
│   ├── cli/
│   └── settings.py
├── web/
│   ├── src/
│   └── package.json
├── tests/
│   ├── unit/
│   ├── golden/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
├── schemas/
├── migrations/
├── docs/
├── pyproject.toml
├── uv.lock
├── package-lock.json
└── README.md
```

### 29.1 Dependency direction

Allowed dependency direction:

```text
interfaces -> application -> domain
infrastructure -> application ports and domain
```

The domain must never import infrastructure or interface code. Generators may depend on domain models but not on FastAPI or SQLAlchemy models.

## 30. Implementation phases

### Phase 0: repository and technical spike

Deliverables:

- Python package skeleton.
- Configuration loader.
- `kcf doctor`.
- KiCad capability detector.
- Minimal Git adapter.
- One hand-authored canonical fixture.
- One generated symbol and footprint successfully loaded by KiCad.

Exit criteria:

- A clean clone can run tests and generate the fixture reproducibly.

### Phase 1: deterministic core and CLI

Deliverables:

- Canonical schema version 1.0.
- Stable YAML serializer.
- Workflow state machine.
- Terminal-block and explicit-coordinate footprint templates.
- Symbol generator.
- Footprint generator.
- Test-project generator.
- Core validators.
- CLI lifecycle through local commit.

Exit criteria:

- A terminal block can be created from a manually completed specification, validated, rendered, and committed.

### Phase 2: source evidence and AI extraction

Deliverables:

- PDF ingestion and page rendering.
- Evidence region model.
- Model gateway and one provider adapter.
- Source extraction agent.
- Symbol and footprint planning agents.
- Structured result persistence.
- Manual ambiguity-resolution workflow.

Exit criteria:

- A supported datasheet can produce a proposed specification with evidence, and the workflow blocks correctly on missing facts.

### Phase 3: local web application

Deliverables:

- FastAPI endpoints.
- React UI.
- Source viewer and evidence overlays.
- Specification editor.
- Render and findings review screen.
- SSE progress.

Exit criteria:

- A user can complete the component lifecycle without using the CLI except for repository setup.

### Phase 4: CI and pull-request integration

Deliverables:

- GitHub Actions workflows.
- GitHub adapter.
- PR body generation.
- Build artifact publication.
- Repository-wide validation.

Exit criteria:

- A candidate branch produces an independently validated pull request and can be merged into a usable library.

### Phase 5: advanced components

Deliverables:

- Multi-unit symbols.
- Complex modules.
- Mechanical access overlays.
- 3D transform review.
- Additional template families.
- Optional visual-review agent.

Exit criteria:

- The system supports representative terminal blocks, relays, sensors, power supplies, and controller modules.

## 31. MVP acceptance criteria

The MVP is complete when all of the following are true:

1. The application initializes or opens a private Git-centered component library repository.
2. A user can create a component job and attach a datasheet.
3. The application hashes and records the source.
4. A canonical specification can be created manually and through a structured extraction adapter.
5. The user can review and explicitly approve the specification.
6. The generator creates a KiCad symbol and footprint without model-authored raw syntax.
7. The generator creates a symbol/footprint integration test project.
8. Deterministic validators catch pin-pad mismatches, missing evidence, invalid geometry, and naming violations.
9. The KiCad adapter proves the generated files can be processed by the configured KiCad installation.
10. The application produces review renders.
11. Editing an approved specification invalidates downstream approvals.
12. The application creates a part branch and commits only explicit candidate files.
13. A clean regeneration produces no diff.
14. CI can validate a candidate without calling an AI model.
15. A human approval record is required before release.
16. The released main branch is directly usable as a KiCad library.

## 32. Definition of done for implementation tasks

A Codex implementation task is done only when:

- Code follows the dependency rules in this document.
- Public models and APIs are typed.
- Schema or behavior changes include migrations or compatibility handling.
- Unit tests cover normal and failure paths.
- File-generation changes include golden tests.
- External commands have timeouts, captured output, and actionable errors.
- User-visible errors identify the failed gate and remediation.
- Formatting, linting, type checking, and tests pass.
- Documentation is updated.
- No secrets or user-specific absolute paths are committed.

## 33. Initial architecture decision records

### ADR-001: Git is the release system of record

**Decision:** Released specifications and artifacts live in Git.  
**Reason:** Auditability, review, reproducibility, and direct distribution to KiCad users.  
**Consequence:** The application must handle diffs, branches, and merge-friendly file organization carefully.

### ADR-002: Commit generated artifacts

**Decision:** Commit generated KiCad files and review renders, while treating canonical YAML as authoritative.  
**Reason:** Libraries remain directly usable and reviewable without running the generator.  
**Consequence:** CI must perform regeneration-drift checks.

### ADR-003: AI cannot generate release files directly

**Decision:** AI returns validated structured proposals only.  
**Reason:** Raw KiCad syntax and geometry require deterministic, testable output.  
**Consequence:** A canonical schema and generator library are mandatory before advanced agent work.

### ADR-004: Local-first application

**Decision:** Run the orchestration, Git, and KiCad integrations locally.  
**Reason:** Direct tool access, confidentiality, and low deployment burden.  
**Consequence:** Hosted model calls must be optional and transparent.

### ADR-005: Workflow state machine

**Decision:** Use explicit states and guarded transitions rather than autonomous agent loops.  
**Reason:** Engineering workflows need auditability and resumable human gates.  
**Consequence:** Every command must declare preconditions and invalidation effects.

### ADR-006: CLI-first shared application services

**Decision:** Implement core use cases and CLI before depending on the browser UI.  
**Reason:** It creates a testable automation surface and prevents business logic from becoming frontend-specific.  
**Consequence:** The REST API and UI must call the same application services.

### ADR-007: CI is deterministic and model-free

**Decision:** Pull-request and main-branch validation never require AI calls.  
**Reason:** Reliability, cost control, reproducibility, and security.  
**Consequence:** AI results needed for release must be reviewed and committed as structured evidence before CI.

## 34. Open decisions and extension points

The following do not block implementation because defaults are defined, but they should be confirmed before broad deployment:

- Final product name and Python package name.
- Whether manufacturer datasheets may be committed to the private repository.
- Preferred hosted model provider and data-retention terms.
- Whether GitHub is the only supported remote host.
- Required reviewer roles and how identity should be verified.
- Company-specific symbol and footprint style rules.
- Naming scheme for generic versus manufacturer-specific components.
- Whether review renders should remain in Git after release or be CI artifacts only.
- Required Windows support date.
- Whether 3D model license metadata requires a separate approval gate.
- Whether future complete-schematic generation belongs in this repository or a separate application.

These choices should be represented by configuration or new ADRs rather than hard-coded assumptions.

## 35. Codex implementation directive

Codex should implement the system incrementally in the phase order above. It should not begin with autonomous multi-agent orchestration or a complex frontend. The first working vertical slice must be:

```text
component.yaml
    -> schema validation
    -> deterministic symbol and footprint generation
    -> test project generation
    -> KiCad validation adapter
    -> review renders
    -> Git part-branch commit
    -> clean regeneration check
```

After this slice is reliable, add source evidence and model-backed extraction behind ports. Preserve the architectural boundary that model output is proposed data and deterministic code owns release artifacts.

When implementation details are uncertain, favor:

- Explicit typed models over dictionaries.
- Pure functions over hidden mutation.
- Append-only events over state replacement.
- Stable files over database-only data.
- Failing with actionable findings over guessing.
- Small adapters over provider-specific logic in the domain.
- Reproducibility over convenience.

---

# Appendix A: Suggested command and service interfaces

```python
@dataclass(frozen=True)
class CreateJobCommand:
    repository_root: Path
    manufacturer: str
    manufacturer_part_number: str

@dataclass(frozen=True)
class ApproveSpecificationCommand:
    job_id: UUID
    expected_spec_hash: str
    actor: ActorIdentity
    notes: str | None = None

@dataclass(frozen=True)
class GenerateArtifactsCommand:
    job_id: UUID
    expected_spec_hash: str
    clean: bool = True

@dataclass(frozen=True)
class ValidateCandidateCommand:
    job_id: UUID
    expected_artifact_manifest_hash: str
    include_visual_review: bool = False

@dataclass(frozen=True)
class CommitCandidateCommand:
    job_id: UUID
    expected_validation_hash: str
    message: str | None = None
```

Application service interfaces:

```python
class JobService(Protocol): ...
class SourceService(Protocol): ...
class ExtractionService(Protocol): ...
class SpecificationService(Protocol): ...
class GenerationService(Protocol): ...
class ValidationService(Protocol): ...
class ReviewService(Protocol): ...
class ReleaseService(Protocol): ...
```

# Appendix B: Example pull-request body

```markdown
## Component

- Manufacturer: Example Manufacturer
- Part number: ABC123
- Component key: example-mfr-abc123
- Risk: Medium

## Sources

- Primary datasheet: revision 4, SHA-256 ...
- Manufacturer STEP model: SHA-256 ...

## Generated artifacts

- Symbol: Company_Electrical:ABC123
- Footprint: Company_Electrical:TerminalBlock_ABC123_1x03_P5.08mm
- Test project: test-projects/example-mfr-abc123

## Validation

- Schema: passed
- Evidence: passed
- Pin-pad parity: passed
- Geometry: passed
- KiCad parse/export: passed
- ERC/DRC fixture: passed
- Deterministic regeneration: passed

## Assumptions

None.

## Review

- [ ] Electrical review
- [ ] Mechanical review
- [ ] 3D orientation review
```

# Appendix C: Recommended first fixture set

| Fixture | Purpose |
|---|---|
| Two-pin passive device | Simplest symbol and footprint integration. |
| Three-position terminal block | Parametric pitch and body generation. |
| Eight-pin relay | Multi-unit symbol and contact/coil semantics. |
| Pressure transmitter connector | Power, signal, and shield pin typing. |
| Duet-style controller module | Large multi-unit module and connector placement. |
| Existing imported footprint | Validate and normalize third-party ECAD artifacts. |

# Appendix D: Future capabilities

The architecture can later support:

- Generation of machine-level schematic sheets from connection specifications.
- Connector mating-pair consistency checks.
- Cable and wire schedule generation.
- Terminal-strip and DIN-rail layout generation.
- Bill-of-materials integration.
- PLM or ERP synchronization.
- Company-wide component search.
- Automated migration between KiCad major versions.
- Automated revision comparison and change-impact analysis, including reuse of approved component primitives.
