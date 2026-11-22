from __future__ import annotations

import os
import re
from contextlib import contextmanager
from typing import Any, Iterator, Mapping, Optional, Sequence
from urllib.parse import urlsplit

import psycopg2
from psycopg2.extras import RealDictCursor


class SupabaseOps:
    """Run small, parameterized CRUD operations over a Supabase Postgres DB."""

    identifier_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?$")

    def __init__(self, database_url: Optional[str] = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL is required to connect to Supabase.")
        self._validate_database_url(self.database_url)

    @contextmanager
    def _connection(self) -> Iterator[Any]:
        connection = psycopg2.connect(self.database_url, sslmode="require")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def insert(self, table: str, values: Mapping[str, Any]) -> dict[str, Any]:
        """Insert one row and return the inserted row."""
        columns, placeholders = self._columns_and_placeholders(values)
        query = (
            f"INSERT INTO {self._identifier(table)} ({columns}) "
            f"VALUES ({placeholders}) RETURNING *"
        )

        with self._connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, tuple(values.values()))
                return dict(cursor.fetchone())

    def delete(self, table: str, filters: Mapping[str, Any]) -> int:
        """Delete rows matching ``filters`` and return the number deleted."""
        where_clause, parameters = self._where_clause(filters)
        query = f"DELETE FROM {self._identifier(table)} WHERE {where_clause}"

        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, parameters)
                return cursor.rowcount

    def update(
        self,
        table: str,
        values: Mapping[str, Any],
        filters: Mapping[str, Any],
    ) -> int:
        """Update rows matching ``filters`` and return the number updated."""
        if not values:
            raise ValueError("At least one value is required for update.")

        assignments = ", ".join(
            f"{self._identifier(column)} = %s" for column in values
        )
        where_clause, filter_parameters = self._where_clause(filters)
        query = (
            f"UPDATE {self._identifier(table)} SET {assignments} "
            f"WHERE {where_clause}"
        )

        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, tuple(values.values()) + filter_parameters)
                return cursor.rowcount

    def fetch(
        self,
        table: str,
        filters: Optional[Mapping[str, Any]] = None,
        columns: Optional[Sequence[str]] = None,
    ) -> list[dict[str, Any]]:
        """Fetch rows, optionally filtered by equality values."""
        selected_columns = "*" if columns is None else ", ".join(
            self._identifier(column) for column in columns
        )
        query = f"SELECT {selected_columns} FROM {self._identifier(table)}"
        parameters: tuple[Any, ...] = ()
        if filters:
            where_clause, parameters = self._where_clause(filters)
            query += f" WHERE {where_clause}"

        with self._connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, parameters)
                return [dict(row) for row in cursor.fetchall()]

    def _identifier(self, value: str) -> str:
        if not self.identifier_pattern.fullmatch(value):
            raise ValueError(f"Invalid SQL identifier: {value!r}")
        return ".".join(f'"{part}"' for part in value.split("."))

    def _validate_database_url(self, database_url: str) -> None:
        """Catch common connection-string mistakes before opening a socket."""
        parsed = urlsplit(database_url)
        if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL URL from Supabase's Connect panel."
            )
        if parsed.netloc.count("@") > 1:
            raise ValueError(
                "DATABASE_URL contains an unescaped '@' in the password. "
                "Encode it as '%40' (and encode other reserved characters)."
            )

    def _columns_and_placeholders(
        self, values: Mapping[str, Any]
    ) -> tuple[str, str]:
        if not values:
            raise ValueError("At least one value is required for insert.")
        columns = ", ".join(self._identifier(column) for column in values)
        placeholders = ", ".join("%s" for _ in values)
        return columns, placeholders

    def _where_clause(
        self, filters: Mapping[str, Any]
    ) -> tuple[str, tuple[Any, ...]]:
        if not filters:
            raise ValueError("At least one filter is required.")
        clause = " AND ".join(
            f"{self._identifier(column)} = %s" for column in filters
        )
        return clause, tuple(filters.values())


if __name__ == "__main__":
    ops = SupabaseOps()

    TEST_TABLE = "supabase_ops_test"

    # --- 0. Setup: create a throwaway table ----------------------------------
    with ops._connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {TEST_TABLE}")
            cur.execute(
                f"""
                CREATE TABLE {TEST_TABLE} (
                    id         serial PRIMARY KEY,
                    name       varchar(50) NOT NULL,
                    score      integer     NOT NULL,
                    updated_at timestamp DEFAULT current_timestamp
                )
                """
            )
    print(f"[setup] created table {TEST_TABLE}")

    try:
        # --- 1. INSERT --------------------------------------------------------
        row = ops.insert(TEST_TABLE, {"name": "alice", "score": 10})
        print("[insert] inserted:", row)
        assert row["name"] == "alice"
        assert row["score"] == 10
        assert row["id"] is not None

        # --- 2. FETCH ---------------------------------------------------------
        rows = ops.fetch(TEST_TABLE, {"name": "alice"})
        print("[fetch] fetched:", rows)
        assert len(rows) == 1
        assert rows[0]["id"] == row["id"]

        # fetch all rows (no filter)
        all_rows = ops.fetch(TEST_TABLE)
        assert len(all_rows) == 1

        # fetch with column projection
        projected = ops.fetch(TEST_TABLE, {"name": "alice"}, columns=["name", "score"])
        assert projected == [{"name": "alice", "score": 10}]

        # --- 3. UPDATE --------------------------------------------------------
        updated_count = ops.update(TEST_TABLE, {"score": 99}, {"name": "alice"})
        print("[update] rows updated:", updated_count)
        assert updated_count == 1

        refreshed = ops.fetch(TEST_TABLE, {"id": row["id"]})
        assert refreshed[0]["score"] == 99
        assert refreshed[0]["name"] == "alice"  # untouched
        print("[update] refreshed:", refreshed[0])

        # --- 4. DELETE --------------------------------------------------------
        deleted_count = ops.delete(TEST_TABLE, {"name": "alice"})
        print("[delete] rows deleted:", deleted_count)
        assert deleted_count == 1

        remaining = ops.fetch(TEST_TABLE)
        assert remaining == []
        print("[delete] remaining rows:", remaining)

        print("\nAll CRUD tests passed ✅")

    finally:
        # --- Cleanup ----------------------------------------------------------
        with ops._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {TEST_TABLE}")
        print(f"[cleanup] dropped table {TEST_TABLE}")
