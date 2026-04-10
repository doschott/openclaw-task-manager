#!/usr/bin/env python3
"""
registry.py - Task Registry CRUD Operations

Manages the OpenClaw task registry at ~/.openclaw/task-registry.json
"""

import json
import os
import sys
import argparse
import subprocess
from pathlib import Path

# Resolve schtasks.exe path (WSL vs Windows native)
if os.path.exists("/mnt/c/Windows/System32/schtasks.exe"):
    SCHTASKS = "/mnt/c/Windows/System32/schtasks.exe"
else:
    SCHTASKS = "schtasks"

REGISTRY_PATH = Path.home() / ".openclaw" / "task-registry.json"

def ensure_registry_dir():
    """Ensure the registry directory exists."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)

def load_registry():
    """Load the task registry from disk."""
    ensure_registry_dir()
    if not REGISTRY_PATH.exists():
        return {}
    try:
        with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading registry: {e}", file=sys.stderr)
        return {}

def save_registry(registry):
    """Save the task registry to disk."""
    ensure_registry_dir()
    try:
        with open(REGISTRY_PATH, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error writing registry: {e}", file=sys.stderr)
        return False
    return True

def add_task(task_name, metadata):
    """Add a task to the registry."""
    registry = load_registry()
    registry[task_name] = metadata
    return save_registry(registry)

def remove_task(task_name):
    """Remove a task from the registry."""
    registry = load_registry()
    if task_name in registry:
        del registry[task_name]
        return save_registry(registry)
    return False

def get_task(task_name):
    """Get a specific task from the registry."""
    registry = load_registry()
    return registry.get(task_name)

def list_tasks():
    """List all tasks in the registry."""
    return load_registry()

def clean_orphaned():
    """Remove registry entries that no longer exist in Windows Task Scheduler."""
    registry = load_registry()
    removed = []
    still_missing = []

    for task_name in list(registry.keys()):
        result = subprocess.run(
            [SCHTASKS, '/query', '/tn', task_name],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode != 0 or 'ERROR' in result.stdout:
            del registry[task_name]
            removed.append(task_name)
        else:
            still_missing.append(task_name)

    if removed:
        save_registry(registry)

    return removed, still_missing

def show_registry():
    """Display the full registry contents."""
    registry = load_registry()
    if not registry:
        print("Registry is empty. No tasks registered.")
        return

    print(f"Registry: {REGISTRY_PATH}")
    print(f"Total tasks: {len(registry)}")
    print("-" * 60)

    for name, meta in sorted(registry.items()):
        print(f"\n{name}")
        print(f"  Created: {meta.get('created_at', 'unknown')}")
        print(f"  Schedule: {meta.get('schedule', 'unknown')}")
        print(f"  Time: {meta.get('time', 'unknown')}")
        print(f"  Command: {meta.get('command', 'unknown')}")
        if meta.get('last_run'):
            print(f"  Last Run: {meta.get('last_run')}")
        if meta.get('last_result'):
            print(f"  Last Result: {meta.get('last_result')}")

def export_registry(path):
    """Export registry to a JSON file."""
    registry = load_registry()
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
        print(f"Exported {len(registry)} tasks to {path}")
        return True
    except IOError as e:
        print(f"Export failed: {e}", file=sys.stderr)
        return False

def import_registry(path):
    """Import registry from a JSON file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            imported = json.load(f)

        current = load_registry()
        current.update(imported)

        if save_registry(current):
            print(f"Imported {len(imported)} tasks from {path}")
            return True
        return False
    except (json.JSONDecodeError, IOError) as e:
        print(f"Import failed: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description='OpenClaw Task Registry Utility')
    parser.add_argument('--show', action='store_true', help='Display full registry')
    parser.add_argument('--export', metavar='PATH', help='Export registry to file')
    parser.add_argument('--import', dest='import_path', metavar='PATH', help='Import registry from file')
    parser.add_argument('--clean', action='store_true', help='Remove orphaned entries (not in Windows Task Scheduler)')

    args = parser.parse_args()

    if args.show:
        show_registry()
    elif args.export:
        export_registry(args.export)
    elif args.import_path:
        import_registry(args.import_path)
    elif args.clean:
        removed, still_missing = clean_orphaned()
        if removed:
            print(f"Removed {len(removed)} orphaned entries:")
            for name in removed:
                print(f"  - {name}")
        else:
            print("No orphaned entries found.")
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
