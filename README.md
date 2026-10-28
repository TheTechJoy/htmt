# HTMT 1.0 — HyperText Markup Transcript

A small, human-readable XML format for conversations: who said what, when, in response to what, what it meant, and what it connects to.

**Specification:** `index.html` (publish with GitHub Pages; no build step needed).

```
htmt/
├── index.html              the specification (generated from src/ by tools/build.py)
├── htmt-1.0.rnc            normative RELAX NG schema (compact syntax)
├── examples/
│   ├── minimal.htmt        smallest conforming document
│   └── engineering-standup.htmt   complete example from Section 18
├── tools/
│   ├── validate.py         reference validator: schema + integrity rules (Section 13.1)
│   └── build.py            assembles index.html, embedding the schema and examples verbatim
└── src/                    specification source, split by section
```

## Validate a transcript

```
pip install lxml rnc2rng
python3 tools/validate.py path/to/file.htmt
```

Exit status is non-zero if any file fails. The validator rejects documents with a DOCTYPE and parses with entity resolution and network access disabled, as Section 14.1 requires.

## Edit the specification

Edit the files in `src/`, the schema, or the examples, then run `python3 tools/build.py`. The schema and both examples are embedded into `index.html` at build time, so there is one source of truth for each.

## License

Specification, schema, validator, and examples are released into the public domain under [The Unlicense](https://unlicense.org/). See `LICENSE`.
