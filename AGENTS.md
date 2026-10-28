# Instructions for AI agents

This repository defines HTMT 1.0, an XML format for conversation transcripts.

- To create, convert, enrich or validate an HTMT document, follow
  `skills/htmt/SKILL.md`. The element reference is `skills/htmt/reference.md`.
- Validate every `.htmt` file you write: `python3 tools/validate.py FILE`.
- Editing this repository: change `src/`, `htmt-1.0.rnc` or `examples/`, never
  `index.html` directly; then run `make build` and `make check`. After
  changing `htmt-1.0.rnc`, regenerate `htmt-1.0.rng` with `make schema`.
- Example content must be fictional: no real names, organizations or URLs
  other than `example.com` / `example.org`.
