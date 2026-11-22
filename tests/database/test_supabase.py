import unittest
from unittest.mock import MagicMock, patch

from src.database.supabase import SupabaseOps


class TestSupabaseOps(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = MagicMock()
        self.cursor = MagicMock()
        self.connection.cursor.return_value.__enter__.return_value = self.cursor
        self.connect_patcher = patch(
            "src.database.supabase.psycopg2.connect",
            return_value=self.connection,
        )
        self.connect = self.connect_patcher.start()
        self.ops = SupabaseOps(database_url="postgresql://example")

    def tearDown(self) -> None:
        self.connect_patcher.stop()

    def test_insert_returns_inserted_row(self) -> None:
        self.cursor.fetchone.return_value = {"id": 1, "title": "Note"}

        result = self.ops.insert("public.notes", {"title": "Note"})

        self.assertEqual(result, {"id": 1, "title": "Note"})
        self.cursor.execute.assert_called_once_with(
            'INSERT INTO "public"."notes" ("title") VALUES (%s) RETURNING *',
            ("Note",),
        )
        self.connection.commit.assert_called_once_with()

    def test_update_fetch_and_delete_use_parameterized_filters(self) -> None:
        self.cursor.rowcount = 1
        self.cursor.fetchall.return_value = [{"id": 1, "title": "Updated"}]

        updated = self.ops.update("notes", {"title": "Updated"}, {"id": 1})
        rows = self.ops.fetch("notes", {"id": 1}, columns=["id", "title"])
        deleted = self.ops.delete("notes", {"id": 1})

        self.assertEqual(updated, 1)
        self.assertEqual(rows, [{"id": 1, "title": "Updated"}])
        self.assertEqual(deleted, 1)
        self.assertEqual(self.cursor.execute.call_count, 3)
        self.assertEqual(
            self.cursor.execute.call_args_list[0].args,
            ('UPDATE "notes" SET "title" = %s WHERE "id" = %s', ("Updated", 1)),
        )
        self.assertEqual(
            self.cursor.execute.call_args_list[1].args,
            ('SELECT "id", "title" FROM "notes" WHERE "id" = %s', (1,)),
        )
        self.assertEqual(
            self.cursor.execute.call_args_list[2].args,
            ('DELETE FROM "notes" WHERE "id" = %s', (1,)),
        )

    def test_rejects_invalid_table_names(self) -> None:
        with self.assertRaises(ValueError):
            self.ops.fetch("notes; DROP TABLE users")


if __name__ == "__main__":
    unittest.main()
