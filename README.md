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
