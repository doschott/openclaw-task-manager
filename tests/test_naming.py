"""
test_naming.py - Naming convention validation tests
"""

import pytest
import re

# Import patterns from create.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import importlib.util
spec = importlib.util.spec_from_file_location("create_module",
    Path(__file__).parent.parent / "scripts" / "create.py")
create_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(create_mod)

NAMING_PATTERN = create_mod.NAMING_PATTERN
ALT_NAMING_PATTERN = create_mod.ALT_NAMING_PATTERN


class TestStandardNaming:
    """Tests for standard OpenClaw naming convention: OpenClaw_{Project}_{Action}_{Schedule}"""

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
    def test_valid_standard_names_match(self, name):
        """Valid standard names should match the pattern."""
        assert NAMING_PATTERN.match(name), f"Expected '{name}' to be valid"

    @pytest.mark.parametrize("name", [
        "DOSBot_ProphecyNews_NewsFull_0700",
        "openclaw_ProphecyNews_NewsFull_0700",
        "Openclaw_ProphecyNews_NewsFull_0700",
        "CLAWBOT_ProphecyNews_NewsFull_0700",
        "ProphecyNews_NewsFull_0700",
    ])
    def test_invalid_prefix_rejected(self, name):
        """Names with wrong prefix should be rejected."""
        assert not NAMING_PATTERN.match(name), f"Expected '{name}' to be invalid (wrong prefix)"

    @pytest.mark.parametrize("name", [
        "OpenClaw_ProphecyNews_NewsFull",
        "OpenClaw_ProphecyNews_0700",
        "OpenClaw_NewsFull_0700",
        "OpenClaw_ProphecyNews_NewsFull_0700_Extra",
        "OpenClaw_",
        "OpenClaw_A_B",
    ])
    def test_invalid_component_count_rejected(self, name):
        """Names with wrong number of components should be rejected."""
        assert not NAMING_PATTERN.match(name), f"Expected '{name}' to be invalid (wrong component count)"

    @pytest.mark.parametrize("name", [
        "OpenClaw_news_fetch_0700",
        "OpenClaw_prophecy_news_full_0700",
        "OpenClaw_ProphecyNews_news_full_0700",
        "openclaw_ProphecyNews_NewsFull_0700",
    ])
    def test_invalid_case_rejected(self, name):
        """Names not using PascalCase should be rejected."""
        assert not NAMING_PATTERN.match(name), f"Expected '{name}' to be invalid (wrong case)"

    @pytest.mark.parametrize("name", [
        "OpenClaw_ProphecyNews_NewsFull_",
        "OpenClaw_ProphecyNews_NewsFull___",
    ])
    def test_invalid_schedule_rejected(self, name):
        """Names with invalid schedule component should be rejected."""
        assert not NAMING_PATTERN.match(name), f"Expected '{name}' to be invalid (bad schedule)"

    def test_exactly_correct_format(self):
        name = "OpenClaw_ProphecyNews_NewsFull_0700"
        assert name == "OpenClaw_ProphecyNews_NewsFull_0700"
        assert len(name.split("_")) == 4
        assert name.startswith("OpenClaw_")

    def test_schedule_allows_mixed_case(self):
        valid = [
            "OpenClaw_ProphecyNews_NewsFull_Sunday",
            "OpenClaw_ProphecyNews_NewsFull_MONDAY",
            "OpenClaw_ProphecyNews_NewsFull_Daily",
            "OpenClaw_ProphecyNews_NewsFull_daily",
        ]
        for name in valid:
            assert NAMING_PATTERN.match(name), f"Expected '{name}' to be valid"

    def test_numbers_in_components(self):
        valid = [
            "OpenClaw_Prophecy2_NewsFull2_0700",
            "OpenClaw_Prop2News_Full3_1234",
        ]
        for name in valid:
            assert NAMING_PATTERN.match(name), f"Expected '{name}' to be valid"


class TestAlternativeNaming:
    """Tests for alternative dash-separated naming: {ProjectName}-{Descriptor}(-{Schedule})?"""

    @pytest.mark.parametrize("name", [
        # OpenClaw system tasks
        "OpenClaw-SecurityAudit",
        "OpenClaw-SessionCleanup",
        "OpenClaw-SilentBackup",
        # ProphecyNews tasks
        "ProphecyNews-Dashboard",
        "ProphecyNews-Digest",
        "ProphecyNews-ReaderResponses",
        "ProphecyNews-Video",
        "ProphecyNews-Weekly",
        "ProphecyNews-NewsFull-1pm",
        "ProphecyNews-NewsFull-6pm",
        "ProphecyNews-NewsFull-7am",
        "ProphecyNews-PushVercel-1pm",
        "ProphecyNews-PushVercel-6pm",
        "ProphecyNews-PushVercel-7am",
        # QuantumHub tasks
        "QuantumHub-Alerts-1pm",
        "QuantumHub-Alerts-6pm",
        "QuantumHub-Alerts-7am",
        "QuantumHub-News-1pm",
        "QuantumHub-News-6pm",
        "QuantumHub-News-7am",
        "QuantumHub-PushVercel-1pm",
        "QuantumHub-PushVercel-6pm",
        "QuantumHub-PushVercel-7am",
        "QuantumHub-Video-6am",
    ])
    def test_valid_alt_names_match(self, name):
        """Valid alternative names should match the pattern."""
        assert ALT_NAMING_PATTERN.match(name), f"Expected '{name}' to be valid"

    @pytest.mark.parametrize("name", [
        "DOSBot-SecurityAudit",
        "Prophecy-Dashboard",
        "Quantum-Digest",
        "UnknownProject-Task",
        "OpenClaw_",
        "ProphecyNews_Weekly",
    ])
    def test_invalid_alt_prefix_rejected(self, name):
        """Names with unknown project prefixes should be rejected."""
        assert not ALT_NAMING_PATTERN.match(name), f"Expected '{name}' to be invalid (unknown prefix)"

    @pytest.mark.parametrize("name", [
        "OpenClaw-",
        "ProphecyNews-",
        "QuantumHub-Alerts-",
        "ProphecyNews-NewsFull-1pm-Extra",
    ])
    def test_invalid_alt_component_rejected(self, name):
        """Names with too many or empty components should be rejected."""
        assert not ALT_NAMING_PATTERN.match(name), f"Expected '{name}' to be invalid"


class TestCombinedValidation:
    """Tests that either standard OR alternative pattern is accepted."""

    @pytest.mark.parametrize("name", [
        "OpenClaw_ProphecyNews_NewsFull_0700",
        "ProphecyNews-NewsFull-7am",
        "QuantumHub-Alerts-1pm",
        "OpenClaw-SecurityAudit",
        "ProphecyNews-Weekly",
    ])
    def test_either_pattern_accepted(self, name):
        """Names matching either standard or alt pattern are valid."""
        assert NAMING_PATTERN.match(name) or ALT_NAMING_PATTERN.match(name), \
            f"Expected '{name}' to be accepted by at least one pattern"
