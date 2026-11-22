from __future__ import annotations

import os
import time
from pathlib import Path
from typing import BinaryIO, Optional, Union

import boto3
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError


class S3Ops:
    """Manage objects stored under ``s3://mcp-knowledgebase-store/objects/``.

    The supplied S3 client uses boto3's normal credential chain, so credentials
    remain outside application source code. All keys are constrained to the
    configured object prefix.
    """

    default_bucket = "mcp-knowledgebase-store"
    default_prefix = "objects"

    def __init__(
        self,
        bucket: str = default_bucket,
        prefix: str = default_prefix,
        s3_client: Optional[BaseClient] = None,
    ) -> None:
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
        self.client = s3_client or boto3.client("s3", region_name=region)

    def upload(
        self,
        source: Union[str, Path, BinaryIO],
        object_name: str,
    ) -> str:
        """Upload a file or binary stream, replacing an existing object if present.

        Returns the full S3 URI of the uploaded object.
        """
        key = self._key_for(object_name)

        try:
            if hasattr(source, "read"):
                self.client.upload_fileobj(source, self.bucket, key)
            else:
                source_path = Path(source)
                if not source_path.is_file():
                    raise FileNotFoundError(f"Upload source does not exist: {source_path}")
                self.client.upload_file(str(source_path), self.bucket, key)
        except (BotoCoreError, ClientError) as error:
            raise RuntimeError(self._error_message("upload", key, error)) from error

        return f"s3://{self.bucket}/{key}"

    def delete(self, object_name: str) -> None:
        """Delete an object from the configured prefix."""
        key = self._key_for(object_name)
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except (BotoCoreError, ClientError) as error:
            raise RuntimeError(self._error_message("delete", key, error)) from error

    def download(self, object_name: str, destination: Union[str, Path]) -> Path:
        """Download an object to ``destination`` and return its local path."""
        key = self._key_for(object_name)
        destination_path = Path(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.client.download_file(self.bucket, key, str(destination_path))
        except (BotoCoreError, ClientError) as error:
            raise RuntimeError(self._error_message("download", key, error)) from error

        return destination_path

    def fetch(self, object_name: str) -> bytes:
        """Fetch an object's complete binary contents into memory."""
        key = self._key_for(object_name)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except (BotoCoreError, ClientError) as error:
            raise RuntimeError(self._error_message("fetch", key, error)) from error

    def _key_for(self, object_name: str) -> str:
        """Build a safe object key within the configured prefix."""
        clean_name = object_name.replace("\\", "/").strip("/")
        if not clean_name or clean_name in {".", ".."}:
            raise ValueError("An object name is required.")
        if any(part == ".." for part in clean_name.split("/")):
            raise ValueError("Object names cannot contain parent-directory segments.")

        return f"{self.prefix}/{clean_name}" if self.prefix else clean_name

    def _error_message(self, operation: str, key: str, error: Exception) -> str:
        """Return a useful message while keeping the original exception as cause."""
        if isinstance(error, ClientError):
            details = error.response.get("Error", {})
            code = details.get("Code", "UnknownError")
            message = details.get("Message", str(error))
            return (
                f"Could not {operation} S3 object '{key}' in bucket "
                f"'{self.bucket}' ({code}): {message}"
            )
        return f"Could not {operation} S3 object '{key}': {error}"




if __name__ == "__main__":
    from io import BytesIO

    object_name = "temp/test_upload.txt"
    s3_ops = S3Ops()

    with BytesIO(b"Hello, S3!") as source:
        s3_uri = s3_ops.upload(source, object_name)

    print(f"Uploaded to: {s3_uri}")
    print("Waiting 10 seconds before deleting the object...")
    time.sleep(10)
    s3_ops.delete(object_name)
    print(f"Deleted object: {object_name}")
