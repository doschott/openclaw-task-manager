#!/usr/bin/env python3
"""
status.py - Check OpenClaw task status

Queries Windows Task Scheduler for detailed status information
about a specific OpenClaw task, including last run result and
next scheduled run.
"""

import subprocess
import sys
import re
from datetime import datetime
from pathlib import Path

# Add parent dir to path for registry module
sys.path.insert(0, str(Path(__file__).parent))
import registry

def query_task_details(task_name):
    """Query detailed information about a task from Windows Task Scheduler."""
    result = subprocess.run(
        ['schtasks', '/query', '/tn', task_name, '/fo', 'LIST', '/v'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    if result.returncode != 0 or 'ERROR' in result.stdout:
        return None
    
    details = {}
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
        elif line.startswith('Enabled:'):
            details['enabled'] = line.split('Enabled:', 1)[1].strip()
    
    return details

def interpret_result(result_code):
    """Interpret the last result code into human-readable form."""
    codes = {
        '0': 'Success',
        '1': 'Incorrect function called or invalid arguments',
        '2': 'File not found',
        '3': 'Path not found',
        '4': 'Invalid access',
        '10': 'Invalid environment',
        '267005': 'Task has not run yet',
        '267006': 'Task disabled',
        '267007': 'Task has not started yet',
        '267008': 'One or more arguments invalid',
        '267009': 'Multiple instances of task not allowed',
        '267010': 'Schedule type not supported',
        '267011': 'Several instances of task not allowed',
        '267012': 'Password expired',
        '267013': 'Runner account is expired',
        '267014': 'Task not ready to run at next scheduled time',
        '267015': 'Task marked for deletion',
        '267016': 'Task security context mismatch',
        '267017': 'Cannot create task directory',
        '267018': 'Unable to start task',
    }
    return codes.get(result_code, f'Unknown ({result_code})')

def format_status_display(details, reg_entry):
    """Format task details for display."""
    print(f"\n{'='*60}")
    print(f"Task: {details.get('name', 'Unknown')}")
    print(f"{'='*60}")
    
    print(f"\n{'Status':<20} {details.get('status', 'Unknown'):<15} (Enabled: {details.get('enabled', 'Unknown')})")
    print(f"{'Schedule Type':<20} {details.get('schedule_type', 'Unknown'):<15}")
    print(f"{'Start Time':<20} {details.get('start_time', details.get('next_run', 'Unknown')):<15}")
    if details.get('days'):
        print(f"{'Days':<20} {details.get('days'):<15}")
    
    print(f"\n{'Next Run':<20} {details.get('next_run', 'Not scheduled')}")
    print(f"{'Last Run':<20} {details.get('last_run', 'Never')}")
    
    last_result = details.get('last_result', 'N/A')
    if last_result and last_result != 'N/A':
        result_interpretation = interpret_result(last_result)
        print(f"{'Last Result':<20} {last_result} - {result_interpretation}")
    else:
        print(f"{'Last Result':<20} {last_result}")
    
    print(f"\n{'Command':<20}")
    print(f"  {details.get('command', 'Unknown')}")
    
    # Show registry metadata if available
    if reg_entry:
        print(f"\n{'Registry Info':<20}")
        if reg_entry.get('created_at'):
            created = reg_entry.get('created_at')
            # Format ISO timestamp nicely
            try:
                dt = datetime.fromisoformat(created)
                created = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
            print(f"  Created: {created}")
        if reg_entry.get('schedule'):
            print(f"  Schedule Type: {reg_entry.get('schedule')}")
        if reg_entry.get('time'):
            print(f"  Configured Time: {reg_entry.get('time')}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Check OpenClaw task status')
    parser.add_argument('task_name', help='Name of the task to check')
    parser.add_argument('--registry', help='Path to registry file (default: ~/.openclaw/task-registry.json)')
    
    args = parser.parse_args()
    
    # Get registry entry
    if args.registry:
        try:
            import json
            with open(args.registry, 'r', encoding='utf-8') as f:
                reg_tasks = json.load(f)
            reg_entry = reg_tasks.get(args.task_name)
        except Exception as e:
            print(f"Warning: Could not read registry: {e}", file=sys.stderr)
            reg_entry = None
    else:
        reg_entry = registry.get_task(args.task_name)
    
    # Query Windows Task Scheduler
    details = query_task_details(args.task_name)
    
    if not details:
        print(f"\033[91mTask not found:\033[0m '{args.task_name}'")
        print("\nThis task does not exist in Windows Task Scheduler.")
        
        if reg_entry:
            print("\n\033[93mWarning:\033[0m The task exists in the registry but not in Task Scheduler.")
            print("This usually means the task was manually deleted or never fully created.")
            print(f"\nRegistry entry: {reg_entry}")
            print("\nTo remove the orphaned registry entry, run:")
            print(f"  python scripts/registry.py --clean")
        
        sys.exit(5)
    
    format_status_display(details, reg_entry)
    print()
    sys.exit(0)

if __name__ == '__main__':
    main()