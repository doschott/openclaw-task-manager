"""
test_registry.py - Task registry CRUD operation tests
"""

import json
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import registry module
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import importlib.util
spec = importlib.util.spec_from_file_location("registry",
    Path(__file__).parent.parent / "scripts" / "registry.py")
registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry)


class TestRegistryCRUD:
    """Test registry load, save, create, update, delete operations."""

    def test_load_empty_registry(self, temp_home, monkeypatch):
        """Loading a non-existent registry returns empty dict."""
        monkeypatch.setattr(registry, "REGISTRY_PATH", temp_home / ".openclaw" / "task-registry.json")
        monkeypatch.setattr(registry, "VERSION_REGISTRY_PATH", temp_home / ".openclaw" / "task-registry-versions.json")
        result = registry.load_registry()
        assert result == {}

    def test_save_and_load_registry(self, temp_home, sample_registry_data, monkeypatch):
        """Saving then loading returns the same data."""
        monkeypatch.setattr(registry, "REGISTRY_PATH", temp_home / ".openclaw" / "task-registry.json")
        monkeypatch.setattr(registry, "VERSION_REGISTRY_PATH", temp_home / ".openclaw" / "task-registry-versions.json")
        registry.save_registry(sample_registry_data)
        result = registry.load_registry()
        assert result == sample_registry_data

    def test_registry_path(self, temp_home, monkeypatch):
        """Registry is saved to ~/.openclaw/task-registry.json."""
        monkeypatch.setattr(registry, "REGISTRY_PATH", temp_home / ".openclaw" / "task-registry.json")
        monkeypatch.setattr(registry, "VERSION_REGISTRY_PATH", temp_home / ".openclaw" / "task-registry-versions.json")
        registry.save_registry({})
        expected = temp_home / ".openclaw" / "task-registry.json"
        assert expected.exists()

    def test_add_task(self, temp_home, monkeypatch):
        """add_task adds a task to the registry."""
        monkeypatch.setattr(registry, "REGISTRY_PATH", temp_home / ".openclaw" / "task-registry.json")
        monkeypatch.setattr(registry, "VERSION_REGISTRY_PATH", temp_home / ".openclaw" / "task-registry-versions.json")

        task_name = "OpenClaw_Test_Task_0700"
        metadata = {
            "command": "python test.py",
            "time": "07:00",
            "schedule": "daily",
            "created_at": "2026-04-10T07:00:00",
        }

        result = registry.add_task(task_name, metadata)
        assert result is True

        reg = registry.load_registry()
        assert task_name in reg
        assert reg[task_name]["command"] == "python test.py"

    def test_remove_task(self, temp_home, sample_registry_data, monkeypatch):
        """remove_task deletes a task from the registry."""
        monkeypatch.setattr(registry, "REGISTRY_PATH", temp_home / ".openclaw" / "task-registry.json")
        monkeypatch.setattr(registry, "VERSION_REGISTRY_PATH", temp_home / ".openclaw" / "task-registry-versions.json")
        registry.save_registry(sample_registry_data)
        task_to_delete = "OpenClaw_ProphecyNews_NewsFull_0700"

        result = registry.remove_task(task_to_delete)
        assert result is True

        reg = registry.load_registry()
        assert task_to_delete not in reg

    def test_remove_nonexistent_task(self, temp_home, monkeypatch):
        """Removing a non-existent task returns False."""
        monkeypatch.setattr(registry, "REGISTRY_PATH", temp_home / ".openclaw" / "task-registry.json")
        monkeypatch.setattr(registry, "VERSION_REGISTRY_PATH", temp_home / ".openclaw" / "task-registry-versions.json")
        result = registry.remove_task("OpenClaw_DoesNotExist_Task_0000")
        assert result is False

    def test_get_task(self, temp_home, sample_registry_data, monkeypatch):
        """get_task returns a specific task's metadata."""
        monkeypatch.setattr(registry, "REGISTRY_PATH", temp_home / ".openclaw" / "task-registry.json")
        monkeypatch.setattr(registry, "VERSION_REGISTRY_PATH", temp_home / ".openclaw" / "task-registry-versions.json")
        registry.save_registry(sample_registry_data)

        task = registry.get_task("OpenClaw_ProphecyNews_NewsFull_0700")
        assert task is not None
        assert task["command"] == "python D:\\scripts\\fetch_news.py"

    def test_list_tasks(self, temp_home, sample_registry_data, monkeypatch):
        """list_tasks returns all registered tasks."""
        monkeypatch.setattr(registry, "REGISTRY_PATH", temp_home / ".openclaw" / "task-registry.json")
        monkeypatch.setattr(registry, "VERSION_REGISTRY_PATH", temp_home / ".openclaw" / "task-registry-versions.json")
        registry.save_registry(sample_registry_data)

        tasks = registry.list_tasks()
        assert len(tasks) == 2
        assert "OpenClaw_ProphecyNews_NewsFull_0700" in tasks


class TestVersionRegistry:
    """Test version history tracking."""

    def test_load_empty_version_registry(self, temp_home, monkeypatch):
        """Loading non-existent version registry returns empty dict."""
        monkeypatch.setattr(registry, "REGISTRY_PATH", temp_home / ".openclaw" / "task-registry.json")
        monkeypatch.setattr(registry, "VERSION_REGISTRY_PATH", temp_home / ".openclaw" / "task-registry-versions.json")
        result = registry.load_version_registry()
        assert result == {}

    def test_add_version(self, temp_home, sample_registry_data, monkeypatch):
        """add_version adds a version entry for a task."""
        monkeypatch.setattr(registry, "REGISTRY_PATH", temp_home / ".openclaw" / "task-registry.json")
        monkeypatch.setattr(registry, "VERSION_REGISTRY_PATH", temp_home / ".openclaw" / "task-registry-versions.json")
        registry.save_registry(sample_registry_data)

        task_name = "OpenClaw_ProphecyNews_NewsFull_0700"
        task_meta = sample_registry_data[task_name]

        result = registry.add_version(task_name, task_meta, "Test version")
        assert result is True

        versions = registry.get_versions(task_name)
        assert len(versions) == 1
        assert versions[0]["reason"] == "Test version"

    def test_get_versions(self, temp_home, sample_registry_data, monkeypatch):
        """get_versions returns all versions for a task."""
        monkeypatch.setattr(registry, "REGISTRY_PATH", temp_home / ".openclaw" / "task-registry.json")
        monkeypatch.setattr(registry, "VERSION_REGISTRY_PATH", temp_home / ".openclaw" / "task-registry-versions.json")
        registry.save_registry(sample_registry_data)

        task_name = "OpenClaw_QuantumHub_SyncDaily_0900"
        task_meta = sample_registry_data[task_name]

        registry.add_version(task_name, task_meta, "v1")
        registry.add_version(task_name, task_meta, "v2")

        versions = registry.get_versions(task_name)
        assert len(versions) == 2

    def test_get_latest_version(self, temp_home, sample_registry_data, monkeypatch):
        """get_latest_version returns the most recent version."""
        monkeypatch.setattr(registry, "REGISTRY_PATH", temp_home / ".openclaw" / "task-registry.json")
        monkeypatch.setattr(registry, "VERSION_REGISTRY_PATH", temp_home / ".openclaw" / "task-registry-versions.json")
        registry.save_registry(sample_registry_data)

        task_name = "OpenClaw_ProphecyNews_NewsFull_0700"
        task_meta = sample_registry_data[task_name]

        registry.add_version(task_name, task_meta, "v1")
        registry.add_version(task_name, task_meta, "v2")

        latest = registry.get_latest_version(task_name)
        assert latest["reason"] == "v2"

    def test_delete_versions(self, temp_home, sample_registry_data, monkeypatch):
        """delete_versions removes all version history for a task."""
        monkeypatch.setattr(registry, "REGISTRY_PATH", temp_home / ".openclaw" / "task-registry.json")
        monkeypatch.setattr(registry, "VERSION_REGISTRY_PATH", temp_home / ".openclaw" / "task-registry-versions.json")
        registry.save_registry(sample_registry_data)

        task_name = "OpenClaw_ProphecyNews_NewsFull_0700"
        registry.add_version(task_name, sample_registry_data[task_name], "v1")

        result = registry.delete_versions(task_name)
        assert result is True

        versions = registry.get_versions(task_name)
        assert versions == []

    def test_version_number_auto_increment(self, temp_home, sample_registry_data, monkeypatch):
        """Version numbers auto-increment with each new version."""
        monkeypatch.setattr(registry, "REGISTRY_PATH", temp_home / ".openclaw" / "task-registry.json")
        monkeypatch.setattr(registry, "VERSION_REGISTRY_PATH", temp_home / ".openclaw" / "task-registry-versions.json")
        registry.save_registry(sample_registry_data)

        task_name = "OpenClaw_ProphecyNews_NewsFull_0700"
        task_meta = sample_registry_data[task_name]

        for i in range(3):
            registry.add_version(task_name, task_meta, f"v{i+1}")

        versions = registry.get_versions(task_name)
        assert [v["version"] for v in versions] == [1, 2, 3]


class TestRegistryValidation:
    """Test registry validation and safety checks."""

    def test_task_has_required_fields(self, temp_home, monkeypatch):
        """A registered task has all required fields."""
        monkeypatch.setattr(registry, "REGISTRY_PATH", temp_home / ".openclaw" / "task-registry.json")
        monkeypatch.setattr(registry, "VERSION_REGISTRY_PATH", temp_home / ".openclaw" / "task-registry-versions.json")

        task_name = "OpenClaw_Test_Valid_0700"
        metadata = {
            "command": "cmd",
            "time": "07:00",
            "schedule": "daily",
            "created_at": "2026-04-10T07:00:00",
        }

        registry.add_task(task_name, metadata)
        task = registry.get_task(task_name)

        assert "command" in task
        assert "schedule" in task
        assert "time" in task

    def test_ensure_registry_dir_creates_directory(self, temp_home, monkeypatch):
        """ensure_registry_dir creates ~/.openclaw if it doesn't exist."""
        monkeypatch.setattr(registry, "REGISTRY_PATH", temp_home / ".openclaw" / "task-registry.json")
        monkeypatch.setattr(registry, "VERSION_REGISTRY_PATH", temp_home / ".openclaw" / "task-registry-versions.json")

        reg_path = registry.REGISTRY_PATH
        assert not reg_path.parent.exists()

        registry.ensure_registry_dir()
        assert reg_path.parent.exists()

    def test_export_registry_round_trip(self, temp_home, sample_registry_data, monkeypatch, tmp_path):
        """export_registry produces valid JSON that can be re-imported."""
        monkeypatch.setattr(registry, "REGISTRY_PATH", temp_home / ".openclaw" / "task-registry.json")
        monkeypatch.setattr(registry, "VERSION_REGISTRY_PATH", temp_home / ".openclaw" / "task-registry-versions.json")

        registry.save_registry(sample_registry_data)

        export_path = tmp_path / "export.json"
        result = registry.export_registry(str(export_path))
        assert result is True
        assert export_path.exists()

        # Clear registry and import
        registry.save_registry({})
        assert registry.load_registry() == {}

        registry.import_registry(str(export_path))
        restored = registry.load_registry()
        assert restored == sample_registry_data
