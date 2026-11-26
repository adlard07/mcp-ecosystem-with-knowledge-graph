"""MCP tools for reading and writing Google Calendar events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.connectors import google_credentials, mcp

CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def _service():
    return build("calendar", "v3", credentials=google_credentials(CALENDAR_SCOPES))


def _execute(request):
    try:
        return request.execute()
    except RefreshError as error:
        raise RuntimeError(f"Calendar OAuth refresh failed: {error}") from error
    except HttpError as error:
        raise RuntimeError(
            f"Calendar API error ({error.resp.status}): {error.reason or 'request failed'}"
        ) from error


def _parse_time(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be an ISO 8601 datetime.") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone offset.")
    return parsed


def _calendar_id(value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError("calendar_id must not be empty.")
    return value


@mcp.tool()
def calendar_list_events(
    time_min: str | None = None,
    time_max: str | None = None,
    max_results: int = 10,
    calendar_id: str = "primary",
) -> list[dict[str, Any]]:
    """List calendar events, defaulting to upcoming events from now."""
    if not 1 <= max_results <= 2500:
        raise ValueError("max_results must be between 1 and 2500.")
    calendar_id = _calendar_id(calendar_id)

    start = _parse_time(time_min, "time_min") if time_min else datetime.now(timezone.utc)
    end = _parse_time(time_max, "time_max") if time_max else None
    if end is not None and end <= start:
        raise ValueError("time_max must be after time_min.")

    response = _execute(
        _service()
        .events()
        .list(
            calendarId=calendar_id,
            timeMin=start.isoformat(),
            timeMax=end.isoformat() if end else None,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
    )
    return response.get("items", [])


@mcp.tool()
def calendar_create_event(
    summary: str,
    start: str,
    end: str,
    description: str | None = None,
    location: str | None = None,
    calendar_id: str = "primary",
) -> dict[str, Any]:
    """Create a calendar event from ISO 8601 datetimes with a timezone offset."""
    summary = (summary or "").strip()
    if not summary:
        raise ValueError("summary must not be empty.")
    start_time = _parse_time(start, "start")
    end_time = _parse_time(end, "end")
    if end_time <= start_time:
        raise ValueError("end must be after start.")
    calendar_id = _calendar_id(calendar_id)

    body: dict[str, Any] = {
        "summary": summary,
        "start": {"dateTime": start_time.isoformat()},
        "end": {"dateTime": end_time.isoformat()},
    }
    if description is not None:
        body["description"] = description
    if location is not None:
        body["location"] = location

    return _execute(
        _service().events().insert(calendarId=calendar_id, body=body)
    )


@mcp.tool()
def calendar_update_event(
    event_id: str,
    summary: str | None = None,
    start: str | None = None,
    end: str | None = None,
    description: str | None = None,
    location: str | None = None,
    calendar_id: str = "primary",
) -> dict[str, Any]:
    """Update only the supplied fields of an existing calendar event."""
    event_id = (event_id or "").strip()
    if not event_id:
        raise ValueError("event_id must not be empty.")
    calendar_id = _calendar_id(calendar_id)

    body: dict[str, Any] = {}
    if summary is not None:
        summary = summary.strip()
        if not summary:
            raise ValueError("summary must not be empty.")
        body["summary"] = summary
    start_time = _parse_time(start, "start") if start is not None else None
    end_time = _parse_time(end, "end") if end is not None else None
    if start_time is not None and end_time is not None and end_time <= start_time:
        raise ValueError("end must be after start.")
    if start_time is not None:
        body["start"] = {"dateTime": start_time.isoformat()}
    if end_time is not None:
        body["end"] = {"dateTime": end_time.isoformat()}
    if description is not None:
        body["description"] = description
    if location is not None:
        body["location"] = location
    if not body:
        raise ValueError("Provide at least one field to update.")

    return _execute(
        _service()
        .events()
        .patch(calendarId=calendar_id, eventId=event_id, body=body)
    )


@mcp.tool()
def calendar_delete_event(
    event_id: str, calendar_id: str = "primary"
) -> dict[str, Any]:
    """Delete a calendar event."""
    event_id = (event_id or "").strip()
    if not event_id:
        raise ValueError("event_id must not be empty.")
    calendar_id = _calendar_id(calendar_id)

    _execute(_service().events().delete(calendarId=calendar_id, eventId=event_id))
    return {"deleted": True, "event_id": event_id}
