---
name: openclaw-task-manager
description: Manage Windows Task Scheduler tasks for OpenClaw agents with naming convention enforcement, registry tracking, and safe deletion.
license: MIT
compatibility: "Windows 10/11 with schtasks.exe"
---

# OpenClaw Task Manager

Manages scheduled tasks via Windows Task Scheduler (`schtasks.exe`) for OpenClaw agents. Tracks all managed tasks in a local registry and enforces naming conventions.

> ⚠️ **CRITICAL: WSL cron does NOT work reliably.** If you're running OpenClaw under WSL2, **do not use WSL cron**. Tasks will silently fail to execute when WSL shuts down or sleeps. Use Windows Task Scheduler instead — see [WSL_CRON_WARNING.md](references/WSL_CRON_WARNING.md) for full details.

## Quick Start

```bash
# List all OpenClaw tasks
python scripts/list.py

# Create a new task
python scripts/create.py OpenClaw_ProphecyNews_NewsFull_0700 "python D:\scripts\fetch_news.py" --time 07:00 --daily

# Check task status
python scripts/status.py OpenClaw_ProphecyNews_NewsFull_0700

# Delete a task (with registry verification)
python scripts/delete.py OpenClaw_ProphecyNews_NewsFull_0700
```

## Core Concepts

### Task Registry

All managed tasks are tracked in `~/.openclaw/task-registry.json`. This registry:
- Auto-populated when tasks are created
- Verified before any deletion
- Stores metadata: created_at, last_run, schedule, command

Registry location: `~/.openclaw/task-registry.json`

### Naming Convention (MANDATORY)

All task names must follow this pattern:

```
OpenClaw_{Project}_{Action}_{Schedule}
```

| Component   | Description                                           | Example           |
|-------------|-------------------------------------------------------|-------------------|
| `OpenClaw`  | Fixed prefix                                          | `OpenClaw`        |
| `{Project}` | Project or domain identifier (PascalCase)             | `ProphecyNews`    |
| `{Action}`  | What the task does (PascalCase)                        | `NewsFull`, `Backup` |
| `{Schedule}`| Execution time or frequency (HHMM or descriptive)     | `0700`, `Daily`   |

**Valid Examples:**
- `OpenClaw_ProphecyNews_NewsFull_0700` — News fetch at 7:00 AM
- `OpenClaw_QuantumHub_SyncDaily_0900` — Daily sync at 9:00 AM
- `OpenClaw_MedicalIntel_ReportWeekly_Sunday` — Weekly on Sunday

**Invalid Examples (will be rejected):**
- `DOSBot_ProphecyNews_NewsFull_0700` — Wrong prefix
- `openclaw_news_fetch` — Wrong case convention
- `OpenClaw_News_Full` — Missing schedule component

See [references/NAMING_CONVENTION.md](references/NAMING_CONVENTION.md) for full specification.

### WSL Cron Warning ⚠️

**WSL cron is fundamentally broken for background tasks.** Here's why:

1. **WSL shuts down when idle** — Ubuntu's cron daemon is killed when WSL goes to sleep
2. **No persistence** — cron dies with the WSL instance, no auto-restart
3. **Timing drift** — tasks run at wrong times or not at all
4. **No Windows integration** — Windows can't see or manage WSL tasks

**The Solution: Windows Task Scheduler**

Use `schtasks.exe` (built into Windows) or the Task Scheduler GUI (`taskschd.msc`). All scripts in this skill use `schtasks.exe` for reliable Windows-native scheduling.

See [references/WSL_CRON_WARNING.md](references/WSL_CRON_WARNING.md) for complete explanation.

## Scripts

### list.py — List All Tasks

Lists all registered OpenClaw tasks and their current Windows Task Scheduler status.

```bash
python scripts/list.py [--registry PATH]
```

**Output includes:**
- Task name
- Next scheduled run
- Last run result
- Enabled/Disabled state

### create.py — Create a Task

Creates a new Windows scheduled task and registers it in the registry.

```bash
python scripts/create.py <TASK_NAME> <COMMAND> --time HH:MM --daily|--weekly|--once [--day DAY]
```

**Arguments:**
| Argument     | Description                          |
|--------------|--------------------------------------|
| `TASK_NAME`  | Must follow naming convention        |
| `COMMAND`    | Full command to execute              |
| `--time`     | Run time (24-hour, e.g., 07:00)     |
| `--daily`    | Run every day at `--time`           |
| `--weekly`   | Run on specified day (see `--day`)  |
| `--once`     | Run once at `--time` on `--date`    |

**Examples:**
```bash
# Daily news fetch at 7 AM
python scripts/create.py OpenClaw_ProphecyNews_NewsFull_0700 "python D:\scripts\fetch_news.py" --time 07:00 --daily

# Weekly backup every Sunday at 3 AM
python scripts/create.py OpenClaw_Backups_FullWeekly_Sunday "D:\scripts\backup.bat" --time 03:00 --weekly --day Sunday
```

**Auto-Registration:** Task is immediately added to `~/.openclaw/task-registry.json` with metadata.

### status.py — Check Task Status

Shows detailed status for a specific task.

```bash
python scripts/status.py <TASK_NAME> [--registry PATH]
```

**Output includes:**
- Task state (Ready, Running, Disabled)
- Last run time and result
- Next scheduled run
- Task command

### delete.py — Delete a Task

Safely deletes a task after registry verification.

```bash
python scripts/delete.py <TASK_NAME> [--force] [--registry PATH]
```

**Safety checks:**
1. Task must exist in registry (unless `--force`)
2. Confirmation prompt before deletion
3. Registry entry removed after successful deletion

**`--force` flag:** Skip registry check and skip confirmation. Use with caution.

### registry.py — Registry Utility

Direct registry management for advanced users.

```bash
# Show full registry
python scripts/registry.py --show

# Export registry
python scripts/registry.py --export PATH

# Import registry
python scripts/registry.py --import PATH

# Remove orphaned entries
python scripts/registry.py --clean
```

## Naming Convention Enforcement

Every create operation validates the task name against the pattern:

```
^OpenClaw_[A-Z][a-zA-Z0-9]*_[A-Z][a-zA-Z0-9]*_[A-Z0-9a-z]+$
```

**Validation rules:**
1. Must start with `OpenClaw_` (exactly, case-sensitive)
2. Three underscore-separated components
3. Each component uses PascalCase or alphanumeric
4. Schedule component must have at least one letter or digit

**Rejection examples:**
```
✗ DOSBot_ProphecyNews_NewsFull_0700   → Wrong prefix
✗ OpenClaw_news_fetch_0700           → Not PascalCase
✗ OpenClaw_ProphecyNews_              → Missing action/schedule
```

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Task name does not match convention` | Invalid naming | Review naming convention and retry |
| `Task already exists in registry` | Duplicate creation | Use different name or check existing |
| `Task not found in registry` | Trying to delete unregistered task | Use `--force` or register first |
| `Access denied` | Insufficient permissions | Run as administrator |
| `System cannot find file` | Command path invalid | Verify command path exists |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Invalid arguments |
| `3` | Naming convention violation |
| `4` | Registry error |
| `5` | Task not found |
| `6` | Task already exists |

## Windows Task Scheduler Reference

### Common schtasks.exe Commands

```powershell
# Create daily task at 7 AM
schtasks /create /tn "OpenClaw_Project_Task_0700" /tr "python D:\script.py" /sc daily /st 07:00

# Create weekly task on Sunday at 3 AM
schtasks /create /tn "OpenClaw_Project_Task_Sunday" /tr "D:\script.bat" /sc weekly /d SUN /st 03:00

# Delete task
schtasks /delete /tn "OpenClaw_Project_Task_0700" /f

# Query task status
schtasks /query /tn "OpenClaw_Project_Task_0700" /fo LIST /v

# Enable/Disable task
schtasks /change /tn "OpenClaw_Project_Task_0700" /enable
schtasks /change /tn "OpenClaw_Project_Task_0700" /disable

# Run task immediately
schtasks /run /tn "OpenClaw_Project_Task_0700"
```

See [references/SCHTASKS_REFERENCE.md](references/SCHTASKS_REFERENCE.md) for complete reference.

## File Structure

```
openclaw-task-manager/
├── SKILL.md
├── scripts/
│   ├── list.py        # List all registered tasks
│   ├── create.py      # Create + auto-register task
│   ├── delete.py      # Delete with registry verification
│   ├── status.py      # Show task status
│   └── registry.py   # Registry CRUD utility
├── references/
│   ├── NAMING_CONVENTION.md   # Naming spec with examples
│   ├── WSL_CRON_WARNING.md    # Why WSL cron fails
│   └── SCHTASKS_REFERENCE.md # schtasks.exe reference
└── assets/
    └── task-template.json    # Example task definition
```

## Dashboard

A visual web dashboard is included for browser-based task management.

### Setup
```powershell
cd openclaw-task-manager\dashboard
pip install -r requirements.txt
python dashboard.py
```
Then open http://localhost:5173/ in your browser.

### Dashboard Features
- **Stats overview** — total tasks, ready count, orphaned count, error count
- **Task list** — all OpenClaw tasks with status, last result, next run time
- **Create tasks** — form with naming convention validation
- **Manage tasks** — enable, disable, run now, delete
- **Orphan detection** — highlights tasks in Windows but not in registry
- **Responsive** — works on desktop and mobile

### Quick Launch
```powershell
# From the dashboard directory
python dashboard.py

# Or run directly
py -3 dashboard.py
```

## Installation

```bash
npx clawhub@latest install openclaw-task-manager
```

Requires: Python 3.6+, Windows 10/11, schtasks.exe access