# faker/snake_player.py
import time, random, math, os, sys
from typing import List, Tuple, Optional
from dataclasses import dataclass

# Helpers réutilisés du pipeline image/eHuB
from image_player import load_columns_from_excel, pack_update, send_udp, chunked

# ---- Config jeu par défaut ----
GRID_W = 32         # grille logique (32x32) -> chaque case = 4x4 LEDs
GRID_H = 32
CELL_PIX = 4        # 4x4 = 16 pixels par case
BG_COLOR = (0, 0, 0)
SNAKE_BODY = (0, 160, 0)
SNAKE_HEAD = (0, 255, 0)
FOOD_COLOR = (255, 40, 40)

# ---- Input clavier (Windows / Unix) ----
WIN = (os.name == "nt")
if WIN:
    import msvcrt
else:
    import curses

@dataclass
class SnakeState:
    snake: List[Tuple[int,int]]  # liste de cases (x,y), head = snake[0]
    dir: Tuple[int,int]          # direction courante (dx,dy)
    food: Tuple[int,int]         # position de la nourriture
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
    # serpent au centre, 3 segments
    cx, cy = W//4, H//2
    snake = [(cx,cy), (cx-1,cy), (cx-2,cy)]
    st = SnakeState(
        snake=snake,
        dir=(1,0),
        food=(0,0),
        alive=True,
        score=0
    )
    occ = set(snake)
    st.food = rand_empty_cell(occ, W, H)
    return st

def step_game(st: SnakeState, W=GRID_W, H=GRID_H) -> None:
    """Avance d'un pas : wrap aux bords, collision avec soi-même -> mort, manger -> grandit."""
    if not st.alive: return
    dx, dy = st.dir
    hx, hy = st.snake[0]
    nx, ny = wrap(hx+dx, W), wrap(hy+dy, H)

    # collision
    if (nx,ny) in st.snake:
        st.alive = False
        return

    # avance
    st.snake.insert(0, (nx,ny))
    if (nx,ny) == st.food:
        st.score += 1
        occ = set(st.snake)
        st.food = rand_empty_cell(occ, W, H)
    else:
        st.snake.pop()  # enlève la queue

def change_dir(st: SnakeState, newdir: Tuple[int,int]) -> None:
    """Empêche de faire demi-tour direct."""
    if not st.alive: return
    ndx, ndy = newdir
    cdx, cdy = st.dir
    if (ndx == -cdx and ndy == -cdy):
        return
    st.dir = newdir

# ---------- Mapping logique (32x32 cases) -> entités LED (128x128) ----------
def build_cell_to_entities(columns_128x128: List[List[int]],
                           W=GRID_W, H=GRID_H, cell_pix=CELL_PIX) -> List[List[List[int]]]:
    """
    Retourne une table [W][H] -> liste des entity_ids pour cette case (4x4=16 entités).
    columns_128x128[x][y] = entity_id
    """
    cell_to_eids: List[List[List[int]]] = [[[] for _ in range(H)] for _ in range(W)]
    for cx in range(W):
        for cy in range(H):
            eids: List[int] = []
            x0 = cx * cell_pix
            y0 = cy * cell_pix
            for dx in range(cell_pix):
                for dy in range(cell_pix):
                    x = x0 + dx
                    y = y0 + dy
                    eids.append(columns_128x128[x][y])
            cell_to_eids[cx][cy] = eids
    return cell_to_eids

def render_frame_to_ents(st: SnakeState,
                         cell_to_eids: List[List[List[int]]],
                         W=GRID_W, H=GRID_H) -> List[Tuple[int,int,int,int,int]]:
    """
    Construit la frame complète: on colore fond + food + snake (head plus vif).
    Pour simplicité/robustesse, on envoie la frame *complète* (toutes cases) => 16 384 entités.
    """
    ents: List[Tuple[int,int,int,int,int]] = []

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
        if i == 0:
            cr, cg, cb = SNAKE_HEAD
        else:
            cr, cg, cb = SNAKE_BODY
        for eid in cell_to_eids[sx][sy]:
            ents.append((eid, cr, cg, cb, 0))

    return ents

# ---------- Envoi eHuB ----------
def send_ents_ehub(ents: List[Tuple[int,int,int,int,int]], host: str, port: int,
                   chunk_size: int = 3000) -> None:
    u = 0
    for chunk in chunked(ents, chunk_size):
        pkt = pack_update(universe=u, entities=chunk)
        send_udp(pkt, host, port)
        u += 1

# ---------- Entrées clavier ----------
def poll_dir_windows() -> Optional[Tuple[int,int]]:
    """
    Flèches (Windows, msvcrt): codes étendus b'\xe0' + [H=72, P=80, K=75, M=77]
    Retourne (dx,dy) ou None si rien.
    """
    if not msvcrt.kbhit():
        return None
    ch = msvcrt.getch()
    if ch in (b'q', b'Q'):
        return ('QUIT')
    if ch == b'\xe0' and msvcrt.kbhit():
        code = msvcrt.getch()
        # up,down,left,right
        if code == b'H': return (0,-1)
        if code == b'P': return (0, 1)
        if code == b'K': return (-1,0)
        if code == b'M': return (1, 0)
    return None

def run_snake(excel: str, host: str, port: int,
              tick_hz: float = 8.0,
              seed: int = 1234,
              W: int = GRID_W, H: int = GRID_H):
    """
    Lance le jeu Snake et envoie les frames eHuB à chaque tick.
    - Déplacements avec les flèches du clavier.
    - 'Q' pour quitter.
    """
    random.seed(seed)
    columns = load_columns_from_excel(excel)       # [128][128] -> entity_id
    cellmap = build_cell_to_entities(columns, W, H, CELL_PIX)

    st = init_game(W, H)
    tick_dt = 1.0 / max(1e-3, tick_hz)
    last_send = 0.0

    print("🐍 Snake lancé.")
    print("Flèches: diriger | Q: quitter | Wrap sur bords | +1 point par food.")
    print(f"Grille: {W}x{H} | Tick: {tick_hz} Hz")

    if WIN:
        t0 = time.time()
        while True:
            # lecture clavier non bloquante
            d = poll_dir_windows()
            if d == 'QUIT':
                break
            if isinstance(d, tuple) and len(d) == 2:
                change_dir(st, d)

            # tick
            now = time.time()
            if now - last_send >= tick_dt:
                step_game(st, W, H)
                ents = render_frame_to_ents(st, cellmap, W, H)
                send_ents_ehub(ents, host, port, chunk_size=3000)
                last_send = now

            if not st.alive:
                print(f"💀 Game Over — score: {st.score}")
                # petite pause avec affichage tête en rouge
                # (on réutilise la frame mais pas obligatoire)
                time.sleep(1.0)
                break

            time.sleep(0.005)
    else:
        # Unix/Mac : curses pour lire les flèches sans bloquer
        def _unix_main(stdscr):
            curses.curs_set(0)
            stdscr.nodelay(True)
            stdscr.timeout(0)

            nonlocal last_send
            while True:
                c = stdscr.getch()
                if c == ord('q') or c == ord('Q'):
                    break
                elif c == curses.KEY_UP:    change_dir(st, (0,-1))
                elif c == curses.KEY_DOWN:  change_dir(st, (0, 1))
                elif c == curses.KEY_LEFT:  change_dir(st, (-1,0))
                elif c == curses.KEY_RIGHT: change_dir(st, (1, 0))

                now = time.time()
                if now - last_send >= tick_dt:
                    step_game(st, W, H)
                    ents = render_frame_to_ents(st, cellmap, W, H)
                    send_ents_ehub(ents, host, port, chunk_size=3000)
                    last_send = now

                if not st.alive:
                    stdscr.addstr(0,0, f"Game Over — score: {st.score}")
                    stdscr.refresh()
                    time.sleep(1.0)
                    break

                time.sleep(0.005)

        curses.wrapper(_unix_main)
