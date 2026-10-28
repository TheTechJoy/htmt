#!/usr/bin/env python3
"""Assemble index.html from src/part*.html, embedding the schema and examples verbatim."""
import glob
import html
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


parts = sorted(glob.glob(os.path.join(ROOT, "src", "part*.html")))
page = "".join(open(p, encoding="utf-8").read() for p in parts)
subs = {
    "{{RNC}}": read("htmt-1.0.rnc").rstrip(),
    "{{EXAMPLE}}": read("examples/engineering-standup.htmt").rstrip(),
    "{{MINIMAL}}": read("examples/minimal.htmt").rstrip(),
}
for k, v in subs.items():
    assert k in page, k
    page = page.replace(k, html.escape(v, quote=False))
assert "{{" not in page
page = page.replace("<table", "<div class=\"table-wrap\"><table").replace("</table>", "</table></div>")
with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
    f.write(page)
print("wrote index.html", len(page), "bytes")
