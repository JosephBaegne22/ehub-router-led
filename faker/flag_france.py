# faker/flag_france.py
import struct, gzip, socket, time, argparse
from typing import List, Tuple
import pandas as pd

MAGIC = b"eHuB"

# ------------- eHuB helpers -------------
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

# ------------- mapping 128x128 -> entity_id -------------
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
        columns = [[0]*128 for _ in range(128)]
    return columns

# ------------- Drapeau de la France -------------
def build_french_flag(columns: List[List[int]]) -> List[Tuple[int,int,int,int,int]]:
    """
    Construit une frame complète : bandes verticales BLEU | BLANC | ROUGE
    sur 128 colonnes. Les largeurs sont ~43/42/43.
    """
    ents: List[Tuple[int,int,int,int,int]] = []
    for x in range(128):
        if x < 43:            # bleu
            color = (0, 0, 255)
        elif x < 85:          # blanc
            color = (255, 255, 255)
        else:                 # rouge
            color = (255, 0, 0)
        for y in range(128):
            eid = columns[x][y]
            ents.append((eid, color[0], color[1], color[2], 0))
    return ents

def play_flag(excel: str, host: str, port: int, seconds: float, fps: float, chunk_size: int):
    columns = load_columns_from_excel(excel)
    frame = build_french_flag(columns)
    dt = 1.0 / max(1e-3, fps)
    t_end = time.time() + seconds
    u0 = 0
    while time.time() < t_end:
        u = u0
        for chunk in chunked(frame, chunk_size):
            pkt = pack_update(universe=u, entities=chunk)
            send_udp(pkt, host, port)
            u += 1
        time.sleep(dt)

# ------------- CLI -------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Drapeau 🇫🇷 128x128 via eHuB (bandes verticales)")
    ap.add_argument("--excel", default="faker/Ecran (2).xlsx")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=50000)
    ap.add_argument("--seconds", type=float, default=10.0, help="durée d'envoi (rafraîchi en boucle)")
    ap.add_argument("--fps", type=float, default=5.0, help="fréquence de ré-envoi")
    ap.add_argument("--chunk", type=int, default=3000, help="taille paquet eHuB (entités/paquet)")
    args = ap.parse_args()
    play_flag(args.excel, args.host, args.port, args.seconds, args.fps, args.chunk)
