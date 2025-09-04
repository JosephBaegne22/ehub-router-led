# faker/pong_live.py
import struct, gzip, socket, time, argparse, math, random, threading
from typing import List, Tuple
import pandas as pd
from flask import Flask, jsonify, Response

MAGIC = b"eHuB"

# ---------------- eHuB helpers ----------------
def pack_update(universe: int, entities: List[Tuple[int,int,int,int,int]]) -> bytes:
    payload = bytearray()
    for eid, r, g, b, w in entities:
        payload += struct.pack("<HBBBB", eid, r, g, b, w)
    comp = gzip.compress(bytes(payload))
    header = bytearray()
    header += MAGIC
    header += bytes([2])                       # UPDATE
    header += bytes([universe & 0xFF])         # eHuB "universe" (index du paquet, pas ArtNet)
    header += struct.pack("<H", len(entities))
    header += struct.pack("<H", len(comp))
    return bytes(header) + comp

def send_udp(packet: bytes, host="127.0.0.1", port=50000):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet, (host, port))

def chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

# ---------------- mapping 128x128 -> entity_id ----------------
def load_columns_from_excel(xlsx_path: str) -> List[List[int]]:
    df = pd.read_excel(xlsx_path, sheet_name="eHuB")
    df = df.rename(columns={
        "Entity Start": "entity_start",
        "Entity End": "entity_end",
        "ArtNet IP": "ip",
        "ArtNet Universe": "universe",
        "Name": "name",
    })
    df = df[(df["universe"] >= 0) & (df["universe"] <= 127)].copy()
    df = df.sort_values(["ip", "universe"]).reset_index(drop=True)

    columns: List[List[int]] = []
    for ip, g in df.groupby("ip"):
        g = g.sort_values("universe")
        uv = list(g["universe"].astype(int))
        for u in uv:
            if u % 2 != 0:
                continue
            rowA = g[g["universe"] == u]
            if rowA.empty:
                continue
            rowA = rowA.iloc[0]
            rowB = g[g["universe"] == (u+1)]
            rowB = (None if rowB.empty else rowB.iloc[0])

            a0, a1 = int(rowA["entity_start"]), int(rowA["entity_end"])
            listA = list(range(min(a0, a1), max(a0, a1) + 1))

            listB: List[int] = []
            if rowB is not None:
                b0, b1 = int(rowB["entity_start"]), int(rowB["entity_end"])
                listB = list(range(min(b0, b1), max(b0, b1) + 1))

            band = listA + listB
            if len(band) < 200:
                continue

            up_visible   = band[1:1+128]
            down_visible = band[130:130+128]

            col0 = list(reversed(up_visible))
            col1 = down_visible

            if len(col0) < 128: col0 = (col0 + [col0[-1]]*128)[:128]
            if len(col1) < 128: col1 = (col1 + [col1[-1]]*128)[:128]

            columns.append(col0)
            columns.append(col1)

    if len(columns) >= 128:
        return columns[:128]
    while len(columns) < 128 and len(columns) > 0:
        columns.append(columns[-1])
    if not columns:
        columns = [[0]*128 for _ in range(128)]
    return columns

# ---------------- draw helpers ----------------
def draw_rect(ents, columns, x, y, w, h, color):
    x0, y0 = int(x), int(y)
    for yy in range(y0, y0 + h):
        if yy < 0 or yy >= 128: continue
        col = columns
        for xx in range(x0, x0 + w):
            if 0 <= xx < 128:
                eid = columns[xx][yy]
                ents.append((eid, color[0], color[1], color[2], 0))

# ---------------- PONG core ----------------
class PongGame:
    def __init__(self, columns, host, port, fps, chunk):
        self.columns = columns
        self.host, self.port = host, port
        self.dt = 1.0 / max(1e-3, fps)
        self.chunk = chunk

        # Couleurs
        self.BG = (0, 0, 0)           # fond noir pour le diff-only
        self.PADDLE = (255, 255, 255) # blanc
        self.BALL = (255, 220, 0)     # jaune
        self.MID = (80, 80, 80)

        # Paddles
        self.paddle_w = 3
        self.paddle_h = 18
        self.left_x = 4
        self.right_x = 128 - 4 - self.paddle_w
        self.left_y = 55.0
        self.right_y = 55.0
        self.left_v = 0.0   # vitesse en px/s contrôlable
        self.right_v = 0.0

        # Balle
        self.ball_size = 4
        self.ball_speed = 90.0  # accéléré
        self.bx, self.by = 64.0, 64.0
        angle = random.uniform(-0.7, 0.7)
        self.vx = math.copysign(self.ball_speed, random.choice([-1, 1])) * math.cos(angle)
        self.vy = self.ball_speed * math.sin(angle)

        # Pour diff-only (effacer anciennes positions)
        self.prev = {
            "L": (int(self.left_x), int(self.left_y)),
            "R": (int(self.right_x), int(self.right_y)),
            "B": (int(self.bx), int(self.by)),
        }

        # Dessin initial (centre + filets)
        self._paint_initial()

        # Contrôles exposés
        self.running = True

    def _emit(self, ents):
        u = 0
        for ch in chunked(ents, self.chunk):
            pkt = pack_update(u, ch)
            send_udp(pkt, self.host, self.port)
            u += 1

    def _paint_initial(self):
        # Filet central statique (peint une fois)
        ents = []
        x = 64
        for y in range(0, 128, 6):
            for dy in range(3):
                eid = self.columns[x][y+dy]
                ents.append((eid, self.MID[0], self.MID[1], self.MID[2], 0))
        self._emit(ents)

        # Paddles + balle init
        ents = []
        draw_rect(ents, self.columns, self.left_x, int(self.left_y), self.paddle_w, self.paddle_h, self.PADDLE)
        draw_rect(ents, self.columns, self.right_x, int(self.right_y), self.paddle_w, self.paddle_h, self.PADDLE)
        draw_rect(ents, self.columns, int(self.bx), int(self.by), self.ball_size, self.ball_size, self.BALL)
        self._emit(ents)

    def _erase_prev(self, ents):
        # Efface anciennes positions en noir (BG)
        lx, ly = self.prev["L"]
        rx, ry = self.prev["R"]
        bx, by = self.prev["B"]
        draw_rect(ents, self.columns, lx, ly, self.paddle_w, self.paddle_h, self.BG)
        draw_rect(ents, self.columns, rx, ry, self.paddle_w, self.paddle_h, self.BG)
        draw_rect(ents, self.columns, bx, by, self.ball_size, self.ball_size, self.BG)

    def _record_curr(self):
        self.prev["L"] = (int(self.left_x), int(self.left_y))
        self.prev["R"] = (int(self.right_x), int(self.right_y))
        self.prev["B"] = (int(self.bx), int(self.by))

    def step(self):
        dt = self.dt
        ents: List[Tuple[int,int,int,int,int]] = []

        # 1) Effacer anciennes positions
        self._erase_prev(ents)

        # 2) Update positions (paddles contrôlées)
        self.left_y  = max(0, min(128 - self.paddle_h, self.left_y  + self.left_v  * dt))
        self.right_y = max(0, min(128 - self.paddle_h, self.right_y + self.right_v * dt))

        # 3) Physique balle
        self.bx += self.vx * dt
        self.by += self.vy * dt

        # Mur haut/bas
        if self.by <= 0:
            self.by = 0; self.vy = abs(self.vy)
        elif self.by + self.ball_size >= 128:
            self.by = 128 - self.ball_size; self.vy = -abs(self.vy)

        # Paddle gauche
        if self.left_x <= self.bx <= self.left_x + self.paddle_w and self.left_y <= self.by + self.ball_size/2 <= self.left_y + self.paddle_h:
            self.bx = self.left_x + self.paddle_w + 0.1
            self.vx = abs(self.vx) * 1.04
            offset = ((self.by + self.ball_size/2) - (self.left_y + self.paddle_h/2)) / (self.paddle_h/2)
            self.vy = max(-self.ball_speed*1.3, min(self.ball_speed*1.3, self.vy + offset * 40))

        # Paddle droite
        if self.right_x <= self.bx + self.ball_size <= self.right_x + self.paddle_w and self.right_y <= self.by + self.ball_size/2 <= self.right_y + self.paddle_h:
            self.bx = self.right_x - self.ball_size - 0.1
            self.vx = -abs(self.vx) * 1.04
            offset = ((self.by + self.ball_size/2) - (self.right_y + self.paddle_h/2)) / (self.paddle_h/2)
            self.vy = max(-self.ball_speed*1.3, min(self.ball_speed*1.3, self.vy + offset * 40))

        # Sortie gauche/droite → reset centre
        if self.bx < -8 or self.bx > 136:
            self.bx, self.by = 64.0, 64.0
            ang = random.uniform(-0.7, 0.7)
            self.vx = math.copysign(self.ball_speed, random.choice([-1, 1])) * math.cos(ang)
            self.vy = self.ball_speed * math.sin(ang)

        # 4) Dessiner nouvelles positions
        draw_rect(ents, self.columns, self.left_x, int(self.left_y), self.paddle_w, self.paddle_h, self.PADDLE)
        draw_rect(ents, self.columns, self.right_x, int(self.right_y), self.paddle_w, self.paddle_h, self.PADDLE)
        draw_rect(ents, self.columns, int(self.bx), int(self.by), self.ball_size, self.ball_size, self.BALL)

        # 5) Envoyer diff
        self._emit(ents)
        # 6) Mémoriser
        self._record_curr()

# ---------------- Flask controls ----------------
def make_app(game: PongGame):
    app = Flask(__name__)

    @app.get("/")
    def index():
        html = """
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'/>
        <style>button{font-size:22px;padding:12px 18px;margin:6px}</style></head><body>
        <h2>Pong Controls</h2>
        <div>
          <h3>Left</h3>
          <button onclick="fetch('/left/up')">⬆️ Up</button>
          <button onclick="fetch('/left/stop')">⏸️ Stop</button>
          <button onclick="fetch('/left/down')">⬇️ Down</button>
        </div>
        <div>
          <h3>Right</h3>
          <button onclick="fetch('/right/up')">⬆️ Up</button>
          <button onclick="fetch('/right/stop')">⏸️ Stop</button>
          <button onclick="fetch('/right/down')">⬇️ Down</button>
        </div>
        </body></html>
        """
        return Response(html, mimetype="text/html")

    @app.get("/left/up")
    def left_up():
        game.left_v = -120.0
        return jsonify(ok=True, left_v=game.left_v)

    @app.get("/left/down")
    def left_down():
        game.left_v = 120.0
        return jsonify(ok=True, left_v=game.left_v)

    @app.get("/left/stop")
    def left_stop():
        game.left_v = 0.0
        return jsonify(ok=True, left_v=game.left_v)

    @app.get("/right/up")
    def right_up():
        game.right_v = -120.0
        return jsonify(ok=True, right_v=game.right_v)

    @app.get("/right/down")
    def right_down():
        game.right_v = 120.0
        return jsonify(ok=True, right_v=game.right_v)

    @app.get("/right/stop")
    def right_stop():
        game.right_v = 0.0
        return jsonify(ok=True, right_v=game.right_v)

    return app

# ---------------- Runner ----------------
def run_pong(excel, host, port, seconds, fps, chunk, http_port):
    columns = load_columns_from_excel(excel)
    game = PongGame(columns, host, port, fps, chunk)

    # Thread Flask (contrôles)
    app = make_app(game)
    th = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=http_port, debug=False, use_reloader=False))
    th.daemon = True
    th.start()

    t_end = time.time() + seconds if seconds > 0 else float("inf")
    while time.time() < t_end and game.running:
        game.step()
        time.sleep(game.dt)

# ---------------- CLI ----------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Pong live (diff-only + contrôles web) 128x128 via eHuB")
    ap.add_argument("--excel", default="faker/Ecran (2).xlsx")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=50000)
    ap.add_argument("--seconds", type=float, default=0.0, help="0 = infini")
    ap.add_argument("--fps", type=float, default=40.0)
    ap.add_argument("--chunk", type=int, default=3000, help="entités/paquet eHuB")
    ap.add_argument("--http_port", type=int, default=5055, help="port des contrôles web")
    args = ap.parse_args()

    run_pong(args.excel, args.host, args.port, args.seconds, args.fps, args.chunk, args.http_port)
