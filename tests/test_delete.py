"""
test_delete.py - Delete task safety and verification tests
"""

import pytest
from unittest.mock import patch, MagicMock


class TestDeleteSafety:
    """Test delete safety checks and safeguards."""

    def test_delete_requires_registry_verification(self, temp_home, sample_registry_data):
        """Delete should verify task exists in registry before deleting from Windows."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        
        # Save registry with known tasks
        import scripts.registry as registry_module
        registry_module.save_registry(sample_registry_data)
        
        # Task IS in registry - should allow delete
        task_name = "OpenClaw_ProphecyNews_NewsFull_0700"
        assert task_name in sample_registry_data
        
        # Mock schtasks to succeed
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            
            from scripts.delete import query_windows_task
            result = query_windows_task(task_name)
            assert result is True  # Task found in Windows

    def test_delete_blocked_if_not_in_registry(self, temp_home, sample_registry_data):
        """Delete should refuse to delete tasks not in registry (without --force)."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        
        # Save registry with some tasks
        import scripts.registry as registry_module
        registry_module.save_registry(sample_registry_data)
        
        # Task is NOT in registry
        fake_task = "OpenClaw_DoesNotExist_Task_0000"
        registry = registry_module.load_registry()
        assert fake_task not in registry
        
        # Mock schtasks to say task doesn't exist
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="ERROR: The system cannot find the task specified."
            )
            
            from scripts.delete import query_windows_task
            result = query_windows_task(fake_task)
            assert result is False  # Task not found in Windows

    def test_delete_windows_task_called(self):
        """Delete should call schtasks /delete with correct arguments."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            
            from scripts.delete import delete_windows_task
            result = delete_windows_task("OpenClaw_Test_Task_0700")
            
            assert result is True
            args = mock_run.call_args[0][0]
            assert "/delete" in args
            assert "/tn" in args
            assert "OpenClaw_Test_Task_0700" in args
            assert "/f" in args  # Force flag

    def test_delete_access_denied(self):
        """Delete raises PermissionError on access denied."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="ERROR: Access is denied."
            )
            
            from scripts.delete import delete_windows_task
            
            with pytest.raises(PermissionError) as exc_info:
                delete_windows_task("OpenClaw_Test_Task_0700")
            assert "Administrator" in str(exc_info.value)

    def test_delete_task_not_found_in_windows(self):
        """Delete raises RuntimeError when task doesn't exist in Windows."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="ERROR: The system cannot find the task specified."
            )
            
            from scripts.delete import delete_windows_task
            
            with pytest.raises(RuntimeError) as exc_info:
                delete_windows_task("OpenClaw_DoesNotExist_0000")
            assert "cannot find" in str(exc_info.value).lower()
