# Naming Convention Specification

All OpenClaw scheduled tasks must follow this naming convention to ensure consistency, easy identification, and automated management.

## Pattern

```
OpenClaw_{Project}_{Action}_{Schedule}
```

## Components

### 1. Prefix (Fixed)
```
OpenClaw_
```
Must be exactly `OpenClaw_` (case-sensitive). This identifies tasks managed by the OpenClaw Task Manager skill.

### 2. Project Identifier
```
{Project}
```
- PascalCase (first letter of each word capitalized)
- Short, descriptive name for the project or domain
- Letters and numbers only

**Examples:** `ProphecyNews`, `QuantumHub`, `MedicalIntel`, `LemonPartyAdvocacy`

### 3. Action Identifier
```
{Action}
```
- PascalCase (first letter of each word capitalized)
- Describes what the task does
- Should be concise but descriptive

**Examples:** `NewsFull`, `Backup`, `Sync`, `ReportGenerate`, `DashboardRefresh`

### 4. Schedule
```
{Schedule}
```
- Time-based: `HHMM` (e.g., `0700`, `2300`)
- Day-based: `Monday`, `Sunday`, `Weekend`
- Frequency: `Daily`, `Weekly`, `Hourly`

**Examples:** `0700`, `1430`, `Sunday`, `Monday`, `Daily`, `Weekly`

## Valid Examples

| Task Name | Project | Action | Schedule | Description |
|-----------|---------|--------|----------|-------------|
| `OpenClaw_ProphecyNews_NewsFull_0700` | ProphecyNews | NewsFull | 0700 | Fetch news at 7:00 AM |
| `OpenClaw_QuantumHub_SyncDaily_0900` | QuantumHub | SyncDaily | 0900 | Daily sync at 9:00 AM |
| `OpenClaw_MedicalIntel_ReportWeekly_Sunday` | MedicalIntel | ReportWeekly | Sunday | Weekly report on Sunday |
| `OpenClaw_LemonPartyAdvocacy_ScrapeDaily_1200` | LemonPartyAdvocacy | ScrapeDaily | 1200 | Daily scrape at noon |
| `OpenClaw_Backups_FullWeekly_Saturday` | Backups | FullWeekly | Saturday | Full backup Saturday |
| `OpenClaw_Dashboard_RefreshHourly_Hourly` | Dashboard | RefreshHourly | Hourly | Hourly refresh |

## Invalid Examples

| Task Name | Reason | Correction |
|-----------|--------|------------|
| `DOSBot_ProphecyNews_NewsFull_0700` | Wrong prefix | Use `OpenClaw_` prefix |
| `openclaw_news_fetch_0700` | Not PascalCase | Use `OpenClaw_ProphecyNews_NewsFull_0700` |
| `OpenClaw_News_Full_0700` | Incomplete components | Needs three parts after prefix |
| `OpenClaw_ProphecyNews_news_full_0700` | Lowercase action | Use `NewsFull` not `news_full` |
| `OpenClaw_ProphecyNews_NewsFull` | Missing schedule | Add schedule like `_0700` |
| `OpenClaw ProphecyNews NewsFull 0700` | Spaces instead of underscores | Use underscores `_` |
| `OpenClaw-ProphecyNews-NewsFull-0700` | Dashes instead of underscores | Use underscores `_` |

## Regex Pattern

```regex
^OpenClaw_[A-Z][a-zA-Z0-9]*_[A-Z][a-zA-Z0-9]*_[A-Z0-9a-z]+$
```

## Implementation

The `create.py` script validates task names against this pattern before creating any task. Invalid names are rejected with exit code `3`.

```python
import re

NAMING_PATTERN = re.compile(r'^OpenClaw_[A-Z][a-zA-Z0-9]*_[A-Z][a-zA-Z0-9]*_[A-Z0-9a-z]+$')

def validate_name(name):
    if not NAMING_PATTERN.match(name):
        raise ValueError(f"Task name '{name}' does not match convention. "
                        f"Expected: OpenClaw_{{Project}}_{{Action}}_{{Schedule}}")
```

## Best Practices

1. **Be descriptive but concise** — `OpenClaw_ProphecyNews_NewsFull_0700` > `OpenClaw_PN_NF_0700`
2. **Use consistent time format** — Always 24-hour HHMM (`0700` not `7:00`)
3. **Prefer descriptive days** — `Sunday` over `Weekly_Sunday` to avoid redundancy
4. **Group related tasks** — `OpenClaw_ProphecyNews_NewsFull_0700` and `OpenClaw_ProphecyNews_SummaryEvening_1800`