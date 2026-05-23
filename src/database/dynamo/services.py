import json
import os
from decimal import Decimal
from typing import Any, List, Optional

from dotenv import load_dotenv

from src.database.dynamo.initialize import DatabaseInit
from src.models.servers import CreateServer, Server
from src.models.sessions import CreateSession, Session
from utils.utils import _build_update_expression

load_dotenv(override=True)


def _convert_floats(obj: Any) -> Any:
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _convert_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_floats(i) for i in obj]
    return obj


class SchemeInit:
    """Run once at startup to ensure all required tables exist."""

    def __init__(self):
        self.dbi = DatabaseInit()
        self.user_table = os.getenv("USERS_TABLE", "mcp-ecosystem-users")
        self.server_table = os.getenv("SERVER_TABLE", "mcp-ecosystem-servers")
        self.session_table = os.getenv("SESSIONS_TABLE", "mcp-ecosystem-sessions")
        self.api_keys_table = os.getenv("API_KEYS_TABLE", "mcp-ecosystem-api-keys")

    def create_auth_tables(self) -> None:
        self.dbi.create_table(
            table_name=self.user_table,
            key_schema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
            attribute_definitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "email", "AttributeType": "S"},
                {"AttributeName": "username", "AttributeType": "S"},
            ],
            global_secondary_indexes=[
                {
                    "IndexName": "email-index",
                    "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "username-index",
                    "KeySchema": [{"AttributeName": "username", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            ttl_attribute="ttl",
        )
        self.dbi.create_table(
            table_name=self.session_table,
            key_schema=[{"AttributeName": "session_id", "KeyType": "HASH"}],
            attribute_definitions=[
                {"AttributeName": "session_id", "AttributeType": "S"},
                {"AttributeName": "user_id", "AttributeType": "S"},
            ],
            global_secondary_indexes=[
                {
                    "IndexName": "user-sessions-index",
                    "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            ttl_attribute="ttl",
        )
        self.dbi.create_table(
            table_name=self.api_keys_table,
            key_schema=[{"AttributeName": "key_id", "KeyType": "HASH"}],
            attribute_definitions=[
                {"AttributeName": "key_id", "AttributeType": "S"},
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "hashed_key", "AttributeType": "S"},
            ],
            global_secondary_indexes=[
                {
                    "IndexName": "user-keys-index",
                    "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "hashed-key-index",
                    "KeySchema": [{"AttributeName": "hashed_key", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            ttl_attribute="ttl",
        )

    def create_server_table(self) -> None:
        self.dbi.create_table(
            table_name=self.server_table,
            key_schema=[{"AttributeName": "server_id", "KeyType": "HASH"}],
            attribute_definitions=[
                {"AttributeName": "server_id", "AttributeType": "S"},
            ],
        )


class DatabaseServices:
    def __init__(self):
        self.dbi = DatabaseInit()
        self.user_table = os.getenv("USERS_TABLE", "mcp-users")
        self.session_table = os.getenv("SESSIONS_TABLE", "mcp-sessions")
        self.api_keys_table = os.getenv("API_KEYS_TABLE", "mcp-api-keys")
        self.server_table = os.getenv("SERVER_TABLE", "mcp-ecosystem-servers")

    # ── users ─────────────────────────────────────────────────────────

    def create_user(self, user: dict) -> None:
        self.dbi.put_item(self.user_table, _convert_floats(user))

    def get_user(self, user_id: str) -> Optional[dict]:
        return self.dbi.get_item(self.user_table, {"user_id": user_id})

    def get_user_by_email(self, email: str) -> Optional[dict]:
        items = self.dbi.query_index(self.user_table, "email-index", "email", email)
        return items[0] if items else None

    def get_user_by_username(self, username: str) -> Optional[dict]:
        items = self.dbi.query_index(
            self.user_table, "username-index", "username", username
        )
        return items[0] if items else None

    def update_user(self, user_id: str, update_data: dict) -> bool:
        data = _convert_floats({k: v for k, v in update_data.items() if v is not None})
        if not data:
            return False
        expr, names, values = _build_update_expression(data)
        self.dbi.update_item(self.user_table, {"user_id": user_id}, expr, names, values)
        return True

    def delete_user(self, user_id: str) -> None:
        self.dbi.delete_item(self.user_table, {"user_id": user_id})

    # ── sessions ──────────────────────────────────────────────────────

    def create_session(self, session_info: CreateSession) -> None:
        self.dbi.put_item(self.session_table, session_info.model_dump())

    def get_session(self, session_id: Session) -> Optional[dict]:
        return self.dbi.get_item(self.session_table, {"session_id": session_id})

    def delete_session(self, session_id: str) -> None:
        self.dbi.delete_item(self.session_table, {"session_id": session_id})

    def delete_user_sessions(self, user_id: str) -> int:
        sessions = self.dbi.query_index(
            self.session_table, "user-sessions-index", "user_id", user_id
        )
        for s in sessions:
            self.dbi.delete_item(self.session_table, {"session_id": s["session_id"]})
        return len(sessions)

    # ── api keys ──────────────────────────────────────────────────────

    def create_api_key(self, key: dict) -> None:
        self.dbi.put_item(self.api_keys_table, key)

    def get_api_key(self, key_id: str) -> Optional[dict]:
        return self.dbi.get_item(self.api_keys_table, {"key_id": key_id})

    def get_api_key_by_hash(self, hashed_key: str) -> Optional[dict]:
        items = self.dbi.query_index(
            self.api_keys_table, "hashed-key-index", "hashed_key", hashed_key
        )
        return items[0] if items else None

    def list_user_api_keys(self, user_id: str) -> List[dict]:
        return self.dbi.query_index(
            self.api_keys_table, "user-keys-index", "user_id", user_id
        )

    def revoke_api_key(self, key_id: str, revoked_at: str) -> bool:
        expr, names, values = _build_update_expression(
            {"is_revoked": True, "revoked_at": revoked_at}
        )
        self.dbi.update_item(
            self.api_keys_table, {"key_id": key_id}, expr, names, values
        )
        return True

    def update_api_key_last_used(self, key_id: str, last_used_at: str) -> None:
        expr, names, values = _build_update_expression({"last_used_at": last_used_at})
        self.dbi.update_item(
            self.api_keys_table, {"key_id": key_id}, expr, names, values
        )

    # ── servers ───────────────────────────────────────

    def get_all_servers(self) -> List[dict]:
        return self.dbi.query_index(
            table_name=self.server_table,
            index_name="",
            key_name="",
            key_value="",
        )

    def get_server(self, server_id: str):
        if not server_id:
            return self.get_all_servers()
        return self.dbi.get_item(
            table_name=self.server_table, key={"server_id": server_id}
        )

    def create_server(self, server: CreateServer):
        item = json.loads(
            server.model_dump_json(),
            parse_float=Decimal,
        )
        self.dbi.put_item(self.server_table, item)

    def update_server(self, server: Server):
        update_expression, expression_attribute_names, expression_attribute_values = (
            _build_update_expression(server.model_dump())
        )
        self.dbi.update_item(
            self.server_table,
            key={"server_id": server.server_id},
            update_expression=update_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
        )

    def delete_server(self, server_id: str):
        self.dbi.delete_item(
            self.server_table,
            {"server_id": server_id},
        )
