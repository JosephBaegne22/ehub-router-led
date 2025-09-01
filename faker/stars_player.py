# faker/stars_player.py
import struct, gzip, socket, time, math, random, argparse, os
from typing import List, Tuple
import pandas as pd

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
    """
    Construit une table columns[128][128] -> entity_id
    Hypothèse LAPS: chaque bande = 2 univers (U, U+1) => 2 colonnes visibles de 128 LED.
    On assemble par IP puis par univers croissant, en prenant:
      - up_visible   : band[1:1+128]   (montée visibles)  -> inversée (y=0 en haut)
      - down_visible : band[130:130+128] (descente visibles) -> telle quelle
    """
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
    # pad au besoin
    while len(columns) < 128 and len(columns) > 0:
        columns.append(columns[-1])
    if not columns:
        # fallback: grille vide (mieux que crash)
        columns = [[0]*128 for _ in range(128)]
    return columns

# ---------------- ciel étoilé ----------------
class Star:
    __slots__ = ("x","y","phase","speed","base","color")
    def __init__(self, x:int, y:int, phase:float, speed:float, base:float, color:Tuple[int,int,int]):
        self.x = x; self.y = y
        self.phase = phase      # déphasage du scintillement
        self.speed = speed      # vitesse du twinkle
        self.base = base        # luminosité de base [0..1]
        self.color = color      # RGB de la star (ex: blanc ou légèrement bleuté)

def build_starfield(columns: List[List[int]], density: float, seed: int,
                    white_bias: float = 0.8) -> List[Star]:
    """
    density ∈ (0..1) proportion de pixels allumés (ex: 0.01 → ~1% → ~163 étoiles).
    white_bias: proba d'avoir une étoile blanche (sinon bleu pale / jaune pale).
    """
    rnd = random.Random(seed)
    stars: List[Star] = []
    count = max(1, int(128*128*density))
    for _ in range(count):
        x = rnd.randrange(0,128)
        y = rnd.randrange(0,128)
        phase = rnd.random()*math.tau
        speed = 0.6 + rnd.random()*1.2      # 0.6..1.8 Hz
        base  = 0.3 + rnd.random()*0.5      # 0.3..0.8
        if rnd.random() < white_bias:
            color = (255,255,255)
        else:
            # variantes: bleu pâle ou jaune pâle
            if rnd.random() < 0.5:
                color = (180,200,255)
            else:
                color = (255,220,160)
        stars.append(Star(x,y,phase,speed,base,color))
    return stars

def render_stars_frame(columns: List[List[int]], stars: List[Star], t: float,
                       bg: Tuple[int,int,int]) -> List[Tuple[int,int,int,int,int]]:
    """
    Construit la liste (entity_id, r,g,b,0) pour cette frame:
      - fond = bg (faible bleu nuit)
      - étoiles = couleur * twinkle(t)
    """
    ents: List[Tuple[int,int,int,int,int]] = []

    # fond (optionnel) : on met un léger bleu nuit sur tout le mur
    if bg != (0,0,0):
        for x in range(128):
            col = columns[x]
            for y in range(128):
                eid = col[y]
                ents.append((eid, bg[0], bg[1], bg[2], 0))

    # étoiles qui scintillent
    for st in stars:
        eid = columns[st.x][st.y]
        # twinkle: sinus 0..1 autour de la base
        osc = 0.5*(1.0 + math.sin(st.phase + t*math.tau*st.speed))  # 0..1
        k = min(1.0, st.base + 0.7*osc)   # boost scintillement
        r = min(255, int(st.color[0]*k))
        g = min(255, int(st.color[1]*k))
        b = min(255, int(st.color[2]*k))
        ents.append((eid, r, g, b, 0))

    return ents

def play_starfield(excel: str, host: str, port: int,
                   seconds: float, fps: float,
                   density: float, seed: int,
                   bg: str, chunk_size: int):
    """
    bg: '0,0,0' (fond noir) ou '4,8,16' (bleu nuit doux recommandé).
    chunk_size: nb d'entités par paquet eHuB (sécurité UDP).
    """
    columns = load_columns_from_excel(excel)
    # parse bg
    try:
        br, bgc, bb = [max(0, min(255, int(v))) for v in bg.split(",")]
        bg_rgb = (br, bgc, bb)
    except Exception:
        bg_rgb = (0,0,0)

    stars = build_starfield(columns, density=density, seed=seed, white_bias=0.8)
    print(f"🌌 Starfield: {len(stars)} étoiles | bg={bg_rgb} | fps={fps} | seconds={seconds}")

    dt = 1.0 / max(1e-3, fps)
    t0 = time.time()
    t_end = t0 + seconds

    while time.time() < t_end:
        t = time.time() - t0
        ents = render_stars_frame(columns, stars, t, bg_rgb)

        # chunking eHuB (au cas où le fond non noir => ~16k entités)
        u = 0
        for chunk in chunked(ents, chunk_size):
            pkt = pack_update(universe=u, entities=chunk)
            send_udp(pkt, host, port)
            u += 1

        time.sleep(dt)

# ---------------- CLI ----------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Ciel étoilé 128x128 via eHuB")
    ap.add_argument("--excel", default="faker/Ecran (2).xlsx")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=50000)
    ap.add_argument("--seconds", type=float, default=15.0)
    ap.add_argument("--fps", type=float, default=20.0)
    ap.add_argument("--density", type=float, default=0.01, help="fraction de pixels en étoiles (ex 0.01 = ~163)")
    ap.add_argument("--seed", type=int, default=42, help="aléa reproductible")
    ap.add_argument("--bg", default="4,8,16", help="couleur de fond R,G,B (ex 0,0,0 ou 4,8,16)")
    ap.add_argument("--chunk", type=int, default=3000, help="taille paquet eHuB (entités/paquet)")
    args = ap.parse_args()

    # sécurité des bornes
    density = max(0.001, min(0.2, args.density))   # 0.1% .. 20% max
    play_starfield(args.excel, args.host, args.port, args.seconds, args.fps,
                   density, args.seed, args.bg, args.chunk)
