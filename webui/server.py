import os
import sys
import subprocess
import threading
from pathlib import Path
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, send_from_directory, Response, abort
from werkzeug.utils import secure_filename

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from animations import ANIMATIONS

app = Flask(__name__, static_folder=".", static_url_path="")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
EXCEL_PATH = str(PROJECT_ROOT / "faker" / "Ecran (2).xlsx")
ROUTER_HOST = "127.0.0.1"
ROUTER_PORT = 50000

_current_proc = None
_proc_lock = threading.Lock()

def _start_process(cmd):
    global _current_proc
    with _proc_lock:
        if _current_proc and _current_proc.poll() is None:
            return False, "Une animation est déjà en cours."
        _current_proc = subprocess.Popen(cmd, cwd=str(PROJECT_ROOT))
        return True, "OK"

def _stop_process():
    global _current_proc
    with _proc_lock:
        if _current_proc and _current_proc.poll() is None:
            try: 
                _current_proc.terminate()
                logger.info("Animation stoppée")
            except Exception:
                pass
        _current_proc = None

@app.get("/api/animations")
def get_animations():
    """Renvoie la liste des animations disponibles pour l’UI web."""
    return jsonify({k: v["desc"] for k,v in ANIMATIONS.items()})

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
            "--host", ROUTER_HOST, "--port", str(ROUTER_PORT),
            "--seconds", seconds, "--fps", fps,
            "--density", density, "--bg", bg,
            "--chunk", "3000"
        ]
    else:
        cmd = [
            PYTHON, "faker/animator_cli.py",
            "--mode", mode,
            "--excel", EXCEL_PATH,
            "--host", ROUTER_HOST, "--port", str(ROUTER_PORT),
            "--seconds", seconds, "--fps", fps,
            "--color1", color1, "--color2", color2
        ]

    ok, msg = _start_process(cmd)
    return jsonify(ok=ok, msg=msg, cmd=cmd), (200 if ok else 409)

@app.post("/api/stop")
def api_stop():
    _stop_process()
    return jsonify(ok=True)

@app.get("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

# -----------------------
# Gestion erreurs globales
# -----------------------
@app.errorhandler(Exception)
def handle_exception(e):
    tb = traceback.format_exc()
    logger.error(f"Erreur Flask:\n{tb}")
    return jsonify(ok=False, error=str(e)), 500

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
