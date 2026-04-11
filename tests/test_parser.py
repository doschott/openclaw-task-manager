"""
test_parser.py - Windows schtasks output parser tests

Tests the schtasks /query output parser, including:
- Task names with and without leading backslash
- Field collection before and after Status line
- All parsed fields (status, next_run, last_run, last_result, command)
"""

import pytest
import re
from unittest.mock import patch, MagicMock


class TestSchtasksParser:
    """Test schtasks /query output parsing."""

    def parse_schtasks_output(self, output):
        """Replicate the parser logic from dashboard.py."""
        OPENCLAW_PATTERN = re.compile(r"^\\?OpenClaw_")
        tasks = {}
        current_task = {}
        
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("TaskName:"):
                # Save previous task if any
                if current_task.get("name"):
                    tasks[current_task["name"]] = current_task
                name = line.split("TaskName:", 1)[1].strip()
                if OPENCLAW_PATTERN.match(name):
                    current_task = {"name": name.lstrip("\\")}
                else:
                    current_task = {}
            elif current_task.get("name"):
                if line.startswith("Next Run Time:"):
                    current_task["next_run"] = line.split("Next Run Time:", 1)[1].strip()
                elif line.startswith("Last Run Time:"):
                    current_task["last_run"] = line.split("Last Run Time:", 1)[1].strip()
                elif line.startswith("Last Result:"):
                    current_task["last_result"] = line.split("Last Result:", 1)[1].strip()
                elif line.startswith("Status:"):
                    current_task["status"] = line.split("Status:", 1)[1].strip()
                elif line.startswith("Task To Run:"):
                    current_task["command"] = line.split("Task To Run:", 1)[1].strip()
        
        # Save last task
        if current_task.get("name"):
            tasks[current_task["name"]] = current_task
        
        return tasks

    def test_parses_task_with_leading_backslash(self, sample_schtasks_output):
        """Task names from schtasks have leading backslash - parser must strip it."""
        tasks = self.parse_schtasks_output(sample_schtasks_output)
        
        assert "OpenClaw_ProphecyNews_NewsFull_0700" in tasks
        assert "\\OpenClaw_ProphecyNews_NewsFull_0700" not in tasks

    def test_parses_all_fields_for_single_task(self, sample_schtasks_output):
        """All fields are captured even when they come AFTER the Status line."""
        tasks = self.parse_schtasks_output(sample_schtasks_output)
        
        task = tasks["OpenClaw_ProphecyNews_NewsFull_0700"]
        assert task["status"] == "Ready"
        assert task["next_run"] == "4/12/2026 7:00:00 AM"
        assert task["last_run"] == "4/11/2026 7:00:00 AM"
        assert task["last_result"] == "0"
        assert "fetch_news.py" in task["command"]

    def test_parses_multiple_tasks(self, sample_schtasks_output):
        """Multiple tasks in output are each parsed correctly."""
        tasks = self.parse_schtasks_output(sample_schtasks_output)
        
        assert len(tasks) == 2
        assert "OpenClaw_ProphecyNews_NewsFull_0700" in tasks
        assert "OpenClaw_QuantumHub_SyncDaily_0900" in tasks

    def test_last_result_after_status(self):
        """Last Result comes AFTER Status line - ensure it's captured."""
        output = """TaskName:                             \\OpenClaw_Test_Task_0000
Next Run Time:                        N/A
Last Run Time:                       4/11/2026 8:00:00 AM
Status:                               Ready
Last Result:                         267011
Task To Run:                         echo test
"""
        tasks = self.parse_schtasks_output(output)
        
        task = tasks["OpenClaw_Test_Task_0000"]
        assert task["status"] == "Ready"
        assert task["last_result"] == "267011"
        assert task["command"] == "echo test"

    def test_task_to_run_after_status(self):
        """Task To Run comes AFTER Status line - ensure it's captured."""
        output = """TaskName:                             \\OpenClaw_Test_Task_0000
Next Run Time:                        4/12/2026 7:00:00 AM
Status:                               Ready
Last Result:                         0
Task To Run:                         python D:\\scripts\\test.py
"""
        tasks = self.parse_schtasks_output(output)
        
        task = tasks["OpenClaw_Test_Task_0000"]
        assert task["command"] == "python D:\\scripts\\test.py"

    def test_nona_openclaw_tasks_ignored(self, sample_schtasks_output):
        r"""Non-OpenClaw tasks (e.g., Microsoft\Windows\...) are ignored."""
        tasks = self.parse_schtasks_output(sample_schtasks_output)
        
        # No task names should have backslash at start (they should be stripped)
        for name in tasks.keys():
            assert not name.startswith("\\"), f"Task name should be stripped: {name}"
            assert name.startswith("OpenClaw_"), f"Non-OpenClaw task leaked in: {name}"

    def test_missing_fields_handled(self):
        """Tasks with missing fields don't crash and have None for missing fields."""
        output = """TaskName:                             \\OpenClaw_Test_Task_0000
Status:                               Ready
"""
        tasks = self.parse_schtasks_output(output)
        
        task = tasks["OpenClaw_Test_Task_0000"]
        assert task["status"] == "Ready"
        assert task.get("last_result") is None
        assert task.get("next_run") is None

    def test_task_name_without_backslash(self):
        """Parser also handles task names without leading backslash."""
        output = """TaskName:                             OpenClaw_Test_Task_0000
Status:                               Ready
Last Result:                         0
Task To Run:                         echo test
"""
        tasks = self.parse_schtasks_output(output)
        
        assert "OpenClaw_Test_Task_0000" in tasks
        assert "\\OpenClaw_Test_Task_0000" not in tasks

    def test_empty_output(self):
        """Empty output returns empty dict."""
        tasks = self.parse_schtasks_output("")
        assert tasks == {}

    def test_no_openclaw_tasks(self):
        """Output with no OpenClaw tasks returns empty dict."""
        output = """TaskName:                             \\Microsoft\\Windows\\TaskManager
Status:                               Ready
"""
        tasks = self.parse_schtasks_output(output)
        assert tasks == {}

    def test_task_with_no_status(self):
        """Task without a Status line is still captured."""
        output = """TaskName:                             \\OpenClaw_Test_Task_0000
Next Run Time:                        4/12/2026 7:00:00 AM
Task To Run:                         echo test
"""
        tasks = self.parse_schtasks_output(output)
        
        assert "OpenClaw_Test_Task_0000" in tasks
        assert tasks["OpenClaw_Test_Task_0000"].get("status") is None

    def test_whitespace_variation(self):
        """Parser handles variable whitespace in field values."""
        output = """TaskName:                             \\OpenClaw_Test_Task_0000
Status:                               Ready
Last Result:                         0
Task To Run:                         python   D:\\test.py
"""
        tasks = self.parse_schtasks_output(output)
        
        assert tasks["OpenClaw_Test_Task_0000"]["command"] == "python   D:\\test.py"
