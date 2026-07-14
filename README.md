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

## GitHub runner workflow for uploaded YAML

This repository includes two GitHub Actions workflows:

- **Python Tests** (`.github/workflows/python-tests.yml`) runs the unit tests and a CLI smoke test.
- **Component Check** (`.github/workflows/component-check.yml`) runs deterministic component checks when a component YAML file changes.

To make a YAML upload run on GitHub runners:

1. Commit these workflow files to the default branch.
2. Add a component spec at `components/<manufacturer>/<part>/component.yaml` in a branch or pull request.
3. Push the branch or open the pull request.
4. GitHub Actions will run **Component Check**, which validates the YAML, generates artifacts into `.kcf-ci/generated`, checks deterministic regeneration, and uploads review artifacts.

The workflow also watches `tests/fixtures/*.yaml` so the included fixture can exercise CI before real component files exist. It can also be run manually from the GitHub Actions tab because `workflow_dispatch` is enabled.
