#!/usr/bin/env python3
"""
OpenClaw Task Manager Dashboard

A simple Flask web dashboard for managing Windows Task Scheduler tasks
from a browser. Run this on Windows to access via http://localhost:5173

Usage:
    python dashboard.py [--port 5173] [--host 0.0.0.0]
"""

import json
import subprocess
import re
import sys
import os
from pathlib import Path
from datetime import datetime

# Detect Windows schtasks.exe path
_SCHTASKS = os.environ.get("SCHTASKS", "/mnt/c/Windows/System32/schtasks.exe")

# --- Flask Auto-Detection ---
# Try to find Flask from known venvs before failing
def _find_flask():
    import importlib.util
    if importlib.util.find_spec("flask") is not None:
        return True

    # Known venv paths to search (relative to common project roots)
    script_dir = Path(__file__).resolve().parent
    known_venvs = [
        # Prophecy News Tracker (common on this system)
        Path.home() / "clawd" / "projects" / "prophecy-news-tracker" / "venv",
        # Quantum Hub collector
        Path.home() / "clawd" / "projects" / "quantum-hub" / "collector" / "venv",
        # ShadowBroker backend
        Path.home() / "clawd" / "projects" / "Shadowbroker" / "backend" / "venv",
        # Same-level venv
        script_dir.parent.parent / "venv",
        script_dir.parent / "venv",
        # Generic check in project siblings
        Path.home() / "clawd" / "venv",
    ]

    for venv in known_venvs:
        site_packages = venv / "lib" / "python3.12" / "site-packages"
        if not site_packages.exists():
            # Try python3.11 or python3 sites
            for child in (venv / "lib").iterdir() if (venv / "lib").exists() else []:
                if child.name.startswith("python"):
                    site_packages = child / "site-packages"
                    break
        if site_packages.exists() and (site_packages / "flask").exists():
            sys.path.insert(0, str(site_packages))
            return True

    return False

if not _find_flask():
    print("ERROR: Flask not found.", file=sys.stderr)
    print("Install Flask with one of:", file=sys.stderr)
    print("  pip install flask", file=sys.stderr)
    print("  OR use an existing venv:", file=sys.stderr)
    print("  ~/clawd/projects/prophecy-news-tracker/venv/bin/python dashboard.py", file=sys.stderr)
    sys.exit(1)

from flask import Flask, render_template, jsonify, request, redirect, url_for

# --- Configuration ---
PORT = 5173
HOST = "0.0.0.0"
REGISTRY_PATH = Path.home() / ".openclaw" / "task-registry.json"

# --- Flask App ---
app = Flask(__name__, template_folder="templates", static_folder="static")

OPENCLAW_PATTERN = re.compile(r"^\\?(OpenClaw|ProphecyNews|QuantumHub|LemonParty|MedicalIntel|ShadowBroker)-")
# Standard naming for creating new tasks: OpenClaw_{Project}_{Action}_{Schedule}
NAMING_PATTERN = re.compile(r"^OpenClaw_[A-Z][a-zA-Z0-9]*_[A-Z][a-zA-Z0-9]*_[A-Z0-9a-z]+$")


# --- Registry Helpers ---
def load_registry():
    if not REGISTRY_PATH.exists():
        return {}
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_registry(registry):
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

# --- Registry Version Helpers ---
VERSION_REGISTRY_PATH = Path.home() / ".openclaw" / "task-registry-versions.json"

def load_version_registry():
    if not VERSION_REGISTRY_PATH.exists():
        return {}
    try:
        with open(VERSION_REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_version_registry(versions):
    VERSION_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(VERSION_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(versions, f, indent=2, ensure_ascii=False)

def add_version(task_name, metadata, reason="Manual update"):
    versions = load_version_registry()
    if task_name not in versions:
        versions[task_name] = []
    version_number = len(versions[task_name]) + 1
    version_entry = {
        "version": version_number,
        "timestamp": datetime.now().isoformat(),
        "reason": reason,
        "command": metadata.get("command", ""),
        "schedule": metadata.get("schedule", ""),
        "time": metadata.get("time", ""),
        "day": metadata.get("day", ""),
    }
    versions[task_name].append(version_entry)
    save_version_registry(versions)
    return version_entry

def get_versions(task_name):
    versions = load_version_registry()
    return versions.get(task_name, [])

# Registry module passthrough for dashboard use
class RegistryModule:
    def get_task(self, name): return get_registry_task(name)
    def add_task(self, name, meta): return add_registry_task(name, meta)
    def remove_task(self, name): return remove_registry_task(name)

registry = RegistryModule()

def validate_name(task_name):
    if not NAMING_PATTERN.match(task_name):
        raise ValueError(
            f"Task name '{task_name}' does not match convention. "
            f"Expected: OpenClaw_{{Project}}_{{Action}}_{{Schedule}}"
        )
    return True


# --- Registry CRUD ---
def get_registry_task(name):
    reg = load_registry()
    return reg.get(name)

def add_registry_task(name, meta):
    reg = load_registry()
    reg[name] = meta
    save_registry(reg)

def remove_registry_task(name):
    reg = load_registry()
    if name in reg:
        del reg[name]
        save_registry(reg)
        # Clean up versions
        versions = load_version_registry()
        if name in versions:
            del versions[name]
            save_version_registry(versions)
        return True
    return False


# --- Task Operations ---
def query_windows_tasks():
    """Get all OpenClaw_* tasks from Windows Task Scheduler."""
    tasks = {}
    try:
        result = subprocess.run(
            [_SCHTASKS, "/query", "/fo", "LIST", "/v"],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        current_task = {}
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line.startswith("TaskName:"):
                # Save previous task if any
                if current_task.get("name"):
                    tasks[current_task["name"]] = current_task
                name = line.split("TaskName:", 1)[1].strip()
                if OPENCLAW_PATTERN.match(name):
                    current_task = {"name": name.lstrip("\\")}
                else:
                    current_task = {}
            elif current_task.get("name"):
                if line.startswith("Next Run Time:"):
                    current_task["next_run"] = line.split("Next Run Time:", 1)[1].strip()
                elif line.startswith("Last Run Time:"):
                    current_task["last_run"] = line.split("Last Run Time:", 1)[1].strip()
                elif line.startswith("Last Result:"):
                    current_task["last_result"] = line.split("Last Result:", 1)[1].strip()
                elif line.startswith("Status:"):
                    current_task["status"] = line.split("Status:", 1)[1].strip()
                elif line.startswith("Task To Run:"):
                    current_task["command"] = line.split("Task To Run:", 1)[1].strip()
        # Save last task
        if current_task.get("name"):
            tasks[current_task["name"]] = current_task
    except Exception:
        pass
    return tasks


def query_windows_task_details(task_name):
    """Get full details of a single task from Windows Task Scheduler."""
    result = subprocess.run(
        [_SCHTASKS, "/query", "/tn", task_name, "/fo", "LIST", "/v"],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0 or "ERROR" in result.stdout:
        return None

    details = {
        "name": task_name, "command": "", "status": "Unknown",
        "next_run": "Not scheduled", "last_run": "Never", "last_result": "N/A",
        "schedule_type": "Unknown", "start_time": "Unknown", "start_date": "Unknown",
        "days": "",
    }
    for line in result.stdout.split("\n"):
        line = line.strip()
        if line.startswith("TaskName:"):
            details["name"] = line.split("TaskName:", 1)[1].strip()
        elif line.startswith("Task To Run:"):
            details["command"] = line.split("Task To Run:", 1)[1].strip()
        elif line.startswith("Status:"):
            details["status"] = line.split("Status:", 1)[1].strip()
        elif line.startswith("Next Run Time:"):
            details["next_run"] = line.split("Next Run Time:", 1)[1].strip()
        elif line.startswith("Last Run Time:"):
            details["last_run"] = line.split("Last Run Time:", 1)[1].strip()
        elif line.startswith("Last Result:"):
            details["last_result"] = line.split("Last Result:", 1)[1].strip()
        elif line.startswith("Schedule Type:"):
            details["schedule_type"] = line.split("Schedule Type:", 1)[1].strip()
        elif line.startswith("Start Time:"):
            details["start_time"] = line.split("Start Time:", 1)[1].strip()
        elif line.startswith("Start Date:"):
            details["start_date"] = line.split("Start Date:", 1)[1].strip()
        elif line.startswith("For the following Days:"):
            details["days"] = line.split("For the following Days:", 1)[1].strip()
    return details


def get_result_meaning(code):
    meanings = {
        "0": "Success",
        "1": "Incorrect function or arguments",
        "2": "File not found",
        "3": "Path not found",
        "267005": "Task has not run yet",
        "267008": "Invalid arguments",
        "267009": "Multiple instances not allowed",
        "267012": "Password expired",
        "267014": "Task not ready",
        "267015": "Task marked for deletion",
        "267018": "Unable to start",
    }
    return meanings.get(code, f"Code {code}")


def create_task(task_name, command, time, frequency, day=None, date=None):
    """Create a Windows Task Scheduler task."""
    cmd = [
        _SCHTASKS, "/create",
        "/tn", task_name,
        "/tr", command,
        "/sc", frequency,
        "/st", time,
        "/f"
    ]
    if day:
        day_map = {
            "sunday": "SUN", "monday": "MON", "tuesday": "TUE",
            "wednesday": "WED", "thursday": "THU", "friday": "FRI",
            "saturday": "SAT"
        }
        cmd.extend(["/d", day_map.get(day.lower(), day.upper()[:3])])
    if date:
        cmd.extend(["/sd", date])

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())

    # Auto-register
    registry = load_registry()
    metadata = {
        "command": command,
        "time": time,
        "schedule": frequency,
        "created_at": datetime.now().isoformat(),
    }
    if day:
        metadata["day"] = day
    registry[task_name] = metadata
    save_registry(registry)
    
    # Create version 1
    add_version(task_name, metadata, "Task created")


def delete_task(task_name, force=False):
    """Delete a task from Windows Task Scheduler and registry."""
    # Registry check unless forced
    if not force:
        registry = load_registry()
        if task_name not in registry:
            raise ValueError(f"Task '{task_name}' not found in registry. Use --force to delete anyway.")

    result = subprocess.run(
        [_SCHTASKS, "/delete", "/tn", task_name, "/f"],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())

    # Remove from registry
    registry = load_registry()
    registry.pop(task_name, None)
    save_registry(registry)

    # Clean up version history
    versions = load_version_registry()
    versions.pop(task_name, None)
    save_version_registry(versions)


def toggle_task(task_name, enable=True):
    """Enable or disable a task."""
    action = "/enable" if enable else "/disable"
    result = subprocess.run(
        [_SCHTASKS, "/change", "/tn", task_name, action],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())


def run_task_now(task_name):
    """Trigger a task to run immediately."""
    result = subprocess.run(
        [_SCHTASKS, "/run", "/tn", task_name],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())


# --- Routes ---
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/tasks")
def api_tasks():
    registry = load_registry()
    windows_tasks = query_windows_tasks()

    all_tasks = {}
    for name, reg_meta in registry.items():
        win_meta = windows_tasks.get(name, {})
        all_tasks[name] = {
            "name": name,
            "command": reg_meta.get("command", win_meta.get("command", "")),
            "schedule": reg_meta.get("schedule", ""),
            "time": reg_meta.get("time", ""),
            "day": reg_meta.get("day", ""),
            "created_at": reg_meta.get("created_at", ""),
            "next_run": win_meta.get("next_run", "Not scheduled"),
            "last_run": win_meta.get("last_run", "Never"),
            "last_result": win_meta.get("last_result", "N/A"),
            "status": win_meta.get("status", "Unknown"),
        }

    # Orphaned: in Windows but not in registry
    for name, win_meta in windows_tasks.items():
        if name not in all_tasks:
            all_tasks[name] = {
                "name": name,
                "command": win_meta.get("command", ""),
                "schedule": "",
                "time": "",
                "day": "",
                "created_at": "N/A (not in registry)",
                "next_run": win_meta.get("next_run", "Not scheduled"),
                "last_run": win_meta.get("last_run", "Never"),
                "last_result": win_meta.get("last_result", "N/A"),
                "status": win_meta.get("status", "Unknown"),
                "orphaned": True,
            }

    return jsonify(list(all_tasks.values()))


@app.route("/api/create", methods=["POST"])
def api_create():
    data = request.json
    try:
        validate_name(data["task_name"])
        create_task(
            data["task_name"],
            data["command"],
            data["time"],
            data["frequency"],
            data.get("day"),
            data.get("date"),
        )
        return jsonify({"success": True, "message": f"Task '{data['task_name']}' created."})
    except ValueError as e:
        return jsonify({"success": False, "message": str(e), "exit_code": 3}), 400
    except RuntimeError as e:
        return jsonify({"success": False, "message": str(e), "exit_code": 1}), 500


@app.route("/api/delete/<task_name>", methods=["DELETE"])
def api_delete(task_name):
    force = request.args.get("force", "false").lower() == "true"
    try:
        delete_task(task_name, force=force)
        return jsonify({"success": True, "message": f"Task '{task_name}' deleted."})
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/toggle/<task_name>", methods=["POST"])
def api_toggle(task_name):
    enable = request.args.get("enable", "true").lower() == "true"
    try:
        toggle_task(task_name, enable)
        action = "enabled" if enable else "disabled"
        return jsonify({"success": True, "message": f"Task '{task_name}' {action}."})
    except RuntimeError as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/run/<task_name>", methods=["POST"])
def api_run(task_name):
    try:
        run_task_now(task_name)
        return jsonify({"success": True, "message": f"Task '{task_name}' triggered."})
    except RuntimeError as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/import", methods=["POST"])
def api_import():
    """Import an existing Windows Task Scheduler task into the registry."""
    data = request.json
    task_name = data.get("task_name", "").strip()
    if not task_name:
        return jsonify({"success": False, "message": "task_name is required"}), 400

    # Check if already registered
    existing = registry.get_task(task_name)
    if existing:
        return jsonify({"success": False, "message": f"Task '{task_name}' is already registered."}), 400

    # Query task from Windows
    details = query_windows_task_details(task_name)
    if not details:
        return jsonify({"success": False, "message": f"Task '{task_name}' not found in Windows Task Scheduler."}), 404

    # Build metadata
    metadata = {
        "command": details.get("command", ""),
        "schedule": details.get("schedule_type", ""),
        "time": details.get("start_time", ""),
        "imported": True,
        "imported_at": datetime.now().isoformat(),
        "last_run": details.get("last_run", "Never"),
        "last_result": details.get("last_result", "N/A"),
    }
    if details.get("days"):
        metadata["days"] = details["days"]

    registry.add_task(task_name, metadata)
    registry.add_version(task_name, metadata, "Imported from Windows Task Scheduler")

    return jsonify({
        "success": True,
        "message": f"Task '{task_name}' imported successfully.",
        "task": metadata,
        "version": 1
    })


@app.route("/api/versions/<task_name>")
def api_versions(task_name):
    """Get version history for a task."""
    versions = registry.get_versions(task_name)
    if versions is None:
        return jsonify({"success": False, "message": "Task not found."}), 404
    return jsonify({
        "success": True,
        "task_name": task_name,
        "versions": versions
    })


@app.route("/api/restore/<task_name>/<int:version_num>", methods=["POST"])
def api_restore(task_name, version_num):
    """Restore a task to a specific version."""
    versions = registry.get_versions(task_name)
    if not versions:
        return jsonify({"success": False, "message": f"No version history found for '{task_name}'."}), 404

    target = next((v for v in versions if v["version"] == version_num), None)
    if not target:
        return jsonify({"success": False, "message": f"Version {version_num} not found. Available: {[v['version'] for v in versions]}"}), 404

    # Recreate the task with version's metadata
    task_meta = {
        "command": target.get("command", ""),
        "schedule": target.get("schedule", ""),
        "time": target.get("time", ""),
        "day": target.get("day", ""),
        "restored_from_version": version_num,
        "restored_at": datetime.now().isoformat(),
    }

    # Update registry
    registry.add_task(task_name, task_meta)
    registry.add_version(task_name, task_meta, f"Restored from v{version_num}")

    # Recreate the actual Windows task
    try:
        # Delete old task first (if it exists)
        subprocess.run([_SCHTASKS, "/delete", "/tn", task_name, "/f"],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
        # Create new task
        cmd = [
            _SCHTASKS, "/create",
            "/tn", task_name,
            "/tr", task_meta["command"],
            "/sc", task_meta.get("schedule", "daily"),
            "/st", task_meta.get("time", "00:00"),
            "/f"
        ]
        subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except Exception:
        pass  # Best effort - registry is the primary source

    return jsonify({
        "success": True,
        "message": f"Task '{task_name}' restored to v{version_num}.",
        "restored_to": task_meta
    })


# --- Main ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OpenClaw Task Manager Dashboard")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port to run on (default: {PORT})")
    parser.add_argument("--host", default=HOST, help=f"Host to bind to (default: {HOST})")
    args = parser.parse_args()

    print(f"OpenClaw Task Manager Dashboard")
    print(f"Running at: http://{args.host}:{args.port}/")
    print(f"Registry: {REGISTRY_PATH}")
    print(f"Press Ctrl+C to stop")
    app.run(host=args.host, port=args.port, debug=False)
