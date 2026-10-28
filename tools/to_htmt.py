#!/usr/bin/env python3
"""Convert an existing transcript into an HTMT 1.0 document.

Usage: to_htmt.py [options] INPUT [-o OUTPUT.htmt]

INPUT formats (picked by extension, or --format):
  .vtt   WebVTT captions. Speakers from <v Name> voice tags or "Name: " prefixes.
  .srt   SubRip captions. Speakers from "Name: " or "[Name]" prefixes.
  .txt   Plain text. Either "Name: text" lines (optionally led by a
         [HH:MM:SS] or (HH:MM:SS) timestamp), or a header line ("Name  0:03"
         or "Name:") followed by the paragraph that person spoke. Lines with
         no speaker continue the previous turn.
  .json  ASR output: {"segments": [{"start", "end", "text", "speaker"?}]}
         with times in seconds (Whisper, whisperX), or
         {"utterances": [{"start", "end", "text", "speaker"}]} with times in
         milliseconds (AssemblyAI). A bare list of segments also works.

Options:
  --title TEXT     transcript title
  --date ISO       date or date-time of the conversation (2026-10-07 or 2026-10-07T18:30:00-05:00)
  --id ID          document id
  --lang TAG       xml:lang, e.g. en
  --media SRC      add a <media> element pointing at the recording
  --merge          join consecutive cues from the same speaker into one turn
  --format FMT     force vtt | srt | txt | json
  -o FILE          write here instead of stdout

The output is a mechanical skeleton: participants (with neutral ids p1, p2,
...), turns (t1, t2, ...) and timings. Adding semantic markup (questions,
decisions, actions, ...) is a separate step; see skills/htmt/SKILL.md.
Uses only the Python standard library.
"""
import argparse
import json
import math
import os
import re
import sys
from xml.sax.saxutils import escape, quoteattr

NS = "https://thetechjoy.com/htmt/1.0"
NAME = r"[A-Z][\w.'\-]*(?: [\w.'\-]+){0,3}"
# "Name: text" (a name of up to four words) or "[Name] text".
NAME_PREFIX = re.compile(r"^\s*(?:\[([^\]]{1,60})\]\s*:?|(" + NAME + r"):)\s+(.*)$")
NAME_ONLY = re.compile(r"^\s*(" + NAME + r"):\s*$")
# Words that end in a colon in ordinary prose, and bracketed sound cues: not speakers.
NOT_SPEAKERS = {
    "note", "notes", "time", "date", "update", "edit", "todo", "action", "actions",
    "decision", "agenda", "question", "answer", "summary", "subject", "re", "ps",
    "http", "https", "warning", "error", "example", "step", "tip",
    "music", "applause", "laughter", "laughs", "laughing", "inaudible", "crosstalk",
    "silence", "noise", "background noise", "cough", "coughs", "pause", "unintelligible",
}
CUE_TIME = re.compile(r"((?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})\s*-->\s*((?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})")
TXT_STAMP = re.compile(r"^\s*[\[(](\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)[\])]\s*(.*)$")
TXT_HEADER = re.compile(r"^\s*([^\s:][^:]{0,59}?)\s{2,}(\d{1,2}:\d{2}(?::\d{2})?)\s*$")
# Caption markup only (WebVTT spans and timestamps, SubRip font tags); other "<...>" is real text.
CUE_TAGS = re.compile(r"</?(?:c|i|b|u|v|lang|ruby|rt|font)(?:[.\s][^>]*)?>|<\d+:\d{2}(?::\d{2})?\.\d{3}>", re.I)
XML_INVALID = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff￾￿]")
RESERVED_ID = re.compile(r"[tp]\d+|media")


def seconds(stamp):
    """'1:02:03.5', '02:03', '00:00:01,250' -> float seconds."""
    total = 0.0
    for p in stamp.replace(",", ".").split(":"):
        total = total * 60 + float(p)
    return total


def clock(sec):
    """float seconds -> HTMT clock-time, HH:MM:SS with milliseconds only when present."""
    ms = int(round(sec * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    out = "%02d:%02d:%02d" % (h, m, s)
    return out + (".%03d" % ms).rstrip("0") if ms else out


def xml_safe(text):
    return XML_INVALID.sub("", text)


def clean(text, cue=False):
    if cue:
        text = CUE_TAGS.sub("", text)
    return re.sub(r"\s+", " ", xml_safe(text)).strip()


def is_speaker(name):
    return name.strip().lower() not in NOT_SPEAKERS


def split_speaker(text):
    m = NAME_PREFIX.match(text)
    if m:
        name = clean(m.group(1) or m.group(2))
        if name and is_speaker(name):
            return name, m.group(3)
    return None, text


def parse_cues(raw):
    """VTT and SRT: return [(start, end, speaker, text)].

    A cue runs from its timing line to the next cue's identifier or timing
    line, so a blank line inside cue text does not cut the cue short.
    """
    raw = re.sub(r"(?ms)^(?:NOTE|STYLE|REGION)\b.*?(?=\n[ \t]*\n|\Z)", "", raw.replace("\r\n", "\n"))
    lines = raw.split("\n")
    timings = [i for i, line in enumerate(lines) if CUE_TIME.search(line)]
    out = []
    for k, i in enumerate(timings):
        j = timings[k + 1] if k + 1 < len(timings) else len(lines)
        if k + 1 < len(timings) and j >= 2 and lines[j - 1].strip() and not lines[j - 2].strip():
            j -= 1  # the next cue's identifier line
        m = CUE_TIME.search(lines[i])
        body = "\n".join(lines[i + 1:j])
        speaker = None
        v = re.search(r"<v(?:\.[\w.]+)?\s+([^>]+)>", body)
        if v:
            speaker = clean(v.group(1)) or None
        body = clean(body, cue=True)
        if not speaker:
            speaker, body = split_speaker(body)
        if body:
            out.append((seconds(m.group(1)), seconds(m.group(2)), speaker, body))
    return out


def parse_txt(raw):
    turns = []
    for line in raw.replace("\r\n", "\n").split("\n"):
        if not line.strip():
            continue
        h = TXT_HEADER.match(line)
        n = NAME_ONLY.match(line)
        if h:
            turns.append([seconds(h.group(2)), None, clean(h.group(1)), ""])
            continue
        if n and is_speaker(n.group(1)):
            turns.append([None, None, clean(n.group(1)), ""])
            continue
        start = None
        s = TXT_STAMP.match(line)
        if s:
            start, line = seconds(s.group(1)), s.group(2)
        speaker, text = split_speaker(line)
        text = clean(text)
        if speaker is None and start is None and turns:
            turns[-1][3] = (turns[-1][3] + " " + text).strip()
        else:
            turns.append([start, None, speaker, text])
    return [tuple(t) for t in turns if t[3]]


def json_time(value, scale):
    try:
        sec = float(value) * scale
    except (TypeError, ValueError):
        return None
    return sec if math.isfinite(sec) and sec >= 0 else None


def parse_json(raw):
    data = json.loads(raw)
    scale = 1.0
    if isinstance(data, dict) and "utterances" in data:
        items, scale = data["utterances"], 0.001
    elif isinstance(data, dict):
        items = data.get("segments", [])
    else:
        items = data
    out = []
    for it in items:
        text = clean(str(it.get("text", "")))
        if not text:
            continue
        speaker = it.get("speaker")
        speaker = clean(str(speaker)) if speaker is not None else None
        out.append((json_time(it.get("start"), scale), json_time(it.get("end"), scale), speaker or None, text))
    return out


def merge(turns):
    merged = []
    for t in turns:
        if merged and t[2] is not None and merged[-1][2] == t[2]:
            p = merged[-1]
            merged[-1] = (p[0], t[1], p[2], p[3] + " " + t[3])  # the later cue decides the end
        else:
            merged.append(t)
    return merged


def render(turns, args):
    ids, order = {}, []
    for _, _, sp, _ in turns:
        if sp is not None and sp not in ids:
            # Neutral ids: the spec says ids SHOULD NOT be derived from personal data (14.4).
            ids[sp] = "p%d" % (len(ids) + 1)
            order.append(sp)
    if args.merge:
        turns = merge(turns)

    root = '<transcript xmlns="%s" version="1.0"' % NS
    for attr, val in (("id", args.id), ("title", args.title), ("date", args.date), ("xml:lang", args.lang)):
        if val:
            root += " %s=%s" % (attr, quoteattr(xml_safe(val)))
    out = ['<?xml version="1.0" encoding="UTF-8"?>', root + ">"]
    out.append("  <meta>")
    out.append('    <property name="converted-from">%s</property>' % escape(args.format))
    out.append("  </meta>")
    if order:
        out.append("  <participants>")
        for sp in order:
            out.append("    <person id=%s name=%s />" % (quoteattr(ids[sp]), quoteattr(sp)))
        out.append("  </participants>")
    if args.media:
        out.append('  <media id="media" src=%s />' % quoteattr(xml_safe(args.media)))
    out.append("  <body>")
    for n, (start, end, sp, text) in enumerate(turns, 1):
        attrs = ' id="t%d"' % n
        if sp is not None:
            attrs += " speaker=%s" % quoteattr(ids[sp])
        if start is not None:
            attrs += ' start="%s"' % clock(start)
            if end is not None and end >= start:
                attrs += ' end="%s"' % clock(end)
        out.append("    <turn%s>%s</turn>" % (attrs, escape(text)))
    out.append("  </body>")
    out.append("</transcript>")
    return "\n".join(out) + "\n"


def main(argv):
    ap = argparse.ArgumentParser(description="Convert a transcript to HTMT 1.0.")
    ap.add_argument("input")
    ap.add_argument("-o", "--output")
    ap.add_argument("--format", choices=["vtt", "srt", "txt", "json"])
    ap.add_argument("--title")
    ap.add_argument("--date")
    ap.add_argument("--id")
    ap.add_argument("--lang")
    ap.add_argument("--media")
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args(argv)
    args.format = args.format or os.path.splitext(args.input)[1].lstrip(".").lower()
    if args.format not in ("vtt", "srt", "txt", "json"):
        ap.error("cannot tell the format from the extension; pass --format")
    if args.id and RESERVED_ID.fullmatch(args.id):
        ap.error("--id %s clashes with generated ids (t1, p1, media); pick another" % args.id)
    with open(args.input, encoding="utf-8-sig") as f:
        raw = f.read()
    if args.format in ("vtt", "srt"):
        turns = parse_cues(raw)
    elif args.format == "txt":
        turns = parse_txt(raw)
    else:
        turns = parse_json(raw)
    if not turns:
        sys.exit("no turns found in %s" % args.input)
    doc = render(turns, args).encode("utf-8")
    if args.output:
        with open(args.output, "wb") as f:
            f.write(doc)
        print("wrote %s (%d turns)" % (args.output, doc.count(b"<turn ")), file=sys.stderr)
    else:
        sys.stdout.buffer.write(doc)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
