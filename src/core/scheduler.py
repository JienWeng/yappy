"""Module for OS-native scheduling of Yappy tasks."""
from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path


def register_daily_run(time_str: str) -> str:
    """
    Schedule a daily run of Yappy at the specified time.
    
    Args:
        time_str: Time in HH:MM format.
        
    Returns:
        Success message or error.
    """
    if platform.system() == "Darwin":
        return _schedule_mac(time_str)
    elif platform.system() == "Linux":
        return _schedule_linux(time_str)
    else:
        return f"Scheduling is not supported on {platform.system()} yet."


def _schedule_mac(time_str: str) -> str:
    """Create a launchd agent for macOS."""
    try:
        hour, minute = map(int, time_str.split(":"))
    except ValueError:
        return "Invalid time format. Use HH:MM."

    label = "com.jienweng.yappy.daily"
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
    executable = sys.argv[0]
    if not executable.endswith("yap"):
        # Fallback to current python + module if not run as 'yap'
        command_args = [sys.executable, "-m", "src.cli", "--no-tui"]
    else:
        command_args = [executable, "--no-tui"]

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{"</string><string>".join(command_args)}</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{Path.home()}/.config/yappy/scheduler.log</string>
    <key>StandardErrorPath</key>
    <string>{Path.home()}/.config/yappy/scheduler.log</string>
</dict>
</plist>
"""
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    plist_path.write_text(plist_content)

    # Load the agent
    subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
    result = subprocess.run(["launchctl", "load", str(plist_path)], capture_output=True)
    
    if result.returncode == 0:
        return f"Successfully scheduled daily run at {time_str} (macOS LaunchAgent)"
    else:
        return f"Failed to load schedule: {result.stderr.decode()}"


def _schedule_linux(time_str: str) -> str:
    """Add a crontab entry for Linux."""
    try:
        hour, minute = map(int, time_str.split(":"))
    except ValueError:
        return "Invalid time format. Use HH:MM."

    executable = sys.argv[0]
    cron_cmd = f"{minute} {hour} * * * {executable} --no-tui >> ~/.config/yappy/scheduler.log 2>&1"
    
    try:
        # Get current crontab
        current_cron = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        if "yappy" in current_cron:
            # Update existing
            lines = [line for line in current_cron.splitlines() if "yappy" not in line]
            lines.append(f"# yappy daily run\n{cron_cmd}")
            new_cron = "\n".join(lines) + "\n"
        else:
            new_cron = current_cron + f"\n# yappy daily run\n{cron_cmd}\n"
            
        subprocess.run(["crontab", "-"], input=new_cron, text=True, check=True)
        return f"Successfully scheduled daily run at {time_str} (Linux crontab)"
    except Exception as e:
        return f"Failed to update crontab: {str(e)}"


def list_schedules() -> str:
    """List current Yappy schedules."""
    if platform.system() == "Darwin":
        label = "com.jienweng.yappy.daily"
        plist_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
        if plist_path.exists():
            return f"Found active macOS schedule: {plist_path}"
        return "No active schedules found."
    # Add Linux list logic if needed
    return "Listing not supported on this OS."


def clear_schedules() -> str:
    """Remove all Yappy schedules."""
    if platform.system() == "Darwin":
        label = "com.jienweng.yappy.daily"
        plist_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
        if plist_path.exists():
            subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
            plist_path.unlink()
            return "All macOS schedules cleared."
    return "No schedules to clear."
