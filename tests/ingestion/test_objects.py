import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from src.ingestion.ingest_data import Objects


class TestObjects(unittest.TestCase):
    def setUp(self) -> None:
        self.s3_ops = MagicMock()
        self.s3_ops.upload.side_effect = lambda _, name: f"s3://bucket/objects/{name}"
        self.objects = Objects(s3_ops=self.s3_ops)

    def test_push_file_uses_its_name_by_default(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "note.txt"
            source.write_text("note")

            uploaded = self.objects.push(source)

        self.s3_ops.upload.assert_called_once_with(source, "note.txt")
        self.assertEqual(uploaded, {str(source): "s3://bucket/objects/note.txt"})

    def test_push_folder_preserves_relative_paths(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "documents"
            nested = source / "nested"
            nested.mkdir(parents=True)
            (source / "summary.txt").write_text("summary")
            (nested / "detail.txt").write_text("detail")

            uploaded = self.objects.push(source, "knowledge")

        self.assertEqual(self.s3_ops.upload.call_count, 2)
        self.s3_ops.upload.assert_any_call(source / "summary.txt", "knowledge/summary.txt")
        self.s3_ops.upload.assert_any_call(
            source / "nested" / "detail.txt", "knowledge/nested/detail.txt"
        )
        self.assertEqual(
            uploaded,
            {
                str(source / "summary.txt"): "s3://bucket/objects/knowledge/summary.txt",
                str(source / "nested" / "detail.txt"): (
                    "s3://bucket/objects/knowledge/nested/detail.txt"
                ),
            },
        )


if __name__ == "__main__":
    unittest.main()
