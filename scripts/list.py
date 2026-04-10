#!/usr/bin/env python3
"""
list.py - List all OpenClaw scheduled tasks

Queries both the Windows Task Scheduler and the local registry
to provide a comprehensive view of all OpenClaw-managed tasks.
"""

import json
import subprocess
import sys
import re
import os
from datetime import datetime
from pathlib import Path

# Resolve schtasks.exe path (WSL vs Windows native)
if os.path.exists("/mnt/c/Windows/System32/schtasks.exe"):
    SCHTASKS = "/mnt/c/Windows/System32/schtasks.exe"
else:
    SCHTASKS = "schtasks"

# Add parent dir to path for registry module
sys.path.insert(0, str(Path(__file__).parent))
from registry import load_registry, REGISTRY_PATH

# Pattern to identify OpenClaw task names
OPENCLAW_PATTERN = re.compile(r'^OpenClaw_')

def query_windows_tasks():
    """Query Windows Task Scheduler for all OpenClaw tasks."""
    tasks = []
    try:
        result = subprocess.run(
            [SCHTASKS, '/query', '/fo', 'LIST', '/v'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        current_task = {}
        for line in result.stdout.split('\n'):
            line = line.strip()

            if line.startswith('TaskName:'):
                task_name = line.split('TaskName:', 1)[1].strip()
                if OPENCLAW_PATTERN.match(task_name):
                    current_task['name'] = task_name

            elif line.startswith('Next Run Time:') and current_task.get('name'):
                current_task['next_run'] = line.split('Next Run Time:', 1)[1].strip()

            elif line.startswith('Status:') and current_task.get('name'):
                current_task['status'] = line.split('Status:', 1)[1].strip()
                tasks.append(current_task)
                current_task = {}

            elif line.startswith('Last Run Time:') and current_task.get('name'):
                current_task['last_run'] = line.split('Last Run Time:', 1)[1].strip()

            elif line.startswith('Last Result:') and current_task.get('name'):
                current_task['last_result'] = line.split('Last Result:', 1)[1].strip()

    except Exception as e:
        print(f"Error querying Windows Task Scheduler: {e}", file=sys.stderr)

    return tasks

def format_task_display(windows_tasks, registry_tasks):
    """Format tasks for display."""
    if not windows_tasks and not registry_tasks:
        print("No OpenClaw tasks found.")
        print("\nTo create a task, use:")
        print("  python scripts/create.py <TASK_NAME> <COMMAND> --time HH:MM --daily")
        return

    print(f"{'Task Name':<45} {'Status':<12} {'Next Run':<25} {'Last Result':<10}")
    print("-" * 95)

    windows_by_name = {t['name']: t for t in windows_tasks}
    all_tasks = set(list(windows_by_name.keys()) + list(registry_tasks.keys()))

    for name in sorted(all_tasks):
        win_task = windows_by_name.get(name, {})
        reg_task = registry_tasks.get(name, {})

        status = win_task.get('status', 'Unknown')
        next_run = win_task.get('next_run', 'Not scheduled')
        last_result = win_task.get('last_result', reg_task.get('last_result', '-'))

        if status == 'Ready':
            status_display = '\033[92mReady\033[0m'
        elif status == 'Running':
            status_display = '\033[93mRunning\033[0m'
        elif status == 'Disabled':
            status_display = '\033[90mDisabled\033[0m'
        else:
            status_display = status

        print(f"{name:<45} {status_display:<12} {next_run:<25} {last_result:<10}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='List all OpenClaw scheduled tasks')
    parser.add_argument('--registry', help='Path to registry file (default: ~/.openclaw/task-registry.json)')
    args = parser.parse_args()

    if args.registry:
        registry_tasks = {}
        try:
            with open(args.registry, 'r', encoding='utf-8') as f:
                registry_tasks = json.load(f)
        except Exception as e:
            print(f"Error reading registry: {e}", file=sys.stderr)
    else:
        registry_tasks = load_registry()

    print("OpenClaw Task Manager - Task List")
    print(f"Registry: {REGISTRY_PATH if not args.registry else args.registry}")
    print("=" * 95)

    windows_tasks = query_windows_tasks()
    format_task_display(windows_tasks, registry_tasks)

    print("\n" + "=" * 95)
    print(f"Windows Task Scheduler: {len(windows_tasks)} tasks")
    print(f"Registry entries: {len(registry_tasks)} tasks")

    windows_names = set(t['name'] for t in windows_tasks)
    registry_names = set(registry_tasks.keys())
    orphaned = registry_names - windows_names

    if orphaned:
        print(f"\n\033[91mWARNING: {len(orphaned)} orphaned registry entries (in registry but not in Task Scheduler):\033[0m")
        for name in sorted(orphaned):
            print(f"  - {name}")
        print("Run 'python scripts/registry.py --clean' to remove orphaned entries.")

if __name__ == '__main__':
    main()
