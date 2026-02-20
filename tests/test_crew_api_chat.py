"""Tests for the crew API POST /chat endpoint (crew.kickoff)."""

from unittest.mock import MagicMock, patch

import pytest
import httpx

from crew_api.app import app


@pytest.mark.asyncio
async def test_post_chat_returns_200_with_response_string():
    """POST /chat with {"message": "explain this"} returns 200 and body has response (string)."""
    mock_output = MagicMock()
    mock_output.raw = "Here is the explanation."
    mock_output.final_output = None

    mock_crew = MagicMock()
    mock_crew.kickoff.return_value = mock_output

    with patch("crew_api.chat.create_crew", return_value=mock_crew):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/chat",
                json={"message": "explain this"},
            )

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert isinstance(data["response"], str)
    assert data["response"] == "Here is the explanation."
