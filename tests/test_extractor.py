import unittest

from sharepoint_rag.ingest.extractor import (
    UnsupportedFileType,
    extract_text,
    is_supported,
)


class ExtractorTest(unittest.TestCase):
    def test_is_supported(self):
        self.assertTrue(is_supported("notes.txt"))
        self.assertTrue(is_supported("Report.PDF"))
        self.assertTrue(is_supported("deck.pptx"))
        self.assertFalse(is_supported("image.png"))
        self.assertFalse(is_supported("archive.zip"))

    def test_plain_text_extraction(self):
        self.assertEqual(extract_text("a.txt", b"hello world"), "hello world")

    def test_markdown_extraction(self):
        text = extract_text("a.md", b"# Title\n\nBody text")
        self.assertIn("Title", text)
        self.assertIn("Body text", text)

    def test_csv_and_json_are_decoded(self):
        self.assertIn("a,b", extract_text("t.csv", b"a,b\n1,2"))
        self.assertIn("key", extract_text("t.json", b'{"key": 1}'))

    def test_latin1_fallback(self):
        # 0xe9 is 'é' in latin-1, invalid as utf-8 start byte alone
        out = extract_text("t.txt", b"caf\xe9")
        self.assertTrue(out.startswith("caf"))

    def test_unsupported_type_raises(self):
        with self.assertRaises(UnsupportedFileType):
            extract_text("image.png", b"\x89PNG")


if __name__ == "__main__":
    unittest.main()
