#!/usr/bin/env python3
"""
delete.py - Delete an OpenClaw scheduled task

Safely deletes a task from Windows Task Scheduler only after verifying
it exists in the OpenClaw task registry. Prevents accidental deletion
of tasks not managed by this skill.
"""

import subprocess
import sys
import os
from pathlib import Path

# Resolve schtasks.exe path (WSL vs Windows native)
if os.path.exists("/mnt/c/Windows/System32/schtasks.exe"):
    SCHTASKS = "/mnt/c/Windows/System32/schtasks.exe"
else:
    SCHTASKS = "schtasks"

# Add parent dir to path for registry module
sys.path.insert(0, str(Path(__file__).parent))
import registry

def query_windows_task(task_name):
    """Check if a task exists in Windows Task Scheduler."""
    result = subprocess.run(
        [SCHTASKS, '/query', '/tn', task_name],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    return result.returncode == 0 and 'ERROR' not in result.stdout

def delete_windows_task(task_name, force=False):
    """Delete a task from Windows Task Scheduler."""
    cmd = [SCHTASKS, '/delete', '/tn', task_name, '/f']
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')

    if result.returncode != 0:
        if 'Access is denied' in result.stderr:
            raise PermissionError("Administrator privileges required to delete tasks.")
        elif 'does not exist' in result.stderr or 'not found' in result.stderr:
            raise FileNotFoundError(f"Task '{task_name}' not found in Windows Task Scheduler.")
        else:
            raise RuntimeError(f"schtasks failed: {result.stderr.strip()}")

    return True

def confirm_delete(task_name):
    """Prompt for deletion confirmation."""
    print(f"\n\033[93m⚠️  Confirm Deletion\033[0m")
    print(f"Task: {task_name}")
    print(f"\nThis will permanently delete the task from Windows Task Scheduler.")
    print(f"The registry entry will also be removed.")

    try:
        response = input("\nDelete task? [y/N]: ").strip().lower()
        return response == 'y'
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        return False

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Delete an OpenClaw scheduled task (with registry verification)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Safety checks:
1. Task must exist in the registry (unless --force is used)
2. User confirmation is required (unless --force is used)

Examples:
  python delete.py OpenClaw_ProphecyNews_NewsFull_0700
  python delete.py OpenClaw_Backups_FullWeekly_Sunday --force
        """
    )

    parser.add_argument('task_name', help='Name of the task to delete')
    parser.add_argument('--force', action='store_true', help='Skip registry check and confirmation prompt')
    parser.add_argument('--registry', help='Path to registry file (default: ~/.openclaw/task-registry.json)')

    args = parser.parse_args()

    # Check registry first (unless force)
    if not args.force:
        reg_task = registry.get_task(args.task_name)
        if not reg_task:
            print(f"\033[91mError:\033[0m Task '{args.task_name}' not found in registry.")
            print("Use --force to delete a task that isn't in the registry, or")
            print("check the task name and try again.")
            print(f"\nTo see all registered tasks, run: python scripts/list.py")
            sys.exit(5)

    # Check if task exists in Windows Task Scheduler
    if not query_windows_task(args.task_name):
        print(f"\033[91mError:\033[0m Task '{args.task_name}' not found in Windows Task Scheduler.")
        print("The task may have been deleted manually or doesn't exist.")

        # Clean up orphaned registry entry
        if not args.force:
            print(f"\nRemoving orphaned registry entry for '{args.task_name}'...")
            registry.remove_task(args.task_name)
            print("\033[92mRegistry entry removed.\033[0m")
        sys.exit(5)

    # Confirm deletion (unless force)
    if not args.force:
        if not confirm_delete(args.task_name):
            print("Deletion cancelled.")
            sys.exit(0)

    # Delete from Windows Task Scheduler
    print(f"Deleting task: {args.task_name}")
    try:
        delete_windows_task(args.task_name, force=True)
        print(f"\033[92m✓ Task deleted from Windows Task Scheduler\033[0m")
    except (PermissionError, FileNotFoundError, RuntimeError) as e:
        print(f"\033[91mError:\033[0m {e}", file=sys.stderr)
        sys.exit(1)

    # Remove from registry
    if registry.remove_task(args.task_name):
        print(f"\033[92m✓ Registry entry removed\033[0m")
    else:
        print(f"\033[93mWarning:\033[0m Could not remove registry entry. It may not exist.")

    print(f"\n\033[92mTask '{args.task_name}' deleted successfully.\033[0m")
    sys.exit(0)

if __name__ == '__main__':
    main()
