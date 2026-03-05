import pytest
from unittest.mock import MagicMock, patch
from src.core.updates import check_for_updates

@pytest.mark.asyncio
async def test_check_for_updates_no_update():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = {"info": {"version": "0.1.0"}}
        
        result = await check_for_updates("0.1.0")
        assert result is None

@pytest.mark.asyncio
async def test_check_for_updates_with_new_version():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = {"info": {"version": "0.2.0"}}
        
        result = await check_for_updates("0.1.0")
        assert result == "0.2.0"

@pytest.mark.asyncio
async def test_check_for_updates_network_error():
    with patch("httpx.AsyncClient.get", side_with=Exception("Network failure")):
        result = await check_for_updates("0.1.0")
        assert result is None
