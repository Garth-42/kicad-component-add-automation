# KiCad Component Factory Roadmap

This roadmap converts the architecture baseline into an implementation sequence. It assumes the current first vertical slice remains the foundation: validate a canonical component spec, generate deterministic KiCad symbol and footprint artifacts, create a minimal test project, and check generated output for drift.

## Current baseline

- Canonical component specs can be loaded from YAML/JSON-like input and validated by domain rules.
- The CLI supports `doctor`, `init-library --private`, `schema`, `validate`, `generate`, and `check` commands, with `schema` exporting the committed canonical component JSON Schema.
- Private component-library repositories can be bootstrapped with safe `.kcf` templates, `.env.example`, default local-secret ignore rules, and doctor checks for obvious committed secret patterns.
- Deterministic artifact generation covers a first terminal-block example, including KiCad library files, a test project, SVG review artifacts, and a validation report.
- Unit tests cover schema loading, validation failures, artifact generation, and CLI drift checking.

## Phase 1: Harden the deterministic core

1. Keep the committed canonical component JSON Schema synchronized with the domain model and CLI export.
2. Add stricter canonical-spec validation for source evidence, assumptions, mechanical regions, 3D model metadata, and release constraints.
3. Expand generator coverage beyond the first terminal-block slice with reusable templates for common through-hole connectors, simple SMD passives, and IC packages.
4. Add golden-file tests that assert byte-stable KiCad output for representative component families.
5. Add repository-wide regeneration checks so committed generated artifacts can be compared against freshly generated output.

## Phase 2: Repository workflow and release metadata

1. Implement the recommended component-library repository layout, including `.kcf` policy files, `components/`, `libraries/`, `schemas/`, and `test-projects/` directories.
2. Expand the private-library bootstrap flow with richer policy templates and optional Git initialization.
3. Add source manifests with SHA-256 hashes, source-retention modes, document revision fields, retrieval dates, and external-reference handling.
4. Add review-response retention policies for approval summaries, Slack metadata, full embedded thread exports, external references, and restricted local-only responses.
5. Generate release manifests that record spec hashes, generator versions, KiCad target versions, validation report hashes, known limitations, approver metadata, and review-retention limitations.
6. Add a Git adapter that creates part branches, stages candidate files, verifies a clean candidate worktree, and commits release candidates without force-pushing.
7. Add CI entry points for component checks, full-library regression checks, and secret/configuration safety checks.

## Phase 3: Human review workflow

1. Introduce workflow jobs, immutable events, and the architecture state machine from `DRAFT` through `RELEASED`.
2. Persist approvals with actor, timestamp, scope, and approved specification hash.
3. Invalidate downstream workflow states when sources, approved specs, generator versions, or style policies change.
4. Add review questions as first-class workflow records with blocking and non-blocking semantics so agents and validators can ask for help without stopping unrelated work.
5. Generate workflow status summaries for in-progress parts, including current state, branch, findings, open questions, required actions, review bundle paths, and next recommended action.
6. Generate richer review bundles with symbol, footprint, footprint-layer, optional 3D, and validation-report artifacts.
7. Add commands for answering questions, approving specs, approving release candidates, rejecting candidates, and recording changes requested.
8. Keep approvals hash-bound so Slack, CLI, and web review commands all approve or deny an exact specification or candidate hash.

## Phase 4: Local service and web UI

1. Add the FastAPI application layer around the same services used by the CLI.
2. Add SQLite persistence for jobs, events, approvals, and source-document metadata.
3. Add SQLite persistence for review questions, answers, notification events, and status snapshots or projections.
4. Add server-sent events for job progress, validation findings, questions, approvals, denials, and required actions.
5. Add status API endpoints for in-progress parts and job detail pages.
6. Build the React/TypeScript local UI for job creation, source review, canonical-spec editing, rendered previews, approval gates, open questions, and workflow dashboards.
7. Keep the default service loopback-only for local-first operation.

## Phase 5: KiCad and rendering integrations

1. Add a KiCad CLI adapter with configurable executable paths and portable subprocess handling.
2. Run KiCad syntax, ERC, DRC, and plotting operations where available.
3. Replace or supplement simple SVG renderers with KiCad-derived previews for release review.
4. Add environment-aware `doctor` checks for KiCad version, executable availability, writable repository paths, and policy/schema compatibility.
5. Preserve deterministic fallback checks when KiCad is unavailable in CI or development environments.

## Phase 6: AI-assisted extraction behind validation gates

1. Define provider-neutral model-gateway interfaces and typed structured-output contracts.
2. Add source-document extraction for identity, pin tables, dimensions, package variants, and evidence locations.
3. Add symbol-planning and footprint-planning agents that propose semantic plans, not KiCad S-expressions.
4. Persist model metadata, prompt versions, input hashes, confidence, uncertainties, and raw-response references.
5. Block release when extracted facts are missing, conflicting, unsupported, or unapproved assumptions.

## Phase 7: Team and scale features

1. Add optional Slack integration for review notifications, signed interactive approve/deny actions, question threads, and `/kcf status` queries.
2. Add optional GitHub integration for private fork setup, pushing part branches, and opening pull requests.
3. Add identity mapping from Slack and Git hosting users to KCF actors and reviewer roles.
4. Add policy-driven risk gates for safety-related, mains-rated, or high-risk components.
5. Add migration tooling for schema and generator changes across an existing library.
6. Add library release tags and changelog generation for coherent library snapshots.
7. Add adapters for local model providers after the hosted-provider path is stable.
8. Add optional secret-manager integrations for Slack, model-provider, and Git-host credentials.

## Near-term recommended next issue

Implement the workflow status model and CLI status queries. This should add persisted job/event/status structures, open-question and required-action summaries, and a `kcf jobs status` command that can later power the web UI and Slack `/kcf status` integration.
