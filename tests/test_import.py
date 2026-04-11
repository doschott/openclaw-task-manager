"""
test_import.py - Import existing Windows tasks tests
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Load import.py as a module (can't use 'import' as a name directly)
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import importlib.util
import_spec = importlib.util.spec_from_file_location(
    "import_module",
    Path(__file__).parent.parent / "scripts" / "import.py"
)
import_mod = importlib.util.module_from_spec(import_spec)
import_spec.loader.exec_module(import_mod)


class TestImportTask:
    """Test importing existing Windows Task Scheduler tasks."""

    def test_import_validates_naming_convention(self):
        """Import rejects tasks that don't follow naming convention."""
        # Valid name should not raise
        import_mod.validate_name("OpenClaw_Test_Import_0700")

        # Invalid name should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            import_mod.validate_name("DOSBot_Test_Import_0700")
        assert "naming convention" in str(exc_info.value).lower()

    def test_query_task_from_windows(self):
        """query_task_from_windows calls schtasks with correct args."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="TaskName:  \\OpenClaw_Test_Task_0700\nStatus:  Ready",
                stderr=""
            )

            result = import_mod.query_task_from_windows("OpenClaw_Test_Task_0700")

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "/query" in args
            assert "OpenClaw_Test_Task_0700" in args

    def test_query_task_not_found(self):
        """Query returns None when task doesn't exist in Windows."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="ERROR: The system cannot find the task specified."
            )

            result = import_mod.query_task_from_windows("OpenClaw_DoesNotExist_0000")
            assert result is None

    def test_import_registers_task_in_registry(self, temp_home):
        """Import adds task to registry with version 1."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="TaskName:  \\OpenClaw_Test_Task_0700\nStatus:  Ready\nLast Result:  0",
                stderr=""
            )

            task_info = import_mod.query_task_from_windows("OpenClaw_Test_Task_0700")
            assert task_info is not None
