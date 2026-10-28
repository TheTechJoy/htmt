#!/usr/bin/env python3
"""Regenerate htmt-1.0.rng (RELAX NG XML syntax) from the normative htmt-1.0.rnc.

Maintainers only: run after editing htmt-1.0.rnc. Needs the packages in
requirements-dev.txt (rnc2rng). Users and validate.py only need the
committed htmt-1.0.rng.

Usage: make_rng.py           write htmt-1.0.rng
       make_rng.py --check   exit 1 if htmt-1.0.rng differs from a fresh conversion
"""
import os
import re
import sys

try:
    import rnc2rng
except ImportError:
    if __name__ == "__main__":
        sys.exit("make_rng.py needs rnc2rng: pip install -r requirements-dev.txt")
    raise

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RNC = os.path.join(ROOT, "htmt-1.0.rnc")
RNG = os.path.join(ROOT, "htmt-1.0.rng")
HEADER = """<?xml version="1.0"?>
<!-- HTMT 1.0 schema, RELAX NG XML syntax.
     Equivalent to htmt-1.0.rnc, which is normative; if they differ, the .rnc governs.
     Used by tools/validate.py so that validation needs only lxml.
     Regenerate from the .rnc with: python3 tools/make_rng.py
     Released into the public domain under The Unlicense (https://unlicense.org/). -->
"""


def convert():
    """Return the text of htmt-1.0.rng as generated from htmt-1.0.rnc."""
    rng = rnc2rng.dumps(rnc2rng.load(RNC))
    # rnc2rng emits an illegal xmlns:local="" declaration for `namespace local = ""`;
    # the nsName ns="" it produces is correct, so just drop the declaration.
    rng = re.sub(r'\s+xmlns:local=""', "", rng)
    rng = rng.replace('http://www.w3.org/2001/XMLSchema"', 'http://www.w3.org/2001/XMLSchema-datatypes"')
    return HEADER + re.sub(r"^<\?xml[^>]*\?>\s*", "", rng)


def main(argv):
    rng = convert()
    if "--check" in argv:
        with open(RNG, encoding="utf-8") as f:
            if f.read() != rng:
                return "htmt-1.0.rng is out of date: run python3 tools/make_rng.py"
        print("htmt-1.0.rng is up to date")
        return 0
    with open(RNG, "w", encoding="utf-8") as f:
        f.write(rng)
    print("wrote htmt-1.0.rng", len(rng), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
