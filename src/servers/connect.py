import json
import os
from decimal import Decimal
from typing import Any

import requests

from src.database.dynamo.services import DatabaseServices
from src.models.servers import Server
from src.models.sessions import CreateSession
from src.servers.services import get_server


class ServerAuth:
    def __init__(
        self,
        base_url: str,
        user_id: str,
        server_id: str,
        user_email: str | None = None,
        user_password: str | None = None,
        login_suffix: str = "/auth/login",
        logout_suffix: str = "/auth/logout",
        signup_suffix: str = "/auth/signup",
        refresh_suffix: str = "/auth/refresh",
        user_info_suffix: str = "/auth/me",
    ):
        self.sessions_table = os.getenv("SESSIONS_TABLE", "sessions")
        self.dbi = DatabaseServices()

        self.user_id = user_id
        self.server_id = server_id
        self.base_url = base_url.rstrip("/")
        self.user_email = user_email
        self.user_password = user_password

        self.login_url = self.base_url + login_suffix
        self.logout_url = self.base_url + logout_suffix
        self.signup_url = self.base_url + signup_suffix
        self.refresh_url = self.base_url + refresh_suffix
        self.user_info_url = self.base_url + user_info_suffix

        self.access_token: str | None = None
        self.refresh_token: str | None = None

        self.session = requests.Session()

    def _auth_headers(self) -> dict[str, str]:
        if not self.access_token:
            raise Exception("Access token not found. Please login first.")

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def login(self) -> dict[str, Any]:
        # verify server exists:
        server = get_server(server_id=self.server_id)
        if not server:
            raise Exception(f"Server with id {self.server_id} not found.")

        if not self.user_email or not self.user_password:
            raise Exception("Email and password are required for login.")

        payload = {
            "email": self.user_email,
            "password": self.user_password,
        }

        response = self.session.post(self.login_url, json=payload)
        response.raise_for_status()

        data = response.json()

        self.access_token = data.get("access_token")
        self.refresh_token = data.get("refresh_token")

        if not self.access_token or not self.refresh_token:
            raise Exception(
                "Login failed: either access_token or refresh_token not found in response"
            )

        self.user_id = (
            data.get("user_id")
            or data.get("id")
            or data.get("user", {}).get("id")
            or data.get("user", {}).get("user_id")
        )

        if self.user_id:
            self.dbi.save_session(
                session_info=CreateSession(
                    session=data,
                    user_id=self.user_id,
                    server_id=self.server_id,
                ).model_dump(),
            )

        return data

    def refresh_access_token(self) -> dict[str, Any]:
        if not self.refresh_token:
            raise Exception("Refresh token not found. Please login again.")

        response = self.session.post(
            self.refresh_url,
            json={"refresh_token": self.refresh_token},
        )
        response.raise_for_status()

        data = response.json()

        self.access_token = data.get("access_token")
        self.refresh_token = data.get("refresh_token", self.refresh_token)

        if not self.access_token:
            raise Exception("Refresh failed: access_token not found in response")

        return data

    def request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> requests.Response:
        headers = kwargs.pop("headers", {})
        headers.update(self._auth_headers())

        response = self.session.request(
            method=method,
            url=url,
            headers=headers,
            **kwargs,
        )

        if response.status_code == 401:
            self.refresh_access_token()

            headers.update(self._auth_headers())

            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs,
            )

        response.raise_for_status()
        return response

    def logout(self) -> dict[str, Any]:
        response = self.request(
            method="POST",
            url=self.logout_url,
            json={"refresh_token": self.refresh_token},
        )

        data = response.json()

        self.access_token = None
        self.refresh_token = None

        return data

    def signup(
        self,
        email: str,
        password: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "email": email,
            "password": password,
        }

        if first_name:
            payload["first_name"] = first_name

        if last_name:
            payload["last_name"] = last_name

        response = self.session.post(self.signup_url, json=payload)
        response.raise_for_status()

        return response.json()

    def get_user_info(self) -> dict[str, Any]:
        response = self.request(
            method="GET",
            url=self.user_info_url,
        )

        return response.json()

    def connect_to_mcp_server(
        self,
        mcp_url: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        response = self.request(
            method="POST",
            url=mcp_url,
            json=payload,
        )

        return response.json()


if __name__ == "__main__":
    auth = ServerAuth(
        user_id="",
        server_id="eddeccc5-7f6c-46bc-8ebd-4e717ddb801c",
        base_url="http://localhost:7000",
        user_email="hritika.here@gmail.com",
        user_password="Hritika@123",
    )

    login_response = auth.login()
    print("Login successful:", login_response)

    user_info = auth.get_user_info()
    print("User info:", user_info)

    mcp_response = auth.connect_to_mcp_server(
        mcp_url="http://localhost:8000/mcp",
        payload={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        },
    )

    print("MCP response:", mcp_response)

    logout_response = auth.logout()
    print("Logout successful:", logout_response)
