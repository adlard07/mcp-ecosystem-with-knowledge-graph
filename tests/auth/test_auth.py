import hashlib
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.auth.auth import (
    Authentication,
    AuthenticationServiceError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from src.auth.login import login
from src.auth.signin import signin
from src.auth.signup import signup
from src.database.supabase_postgres import SupabaseOps
from src.models.auth import EmailAlreadyRegisteredError, InvalidSignupDataError


class TestAuthentication(unittest.TestCase):
    def setUp(self) -> None:
        self.database = MagicMock(spec=SupabaseOps)
        self.database.update.return_value = 1
        self.now = datetime.now(timezone.utc)
        self.auth = Authentication(
            self.database,
            secret_key="s" * 32,
            now=lambda: self.now,
            access_token_expire_minutes=15,
            refresh_token_expire_days=30,
        )
        self.password_hash = self.auth.hash_password("correct horse battery staple")

    def test_signin_returns_tokens_and_persists_refresh_digest(self) -> None:
        self.database.fetch.return_value = [
            {
                "user_id": "user-1",
                "first_name": "Alice",
                "last_name": "Example",
                "email": "alice@example.com",
                "password_hash": self.password_hash,
                "rf_token": "old-token-digest",
            }
        ]

        result = signin(
            "alice@example.com",
            "correct horse battery staple",
            authenticator=self.auth,
        )

        self.assertEqual(result["token_type"], "bearer")
        self.assertTrue(result["access_token"])
        self.assertTrue(result["refresh_token"])
        self.database.fetch.assert_called_once_with(
            "users",
            {"email": "alice@example.com"},
            columns=(
                "user_id",
                "first_name",
                "last_name",
                "email",
                "password_hash",
                "rf_token",
            ),
        )
        self.database.update.assert_called_once_with(
            "users",
            {"rf_token": hashlib.sha256(result["refresh_token"].encode()).hexdigest()},
            {"user_id": "user-1"},
        )

    def test_signin_uses_email_as_the_only_identifier(self) -> None:
        self.database.fetch.return_value = [
            {"user_id": "user-1", "password_hash": self.password_hash}
        ]

        self.auth.signin("alice@example.com", "correct horse battery staple")

        self.database.fetch.assert_called_once_with(
            "users",
            {"email": "alice@example.com"},
            columns=(
                "user_id",
                "first_name",
                "last_name",
                "email",
                "password_hash",
                "rf_token",
            ),
        )

    def test_signin_rejects_invalid_credentials(self) -> None:
        self.database.fetch.return_value = [
            {"user_id": "user-1", "password_hash": self.password_hash}
        ]

        with self.assertRaises(InvalidCredentialsError):
            self.auth.signin("alice", "wrong password")

        self.database.update.assert_not_called()

    def test_refresh_rotates_token_and_login_is_alias(self) -> None:
        self.database.fetch.return_value = [
            {
                "user_id": "user-1",
                "rf_token": "placeholder",
            }
        ]
        first = self.auth._issue_tokens("user-1").as_dict()
        self.database.fetch.return_value[0]["rf_token"] = hashlib.sha256(
            first["refresh_token"].encode()
        ).hexdigest()

        second = login(first["refresh_token"], authenticator=self.auth)

        self.assertNotEqual(first["refresh_token"], second["refresh_token"])
        self.assertEqual(second["token_type"], "bearer")
        self.assertEqual(self.database.update.call_count, 1)
        self.assertEqual(
            self.database.update.call_args.args[2],
            {
                "user_id": "user-1",
                "rf_token": hashlib.sha256(first["refresh_token"].encode()).hexdigest(),
            },
        )

    def test_refresh_rejects_revoked_token(self) -> None:
        self.database.fetch.return_value = [
            {"user_id": "user-1", "rf_token": "a-different-digest"}
        ]
        refresh_token = self.auth._issue_tokens("user-1").refresh_token

        with self.assertRaises(InvalidRefreshTokenError):
            self.auth.refresh_access_token(refresh_token)

        self.database.update.assert_not_called()

    def test_refresh_rejects_malformed_token(self) -> None:
        with self.assertRaises(InvalidRefreshTokenError):
            self.auth.refresh_access_token("not-a-jwt")

        self.database.fetch.assert_not_called()

    def test_update_failure_is_not_reported_as_success(self) -> None:
        self.database.fetch.return_value = [
            {"user_id": "user-1", "password_hash": self.password_hash}
        ]
        self.database.update.return_value = 0

        with self.assertRaises(AuthenticationServiceError):
            self.auth.signin("alice", "correct horse battery staple")

    def test_secret_key_is_required_and_strong_enough(self) -> None:
        with self.assertRaises(AuthenticationServiceError):
            Authentication(self.database, secret_key="too-short")


class TestSignup(unittest.TestCase):
    def setUp(self) -> None:
        self.database = MagicMock(spec=SupabaseOps)
        self.auth = Authentication(self.database, secret_key="s" * 32)
        self.database.fetch.return_value = []
        self.database.insert.return_value = {
            "user_id": "user-1",
            "first_name": "Alice",
            "last_name": "Example",
            "email": "alice@example.com",
            "password_hash": "stored-hash",
            "rf_token": "",
        }

    def test_signup_inserts_user_with_hashed_password(self) -> None:
        row = signup(
            " Alice ",
            " Example ",
            " alice@example.com ",
            "secret123",
            authenticator=self.auth,
        )

        self.assertEqual(row["user_id"], "user-1")
        self.database.fetch.assert_called_once_with(
            "users",
            {"email": "alice@example.com"},
            columns=("user_id",),
        )
        values = self.database.insert.call_args.args[1]
        self.assertEqual(values["first_name"], "Alice")
        self.assertEqual(values["last_name"], "Example")
        self.assertEqual(values["email"], "alice@example.com")
        self.assertEqual(values["rf_token"], "")
        self.assertTrue(
            self.auth._passwords.verify("secret123", values["password_hash"])
        )

    def test_signup_rejects_registered_email(self) -> None:
        self.database.fetch.return_value = [{"user_id": "user-1"}]

        with self.assertRaises(EmailAlreadyRegisteredError):
            signup(
                "Alice",
                "Example",
                "alice@example.com",
                "secret123",
                authenticator=self.auth,
            )

        self.database.insert.assert_not_called()

    def test_signup_rejects_blank_fields(self) -> None:
        with self.assertRaises(InvalidSignupDataError):
            signup(
                "  ",
                "Example",
                "alice@example.com",
                "secret123",
                authenticator=self.auth,
            )

        self.database.insert.assert_not_called()

    def test_signup_reports_database_failures(self) -> None:
        self.database.insert.side_effect = RuntimeError("database unavailable")

        with self.assertRaises(AuthenticationServiceError):
            signup(
                "Alice",
                "Example",
                "alice@example.com",
                "secret123",
                authenticator=self.auth,
            )

    def test_signup_delegate_uses_the_service(self) -> None:
        row = self.auth.signup("Alice", "Example", "alice@example.com", "secret123")

        self.assertEqual(row["user_id"], "user-1")


if __name__ == "__main__":
    unittest.main()
