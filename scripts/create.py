#!/usr/bin/env python3
"""
create.py - Create a new OpenClaw scheduled task

Creates a Windows Task Scheduler task and auto-registers it in the
OpenClaw task registry at ~/.openclaw/task-registry.json
"""

import subprocess
import sys
import re
import json
from datetime import datetime
from pathlib import Path

# Add parent dir to path for registry module
sys.path.insert(0, str(Path(__file__).parent))
import registry

# Naming convention pattern: OpenClaw_{Project}_{Action}_{Schedule}
NAMING_PATTERN = re.compile(r'^OpenClaw_[A-Z][a-zA-Z0-9]*_[A-Z][a-zA-Z0-9]*_[A-Z0-9a-z]+$')

def validate_name(task_name):
    """Validate task name against OpenClaw naming convention."""
    if not NAMING_PATTERN.match(task_name):
        raise ValueError(
            f"Task name '{task_name}' does not match OpenClaw naming convention.\n"
            f"Expected pattern: OpenClaw_{{Project}}_{{Action}}_{{Schedule}}\n"
            f"  - Prefix: OpenClaw_\n"
            f"  - Project: PascalCase (e.g., ProphecyNews)\n"
            f"  - Action: PascalCase (e.g., NewsFull)\n"
            f"  - Schedule: HHMM or day name (e.g., 0700, Sunday)\n"
            f"\nValid examples:\n"
            f"  OpenClaw_ProphecyNews_NewsFull_0700\n"
            f"  OpenClaw_QuantumHub_SyncDaily_0900\n"
            f"  OpenClaw_MedicalIntel_ReportWeekly_Sunday\n"
        )
    return True

def create_windows_task(task_name, command, time, frequency, day=None, date=None):
    """Create a task in Windows Task Scheduler using schtasks.exe."""
    cmd = [
        'schtasks', '/create',
        '/tn', task_name,
        '/tr', command,
        '/sc', frequency,
        '/st', time,
        '/f'  # Force create (overwrite if exists)
    ]
    
    # Add day for weekly tasks
    if day:
        day_map = {
            'sunday': 'SUN', 'monday': 'MON', 'tuesday': 'TUE',
            'wednesday': 'WED', 'thursday': 'THU', 'friday': 'FRI',
            'saturday': 'SAT'
        }
        day_abbr = day_map.get(day.lower(), day.upper()[:3])
        cmd.extend(['/d', day_abbr])
    
    # Add date for one-time tasks
    if schedule_type == 'once' and date:
        cmd.extend(['/sd', date])
    
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    
    if result.returncode != 0:
        # Check for specific errors
        if 'Access is denied' in result.stderr:
            raise PermissionError("Administrator privileges required. Run as admin or use elevated command prompt.")
        elif 'does not exist' in result.stderr or 'cannot find' in result.stderr:
            raise FileNotFoundError(f"Command not found: {command}")
        else:
            raise RuntimeError(f"schtasks failed: {result.stderr.strip()}")
    
    return True

def register_task(task_name, command, time, schedule_type, day=None):
    """Register the task in the OpenClaw registry."""
    metadata = {
        'command': command,
        'time': time,
        'schedule': schedule_type,
        'created_at': datetime.now().isoformat(),
    }
    
    if day:
        metadata['day'] = day
    
    return registry.add_task(task_name, metadata)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Create a new OpenClaw scheduled task',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Daily task at 7:00 AM
  python create.py OpenClaw_ProphecyNews_NewsFull_0700 "python D:\\scripts\\fetch.py" --time 07:00 --daily

  # Weekly task on Sunday at 3:00 AM
  python create.py OpenClaw_Backups_FullWeekly_Sunday "D:\\backup.bat" --time 03:00 --weekly --day Sunday

  # One-time task
  python create.py OpenClaw_ProphecyNews_OneTimeRun "python D:\\test.py" --time 14:30 --once --date 04/15/2025
        """
    )
    
    parser.add_argument('task_name', help='Task name following OpenClaw convention (OpenClaw_Project_Action_Schedule)')
    parser.add_argument('command', help='Command to execute')
    parser.add_argument('--time', required=True, help='Run time (24-hour HH:MM format, e.g., 07:00)')
    parser.add_argument('--daily', action='store_true', help='Run daily at --time')
    parser.add_argument('--weekly', action='store_true', help='Run weekly on --day')
    parser.add_argument('--once', action='store_true', help='Run once at --time on --date')
    parser.add_argument('--hourly', action='store_true', help='Run hourly')
    parser.add_argument('--day', help='Day of week (Monday, Tuesday, etc.) for weekly tasks')
    parser.add_argument('--date', help='Date (MM/DD/YYYY) for one-time tasks')
    
    args = parser.parse_args()
    
    # Validate task name
    try:
        validate_name(args.task_name)
    except ValueError as e:
        print(f"\033[91mNaming Convention Error:\033[0m {e}", file=sys.stderr)
        sys.exit(3)
    
    # Determine schedule type
    if args.daily:
        schedule_type = 'daily'
    elif args.weekly:
        schedule_type = 'weekly'
        if not args.day:
            print("\033[91mError:\033[0m --day is required for weekly tasks", file=sys.stderr)
            sys.exit(2)
    elif args.once:
        schedule_type = 'once'
    elif args.hourly:
        schedule_type = 'hourly'
    else:
        print("\033[91mError:\033[0m Must specify --daily, --weekly, --once, or --hourly", file=sys.stderr)
        sys.exit(2)
    
    # Validate time format
    time_pattern = re.compile(r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$')
    if not time_pattern.match(args.time):
        print(f"\033[91mError:\033[0m Invalid time format '{args.time}'. Use HH:MM (24-hour, e.g., 07:00 or 19:30)", file=sys.stderr)
        sys.exit(2)
    
    # Create the Windows task
    print(f"Creating task: {args.task_name}")
    print(f"  Command: {args.command}")
    print(f"  Schedule: {schedule_type} at {args.time}")
    if args.day:
        print(f"  Day: {args.day}")
    
    try:
        create_windows_task(args.task_name, args.command, args.time, schedule_type, args.day, args.date)
        print(f"\033[92m✓ Task created in Windows Task Scheduler\033[0m")
    except (PermissionError, FileNotFoundError, RuntimeError) as e:
        print(f"\033[91mError:\033[0m {e}", file=sys.stderr)
        sys.exit(1)
    
    # Auto-register in registry
    try:
        register_task(args.task_name, args.command, args.time, schedule_type, args.day)
        print(f"\033[92m✓ Registered in task registry\033[0m")
    except Exception as e:
        print(f"\033[93mWarning:\033[0m Task created but registry update failed: {e}", file=sys.stderr)
        print("Task exists in Windows Task Scheduler but may not appear in list output.")
    
    print(f"\n\033[92mTask '{args.task_name}' created successfully.\033[0m")
    sys.exit(0)

if __name__ == '__main__':
    main()