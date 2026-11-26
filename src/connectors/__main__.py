"""Run the PKMS connector MCP server over stdio."""

from src.connectors import mcp

if __name__ == "__main__":
    mcp.run()
