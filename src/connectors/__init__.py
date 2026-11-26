"""Shared MCP server and Google OAuth credentials for the connectors."""

from __future__ import annotations

import os

from google.oauth2.credentials import Credentials
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("pkms-connectors")

TOKEN_URI = "https://oauth2.googleapis.com/token"


def google_credentials(scopes: list[str]) -> Credentials:
    """Build OAuth 2.0 credentials from the refresh-token environment variables."""
    settings = {
        "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID"),
        "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET"),
        "GOOGLE_REFRESH_TOKEN": os.getenv("GOOGLE_REFRESH_TOKEN"),
    }
    missing = [name for name, value in settings.items() if not value]
    if missing:
        raise ValueError(f"Missing OAuth credentials: {', '.join(missing)}")

    return Credentials(
        token=None,
        refresh_token=settings["GOOGLE_REFRESH_TOKEN"],
        token_uri=TOKEN_URI,
        client_id=settings["GOOGLE_CLIENT_ID"],
        client_secret=settings["GOOGLE_CLIENT_SECRET"],
        scopes=scopes,
    )


# Importing the modules registers their tools on the shared server.
from src.connectors import calendar, gmail  # noqa: E402,F401
