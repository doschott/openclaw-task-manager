#!/usr/bin/env python3
"""
import.py - Import an existing Windows Task Scheduler task into the registry

Allows registering pre-existing tasks that weren't created by this skill,
so they show up in the dashboard and are tracked by the registry.
"""

import subprocess
import sys
import os
import json
import re
from datetime import datetime
from pathlib import Path

# Resolve schtasks.exe path (WSL vs Windows native)
if os.path.exists("/mnt/c/Windows/System32/schtasks.exe"):
    SCHTASKS = "/mnt/c/Windows/System32/schtasks.exe"
else:
    SCHTASKS = "schtasks"

# Add parent dir to path for registry module
sys.path.insert(0, str(Path(__file__).parent))
import registry

# Naming convention patterns:
#   Standard: OpenClaw_{Project}_{Action}_{Schedule}
#   Alt:      {ProjectName}-{Descriptor}(-{Schedule})?
NAMING_PATTERN = re.compile(r'^OpenClaw_[A-Z][a-zA-Z0-9]*_[A-Z][a-zA-Z0-9]*_[A-Z0-9a-z]+$')
ALT_NAMING_PATTERN = re.compile(r'^(OpenClaw|ProphecyNews|QuantumHub|LemonParty|MedicalIntel|ShadowBroker)-[A-Za-z0-9]+(-[A-Za-z0-9]+)?$')


def validate_name(task_name):
    """Validate task name against OpenClaw naming convention."""
    if NAMING_PATTERN.match(task_name) or ALT_NAMING_PATTERN.match(task_name):
        return True
    raise ValueError(
        f"Task name '{task_name}' does not match OpenClaw naming convention.\n"
        f"Expected pattern: OpenClaw_{{Project}}_{{Action}}_{{Schedule}}\n"
        f"  OR (alternative): {{ProjectName}}-{{Descriptor}} or {{ProjectName}}-{{Descriptor}}-{{Schedule}}\n"
        f"To register this task anyway (not following convention), use --force."
    )


def query_task_from_windows(task_name):
    """Query full details of a task from Windows Task Scheduler."""
    result = subprocess.run(
        [SCHTASKS, '/query', '/tn', task_name, '/fo', 'LIST', '/v'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )

    if result.returncode != 0 or 'ERROR' in result.stdout:
        return None

    details = {
        'name': task_name,
        'command': '',
        'status': 'Unknown',
        'next_run': 'Not scheduled',
        'last_run': 'Never',
        'last_result': 'N/A',
        'schedule_type': 'Unknown',
        'start_time': 'Unknown',
        'start_date': 'Unknown',
        'days': '',
    }

    for line in result.stdout.split('\n'):
        line = line.strip()

        if line.startswith('TaskName:'):
            details['name'] = line.split('TaskName:', 1)[1].strip()
        elif line.startswith('Task To Run:'):
            details['command'] = line.split('Task To Run:', 1)[1].strip()
        elif line.startswith('Status:'):
            details['status'] = line.split('Status:', 1)[1].strip()
        elif line.startswith('Next Run Time:'):
            details['next_run'] = line.split('Next Run Time:', 1)[1].strip()
        elif line.startswith('Last Run Time:'):
            details['last_run'] = line.split('Last Run Time:', 1)[1].strip()
        elif line.startswith('Last Result:'):
            details['last_result'] = line.split('Last Result:', 1)[1].strip()
        elif line.startswith('Schedule Type:'):
            details['schedule_type'] = line.split('Schedule Type:', 1)[1].strip()
        elif line.startswith('Start Time:'):
            details['start_time'] = line.split('Start Time:', 1)[1].strip()
        elif line.startswith('Start Date:'):
            details['start_date'] = line.split('Start Date:', 1)[1].strip()
        elif line.startswith('For the following Days:'):
            details['days'] = line.split('For the following Days:', 1)[1].strip()

    return details


def import_task(task_name, force=False):
    """Import a Windows Task Scheduler task into the registry."""
    # Check if already registered
    existing = registry.get_task(task_name)
    if existing:
        print(f"\033[93mTask '{task_name}' is already registered.\033[0m")
        print(f"  Command: {existing.get('command', 'unknown')}")
        print(f"  Schedule: {existing.get('schedule', 'unknown')}")
        print(f"  Created: {existing.get('created_at', 'unknown')}")
        return False

    # Query task from Windows
    details = query_task_from_windows(task_name)
    if not details:
        print(f"\033[91mError:\033[0m Task '{task_name}' not found in Windows Task Scheduler.")
        print("Check the task name and try again.")
        print("\nTo list all OpenClaw_* tasks:")
        print("  python scripts/list.py")
        sys.exit(5)

    if not details.get('command'):
        print(f"\033[91mError:\033[0m Task '{task_name}' found but has no command configured.")
        sys.exit(5)

    # Validate naming convention (unless force)
    if not force:
        try:
            validate_name(task_name)
        except ValueError:
            print(f"\033[93mWarning:\033[0m Task '{task_name}' does not follow OpenClaw naming convention.")
            print("Use --force to import it anyway.")
            sys.exit(3)

    # Build metadata from Windows query
    metadata = {
        'command': details['command'],
        'schedule': details['schedule_type'],
        'time': details['start_time'] or details.get('next_run', ''),
        'status': details['status'],
        'imported': True,
        'imported_at': datetime.now().isoformat(),
        'last_run': details['last_run'],
        'last_result': details['last_result'],
    }
    if details.get('days'):
        metadata['days'] = details['days']

    # Save initial version (v1) for version history
    registry.add_task(task_name, metadata)
    registry.add_version(task_name, metadata, "Imported from Windows Task Scheduler")

    return True, details, metadata


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Import an existing Windows Task Scheduler task into the OpenClaw registry',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This allows tracking tasks that were created outside of this skill.

Examples:
  # Import a task (must follow naming convention)
  python import.py OpenClaw_OldTask_Backup_0800

  # Import a task that doesn't follow convention
  python import.py MyCustomTask --force

  # Dry run - show what would be imported
  python import.py OpenClaw_SomeTask --force
        """
    )
    parser.add_argument('task_name', help='Name of the Windows task to import')
    parser.add_argument('--force', action='store_true', help='Skip naming convention validation')
    parser.add_argument('--registry', help='Path to registry file (default: ~/.openclaw/task-registry.json)')

    args = parser.parse_args()

    result = import_task(args.task_name, args.force)

    if result:
        _, details, metadata = result
        print(f"\033[92m✓ Task '{args.task_name}' imported successfully.\033[0m")
        print(f"\nImported details:")
        print(f"  Command: {details.get('command', 'unknown')}")
        print(f"  Schedule: {details.get('schedule_type', 'unknown')}")
        print(f"  Status: {details.get('status', 'unknown')}")
        print(f"  Last Run: {details.get('last_run', 'Never')}")
        print(f"\nThe task is now tracked in the OpenClaw registry and will appear in the dashboard.")
        print(f"Version 1 has been created for this task (reason: 'Imported from Windows Task Scheduler').")

    sys.exit(0)


if __name__ == '__main__':
    main()
