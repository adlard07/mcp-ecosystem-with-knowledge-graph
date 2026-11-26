import unittest
from unittest.mock import MagicMock

from src.database.pinecone_vector import PinconeOps


class TestPinconeOps(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.index = self.client.Index.return_value
        self.ops = PinconeOps(index_name="knowledge", pinecone_client=self.client)

    def test_upsert_fetch_update_and_delete(self) -> None:
        records = [{"id": "note-1", "text": "Journal entry"}]

        self.ops.upsert(records, namespace="notes")
        self.ops.fetch(["note-1"], namespace="notes")
        self.ops.update(
            "note-1",
            namespace="notes",
            values=[0.3, 0.4],
            set_metadata={"source": "journal"},
        )
        self.ops.delete(ids=["note-1"], namespace="notes")

        self.client.Index.assert_called_once_with(name="knowledge", host="")
        self.index.upsert_records.assert_called_once_with(
            records=[{"_id": "note-1", "text": "Journal entry"}],
            namespace="notes",
        )
        self.index.fetch.assert_called_once_with(ids=["note-1"], namespace="notes")
        self.index.update.assert_called_once_with(
            id="note-1",
            namespace="notes",
            values=[0.3, 0.4],
            sparse_values=None,
            set_metadata={"source": "journal"},
        )
        self.index.delete.assert_called_once_with(
            namespace="notes",
            ids=["note-1"],
            filter=None,
            delete_all=False,
        )

    def test_delete_requires_one_deletion_target(self) -> None:
        with self.assertRaises(ValueError):
            self.ops.delete(namespace="notes")

        with self.assertRaises(ValueError):
            self.ops.delete(ids=["note-1"], delete_all=True, namespace="notes")


if __name__ == "__main__":
    unittest.main()
