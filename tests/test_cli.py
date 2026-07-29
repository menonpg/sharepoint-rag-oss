import os
import tempfile
import unittest
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from unittest import mock

from sharepoint_rag.cli import build_parser, main
from sharepoint_rag.state import FileState, StateStore


@contextmanager
def captured_stdout():
    buf = StringIO()
    with mock.patch("sys.stdout", buf):
        yield buf


class CliParserTest(unittest.TestCase):
    def test_requires_subcommand(self):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([])

    def test_init_parses_args(self):
        parser = build_parser()
        args = parser.parse_args(
            ["init", "--site-url", "https://h/sites/X", "--folder", "/Docs"]
        )
        self.assertEqual(args.command, "init")
        self.assertEqual(args.site_url, "https://h/sites/X")
        self.assertEqual(args.folder, "/Docs")

    def test_query_parses_question(self):
        parser = build_parser()
        args = parser.parse_args(["query", "what is the policy?"])
        self.assertEqual(args.question, "what is the policy?")

    def test_doctor_site_url_optional(self):
        parser = build_parser()
        args = parser.parse_args(["doctor"])
        self.assertEqual(args.command, "doctor")
        self.assertIsNone(args.site_url)


class CliStatusTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        # Pre-seed state
        store = StateStore(self.home / "state.json")
        store.state.site_url = "https://host/sites/Research"
        store.state.folder_path = "/Docs"
        store.state.drive_id = "drive1"
        store.put_file(
            FileState("f1", "a.txt", "/a.txt", "h", "indexed", "2026-01-01T00:00:00+00:00")
        )
        store.save()

        self._env = mock.patch.dict(
            os.environ,
            {
                "SP_TENANT_ID": "t",
                "SP_CLIENT_ID": "c",
                "SP_CLIENT_SECRET": "s",
                "EMBEDDING_BACKEND": "none",
                "CHAT_BACKEND": "none",
                "VECTOR_STORE": "local",
                "SP_RAG_HOME": str(self.home),
            },
            clear=False,
        )
        self._env.start()

    def tearDown(self):
        self._env.stop()
        self._tmp.cleanup()

    def test_status_reports_state(self):
        with captured_stdout() as out:
            rc = main(["status"])
        text = out.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("https://host/sites/Research", text)
        self.assertIn("Files known: 1", text)
        self.assertIn("Indexed:     1", text)


if __name__ == "__main__":
    unittest.main()
