"""Tests for calendar booking logic."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
class TestCalendar:
    async def test_get_slots_no_service(self):
        from app.calendar.google_calendar import get_available_slots

        with patch("app.calendar.google_calendar._get_calendar_service", return_value=None):
            slots = await get_available_slots("2025-06-10", "2025-06-14")
            assert slots == []

    async def test_book_meeting_no_service(self):
        from app.calendar.google_calendar import book_meeting

        with patch("app.calendar.google_calendar._get_calendar_service", return_value=None):
            result = await book_meeting(
                start_time="2025-06-10T10:00:00",
                attendee_email="test@example.com",
                attendee_name="Test User",
            )
            assert result.success is False
