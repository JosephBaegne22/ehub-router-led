# faker/snake_remote.py
import time, random, socket, argparse, os
from typing import List, Tuple, Optional
from dataclasses import dataclass

from image_player import load_columns_from_excel, pack_update, send_udp, chunked

GRID_W = 32
GRID_H = 32
CELL_PIX = 4

BG_COLOR = (0, 0, 0)
SNAKE_BODY = (0, 160, 0)
SNAKE_HEAD = (0, 255, 0)
FOOD_COLOR = (255, 40, 40)

CONTROL_HOST = "127.0.0.1"
CONTROL_PORT = 50010  # écoute des directions

@dataclass
class SnakeState:
    snake: List[Tuple[int,int]]
    dir: Tuple[int,int]
    food: Tuple[int,int]
    alive: bool
    score: int

def wrap(p: int, limit: int) -> int:
    if p < 0: return limit - 1
    if p >= limit: return 0
    return p

def rand_empty_cell(occupied: set, W: int, H: int) -> Tuple[int,int]:
    while True:
        x = random.randrange(0, W)
        y = random.randrange(0, H)
        if (x,y) not in occupied:
            return (x,y)

def init_game(W=GRID_W, H=GRID_H) -> SnakeState:
    cx, cy = W//4, H//2
    snake = [(cx,cy), (cx-1,cy), (cx-2,cy)]
    st = SnakeState(snake=snake, dir=(1,0), food=(0,0), alive=True, score=0)
    st.food = rand_empty_cell(set(snake), W, H)
    return st

def step_game(st: SnakeState, W=GRID_W, H=GRID_H) -> None:
    if not st.alive: return
    dx, dy = st.dir
    hx, hy = st.snake[0]
    nx, ny = wrap(hx+dx, W), wrap(hy+dy, H)
    if (nx,ny) in st.snake:
        st.alive = False
        return
    st.snake.insert(0, (nx,ny))
    if (nx,ny) == st.food:
        st.score += 1
        st.food = rand_empty_cell(set(st.snake), W, H)
    else:
        st.snake.pop()

def change_dir(st: SnakeState, newdir: Tuple[int,int]) -> None:
    if not st.alive: return
    ndx, ndy = newdir
    cdx, cdy = st.dir
    if (ndx == -cdx and ndy == -cdy):
        return
    st.dir = newdir

def build_cell_to_entities(columns_128x128, W=GRID_W, H=GRID_H, cell_pix=CELL_PIX):
    cell_to_eids = [[[] for _ in range(H)] for _ in range(W)]
    for cx in range(W):
        for cy in range(H):
            eids = []
            x0 = cx * cell_pix
            y0 = cy * cell_pix
            for dx in range(cell_pix):
                for dy in range(cell_pix):
                    eids.append(columns_128x128[x0+dx][y0+dy])
            cell_to_eids[cx][cy] = eids
    return cell_to_eids

def render_frame_to_ents(st: SnakeState, cell_to_eids, W=GRID_W, H=GRID_H):
    ents = []
    # fond
    br, bg, bb = BG_COLOR
    for cx in range(W):
        for cy in range(H):
            for eid in cell_to_eids[cx][cy]:
                ents.append((eid, br, bg, bb, 0))
    # food
    fx, fy = st.food
    fr, fg, fb = FOOD_COLOR
    for eid in cell_to_eids[fx][fy]:
        ents.append((eid, fr, fg, fb, 0))
    # snake
    for i, (sx, sy) in enumerate(st.snake):
        if i == 0: cr, cg, cb = SNAKE_HEAD
        else:      cr, cg, cb = SNAKE_BODY
        for eid in cell_to_eids[sx][sy]:
            ents.append((eid, cr, cg, cb, 0))
    return ents

def main():
    ap = argparse.ArgumentParser(description="Snake remote-controlled over UDP 127.0.0.1:50010")
    ap.add_argument("--excel", default="faker/Ecran (2).xlsx")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=50000)
    ap.add_argument("--tick", type=float, default=8.0)
    ap.add_argument("--seed", type=int, default=1234)
    args = ap.parse_args()

    random.seed(args.seed)
    columns = load_columns_from_excel(args.excel)
    cellmap = build_cell_to_entities(columns)

    st = init_game()
    tick_dt = 1.0 / max(1e-3, args.tick)
    last_send = 0.0

    # socket UDP non bloquante pour les commandes
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((CONTROL_HOST, CONTROL_PORT))
    sock.setblocking(False)

    print(f"🐍 Snake remote ON — flèches via /api/snake/dir → UDP {CONTROL_HOST}:{CONTROL_PORT}")
    print("Q pour stopper: /api/stop côté serveur")

    try:
        while True:
            # lire commandes si disponibles
            try:
                data, _ = sock.recvfrom(64)
                msg = (data.decode("utf-8", errors="ignore") or "").strip().upper()
                if   msg == "UP":    change_dir(st, (0,-1))
                elif msg == "DOWN":  change_dir(st, (0, 1))
                elif msg == "LEFT":  change_dir(st, (-1,0))
                elif msg == "RIGHT": change_dir(st, (1, 0))
                elif msg == "QUIT":  break
            except BlockingIOError:
                pass

            now = time.time()
            if now - last_send >= tick_dt:
                step_game(st)
                ents = render_frame_to_ents(st, cellmap)
                # chunking sécurisé
                u = 0
                for chunk in chunked(ents, 3000):
                    pkt = pack_update(universe=u, entities=chunk)
                    send_udp(pkt, args.host, args.port)
                    u += 1
                last_send = now

            if not st.alive:
                print(f"💀 Game Over — score: {st.score}")
                time.sleep(1.0)
                break

            time.sleep(0.003)
    finally:
        sock.close()

if __name__ == "__main__":
    main()
