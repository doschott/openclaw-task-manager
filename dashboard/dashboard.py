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
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, jsonify, request, redirect, url_for

# --- Configuration ---
PORT = 5173
HOST = "0.0.0.0"
REGISTRY_PATH = Path.home() / ".openclaw" / "task-registry.json"

# --- Flask App ---
app = Flask(__name__, template_folder="templates", static_folder="static")

OPENCLAW_PATTERN = re.compile(r"^OpenClaw_")
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


def validate_name(task_name):
    if not NAMING_PATTERN.match(task_name):
        raise ValueError(
            f"Task name '{task_name}' does not match convention. "
            f"Expected: OpenClaw_{{Project}}_{{Action}}_{{Schedule}}"
        )
    return True


# --- Task Operations ---
def query_windows_tasks():
    """Get all OpenClaw_* tasks from Windows Task Scheduler."""
    tasks = {}
    try:
        result = subprocess.run(
            ["schtasks", "/query", "/fo", "LIST", "/v"],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        current_task = {}
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line.startswith("TaskName:"):
                name = line.split("TaskName:", 1)[1].strip()
                if OPENCLAW_PATTERN.match(name):
                    current_task["name"] = name
            elif line.startswith("Next Run Time:") and "name" in current_task:
                current_task["next_run"] = line.split("Next Run Time:", 1)[1].strip()
            elif line.startswith("Last Run Time:") and "name" in current_task:
                current_task["last_run"] = line.split("Last Run Time:", 1)[1].strip()
            elif line.startswith("Last Result:") and "name" in current_task:
                current_task["last_result"] = line.split("Last Result:", 1)[1].strip()
            elif line.startswith("Status:") and "name" in current_task:
                current_task["status"] = line.split("Status:", 1)[1].strip()
                tasks[current_task["name"]] = current_task
                current_task = {}
            elif line.startswith("Task To Run:") and "name" in current_task:
                current_task["command"] = line.split("Task To Run:", 1)[1].strip()
    except Exception:
        pass
    return tasks


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
        "schtasks", "/create",
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
    registry[task_name] = {
        "command": command,
        "time": time,
        "schedule": frequency,
        "created_at": datetime.now().isoformat(),
    }
    if day:
        registry[task_name]["day"] = day
    save_registry(registry)


def delete_task(task_name, force=False):
    """Delete a task from Windows Task Scheduler and registry."""
    # Registry check unless forced
    if not force:
        registry = load_registry()
        if task_name not in registry:
            raise ValueError(f"Task '{task_name}' not found in registry. Use --force to delete anyway.")

    result = subprocess.run(
        ["schtasks", "/delete", "/tn", task_name, "/f"],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())

    # Remove from registry
    registry = load_registry()
    registry.pop(task_name, None)
    save_registry(registry)


def toggle_task(task_name, enable=True):
    """Enable or disable a task."""
    action = "/enable" if enable else "/disable"
    result = subprocess.run(
        ["schtasks", "/change", "/tn", task_name, action],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())


def run_task_now(task_name):
    """Trigger a task to run immediately."""
    result = subprocess.run(
        ["schtasks", "/run", "/tn", task_name],
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
