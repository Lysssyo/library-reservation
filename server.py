import json
import re
import subprocess
import sys
from pathlib import Path

from flask import Flask, jsonify, request

BASE_DIR = Path(__file__).parent
STATE_FILE = BASE_DIR / "state.json"
LOG_DIR = BASE_DIR / "logs"

app = Flask(__name__)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/<path:_path>", methods=["OPTIONS"])
@app.route("/", methods=["OPTIONS"])
def options_handler(_path=""):
    return ("", 204)


def load_state():
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


@app.get("/status")
def get_status():
    return jsonify(load_state())


@app.post("/enabled")
def set_enabled():
    body = request.get_json(silent=True) or {}
    enabled = body.get("enabled")
    if not isinstance(enabled, bool):
        return jsonify({"error": "enabled 必须是 true 或 false"}), 400

    state = load_state()
    state["enabled"] = enabled
    save_state(state)
    return jsonify(state)


@app.get("/seat")
def get_seat():
    state = load_state()
    return jsonify({"seat_id": state.get("seat_id")})


@app.post("/seat")
def set_seat():
    body = request.get_json(silent=True) or {}
    seat_id = body.get("seat_id", "")
    if not str(seat_id).isdigit():
        return jsonify({"error": "seat_id 必须是纯数字字符串"}), 400

    state = load_state()
    state["seat_id"] = str(seat_id)
    save_state(state)
    return jsonify(state)


@app.post("/run")
def manual_run():
    subprocess.Popen(
        [sys.executable, str(BASE_DIR / "run_once.py")],
        start_new_session=True,
    )
    return jsonify({"started": True, "message": "任务已开始，请稍后查看日志"})


@app.get("/logs")
def get_logs():
    date = request.args.get("date", "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        return jsonify({"error": "date 格式必须为 YYYY-MM-DD"}), 400

    log_path = LOG_DIR / f"{date}.log"
    if not log_path.exists():
        return jsonify({"date": date, "lines": []})

    lines = log_path.read_text(encoding="utf-8").splitlines()

    tail = request.args.get("tail")
    if tail is not None:
        if not str(tail).isdigit():
            return jsonify({"error": "tail 必须是正整数"}), 400
        lines = lines[-int(tail):]

    return jsonify({"date": date, "lines": lines})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
