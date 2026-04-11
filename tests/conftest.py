"""
conftest.py - Pytest fixtures and shared test configuration
"""

import os
import sys
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))

# Patch HOME to a temp dir for isolated registry tests
@pytest.fixture(autouse=True)
def temp_home(monkeypatch, tmp_path):
    """Use a temp directory as HOME for all tests to avoid touching real registry."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    # Patch Path.home() directly since it doesn't read HOME env var on Linux
    import pathlib
    original_home = pathlib.Path.home
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
    yield tmp_path
    monkeypatch.setattr(pathlib.Path, "home", original_home)


@pytest.fixture
def mock_schtasks():
    """Mock schtasks.exe for tests that don't need real Windows interaction."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        yield mock_run


@pytest.fixture
def sample_registry_data():
    """Sample registry data for testing."""
    return {
        "OpenClaw_ProphecyNews_NewsFull_0700": {
            "name": "OpenClaw_ProphecyNews_NewsFull_0700",
            "command": "python D:\\scripts\\fetch_news.py",
            "schedule": "daily",
            "time": "07:00",
            "created_at": "2026-04-10T07:00:00",
            "last_run": "2026-04-11T07:00:00",
            "last_result": "0",
            "version": 1,
            "versions": [
                {"version": 1, "command": "python D:\\scripts\\fetch_news.py", "schedule": "daily", "time": "07:00", "changed_at": "2026-04-10T07:00:00"}
            ]
        },
        "OpenClaw_QuantumHub_SyncDaily_0900": {
            "name": "OpenClaw_QuantumHub_SyncDaily_0900",
            "command": "python D:\\scripts\\sync_quantum.py",
            "schedule": "daily",
            "time": "09:00",
            "created_at": "2026-04-09T09:00:00",
            "last_run": None,
            "last_result": None,
            "version": 1,
            "versions": []
        }
    }


@pytest.fixture
def sample_schtasks_output():
    r"""Sample schtasks /query output for parser testing."""
    return """Folder: \\
HostName:                             DESKTOP-LHF0B8V
TaskName:                             \OpenClaw_ProphecyNews_NewsFull_0700
Next Run Time:                        4/12/2026 7:00:00 AM
Status:                               Ready
Last Run Time:                       4/11/2026 7:00:00 AM
Last Result:                         0
Task To Run:                         python D:\\scripts\\fetch_news.py
Start In:                            N/A
Comment:                             N/A
Scheduled Type:                       Daily
Start Time:                          7:00:00 AM
Days:                                Every day
Weekly:                              N/A
Monthly:                             N/A
Run Only If Idle:                    Disabled
Idle Time:                           Disabled
Stop If Going On Batteries:          Disabled
Restart On Failure:                  Disabled
Multiple Instances:                  Parallel
Hidden:                              Disabled
Run Privileged:                      Disabled
Wake To Run:                         Disabled
Network Profile Name:                N/A
Network Settings:                    N/A

TaskName:                             \OpenClaw_QuantumHub_SyncDaily_0900
Next Run Time:                        4/12/2026 9:00:00 AM
Status:                               Ready
Last Run Time:                       N/A
Last Result:                         267011
Task To Run:                         python D:\\scripts\\sync_quantum.py
Start In:                            N/A
Comment:                             Fetch quantum news
Scheduled Type:                       Daily
Start Time:                          9:00:00 AM
Days:                                Every day
Weekly:                              N/A
Monthly:                             N/A
Run Only If Idle:                    Disabled
Idle Time:                           Disabled
Stop If Going On Batteries:          Disabled
Restart On Failure:                  Disabled
Multiple Instances:                  Parallel
Hidden:                              Disabled
Run Privileged:                      Disabled
Wake To Run:                         Disabled
Network Profile Name:                N/A
Network Settings:                    N/A
"""
