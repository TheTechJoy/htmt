#!/usr/bin/env python3
"""Validate .htmt files against the HTMT 1.0 RELAX NG schema.

Usage: validate.py [-v] PATH [PATH ...]

Each PATH is an .htmt file or a directory (every *.htmt in it is checked).

Checks: XML well-formedness (DTDs rejected), schema validity, and the
reference-integrity rules in Section 13 that RELAX NG cannot express
(speaker/owner resolution when <participants> is present, fragment hrefs).

Requires lxml (pip install -r requirements.txt). The schema is read from
htmt-1.0.rng, the XML-syntax form of the normative htmt-1.0.rnc.
"""
import sys
import os
import glob

try:
    from lxml import etree
except ImportError:
    sys.exit("validate.py needs lxml: pip install -r requirements.txt")

HERE = os.path.dirname(os.path.abspath(__file__))
RNG = os.path.join(HERE, "..", "htmt-1.0.rng")
NS = "https://thetechjoy.com/htmt/1.0"
H = "{%s}" % NS


def load_schema():
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    return etree.RelaxNG(etree.parse(RNG, parser))


def clock(v):
    """Clock-time to seconds, or None if malformed (the schema check reports that)."""
    try:
        h, m, sec = v.split(":")
        return int(h) * 3600 + int(m) * 60 + float(sec)
    except ValueError:
        return None


def check(path, schema):
    errors = []
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    try:
        doc = etree.parse(path, parser)
    except etree.XMLSyntaxError as e:
        return [f"not well-formed: {e}"]
    except OSError as e:
        return [f"cannot read file: {e}"]
    if doc.docinfo.doctype:
        errors.append("DOCTYPE present (forbidden, Section 4.5)")
    if not schema.validate(doc):
        errors += [f"schema: line {e.line}: {e.message}" for e in schema.error_log]
    root = doc.getroot()
    ids = {el.get("id") for el in root.iter() if el.get("id")}
    participants = root.find(H + "participants")
    pids = set()
    if participants is not None:
        pids = {p.get("id") for p in participants if p.get("id")}
        for el in root.iter(H + "turn", H + "event"):
            s = el.get("speaker")
            if s and s not in pids:
                errors.append(f"line {el.sourceline}: speaker '{s}' is not a declared participant")
        for el in root.iter(H + "action"):
            o = el.get("owner")
            if o and o not in pids:
                errors.append(f"line {el.sourceline}: owner '{o}' is not a declared participant")
        for el in root.iter(H + "note"):
            a = el.get("author")
            if a and a not in pids:
                errors.append(f"line {el.sourceline}: author '{a}' is not a declared participant")
    for el in root.iter():
        for attr in ("href", "source"):
            v = el.get(attr) or ""
            if v.startswith("#") and v[1:] not in ids:
                errors.append(f"line {el.sourceline}: unresolved internal reference {v}")
    byid = {el.get("id"): el for el in root.iter() if el.get("id")}
    for el in root.iter(H + "answer"):
        t = byid.get(el.get("to"))
        if t is not None and t.tag != H + "question":
            errors.append(f"line {el.sourceline}: answer/@to must target a <question>")
    for el in root.iter(H + "decision"):
        t = byid.get(el.get("supersedes"))
        if t is not None and t.tag != H + "decision":
            errors.append(f"line {el.sourceline}: decision/@supersedes must target a <decision>")
    for el in root.iter():
        if el.get("end") and not el.get("start"):
            errors.append(f"line {el.sourceline}: end without start")
        s, e, d = (clock(el.get(a)) if el.get(a) else None for a in ("start", "end", "duration"))
        if s is not None and e is not None and e < s:
            errors.append(f"line {el.sourceline}: end precedes start")
        if None not in (s, e, d) and el.tag == H + "event" and abs(e - s - d) > 1e-6:
            errors.append(f"line {el.sourceline}: duration does not equal end - start")
    medias = [m.get("id") for m in root.iter(H + "media")]
    for el in root.iter():
        m = el.get("media")
        if m and m not in medias:
            errors.append(f"line {el.sourceline}: media '{m}' is not declared")
    return errors


def main(argv):
    verbose = "-v" in argv
    files = []
    for a in argv:
        if a.startswith("-"):
            continue
        files += sorted(glob.glob(os.path.join(a, "*.htmt"))) if os.path.isdir(a) else [a]
    if not files:
        sys.exit(__doc__.strip().splitlines()[2])
    schema = load_schema()
    bad = 0
    for f in files:
        errs = check(f, schema)
        status = "OK " if not errs else "FAIL"
        print(f"{status} {f}")
        for e in errs:
            print("    " + e)
        bad += bool(errs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
