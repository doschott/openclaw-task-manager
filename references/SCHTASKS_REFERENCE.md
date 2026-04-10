# schtasks.exe Reference

`schtasks.exe` is Windows' built-in command-line task scheduler. This reference covers the most useful commands for OpenClaw task management.

## Syntax Overview

```
schtasks /COMMAND [arguments]
```

## Create Task (/create)

### Daily Task
```powershell
schtasks /create /tn "OpenClaw_Project_Task_0700" /tr "python D:\scripts\task.py" /sc daily /st 07:00 /f
```

| Parameter | Meaning |
|-----------|---------|
| `/tn` | Task name (use OpenClaw_ naming convention) |
| `/tr` | Task command to run |
| `/sc` | Schedule type (daily, weekly, once, etc.) |
| `/st` | Start time (24-hour HH:MM) |
| `/f` | Force create (overwrite existing task) |

### Weekly Task
```powershell
schtasks /create /tn "OpenClaw_Backups_FullWeekly_Sunday" /tr "D:\scripts\backup.bat" /sc weekly /d SUN /st 03:00 /f
```

| Parameter | Meaning |
|-----------|---------|
| `/d` | Day of week (MON, TUE, WED, THU, FRI, SAT, SUN) |

### One-Time Task
```powershell
schtasks /create /tn "OpenClaw_Project_OneTimeRun" /tr "python D:\scripts\runonce.py" /sc once /st 14:30 /sd 04/15/2025 /f
```

| Parameter | Meaning |
|-----------|---------|
| `/sd` | Start date (MM/DD/YYYY) |

### Hourly Task
```powershell
schtasks /create /tn "OpenClaw_Dashboard_RefreshHourly" /tr "D:\scripts\refresh.ps1" /sc hourly /st 00:00 /f
```

## Query Tasks (/query)

### List All OpenClaw Tasks
```powershell
schtasks /query /fo LIST | findstr "OpenClaw"
```

### Full Details for One Task
```powershell
schtasks /query /tn "OpenClaw_ProphecyNews_NewsFull_0700" /fo LIST /v
```

### XML Output
```powershell
schtasks /query /tn "OpenClaw_ProphecyNews_NewsFull_0700" /xml
```

### Parseable Table Output
```powershell
schtasks /query /fo CSV
```

## Run Task Immediately (/run)

```powershell
schtasks /run /tn "OpenClaw_ProphecyNews_NewsFull_0700"
```

Useful for testing tasks without waiting for schedule.

## End Running Task (/end)

```powershell
schtasks /end /tn "OpenClaw_ProphecyNews_NewsFull_0700"
```

## Delete Task (/delete)

### With Confirmation
```powershell
schtasks /delete /tn "OpenClaw_ProphecyNews_NewsFull_0700"
```

### Without Confirmation (/f)
```powershell
schtasks /delete /tn "OpenClaw_ProphecyNews_NewsFull_0700" /f
```

## Enable/Disable Task (/change)

### Disable
```powershell
schtasks /change /tn "OpenClaw_ProphecyNews_NewsFull_0700" /disable
```

### Enable
```powershell
schtasks /change /tn "OpenClaw_ProphecyNews_NewsFull_0700" /enable
```

### Change Schedule
```powershell
schtasks /change /tn "OpenClaw_ProphecyNews_NewsFull_0700" /st 08:00 /sc daily
```

### Change Command
```powershell
schtasks /change /tn "OpenClaw_ProphecyNews_NewsFull_0700" /tr "python D:\scripts\new_fetch.py"
```

## Output Format Options

| Format | Flag | Example |
|--------|------|---------|
| LIST | `/fo LIST` | Human-readable key:value pairs |
| TABLE | `/fo TABLE` | Aligned columns |
| CSV | `/fo CSV` | Comma-separated values |

## Common Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Invalid task name |
| `2` | Access denied |
| `3` | Invalid schedule |
| `4` | Task not found |
| `5` | Task already exists |
| `6` | Invalid command |

## Tips

### Use /ru System for System Tasks
To run task even when user is not logged in:
```powershell
schtasks /create /tn "OpenClaw_Task_Name" /tr "..." /sc daily /st 07:00 /ru SYSTEM /f
```

### Use /rl HIGHEST for Elevated Tasks
```powershell
schtasks /create /tn "OpenClaw_Task_Name" /tr "..." /sc daily /st 07:00 /rl HIGHEST /f
```

### Schedule Types Summary

| `/sc` value | Description | Extra args |
|-------------|-------------|------------|
| `minute` | Every N minutes | `/mo` (interval) |
| `hourly` | Every N hours | `/mo` (interval) |
| `daily` | Every day at `/st` | — |
| `weekly` | On specified day | `/d DAY` |
| `once` | One time only | `/sd DATE` |
| `onthly` | Monthly on day | `/d DAY` |
| `onstart` | At Windows startup | — |
| `onlogon` | At user logon | — |
| `onidle` | When system idle | — |

## Error Messages

| Message | Cause |
|---------|-------|
| `ERROR: The system cannot find the file specified.` | Command path invalid |
| `Access is denied.` | Need admin privileges |
| `Task already exists.` | Use `/f` to overwrite |
| `The account name is invalid or does not exist.` | Bad `/ru` account |
| `Invalid schedule type.` | Check `/sc` value |