"""
AI-Powered Timetable Generator — Flask Web Application
"""

import json
from flask import Flask, jsonify, render_template, request

from timetable_generator import (
    ClassSection,
    Room,
    Subject,
    Teacher,
    TimetableGenerator,
    build_weekly_grid,
    entries_to_dict,
)

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/generate", methods=["POST"])
def generate():
    """
    Generate a timetable from the posted configuration.

    Expected JSON body
    ------------------
    {
      "classes": [{"id": "cs_a", "name": "CS-A", "strength": 60}],
      "subjects": [{"id": "math", "name": "Mathematics", "sessions_per_week": 5}],
      "teachers": [{"id": "t1", "name": "Dr. Smith", "subjects": ["math"]}],
      "rooms":    [{"id": "r101", "name": "Room 101", "capacity": 60}],
      "periods_per_day": 6
    }
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON body."}), 400

    errors = _validate_input(data)
    if errors:
        return jsonify({"error": "; ".join(errors)}), 422

    classes = [ClassSection(**c) for c in data["classes"]]
    subjects = [Subject(**s) for s in data["subjects"]]
    teachers = [Teacher(**t) for t in data["teachers"]]
    rooms = [Room(**r) for r in data["rooms"]]
    periods_per_day = min(int(data.get("periods_per_day", 6)), 7)

    generator = TimetableGenerator(
        classes=classes,
        subjects=subjects,
        teachers=teachers,
        rooms=rooms,
        periods_per_day=periods_per_day,
    )
    entries = generator.generate()

    return jsonify(
        {
            "entries": entries_to_dict(entries),
            "grid": build_weekly_grid(entries),
            "stats": {
                "total_entries": len(entries),
                "classes": len(classes),
                "subjects": len(subjects),
                "teachers": len(teachers),
                "rooms": len(rooms),
            },
        }
    )


@app.route("/api/sample", methods=["GET"])
def sample_config():
    """Return a sample configuration that the frontend can use as a starting point."""
    return jsonify(_sample_config())


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_input(data: dict) -> list:
    errors = []

    for key in ("classes", "subjects", "teachers", "rooms"):
        if key not in data or not isinstance(data[key], list) or len(data[key]) == 0:
            errors.append(f"'{key}' must be a non-empty list.")

    if errors:
        return errors

    required_fields = {
        "classes":  ("id", "name"),
        "subjects": ("id", "name"),
        "teachers": ("id", "name"),
        "rooms":    ("id", "name"),
    }
    for key, fields in required_fields.items():
        for i, item in enumerate(data.get(key, [])):
            for f in fields:
                if not item.get(f):
                    errors.append(f"{key}[{i}] is missing required field '{f}'.")

    return errors


# ---------------------------------------------------------------------------
# Sample configuration
# ---------------------------------------------------------------------------

def _sample_config() -> dict:
    return {
        "classes": [
            {"id": "cs_a", "name": "CS Year-1 A", "strength": 60},
            {"id": "cs_b", "name": "CS Year-1 B", "strength": 55},
        ],
        "subjects": [
            {"id": "math",    "name": "Mathematics",         "sessions_per_week": 5},
            {"id": "physics", "name": "Physics",             "sessions_per_week": 4},
            {"id": "cs",      "name": "Computer Science",    "sessions_per_week": 5},
            {"id": "english", "name": "English",             "sessions_per_week": 3},
        ],
        "teachers": [
            {"id": "t1", "name": "Dr. Alice Smith",   "subjects": ["math"]},
            {"id": "t2", "name": "Prof. Bob Johnson",  "subjects": ["physics"]},
            {"id": "t3", "name": "Ms. Carol Williams", "subjects": ["cs"]},
            {"id": "t4", "name": "Mr. David Brown",    "subjects": ["english"]},
            {"id": "t5", "name": "Dr. Eve Davis",      "subjects": ["math", "physics"]},
        ],
        "rooms": [
            {"id": "r101", "name": "Room 101", "capacity": 60},
            {"id": "r102", "name": "Room 102", "capacity": 60},
            {"id": "r103", "name": "Room 103", "capacity": 30},
            {"id": "lab1", "name": "CS Lab",   "capacity": 40},
        ],
        "periods_per_day": 6,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug)
