# HTMT 1.0 quick reference

Condensed from the normative schema `htmt-1.0.rnc` and the specification
`index.html`. If this file and the schema disagree, the schema governs.

## Document shape

```xml
<?xml version="1.0" encoding="UTF-8"?>
<transcript xmlns="https://thetechjoy.com/htmt/1.0" version="1.0"
            id="..." title="..." date="2026-10-07T18:30:00-05:00" duration="01:32:15" xml:lang="en">
  <meta>          <!-- optional, first -->
    <property name="source-system">...</property>
  </meta>
  <participants>  <!-- optional, after meta -->
    <person id="p1" name="..." role="..." />
    <agent id="p2" name="..." model="..." provider="..." role="notetaker" />
  </participants>
  <media id="rec" type="audio" src="./rec.m4a" duration="..." />  <!-- zero or more -->
  <body>          <!-- required, last -->
    <topic name="...">  <turn/> <event/> <note/> <topic/> ...  </topic>
    <turn speaker="p1" start="00:00:04" end="00:00:09.2">Words spoken.</turn>
    <event type="laughter" start="00:01:00" />
  </body>
</transcript>
```

The smallest valid document:

```xml
<transcript xmlns="https://thetechjoy.com/htmt/1.0" version="1.0">
  <body><turn speaker="Ana">Hello.</turn></body>
</transcript>
```

## Value types

| Type | Form | Example |
|---|---|---|
| id | XML name, unique in the document | `t12`, `d3`, `p1` |
| token | lowercase, hyphenated | `screen-share`, `source-system` |
| clock | `H+:MM:SS` with optional `.f` (1 to 6 digits) | `00:13:42.220`, `1:02:07` |
| datetime | ISO 8601 date-time | `2026-10-07T18:30:12-05:00` |
| date | date or date-time | `2026-11-04` |
| confidence | decimal from 0 to 1 | `0.82` |
| uri | URI; `#id` is an internal reference | `#a1`, `other.htmt#t9`, `https://...` |

## Elements

| Element | Where | Attributes (required in **bold**) | Content |
|---|---|---|---|
| `transcript` | root | **`version="1.0"`**, `id`, `title`, `date`, `duration` | meta?, participants?, media*, body |
| `meta` | transcript | | `property`* |
| `property` | meta | **`name`** (token) | text |
| `participants` | transcript | | `person` and `agent`, in any order |
| `person` | participants | **`id`**, `name`, `role`, `href` | extension elements only |
| `agent` | participants | **`id`**, `name`, `model`, `provider`, `role`, `href` | extension elements only |
| `media` | transcript | **`src`**, `id`, `type` (audio, video, text, other), `duration`, `offset` | extension elements only |
| `body` | transcript | | turn, event, topic, note |
| `topic` | body, topic | **`name`**, `id`, `start`, `end` | turn, event, topic, note |
| `turn` | body, topic | `id`, `speaker`, `confidence` (transcription), `start`, `end`, `datetime`, `media` | inline |
| `event` | body, topic | **`type`** (token), `id`, `speaker`, `duration`, `start`, `end`, `datetime`, `media` | inline |
| `ref` | inline | **`href`**, `type` (token: ticket, document, transcript, dashboard, person) | inline |

**Inline** content is text mixed with `ref`, the semantic elements below, and
extension elements.

## Semantic elements (inline, inside a turn or event)

All take optional `id` and `summary` (a normalized restatement).

| Element | Extra attributes | Use for |
|---|---|---|
| `question` | | A question someone asked |
| `answer` | **`to`** (id of a `question`) | The reply to that question |
| `decision` | `status` (proposed, accepted, rejected, superseded), `supersedes` (id of a `decision`) | A choice the group made or considered |
| `action` | `owner`, `due` (date), `status` (open, done, cancelled) | A commitment to do something |
| `claim` | `confidence` (speaker certainty), `source` (uri) | An assertion that may be uncertain |
| `fact` | `source` (uri) | An assertion stated as established |
| `risk` | `severity` (low, medium, high, critical) | A stated risk |
| `quote` | `source` (uri) | Words quoted from elsewhere |
| `note` | `author`, `type` (token: summary, minutes, private, redaction) | Editorial or system annotation; may also stand alone in body or topic |

## Integrity rules (checked by tools/validate.py, not by the schema)

- When `<participants>` exists, every `speaker`, `owner` and `author` must be a declared participant id.
- Every `#id` in `href` or `source` must exist in the document.
- `answer/@to` must point at a `question`; `decision/@supersedes` must point at a `decision`.
- `end` needs `start`, and must not be earlier than it. On an `event` with all three, `duration` must equal `end - start`.
- A `media` attribute must name a declared `<media id>`.
- No `<!DOCTYPE>` (which also rules out entity declarations).

## Well-known event types

`silence`, `inaudible`, `crosstalk`, `laughter`, `applause`, `music`, `join`,
`leave` (need `speaker`), `recording-start`, `recording-stop`, `screen-share`,
`file-shared`, `reaction`, `tool-call`, `tool-result`, `system`. Any other
token is allowed.

## Extensions

Extension elements and attributes must use your own namespace, for example
`xmlns:acme="https://acme.example/htmt-ext"` then `<acme:sentiment value="..."/>`
or `acme:sentiment="negative"` on a turn. Never invent unprefixed elements.
Text inside an inline extension element is treated as spoken words.
