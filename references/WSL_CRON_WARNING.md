# ⚠️ WSL Cron Does Not Work — Use Windows Task Scheduler

This is a critical warning for anyone running OpenClaw under WSL2 (Windows Subsystem for Linux). **WSL cron is fundamentally broken for background task scheduling.** This skill does not support WSL cron and will actively warn against using it.

## Why WSL Cron Fails

### 1. WSL Shuts Down When Idle

WSL2 runs as a lightweight virtual machine that gets shut down when Windows determines it's idle. When WSL shuts down:
- The cron daemon is killed
- All scheduled tasks disappear
- The system does not restore cron on next startup

You may notice this as: tasks work for a while, then suddenly stop running after your computer has been idle or asleep.

### 2. No Automatic Restart

Unlike Windows services, WSL's Ubuntu init system does not automatically restart cron if it dies. There's no supervisor watching the process.

### 3. Windows Cannot See WSL Tasks

Even if WSL cron somehow ran:
- Windows Task Scheduler has no knowledge of WSL cron jobs
- The Windows Event Log doesn't capture them
- You cannot manage them from `taskschd.msc`
- They don't appear in Task Manager's background processes reliably

### 4. Timing Drift and Missed Runs

Because WSL can be shut down for hours (sleep, hibernate, idle timeout), cron jobs scheduled during those hours simply don't run. There's no catch-up mechanism.

### 5. Path and Environment Issues

WSL cron runs in a minimal environment:
- `$PATH` may not include your Python or Node installations
- Home directory paths differ between WSL and Windows
- Unicode handling can break
- subprocess calls to Windows executables fail

## The Solution: Windows Task Scheduler

Use `schtasks.exe` (built into Windows) or the Task Scheduler GUI (`taskschd.msc`).

### Benefits of Task Scheduler

| Feature | WSL Cron | Windows Task Scheduler |
|---------|----------|------------------------|
| Survives sleep/idle | ✗ | ✓ |
| Visible in Windows UI | ✗ | ✓ |
| Runs when user logged out | ✗ | ✓ |
| Built-in retry on failure | ✗ | ✓ |
| Event Log integration | ✗ | ✓ |
| Managed from other machines | ✗ | ✓ |
| survives system restart | ✗ | ✓ |

### Basic schtasks.exe Usage

```powershell
# Create a daily task at 7:00 AM
schtasks /create /tn "OpenClaw_ProphecyNews_NewsFull_0700" `
         /tr "python D:\scripts\fetch_news.py" `
         /sc daily /st 07:00

# Create a weekly task on Sunday at 3:00 AM
schtasks /create /tn "OpenClaw_Backups_FullWeekly_Sunday" `
         /tr "D:\scripts\backup.bat" `
         /sc weekly /d SUN /st 03:00

# Check task status
schtasks /query /tn "OpenClaw_ProphecyNews_NewsFull_0700" /fo LIST /v

# Delete a task
schtasks /delete /tn "OpenClaw_ProphecyNews_NewsFull_0700" /f
```

### How This Skill Implements Task Scheduler

All scripts in this skill use `schtasks.exe` via Python's `subprocess` module:

```python
import subprocess

def create_task(task_name, command, time, frequency):
    cmd = [
        'schtasks', '/create',
        '/tn', task_name,
        '/tr', command,
        '/sc', frequency,
        '/st', time,
        '/f'  # Force create (overwrite if exists)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"schtasks failed: {result.stderr}")
    # Auto-register in ~/.openclaw/task-registry.json
```

## What This Means For OpenClaw

When you create a task with this skill:
1. It runs `schtasks /create` to register the task in Windows
2. The task survives sleep, hibernate, and system restart
3. You can view/manage it in Task Scheduler (`taskschd.msc`)
4. Windows handles retries if the task fails
5. Events appear in Windows Event Log

**If you're running OpenClaw in WSL, create Windows scheduled tasks for your background jobs, not WSL cron entries.**

## Checking Your Current Tasks

To see all OpenClaw-managed tasks registered in Windows:

```powershell
schtasks /query /fo LIST | findstr "OpenClaw"
```

To see tasks in the registry but not in Windows (orphaned):

```python
# Run registry.py --clean
python scripts/registry.py --clean
```

## Summary

| ❌ WSL Cron | ✓ Windows Task Scheduler |
|-------------|-------------------------|
| Dies when WSL sleeps | Survives sleep/hibernate |
| No Windows visibility | Visible in Task Scheduler |
| No retry on failure | Built-in retry logic |
| Environment issues | Clean Windows environment |
| No event logging | Full Event Log integration |

**Never use `crontab` or systemd timers in WSL for OpenClaw background tasks.**