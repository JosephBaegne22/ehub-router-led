import os, sys, subprocess, threading
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder=".", static_url_path="")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
EXCEL_PATH = str(PROJECT_ROOT / "faker" / "Ecran (2).xlsx")
ROUTER_HOST = "127.0.0.1"
ROUTER_PORT = "50000"

_current_proc = None
_proc_lock = threading.Lock()

def _start_process(cmd):
    global _current_proc
    with _proc_lock:
        if _current_proc and _current_proc.poll() is None:
            return False, "Une animation est déjà en cours. Clique d'abord sur STOP."
        _current_proc = subprocess.Popen(cmd, cwd=str(PROJECT_ROOT))
        return True, "OK"

def _stop_process():
    global _current_proc
    with _proc_lock:
        if _current_proc and _current_proc.poll() is None:
            try:
                _current_proc.terminate()
            except Exception:
                pass
        _current_proc = None


@app.post("/api/start")
def api_start():
    data = request.get_json(force=True, silent=True) or {}
    mode = data.get("mode", "blink")
    seconds = str(data.get("seconds", 10))
    fps = str(data.get("fps", 25))
    color1 = data.get("color1", "255,0,0")
    color2 = data.get("color2", "0,0,255")
    density = str(data.get("density", 0.01))
    bg = data.get("bg", "4,8,16")

    if mode == "stars":
        cmd = [
            PYTHON, "faker/stars_player.py",
            "--excel", EXCEL_PATH,
            "--host", ROUTER_HOST, "--port", ROUTER_PORT,
            "--seconds", seconds, "--fps", fps,
            "--density", density, "--bg", bg
        ]

    elif mode == "image":
        img = data.get("image", str(PROJECT_ROOT / "assets" / "ryu.png"))
        fit = data.get("fit", "cover")
        brightness = str(data.get("brightness", 0.7))
        gamma = str(data.get("gamma", 2.0))
        flipy = data.get("flipY", False)
        cmd = [
            PYTHON, "faker/image_player_cli.py",
            "--image", img,
            "--excel", EXCEL_PATH,
            "--host", ROUTER_HOST, "--port", ROUTER_PORT,
            "--seconds", seconds, "--fps", fps,
            "--brightness", brightness, "--gamma", gamma,
            "--fit", fit
        ]
        if flipy:
            cmd.append("--flip-y")

    elif mode in ["blink","wave","chase","gradient","solid"]:
        cmd = [
            PYTHON, "faker/animator_cli.py",
            "--mode", mode,
            "--excel", EXCEL_PATH,
            "--host", ROUTER_HOST, "--port", ROUTER_PORT,
            "--seconds", seconds, "--fps", fps,
            "--color1", color1, "--color2", color2
        ]

    elif mode == "fireworks":
        cmd = [
            PYTHON, "faker/fireworks.py",
            "--excel", EXCEL_PATH,
            "--host", ROUTER_HOST, "--port", ROUTER_PORT,
            "--seconds", seconds, "--fps", fps
        ]

    elif mode == "aurora":
        cmd = [
            PYTHON, "faker/aurora.py",
            "--excel", EXCEL_PATH,
            "--host", ROUTER_HOST, "--port", ROUTER_PORT,
            "--seconds", seconds, "--fps", fps
        ]

    elif mode == "lava":
        cmd = [
            PYTHON, "faker/lava.py",
            "--excel", EXCEL_PATH,
            "--host", ROUTER_HOST, "--port", ROUTER_PORT,
            "--seconds", seconds,
            "--fps", fps
        ]

    else:
        return jsonify({"ok": False, "msg": f"Mode inconnu: {mode}"}), 400

    ok, msg = _start_process(cmd)
    return jsonify({"ok": ok, "msg": msg, "cmd": cmd}), (200 if ok else 409)

@app.post("/api/stop")
def api_stop():
    _stop_process()
    return jsonify({"ok": True})

@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    # http://localhost:8000
    app.run(host="127.0.0.1", port=8000, debug=False)