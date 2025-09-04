# webui/server.py
import os, sys, subprocess, threading, socket
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder=".", static_url_path="")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
EXCEL_PATH = str(PROJECT_ROOT / "faker" / "Ecran (2).xlsx")
ROUTER_HOST = "127.0.0.1"
ROUTER_PORT = "50000"

SNAKE_CTRL_HOST = "127.0.0.1"
SNAKE_CTRL_PORT = 50010  # doit matcher snake_remote.py

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
        # notifier snake s'il tourne
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.sendto(b"QUIT", (SNAKE_CTRL_HOST, SNAKE_CTRL_PORT))
            s.close()
        except Exception:
            pass
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
        cmd = [PYTHON, "faker/stars_player.py", "--excel", EXCEL_PATH,
               "--host", ROUTER_HOST, "--port", ROUTER_PORT,
               "--seconds", seconds, "--fps", fps,
               "--density", density, "--bg", bg]

    elif mode == "image":
        img = data.get("image", str(PROJECT_ROOT / "assets" / "ryu.png"))
        fit = data.get("fit", "cover")
        brightness = str(data.get("brightness", 0.7))
        gamma = str(data.get("gamma", 2.0))
        flipy = data.get("flipY", False)
        cmd = [PYTHON, "faker/image_player_cli.py", "--image", img,
               "--excel", EXCEL_PATH, "--host", ROUTER_HOST, "--port", ROUTER_PORT,
               "--seconds", seconds, "--fps", fps,
               "--brightness", brightness, "--gamma", gamma, "--fit", fit]
        if flipy: cmd.append("--flip-y")

    elif mode == "snake":
        tick = str(data.get("tick", 8.0))
        cmd = [PYTHON, "faker/snake_remote.py",
               "--excel", EXCEL_PATH, "--host", ROUTER_HOST, "--port", ROUTER_PORT,
               "--tick", tick]

    else:
        cmd = [PYTHON, "faker/animator_cli.py", "--mode", mode,
               "--excel", EXCEL_PATH, "--host", ROUTER_HOST, "--port", ROUTER_PORT,
               "--seconds", seconds, "--fps", fps, "--color1", color1, "--color2", color2]

    ok, msg = _start_process(cmd)
    return jsonify({"ok": ok, "msg": msg, "cmd": cmd}), (200 if ok else 409)

@app.post("/api/stop")
def api_stop():
    _stop_process()
    return jsonify({"ok": True})

@app.post("/api/snake/dir")
def api_snake_dir():
    data = request.get_json(force=True, silent=True) or {}
    direction = (data.get("dir") or "").upper()
    if direction not in ("UP","DOWN","LEFT","RIGHT","QUIT"):
        return jsonify({"ok": False, "msg": "dir invalide"}), 400
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(direction.encode("utf-8"), (SNAKE_CTRL_HOST, SNAKE_CTRL_PORT))
        s.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
