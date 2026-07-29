import unittest

from sharepoint_rag.graph import delta as delta_mod
from sharepoint_rag.graph.delta import get_changes

from tests.fakes import FakeGraphClient, FakeResponse, file_item


class DeltaTest(unittest.TestCase):
    def test_single_page(self):
        client = FakeGraphClient(
            [
                FakeResponse(
                    200,
                    {
                        "value": [file_item("1", "a.txt")],
                        "@odata.deltaLink": "https://delta/next",
                    },
                )
            ]
        )
        result = get_changes(client, "drive1", "root1", None)
        self.assertEqual(len(result.changed_items), 1)
        self.assertEqual(result.new_delta_link, "https://delta/next")
        self.assertFalse(result.was_reset)

    def test_pagination_follows_next_link(self):
        client = FakeGraphClient(
            [
                FakeResponse(
                    200,
                    {
                        "value": [file_item("1", "a.txt")],
                        "@odata.nextLink": "https://graph/page2",
                    },
                ),
                FakeResponse(
                    200,
                    {
                        "value": [file_item("2", "b.txt")],
                        "@odata.deltaLink": "https://delta/final",
                    },
                ),
            ]
        )
        result = get_changes(client, "drive1", "root1", None)
        self.assertEqual({i["id"] for i in result.changed_items}, {"1", "2"})
        self.assertEqual(result.new_delta_link, "https://delta/final")

    def test_expired_delta_link_resets(self):
        client = FakeGraphClient(
            [
                FakeResponse(410),  # expired cursor
                FakeResponse(
                    200,
                    {
                        "value": [file_item("1", "a.txt")],
                        "@odata.deltaLink": "https://delta/fresh",
                    },
                ),
            ]
        )
        result = get_changes(client, "drive1", "root1", "https://saved/deltalink")
        self.assertTrue(result.was_reset)
        self.assertEqual(len(result.changed_items), 1)
        self.assertEqual(result.new_delta_link, "https://delta/fresh")

    def test_missing_delta_link_raises(self):
        client = FakeGraphClient([FakeResponse(200, {"value": []})])
        with self.assertRaises(RuntimeError):
            get_changes(client, "drive1", "root1", None)

    def test_uses_saved_delta_link_verbatim(self):
        client = FakeGraphClient(
            [FakeResponse(200, {"value": [], "@odata.deltaLink": "d"})]
        )
        get_changes(client, "drive1", "root1", "https://saved/link")
        # first call should hit the saved link, not the base delta URL
        self.assertEqual(client.calls[0][1], "https://saved/link")

    def test_download_item_content(self):
        # download_item_content uses .content, so use a response-like object
        class R:
            content = b"bytes"

            def raise_for_status(self):
                pass

        class C:
            def request(self, *a, **k):
                return R()

        self.assertEqual(
            delta_mod.download_item_content(C(), "drive1", "item1"), b"bytes"
        )


if __name__ == "__main__":
    unittest.main()
