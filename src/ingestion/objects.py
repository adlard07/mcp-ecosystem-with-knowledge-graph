from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Union

from src.database.s3 import S3Ops


class Objects:
    """Upload files and folders to the configured object store."""

    def __init__(self, s3_ops: Optional[S3Ops] = None) -> None:
        self.s3_ops = s3_ops or S3Ops()

    def push(
        self,
        source: Union[str, Path],
        destination_prefix: Optional[str] = None,
    ) -> Dict[str, str]:
        """Upload a file or all files in a folder and return source-to-S3 URI mappings.

        Folder uploads retain each file's relative path beneath
        ``destination_prefix``. If no prefix is provided, the source file or
        folder name is used as the destination root.
        """
        source_path = Path(source)
        if not source_path.exists():
            raise FileNotFoundError(f"Upload source does not exist: {source_path}")

        root = self._destination_root(destination_prefix, source_path.name)
        if source_path.is_file():
            return {str(source_path): self.s3_ops.upload(source_path, root)}

        if not source_path.is_dir():
            raise ValueError(f"Upload source must be a file or folder: {source_path}")

        uploaded_objects: Dict[str, str] = {}
        for file_path in source_path.rglob("*"):
            if file_path.is_file():
                object_name = f"{root}/{file_path.relative_to(source_path).as_posix()}"
                uploaded_objects[str(file_path)] = self.s3_ops.upload(file_path, object_name)

        return uploaded_objects

    @staticmethod
    def _destination_root(destination_prefix: Optional[str], default: str) -> str:
        root = (destination_prefix or default).replace("\\", "/").strip("/")
        if not root:
            raise ValueError("A destination prefix is required.")
        if any(part == ".." for part in root.split("/")):
            raise ValueError("Destination prefixes cannot contain parent-directory segments.")
        return root
