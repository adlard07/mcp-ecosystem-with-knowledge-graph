import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import ANY, MagicMock

from src.database.s3_object import S3Ops


class TestS3Ops(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.ops = S3Ops(s3_client=self.client)

    def test_upload_fetch_download_and_delete_object(self) -> None:
        object_name = "documents/example.txt"
        object_key = "objects/documents/example.txt"
        content = b"example content"
        self.client.get_object.return_value = {"Body": BytesIO(content)}

        with BytesIO(content) as source:
            uri = self.ops.upload(source, object_name)

        self.assertEqual(uri, "s3://mcp-knowledgebase-store/objects/documents/example.txt")
        self.client.upload_fileobj.assert_called_once_with(
            ANY,
            "mcp-knowledgebase-store",
            object_key,
        )
        self.assertEqual(self.ops.fetch(object_name), content)
        self.client.get_object.assert_called_once_with(
            Bucket="mcp-knowledgebase-store",
            Key=object_key,
        )

        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "downloads" / "example.txt"
            downloaded_path = self.ops.download(object_name, destination)

        self.assertEqual(downloaded_path, destination)
        self.client.download_file.assert_called_once_with(
            "mcp-knowledgebase-store",
            object_key,
            str(destination),
        )

        self.ops.delete(object_name)
        self.client.delete_object.assert_called_once_with(
            Bucket="mcp-knowledgebase-store",
            Key=object_key,
        )

    def test_rejects_parent_directory_segments(self) -> None:
        with self.assertRaises(ValueError):
            self.ops.fetch("../outside.txt")


if __name__ == "__main__":
    unittest.main()
