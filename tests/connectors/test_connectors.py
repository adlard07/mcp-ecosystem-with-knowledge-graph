import asyncio
import os
import unittest
from unittest.mock import MagicMock, patch

from src.connectors import calendar, gmail, google_credentials, mcp


class TestGmailTools(unittest.TestCase):
    def setUp(self) -> None:
        self.service = MagicMock()
        self.service_patcher = patch.object(
            gmail, "_service", return_value=self.service
        )
        self.service_patcher.start()
        self.addCleanup(self.service_patcher.stop)

    def test_search_returns_headers_and_snippets(self) -> None:
        messages = self.service.users.return_value.messages.return_value
        messages.list.return_value.execute.return_value = {
            "messages": [{"id": "m1"}]
        }
        messages.get.return_value.execute.return_value = {
            "id": "m1",
            "threadId": "t1",
            "snippet": "Hello",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Hi"},
                    {"name": "From", "value": "a@example.com"},
                    {"name": "To", "value": "b@example.com"},
                    {"name": "Date", "value": "Thu, 1 Jan 2026"},
                ]
            },
        }

        result = gmail.gmail_search("from:a@example.com", max_results=5)

        self.assertEqual(
            result,
            [
                {
                    "id": "m1",
                    "thread_id": "t1",
                    "subject": "Hi",
                    "from": "a@example.com",
                    "to": "b@example.com",
                    "date": "Thu, 1 Jan 2026",
                    "snippet": "Hello",
                    "label_ids": ["INBOX", "UNREAD"],
                }
            ],
        )
        messages.list.assert_called_once_with(
            userId="me", q="from:a@example.com", maxResults=5
        )

    def test_update_labels_modifies_message(self) -> None:
        modify = self.service.users.return_value.messages.return_value.modify
        modify.return_value.execute.return_value = {
            "id": "m1",
            "labelIds": ["INBOX"],
        }

        result = gmail.gmail_update_labels(
            "m1", remove_labels=["UNREAD", "UNREAD"]
        )

        self.assertEqual(result, {"id": "m1", "label_ids": ["INBOX"]})
        modify.assert_called_once_with(
            userId="me",
            id="m1",
            body={"addLabelIds": [], "removeLabelIds": ["UNREAD"]},
        )

    def test_validation(self) -> None:
        with self.assertRaises(ValueError):
            gmail.gmail_search(" ")
        with self.assertRaises(ValueError):
            gmail.gmail_search("x", max_results=0)
        with self.assertRaises(ValueError):
            gmail.gmail_update_labels(" ")
        with self.assertRaises(ValueError):
            gmail.gmail_update_labels("m1")


class TestCalendarTools(unittest.TestCase):
    def setUp(self) -> None:
        self.service = MagicMock()
        self.service_patcher = patch.object(
            calendar, "_service", return_value=self.service
        )
        self.service_patcher.start()
        self.addCleanup(self.service_patcher.stop)

    def test_list_defaults_to_upcoming_events(self) -> None:
        events = self.service.events.return_value
        events.list.return_value.execute.return_value = {"items": [{"id": "e1"}]}

        result = calendar.calendar_list_events(max_results=3)

        self.assertEqual(result, [{"id": "e1"}])
        call = events.list.call_args.kwargs
        self.assertEqual(call["calendarId"], "primary")
        self.assertEqual(call["maxResults"], 3)
        self.assertEqual(call["singleEvents"], True)
        self.assertEqual(call["orderBy"], "startTime")
        self.assertIsNone(call["timeMax"])
        self.assertTrue(call["timeMin"].endswith("+00:00"))

    def test_create_event(self) -> None:
        insert = self.service.events.return_value.insert
        insert.return_value.execute.return_value = {"id": "e1"}

        result = calendar.calendar_create_event(
            "Standup",
            "2026-12-01T09:00:00+00:00",
            "2026-12-01T09:30:00+00:00",
            description="Daily",
        )

        self.assertEqual(result, {"id": "e1"})
        insert.assert_called_once_with(
            calendarId="primary",
            body={
                "summary": "Standup",
                "start": {"dateTime": "2026-12-01T09:00:00+00:00"},
                "end": {"dateTime": "2026-12-01T09:30:00+00:00"},
                "description": "Daily",
            },
        )

    def test_update_event_patches_only_given_fields(self) -> None:
        patch_call = self.service.events.return_value.patch
        patch_call.return_value.execute.return_value = {
            "id": "e1",
            "summary": "New",
        }

        result = calendar.calendar_update_event("e1", summary="New")

        self.assertEqual(result, {"id": "e1", "summary": "New"})
        patch_call.assert_called_once_with(
            calendarId="primary", eventId="e1", body={"summary": "New"}
        )

    def test_delete_event(self) -> None:
        delete = self.service.events.return_value.delete
        delete.return_value.execute.return_value = None

        result = calendar.calendar_delete_event("e1")

        self.assertEqual(result, {"deleted": True, "event_id": "e1"})
        delete.assert_called_once_with(calendarId="primary", eventId="e1")

    def test_validation(self) -> None:
        with self.assertRaises(ValueError):
            calendar.calendar_create_event(
                "x", "2026-12-01T09:00:00", "2026-12-01T10:00:00+00:00"
            )
        with self.assertRaises(ValueError):
            calendar.calendar_create_event(
                "x", "2026-12-01T10:00:00+00:00", "2026-12-01T09:00:00+00:00"
            )
        with self.assertRaises(ValueError):
            calendar.calendar_update_event("e1")
        with self.assertRaises(ValueError):
            calendar.calendar_list_events(
                time_min="2026-12-01T10:00:00+00:00",
                time_max="2026-12-01T09:00:00+00:00",
            )


class TestConnectorServer(unittest.TestCase):
    def test_all_tools_are_registered(self) -> None:
        names = {tool.name for tool in asyncio.run(mcp.list_tools())}

        self.assertEqual(
            names,
            {
                "gmail_search",
                "gmail_update_labels",
                "calendar_list_events",
                "calendar_create_event",
                "calendar_update_event",
                "calendar_delete_event",
            },
        )

    def test_credentials_require_oauth_environment_variables(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                google_credentials(["scope"])


if __name__ == "__main__":
    unittest.main()
