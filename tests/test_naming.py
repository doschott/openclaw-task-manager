"""
test_naming.py - Naming convention validation tests
"""

import pytest
import re

# Import the validation function directly from create.py
# We test the regex pattern used across all scripts
NAMING_PATTERN = re.compile(r'^OpenClaw_[A-Z][a-zA-Z0-9]*_[A-Z][a-zA-Z0-9]*_[A-Z0-9a-z]+$')


class TestNamingConvention:
    """Tests for the OpenClaw naming convention: OpenClaw_{Project}_{Action}_{Schedule}"""

    # === VALID NAMES ===
    @pytest.mark.parametrize("name", [
        "OpenClaw_ProphecyNews_NewsFull_0700",
        "OpenClaw_QuantumHub_SyncDaily_0900",
        "OpenClaw_LemonParty_Report_Monday",
        "OpenClaw_MedicalIntel_Alert_Hourly",
        "OpenClaw_Backups_FullWeekly_Sunday",
        "OpenClaw_ShadowBroker_OSINT_Daily",
        "OpenClaw_Test_Test_0000",
        "OpenClaw_A_B_C",
        "OpenClaw_ABC_XYZ_123",
        "OpenClaw_ProphecyNews_NewsFull_Daily",
        "OpenClaw_QuantumHub_ThreatCheck_Hourly",
    ])
    def test_valid_names_match(self, name):
        """Valid names should match the pattern exactly."""
        assert NAMING_PATTERN.match(name), f"Expected '{name}' to be valid"

    # === INVALID PREFIX ===
    @pytest.mark.parametrize("name", [
        "DOSBot_ProphecyNews_NewsFull_0700",
        "openclaw_ProphecyNews_NewsFull_0700",
        "Openclaw_ProphecyNews_NewsFull_0700",  # wrong case
        "CLAWBOT_ProphecyNews_NewsFull_0700",
        "ProphecyNews_NewsFull_0700",  # missing prefix entirely
    ])
    def test_invalid_prefix_rejected(self, name):
        """Names with wrong prefix should be rejected."""
        assert not NAMING_PATTERN.match(name), f"Expected '{name}' to be invalid (wrong prefix)"

    # === INVALID COMPONENT COUNT ===
    @pytest.mark.parametrize("name", [
        "OpenClaw_ProphecyNews_NewsFull",           # missing schedule
        "OpenClaw_ProphecyNews_0700",                # missing action
        "OpenClaw_NewsFull_0700",                   # missing project
        "OpenClaw_ProphecyNews_NewsFull_0700_Extra", # too many components
        "OpenClaw_",                                # just prefix
        "OpenClaw_A_B",                             # missing schedule
    ])
    def test_invalid_component_count_rejected(self, name):
        """Names with wrong number of components should be rejected."""
        assert not NAMING_PATTERN.match(name), f"Expected '{name}' to be invalid (wrong component count)"

    # === INVALID CASE ===
    @pytest.mark.parametrize("name", [
        "OpenClaw_news_fetch_0700",     # lowercase action
        "OpenClaw_prophecy_news_full_0700",  # lowercase project
        "OpenClaw_ProphecyNews_news_full_0700",  # camelCase instead of PascalCase
        "openclaw_ProphecyNews_NewsFull_0700",  # lowercase prefix
    ])
    def test_invalid_case_rejected(self, name):
        """Names not using PascalCase should be rejected."""
        assert not NAMING_PATTERN.match(name), f"Expected '{name}' to be invalid (wrong case)"

    # === INVALID SCHEDULE ===
    @pytest.mark.parametrize("name", [
        "OpenClaw_ProphecyNews_NewsFull_",     # empty schedule
        "OpenClaw_ProphecyNews_NewsFull___",  # underscores only
    ])
    def test_invalid_schedule_rejected(self, name):
        """Names with invalid schedule component should be rejected."""
        assert not NAMING_PATTERN.match(name), f"Expected '{name}' to be invalid (bad schedule)"

    # === EDGE CASES ===
    def test_exactly_correct_format(self):
        """Verify the exact format string."""
        name = "OpenClaw_ProphecyNews_NewsFull_0700"
        assert name == "OpenClaw_ProphecyNews_NewsFull_0700"
        assert len(name.split("_")) == 4
        assert name.startswith("OpenClaw_")

    def test_schedule_allows_mixed_case(self):
        """Schedule component allows mixed case (e.g., Sunday, MON, daily)."""
        valid = [
            "OpenClaw_ProphecyNews_NewsFull_Sunday",
            "OpenClaw_ProphecyNews_NewsFull_MONDAY",
            "OpenClaw_ProphecyNews_NewsFull_Daily",
            "OpenClaw_ProphecyNews_NewsFull_daily",
        ]
        for name in valid:
            assert NAMING_PATTERN.match(name), f"Expected '{name}' to be valid"

    def test_numbers_in_components(self):
        """Numbers are allowed in all components."""
        valid = [
            "OpenClaw_Prophecy2_NewsFull2_0700",
            "OpenClaw_Prop2News_Full3_1234",
        ]
        for name in valid:
            assert NAMING_PATTERN.match(name), f"Expected '{name}' to be valid"
