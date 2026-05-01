# envdrift

> Detect drift between `.env` files. Zero dependencies. One file. ~100 lines.

The classic "works on my machine" bug: someone added `STRIPE_KEY` to their `.env` but forgot to update `.env.example`, and now CI is broken. **envdrift** is a tiny CLI that catches this in about a second.

## Why

Every team has this pain. Existing solutions are either:
- Heavy npm packages with 20 transitive deps
- Tied to a specific framework
- Or just "grep + eyeballs"

envdrift is a single Python file. Drop it in your repo, wire it into pre-commit / CI, done.

## Install

```bash
curl -sL https://raw.githubusercontent.com/ChronoKairo/envdrift/main/envdrift.py -o envdrift
chmod +x envdrift
```

Or just `python3 envdrift.py ...`. Requires Python 3.8+.

## Usage

```bash
# Compare two files
envdrift .env.example .env

# Compare many
envdrift .env.example .env .env.local .env.production

# Also flag empty/placeholder values (changeme, todo, xxx, ...)
envdrift --strict .env.example .env
```

### Example output

```
envdrift: comparing 2 file(s), 5 unique key(s)

  [missing in .env]
    - STRIPE_SECRET
  [placeholder values in .env]
    - DATABASE_URL = 'changeme'

envdrift: drift detected
```

Exit codes: `0` clean, `1` drift, `2` usage error — pipeline-friendly.

## Pre-commit hook

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: envdrift
      name: envdrift
      entry: python3 envdrift.py .env.example .env
      language: system
      pass_filenames: false
```

## License

MIT
