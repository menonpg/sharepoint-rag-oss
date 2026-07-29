import unittest

from sharepoint_rag.ingest.chunker import chunk_text


class ChunkerTest(unittest.TestCase):
    def test_empty_text_returns_no_chunks(self):
        self.assertEqual(chunk_text(""), [])
        self.assertEqual(chunk_text("   \n  "), [])

    def test_short_text_is_single_chunk(self):
        chunks = chunk_text("hello world", chunk_size_tokens=800, overlap_tokens=120)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].index, 0)
        self.assertEqual(chunks[0].text, "hello world")

    def test_long_text_splits_with_overlap(self):
        words = " ".join(f"w{i}" for i in range(3000))
        chunks = chunk_text(words, chunk_size_tokens=800, overlap_tokens=120)
        self.assertGreater(len(chunks), 1)
        # indices are contiguous starting at 0
        self.assertEqual([c.index for c in chunks], list(range(len(chunks))))

    def test_overlap_creates_shared_words(self):
        words = " ".join(f"w{i}" for i in range(3000))
        chunks = chunk_text(words, chunk_size_tokens=800, overlap_tokens=120)
        first_tail = set(chunks[0].text.split()[-100:])
        second_head = set(chunks[1].text.split()[:200])
        self.assertTrue(first_tail & second_head, "expected overlapping words")


if __name__ == "__main__":
    unittest.main()
