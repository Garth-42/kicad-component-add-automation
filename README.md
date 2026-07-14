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

## Private library bootstrap

Initialize a private component-library repository with secret-safe templates and default ignore rules:

```bash
kcf init-library ../my-private-kicad-library --private
kcf doctor --repo-root ../my-private-kicad-library
```

The bootstrap command writes `.kcf/config.example.yaml`, `.kcf/slack.example.yaml`, `.env.example`, and a conservative `.gitignore`. Real Slack/model-provider credentials should be supplied through environment variables, local gitignored config, or a secret manager rather than committed files.
