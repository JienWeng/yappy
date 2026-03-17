from unittest.mock import MagicMock, patch

import pytest

from src.core import scheduler


@pytest.fixture
def mock_path_home(tmp_path):
    with patch("pathlib.Path.home", return_value=tmp_path):
        yield tmp_path

def test_register_daily_run_invalid_time():
    result = scheduler.register_daily_run("invalid")
    assert "Invalid time format" in result

@patch("platform.system", return_value="Darwin")
@patch("subprocess.run")
def test_schedule_mac_success(mock_run, mock_system, mock_path_home):
    mock_run.return_value = MagicMock(returncode=0)

    result = scheduler.register_daily_run("09:30")

    assert "Successfully scheduled" in result
    assert "macOS LaunchAgent" in result

    # Verify plist creation
    plist_path = mock_path_home / "Library" / "LaunchAgents" / "com.jienweng.yappy.daily.plist"
    assert plist_path.exists()
    content = plist_path.read_text()
    assert "<integer>9</integer>" in content
    assert "<integer>30</integer>" in content
    assert "--no-tui" in content

@patch("platform.system", return_value="Linux")
@patch("subprocess.run")
def test_schedule_linux_success(mock_run, mock_system):
    # Mock crontab -l
    mock_run.side_effect = [
        MagicMock(stdout="", returncode=0), # crontab -l
        MagicMock(returncode=0),            # crontab -
    ]

    result = scheduler.register_daily_run("23:15")

    assert "Successfully scheduled" in result
    assert "Linux crontab" in result

    # Verify crontab call
    args, kwargs = mock_run.call_args_list[1]
    assert args[0] == ["crontab", "-"]
    assert "15 23 * * *" in kwargs["input"]

@patch("platform.system", return_value="Darwin")
def test_list_schedules_mac(mock_system, mock_path_home):
    # No schedule
    assert "No active schedules found" in scheduler.list_schedules()

    # With schedule
    plist_dir = mock_path_home / "Library" / "LaunchAgents"
    plist_dir.mkdir(parents=True)
    (plist_dir / "com.jienweng.yappy.daily.plist").write_text("dummy")

    assert "Found active macOS schedule" in scheduler.list_schedules()

@patch("platform.system", return_value="Darwin")
@patch("subprocess.run")
def test_clear_schedules_mac(mock_run, mock_system, mock_path_home):
    plist_path = mock_path_home / "Library" / "LaunchAgents" / "com.jienweng.yappy.daily.plist"
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    plist_path.write_text("dummy")

    result = scheduler.clear_schedules()
    assert "macOS schedules cleared" in result
    assert not plist_path.exists()
    mock_run.assert_called_with(["launchctl", "unload", str(plist_path)], capture_output=True)
