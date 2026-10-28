#!/usr/bin/env python3
"""Self-test for the HTMT repository. Standard library unittest; needs lxml.

Usage: python3 tools/test.py

Checks that every example validates, every file in tests/invalid/ fails with
the error named in its "expect:" comment, every file in tests/convert/
converts to a valid document, and index.html matches its sources. When
rnc2rng is installed (requirements-dev.txt) it also checks that a schema
generated from htmt-1.0.rnc accepts and rejects exactly what htmt-1.0.rng does.
"""
import glob
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import validate  # noqa: E402  (exits with an install hint if lxml is missing)


def run(*args):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=ROOT)


def files(pattern):
    return sorted(glob.glob(os.path.join(ROOT, pattern)))


class Examples(unittest.TestCase):
    def test_examples_validate(self):
        schema = validate.load_schema()
        examples = files("examples/*.htmt")
        self.assertGreaterEqual(len(examples), 5)
        for path in examples:
            with self.subTest(os.path.basename(path)):
                self.assertEqual(validate.check(path, schema), [])


class Invalid(unittest.TestCase):
    def test_invalid_documents_fail_with_expected_error(self):
        schema = validate.load_schema()
        fixtures = files("tests/invalid/*.htmt")
        self.assertGreaterEqual(len(fixtures), 1)
        for path in fixtures:
            with self.subTest(os.path.basename(path)):
                with open(path, encoding="utf-8") as f:
                    expect = re.search(r"<!-- expect: (.*?) -->", f.read()).group(1)
                errors = validate.check(path, schema)
                self.assertTrue(any(expect in e for e in errors), "%s not in %s" % (expect, errors))

    def test_cli_exit_status(self):
        self.assertEqual(run("tools/validate.py", "examples").returncode, 0)
        self.assertEqual(run("tools/validate.py", "tests/invalid").returncode, 1)


class Convert(unittest.TestCase):
    def test_every_input_converts_to_a_valid_document(self):
        schema = validate.load_schema()
        inputs = files("tests/convert/*")
        self.assertGreaterEqual(len(inputs), 1)
        with tempfile.TemporaryDirectory() as tmp:
            for path in inputs:
                for extra in ([], ["--merge"]):
                    with self.subTest(os.path.basename(path), merge=bool(extra)):
                        out = os.path.join(tmp, "out.htmt")
                        r = run("tools/to_htmt.py", path, "-o", out, "--title", "Test & <check>",
                                "--date", "2026-10-07", "--lang", "en", "--media", "rec.mp3", *extra)
                        self.assertEqual(r.returncode, 0, r.stderr)
                        self.assertEqual(validate.check(out, schema), [])

    def test_speakers_and_timing(self):
        r = run("tools/to_htmt.py", "tests/convert/captions.vtt", "--merge")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.count("<person "), 3)
        self.assertEqual(r.stdout.count("<turn "), 3)  # Ben's two cues merged
        self.assertIn('<person id="p2" name="Ben Carter" />', r.stdout)
        self.assertIn('speaker="p2" start="00:00:05" end="00:00:10"', r.stdout)
        self.assertIn("release &amp; the build", r.stdout)

    def test_assemblyai_milliseconds(self):
        r = run("tools/to_htmt.py", "tests/convert/assemblyai.json")
        self.assertIn('start="00:00:00.25" end="00:00:03.1"', r.stdout)

    def test_header_style_hours(self):
        r = run("tools/to_htmt.py", "tests/convert/header-style.txt")
        self.assertIn('start="01:02:07"', r.stdout)


class ConvertEdgeCases(unittest.TestCase):
    """Regression tests: each input once produced invalid output or lost text."""

    def convert(self, name, content, *extra):
        schema = validate.load_schema()
        with tempfile.TemporaryDirectory() as tmp:
            src, out = os.path.join(tmp, name), os.path.join(tmp, "out.htmt")
            with open(src, "w", encoding="utf-8", errors="surrogatepass") as f:
                f.write(content)
            r = run("tools/to_htmt.py", src, "-o", out, *extra)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(validate.check(out, schema), [])
            with open(out, encoding="utf-8") as f:
                return f.read()

    def test_control_characters_in_speaker_names(self):
        self.convert("a.vtt", "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<v Bob\x01>hi</v>\n")
        self.convert("a.json", '{"segments": [{"start": 0, "end": 1, "text": "hi", "speaker": "A\\u0001"}]}')
        self.convert("a.txt", "[Bo\x02b] hello\n", "--title", "T\x03")

    def test_lone_surrogate_in_json(self):
        doc = self.convert("a.json", '{"segments": [{"start": 0, "end": 1, "text": "bad \\ud800 x"}]}')
        self.assertIn("bad x", doc)

    def test_angle_brackets_in_plain_text_are_kept(self):
        doc = self.convert("a.txt", "Ana: If x <5 and y> 3 ok\n")
        self.assertIn("If x &lt;5 and y&gt; 3 ok", doc)

    def test_caption_tags_are_stripped(self):
        doc = self.convert("a.srt", '1\n00:00:01,000 --> 00:00:02,000\n<font color="red">Ana: <i>hi</i></font>\n')
        self.assertIn(">hi</turn>", doc)

    def test_bad_json_times_are_dropped(self):
        doc = self.convert("a.json", '[{"start": -1, "end": NaN, "text": "a"}, {"start": "x", "text": "b"}]')
        self.assertNotIn("start=", doc)

    def test_sound_cues_and_labels_are_not_speakers(self):
        doc = self.convert("a.txt", "Ana: Hello.\n[Applause] Thanks.\nNote: see the doc.\nTime: 5pm\n")
        self.assertEqual(doc.count("<person "), 1)
        self.assertEqual(doc.count("<turn "), 1)  # unlabelled lines continue the previous turn
        self.assertIn("Hello. [Applause] Thanks. Note: see the doc. Time: 5pm", doc)

    def test_bare_name_line_is_a_header(self):
        doc = self.convert("a.txt", "Alice:\nHello there.\nBob:\nHi.\n")
        self.assertEqual(doc.count("<person "), 2)
        self.assertIn('speaker="p2">Hi.</turn>', doc)

    def test_unbracketed_clock_is_text(self):
        doc = self.convert("a.txt", "Ana: When?\n10:30 is when we start.\n")
        self.assertIn("When? 10:30 is when we start.", doc)

    def test_blank_line_inside_srt_cue(self):
        doc = self.convert("a.srt", "1\n00:00:01,000 --> 00:00:02,000\nline one\n\nline two\n\n2\n00:00:03,000 --> 00:00:04,000\nthree\n")
        self.assertIn("line one line two", doc)
        self.assertEqual(doc.count("<turn "), 2)

    def test_vtt_note_blocks_are_skipped(self):
        doc = self.convert("a.vtt", "WEBVTT\n\nNOTE a comment\n\n00:00:01.000 --> 00:00:02.000\nhi\n\nNOTE\nlater\n\n00:00:03.000 --> 00:00:04.000\nbye\n")
        self.assertNotIn("comment", doc)
        self.assertNotIn("later", doc)

    def test_merge_takes_end_from_last_cue(self):
        doc = self.convert("a.json", '[{"start": 1, "end": 2, "text": "a", "speaker": "A"}, {"start": 3, "text": "b", "speaker": "A"}]', "--merge")
        self.assertIn('start="00:00:01">a b</turn>', doc)

    def test_reserved_document_id_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "a.txt")
            with open(src, "w") as f:
                f.write("Ana: hi\n")
            self.assertEqual(run("tools/to_htmt.py", src, "--id", "t1").returncode, 2)


class ValidatorRobustness(unittest.TestCase):
    def test_bad_clock_and_missing_file_report_fail_not_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "bad.htmt")
            with open(bad, "w") as f:
                f.write('<transcript xmlns="https://thetechjoy.com/htmt/1.0" version="1.0">'
                        '<body><turn start="12" end="00:00:01">x</turn></body></transcript>')
            r = run("tools/validate.py", bad, os.path.join(tmp, "missing.htmt"))
            self.assertEqual(r.returncode, 1)
            self.assertNotIn("Traceback", r.stderr)
            self.assertEqual(r.stdout.count("FAIL"), 2)


class Build(unittest.TestCase):
    def test_index_html_is_up_to_date(self):
        r = run("tools/build.py", "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class SchemaForms(unittest.TestCase):
    def test_rng_matches_rnc(self):
        try:
            import make_rng
        except ImportError:
            self.skipTest("rnc2rng not installed (pip install -r requirements-dev.txt)")
        from lxml import etree
        generated = etree.RelaxNG(etree.fromstring(make_rng.convert().encode()))
        committed = validate.load_schema()
        parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
        for path in files("examples/*.htmt") + files("tests/invalid/*.htmt"):
            with self.subTest(os.path.basename(path)):
                doc = etree.parse(path, parser)
                self.assertEqual(generated.validate(doc), committed.validate(doc))


if __name__ == "__main__":
    unittest.main(verbosity=2)
