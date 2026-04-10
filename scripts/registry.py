#!/usr/bin/env python3
"""
registry.py - Task Registry CRUD Operations

Manages the OpenClaw task registry at ~/.openclaw/task-registry.json
and version history at ~/.openclaw/task-registry-versions.json
"""

import json
import os
import sys
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# Resolve schtasks.exe path (WSL vs Windows native)
if os.path.exists("/mnt/c/Windows/System32/schtasks.exe"):
    SCHTASKS = "/mnt/c/Windows/System32/schtasks.exe"
else:
    SCHTASKS = "schtasks"

REGISTRY_PATH = Path.home() / ".openclaw" / "task-registry.json"
VERSION_REGISTRY_PATH = Path.home() / ".openclaw" / "task-registry-versions.json"


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
    """Remove a task from the registry and its version history."""
    registry = load_registry()
    if task_name in registry:
        del registry[task_name]
        save_registry(registry)
        delete_versions(task_name)
        return True
    return False


def get_task(task_name):
    """Get a specific task from the registry."""
    registry = load_registry()
    return registry.get(task_name)


def list_tasks():
    """List all tasks in the registry."""
    return load_registry()


# --- Version Management ---

def load_version_registry():
    """Load the version registry from disk."""
    if not VERSION_REGISTRY_PATH.exists():
        return {}
    try:
        with open(VERSION_REGISTRY_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_version_registry(versions):
    """Save the version registry to disk."""
    VERSION_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(VERSION_REGISTRY_PATH, 'w', encoding='utf-8') as f:
            json.dump(versions, f, indent=2, ensure_ascii=False)
    except IOError:
        return False
    return True


def add_version(task_name, metadata, reason="Manual update"):
    """Add a new version entry for a task."""
    versions = load_version_registry()
    if task_name not in versions:
        versions[task_name] = []
    
    version_number = len(versions[task_name]) + 1
    version_entry = {
        'version': version_number,
        'timestamp': datetime.now().isoformat(),
        'reason': reason,
        'command': metadata.get('command', ''),
        'schedule': metadata.get('schedule', ''),
        'time': metadata.get('time', ''),
        'day': metadata.get('day', ''),
    }
    versions[task_name].append(version_entry)
    return save_version_registry(versions)


def get_versions(task_name):
    """Get all versions for a task."""
    versions = load_version_registry()
    return versions.get(task_name, [])


def get_latest_version(task_name):
    """Get the latest version entry for a task."""
    versions = get_versions(task_name)
    return versions[-1] if versions else None


def delete_versions(task_name):
    """Delete all version history for a task."""
    versions = load_version_registry()
    if task_name in versions:
        del versions[task_name]
        return save_version_registry(versions)
    return True


def show_versions(task_name=None):
    """Display version history for a task or all tasks."""
    versions = load_version_registry()
    
    if task_name:
        task_versions = versions.get(task_name, [])
        if not task_versions:
            print(f"No version history found for '{task_name}'.")
            return
        print(f"\n{'='*70}")
        print(f"Version History: {task_name}")
        print(f"{'='*70}")
        for v in task_versions:
            print(f"\n  Version {v['version']} - {v['timestamp']}")
            print(f"  Reason: {v['reason']}")
            print(f"  Command: {v.get('command', '-')}")
            print(f"  Schedule: {v.get('schedule', '-')} at {v.get('time', '-')}")
            if v.get('day'):
                print(f"  Day: {v['day']}")
        print(f"\n{'='*70}")
    else:
        all_tasks = list(versions.keys())
        if not all_tasks:
            print("No version history found for any task.")
            return
        
        print(f"\n{'='*70}")
        print(f"Version History - All Tasks ({len(all_tasks)} tasks tracked)")
        print(f"{'='*70}")
        for name in sorted(all_tasks):
            task_versions = versions[name]
            latest = task_versions[-1]
            print(f"\n{name}")
            print(f"  Versions: {len(task_versions)} | Latest: v{latest['version']} ({latest['timestamp']})")
            print(f"  Latest reason: {latest['reason']}")


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
    parser.add_argument('--import-registry', metavar='PATH', help='Import registry from file')
    parser.add_argument('--clean', action='store_true', help='Remove orphaned entries')
    parser.add_argument('--versions', metavar='TASK_NAME', nargs='?', const='__all__',
                        help='Show version history for a task (all tasks if no name given)')
    parser.add_argument('--restore', nargs=2, metavar=('TASK_NAME', 'VERSION'),
                        help='Restore a task to a specific version (TASK_NAME VERSION)')
    parser.add_argument('--note', metavar='TASK_NAME',
                        help='Add a version note for a task (e.g., after manual changes)')

    args = parser.parse_args()

    if args.show:
        show_registry()
    elif args.export:
        export_registry(args.export)
    elif args.import_registry:
        import_registry(args.import_registry)
    elif args.clean:
        removed, still_missing = clean_orphaned()
        if removed:
            print(f"Removed {len(removed)} orphaned entries:")
            for name in removed:
                print(f"  - {name}")
        else:
            print("No orphaned entries found.")
    elif args.versions is not None:
        if args.versions == '__all__':
            show_versions()
        else:
            show_versions(args.versions)
    elif args.restore:
        task_name, version_str = args.restore
        try:
            version_num = int(version_str)
        except ValueError:
            print(f"Version must be a number, got: {version_str}", file=sys.stderr)
            sys.exit(1)
        versions = get_versions(task_name)
        target = next((v for v in versions if v['version'] == version_num), None)
        if not target:
            print(f"Version {version_num} not found for '{task_name}'. Available versions: {[v['version'] for v in versions]}")
            sys.exit(1)
        
        # Recreate the task with the version's metadata
        task_meta = {
            'command': target['command'],
            'schedule': target['schedule'],
            'time': target['time'],
            'day': target.get('day', ''),
            'restored_from_version': version_num,
            'restored_at': datetime.now().isoformat(),
        }
        add_task(task_name, task_meta)
        add_version(task_name, task_meta, f"Restored from v{version_num}")
        print(f"Task '{task_name}' restored to v{version_num}.")
    elif args.note:
        task = get_task(args.note)
        if not task:
            print(f"Task '{args.note}' not found in registry.", file=sys.stderr)
            sys.exit(1)
        print(f"Adding version note for '{args.note}'...")
        print("Enter reason for this version (e.g., 'Changed schedule time'):")
        reason = input("Reason: ").strip() or "Manual update"
        add_version(args.note, task, reason)
        print(f"Version note added for '{args.note}'.")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
