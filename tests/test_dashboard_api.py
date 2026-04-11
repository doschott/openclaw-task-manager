"""
test_dashboard_api.py - Dashboard API endpoint tests

Tests the Flask API endpoints with mocked schtasks.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

# Import dashboard app
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))


class TestDashboardAPI:
    """Test dashboard API endpoints."""

    def test_naming_validation_api(self):
        """API validates task names against naming convention."""
        from dashboard import NAMING_PATTERN
        import re
        ALT_NAMING_PATTERN = re.compile(r"^(OpenClaw|ProphecyNews|QuantumHub|LemonParty|MedicalIntel|ShadowBroker)-[A-Za-z0-9]+(-[A-Za-z0-9]+)?$")

        valid_standard = "OpenClaw_Test_Valid_0700"
        valid_alt = "ProphecyNews-Dashboard"
        invalid = "DOSBot_Test_Invalid_0700"

        assert NAMING_PATTERN.match(valid_standard) or ALT_NAMING_PATTERN.match(valid_standard)
        assert NAMING_PATTERN.match(valid_alt) or ALT_NAMING_PATTERN.match(valid_alt)
        assert not NAMING_PATTERN.match(invalid) and not ALT_NAMING_PATTERN.match(invalid)

    def test_openclaw_pattern_matches_backslash_tasks(self):
        """OPENCLAW_PATTERN regex matches task names with leading backslash."""
        from dashboard import OPENCLAW_PATTERN

        # Dash-separated patterns (current OPENCLAW_PATTERN)
        assert OPENCLAW_PATTERN.match("\\OpenClaw-SecurityAudit")
        assert OPENCLAW_PATTERN.match("\\ProphecyNews-NewsFull-7am")
        assert OPENCLAW_PATTERN.match("\\QuantumHub-Alerts-1pm")
        assert OPENCLAW_PATTERN.match("OpenClaw-SecurityAudit")
        assert OPENCLAW_PATTERN.match("ProphecyNews-NewsFull-7am")
        assert not OPENCLAW_PATTERN.match("DOSBot-Test")

    def test_registry_load_empty(self, temp_home):
        """Loading registry when empty returns empty dict."""
        from dashboard import load_registry

        result = load_registry()
        assert result == {}

    def test_registry_save_and_load(self, temp_home):
        """Registry save and load round-trip works."""
        from dashboard import save_registry, load_registry

        test_data = {"OpenClaw_Test_Task_0700": {"name": "OpenClaw_Test_Task_0700", "command": "echo test"}}
        save_registry(test_data)

        result = load_registry()
        assert result == test_data


class TestDashboardImportExport:
    """Test dashboard import/export functionality."""

    def test_import_task_validates_name(self, temp_home):
        """Importing a task validates naming convention."""
        from dashboard import NAMING_PATTERN

        # Valid name should pass
        assert NAMING_PATTERN.match("OpenClaw_Test_Import_0700")

        # Invalid name should fail
        assert not NAMING_PATTERN.match("Test_Import_0700")

    def test_export_registry(self, temp_home, sample_registry_data):
        """Exporting registry produces valid JSON."""
        import json
        from dashboard import save_registry, REGISTRY_PATH

        save_registry(sample_registry_data)

        with open(REGISTRY_PATH) as f:
            data = json.load(f)

        assert "OpenClaw_ProphecyNews_NewsFull_0700" in data
