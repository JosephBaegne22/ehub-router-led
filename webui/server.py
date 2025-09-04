<<<<<<< Updated upstream
import os, sys, subprocess, threading, time, yaml, logging, shutil, traceback
=======
import os
import sys
import subprocess
import threading
>>>>>>> Stashed changes
from pathlib import Path
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, send_from_directory, Response, abort
from werkzeug.utils import secure_filename

<<<<<<< Updated upstream
# -----------------------
# CONFIG
# -----------------------
BASE_DIR = Path(__file__).resolve().parent        # webui/
PROJECT_ROOT = BASE_DIR.parent                    # racine projet
UPLOAD_FOLDER = PROJECT_ROOT / "faker"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
LOG_PATH = BASE_DIR / "webui.log"

PYTHON = sys.executable
EXCEL_PATH = str(UPLOAD_FOLDER / "Ecran (2).xlsx")
ROUTER_HOST = "127.0.0.1"
ROUTER_PORT = "50000"

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}

# -----------------------
# Flask
# -----------------------
app = Flask(__name__, static_folder=".", static_url_path="")
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)

# -----------------------
# Logging
# -----------------------
logger = logging.getLogger("webui")
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(str(LOG_PATH), maxBytes=2*1024*1024, backupCount=3)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(logging.StreamHandler())

# -----------------------
# Init dossiers/fichiers
# -----------------------
UPLOAD_FOLDER.mkdir(exist_ok=True)
if not CONFIG_PATH.exists():
    CONFIG_PATH.write_text("{}", encoding="utf-8")

# -----------------------
# Utils
# -----------------------
def allowed_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            logger.exception("Erreur lecture config.yaml")
    return {}

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)
        return True, ""
    except Exception as e:
        logger.exception("Erreur sauvegarde config.yaml")
        return False, str(e)

# -----------------------
# Upload Excel
# -----------------------
@app.post("/upload_excel")
def upload_excel():
    if "file" not in request.files:
        return jsonify(ok=False, error="Aucun fichier reçu"), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify(ok=False, error="Nom vide"), 400
    if not allowed_file(file.filename):
        return jsonify(ok=False, error="Extension interdite"), 400

    filename = secure_filename(file.filename)
    target = UPLOAD_FOLDER / filename
    file.save(str(target))
    logger.info(f"Excel uploadé: {target}")
    return jsonify(ok=True, path=target.name)

@app.post("/set_active_excel")
def set_active_excel():
    data = request.json or {}
    fname = data.get("filename")
    if not fname:
        return jsonify(ok=False, error="filename manquant"), 400
    candidate = UPLOAD_FOLDER / secure_filename(fname)
    if not candidate.exists():
        return jsonify(ok=False, error="fichier introuvable"), 404
    active = UPLOAD_FOLDER / "active_lookup.xlsx"
    try:
        shutil.copy(candidate, active)
        logger.info(f"Excel activé: {active}")
        return jsonify(ok=True, active=active.name)
    except Exception as e:
        logger.exception("set_active_excel error")
        return jsonify(ok=False, error=str(e)), 500

@app.get("/download/<filename>")
def download_file(filename):
    if not allowed_file(filename):
        abort(403)
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)

# -----------------------
# Config
# -----------------------
@app.route("/config", methods=["GET", "POST"])
def config_route():
    if request.method == "GET":
        return jsonify(ok=True, config=load_config())
    else:
        data = request.get_json()
        if data is None:
            return jsonify(ok=False, error="JSON attendu"), 400
        ok, err = save_config(data)
        return jsonify(ok=ok, error=err)

# -----------------------
# Logs (SSE)
# -----------------------
def follow_file(path: Path):
    path.touch(exist_ok=True)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.2)
                continue
            yield line

@app.get("/logs/stream")
def logs_stream():
    def gen():
        for line in follow_file(LOG_PATH):
            yield f"data: {line.rstrip()}\n\n"
    return Response(gen(), mimetype="text/event-stream")

@app.get("/logs/recent")
def logs_recent():
    try:
        lines = LOG_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()[-200:]
        return jsonify(ok=True, lines=lines)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

# -----------------------
# Process handling (start/stop animations)
# -----------------------
=======
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from animations import ANIMATIONS

app = Flask(__name__, static_folder=".", static_url_path="")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
EXCEL_PATH = str(PROJECT_ROOT / "faker" / "Ecran (2).xlsx")
ROUTER_HOST = "127.0.0.1"
ROUTER_PORT = 50000

>>>>>>> Stashed changes
_current_proc = None
_proc_lock = threading.Lock()

def _start_process(cmd):
    global _current_proc
    with _proc_lock:
        if _current_proc and _current_proc.poll() is None:
<<<<<<< Updated upstream
            return False, "Une animation est déjà en cours. Clique d'abord sur STOP."
        try:
            # Lancer le processus et capturer stdout/stderr
            _current_proc = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
        except Exception as e:
            logger.exception("Erreur lancement animation")
            return False, str(e)

        # Thread pour lire stdout/stderr et logger
        def reader(proc):
            try:
                for line in proc.stdout:
                    logger.info("[ANIM] " + line.strip())
            except Exception:
                logger.exception("Erreur lecture stdout animation")

        threading.Thread(target=reader, args=(_current_proc,), daemon=True).start()
=======
            return False, "Une animation est déjà en cours."
        _current_proc = subprocess.Popen(cmd, cwd=str(PROJECT_ROOT))
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
=======
@app.get("/api/animations")
def get_animations():
    """Renvoie la liste des animations disponibles pour l’UI web."""
    return jsonify({k: v["desc"] for k,v in ANIMATIONS.items()})

>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
        cmd = [PYTHON, "faker/stars_player.py",
               "--excel", EXCEL_PATH, "--host", ROUTER_HOST, "--port", ROUTER_PORT,
               "--seconds", seconds, "--fps", fps,
               "--density", density, "--bg", bg]
    elif mode == "image":
        img = data.get("image", str(PROJECT_ROOT / "assets" / "ryu.png"))
        fit = data.get("fit", "cover")
        brightness = str(data.get("brightness", 0.7))
        gamma = str(data.get("gamma", 2.0))
        flipy = data.get("flipY", False)
        cmd = [PYTHON, "faker/image_player_cli.py",
               "--image", img,
               "--excel", EXCEL_PATH, "--host", ROUTER_HOST, "--port", ROUTER_PORT,
               "--seconds", seconds, "--fps", fps,
               "--brightness", brightness, "--gamma", gamma,
               "--fit", fit]
        if flipy: cmd.append("--flip-y")
    elif mode in ["blink","wave","chase","gradient","solid"]:
        cmd = [PYTHON, "faker/animator_cli.py",
               "--mode", mode,
               "--excel", EXCEL_PATH, "--host", ROUTER_HOST, "--port", ROUTER_PORT,
               "--seconds", seconds, "--fps", fps,
               "--color1", color1, "--color2", color2]
    elif mode == "plasma":
        cmd = [PYTHON, "faker/plasma_rainbow.py",
               "--excel", EXCEL_PATH, "--host", ROUTER_HOST, "--port", ROUTER_PORT,
               "--seconds", seconds, "--fps", fps]
    elif mode == "fireworks":
        cmd = [PYTHON, "faker/fireworks.py",
               "--excel", EXCEL_PATH, "--host", ROUTER_HOST, "--port", ROUTER_PORT,
               "--seconds", seconds, "--fps", fps]
    elif mode == "aurora":
        cmd = [PYTHON, "faker/aurora.py",
               "--excel", EXCEL_PATH, "--host", ROUTER_HOST, "--port", ROUTER_PORT,
               "--seconds", seconds, "--fps", fps]
    elif mode == "lava":
        cmd = [PYTHON, "faker/lava.py",
               "--excel", EXCEL_PATH, "--host", ROUTER_HOST, "--port", ROUTER_PORT,
               "--seconds", seconds, "--fps", fps]
    else:
        return jsonify(ok=False, msg=f"Mode inconnu: {mode}"), 400
=======
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
>>>>>>> Stashed changes

    ok, msg = _start_process(cmd)
    return jsonify(ok=ok, msg=msg, cmd=cmd), (200 if ok else 409)

@app.post("/api/stop")
def api_stop():
    _stop_process()
    return jsonify(ok=True)

<<<<<<< Updated upstream
# -----------------------
# Index
# -----------------------
=======
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
    logger.info("Démarrage webui server.py")
    app.run(host="127.0.0.1", port=8000, debug=False, threaded=True)
=======
    app.run(host="127.0.0.1", port=8000, debug=False)
>>>>>>> Stashed changes
