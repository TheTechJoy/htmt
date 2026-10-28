#!/usr/bin/env python3
"""Validate .htmt files against the HTMT 1.0 RELAX NG schema.

Usage: validate.py [-v] FILE.htmt [FILE.htmt ...]

Checks: XML well-formedness (DTDs rejected), schema validity, and the
reference-integrity rules in Section 13 that RELAX NG cannot express
(speaker/owner resolution when <participants> is present, fragment hrefs).
"""
import sys
import os
import re
import rnc2rng
from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
RNC = os.path.join(HERE, "..", "htmt-1.0.rnc")
NS = "https://thetechjoy.com/htmt/1.0"
H = "{%s}" % NS


def load_schema():
    rng_text = rnc2rng.dumps(rnc2rng.load(RNC))
    # rnc2rng emits an illegal xmlns:local="" declaration for `namespace local = ""`;
    # the nsName ns="" it produces is correct, so just drop the declaration.
    rng_text = re.sub(r'\s+xmlns:local=""', "", rng_text)
    rng_text = rng_text.replace('http://www.w3.org/2001/XMLSchema"', 'http://www.w3.org/2001/XMLSchema-datatypes"')
    return etree.RelaxNG(etree.fromstring(rng_text.encode()))


def clock(v):
    h, m, sec = v.split(":")
    return int(h) * 3600 + int(m) * 60 + float(sec)


def check(path, schema):
    errors = []
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    try:
        doc = etree.parse(path, parser)
    except etree.XMLSyntaxError as e:
        return [f"not well-formed: {e}"]
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
        s, e, d = el.get("start"), el.get("end"), el.get("duration")
        if e and not s:
            errors.append(f"line {el.sourceline}: end without start")
        if s and e and clock(e) < clock(s):
            errors.append(f"line {el.sourceline}: end precedes start")
        if s and e and d and el.tag == H + "event" and abs(clock(e) - clock(s) - clock(d)) > 1e-6:
            errors.append(f"line {el.sourceline}: duration does not equal end - start")
    medias = [m.get("id") for m in root.iter(H + "media")]
    for el in root.iter():
        m = el.get("media")
        if m and m not in medias:
            errors.append(f"line {el.sourceline}: media '{m}' is not declared")
    return errors


def main(argv):
    verbose = "-v" in argv
    files = [a for a in argv if not a.startswith("-")]
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
