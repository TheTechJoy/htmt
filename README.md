# HTMT 1.0 — HyperText Markup Transcript

A small, human-readable XML format for conversations: who said what, when, in response to what, what it meant, and what it connects to.

**Specification:** `index.html` (publish with GitHub Pages; no build step needed).

```xml
<transcript xmlns="https://thetechjoy.com/htmt/1.0" version="1.0">
  <body>
    <turn speaker="Ana">Can we ship on Friday?</turn>
    <turn speaker="Ben"><decision status="accepted">Yes, Friday.</decision></turn>
  </body>
</transcript>
```

## Quick start

```
git clone https://github.com/TheTechJoy/htmt && cd htmt
make setup                                   # .venv with lxml, needed only to validate
make convert IN=meeting.vtt OUT=meeting.htmt  # VTT, SRT, TXT or Whisper/AssemblyAI JSON
make validate FILES=meeting.htmt
```

Without `make`:

```
python3 tools/to_htmt.py meeting.vtt -o meeting.htmt --title "Weekly sync" --date 2026-10-07 --merge
pip install -r requirements.txt
python3 tools/validate.py meeting.htmt
```

`to_htmt.py` builds the skeleton (participants, turns, timings). Marking up questions, decisions, actions and risks is the next step, by hand or with the AI skill below.

## Use it with an AI agent

`skills/htmt/` is an agent skill that converts, enriches and validates transcripts and helps add HTMT output to an app or transcription pipeline.

- **Claude Code:** `/plugin install htmt --marketplace TheTechJoy/htmt`
  (older versions: `/plugin marketplace add TheTechJoy/htmt`, then `/plugin install htmt@htmt`)
- **Other agents:** point them at `skills/htmt/SKILL.md`. `AGENTS.md` does this for agents that read it.

Then ask, for example: "Convert this Zoom transcript to HTMT and mark the decisions and action items."

## What is in the repository

```
htmt/
├── index.html              the specification (generated from src/ by tools/build.py)
├── htmt-1.0.rnc            normative RELAX NG schema (compact syntax)
├── htmt-1.0.rng            the same schema in XML syntax, used by the validator
├── examples/
│   ├── minimal.htmt        smallest conforming document
│   ├── engineering-standup.htmt   complete example from Section 18
│   ├── one-on-one.htmt     manager and direct report: questions, decisions, actions
│   ├── team-meeting.htmt   planning meeting with an AI notetaker: join/leave, screen share
│   └── board-meeting.htmt  many-speaker board meeting: motions, votes, public comment
├── tools/
│   ├── to_htmt.py          converter: WebVTT, SRT, plain text, Whisper and AssemblyAI JSON
│   ├── validate.py         reference validator: schema + integrity rules (Section 13.1)
│   ├── test.py             self-test suite
│   ├── build.py            assembles index.html, embedding the schema and examples verbatim
│   └── make_rng.py         maintainers: regenerates htmt-1.0.rng from htmt-1.0.rnc
├── tests/                  converter inputs and invalid documents used by test.py
├── skills/htmt/            AI agent skill and quick reference
├── .claude-plugin/         Claude Code plugin and marketplace manifests
└── src/                    specification source, split by section
```

## Validate a transcript

```
python3 tools/validate.py path/to/file.htmt   # or a folder of .htmt files
```

Exit status is non-zero if any file fails. The validator rejects documents with a DOCTYPE and parses with entity resolution and network access disabled, as Section 14.1 requires. It needs only `lxml`.

## Edit the specification

Edit the files in `src/`, the schema, or the examples, then run `make build` and `make check`. The schema and two examples are embedded into `index.html` at build time, so there is one source of truth for each. After changing `htmt-1.0.rnc`, run `make setup-dev` once and then `make schema` to regenerate `htmt-1.0.rng`.

## License

Released into the public domain under [The Unlicense](https://unlicense.org/). See `LICENSE`.
