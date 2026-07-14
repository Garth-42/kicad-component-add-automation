# KiCad Component Factory

First vertical slice for deterministic KiCad component generation from canonical YAML.

## Development

```bash
python -m pip install -e '.[dev]'
pytest
```

## CLI

```bash
kcf validate tests/fixtures/terminal_block.yaml
kcf generate tests/fixtures/terminal_block.yaml --output-root build/example
kcf check tests/fixtures/terminal_block.yaml --output-root build/example
```

Generated candidates include a review bundle under `components/<manufacturer>/<component>/review/`
with `symbol.svg`, `footprint.svg`, `footprint-layers.svg`, `validation-report.json`, and
`model-3d.svg` when the canonical specification references a 3D model path.

## Private library bootstrap

Initialize a private component-library repository with secret-safe templates and default ignore rules:

```bash
kcf init-library ../my-private-kicad-library --private
kcf doctor --repo-root ../my-private-kicad-library
```

The bootstrap command writes `.kcf/config.example.yaml`, `.kcf/slack.example.yaml`, `.env.example`, and a conservative `.gitignore`. Real Slack/model-provider credentials should be supplied through environment variables, local gitignored config, or a secret manager rather than committed files.

## Workflow status

Inspect persisted workflow jobs from a private library repository:

```bash
kcf jobs status --repo-root ../my-private-kicad-library
kcf jobs status job-123 --repo-root ../my-private-kicad-library --json
kcf jobs answer-question job-123 q-1 --answer "Pin 1 is square." --actor reviewer --repo-root ../my-private-kicad-library
kcf jobs approve-spec job-123 --spec-hash sha256:... --actor reviewer --repo-root ../my-private-kicad-library
kcf jobs reject-candidate job-123 --candidate-hash sha256:... --reason "Courtyard too tight." --actor reviewer --repo-root ../my-private-kicad-library
kcf jobs approve-release job-123 --candidate-hash sha256:... --actor reviewer --repo-root ../my-private-kicad-library
kcf jobs reconcile job-123 --actor automation --repo-root ../my-private-kicad-library
```

Jobs are read from `.kcf/runtime/jobs/*.json` and status output summarizes state, open questions, finding counts, branch, review bundle path, and the next required action.
Review commands update the same job files with immutable workflow events and require exact specification or candidate hashes for approvals and release decisions. Successful spec and release approvals also persist dedicated approval records with actor, timestamp, approval scope, approved hash, and the event that recorded the decision. Specification approvals capture source-manifest, generator-version, and style-policy baselines; `jobs reconcile` invalidates downstream candidate/release state when any approved baseline changes so the part must be re-reviewed before release.
