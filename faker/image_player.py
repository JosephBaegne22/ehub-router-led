# faker/image_player.py
import struct, gzip, socket, time, math, os
from typing import List, Tuple
import pandas as pd
from PIL import Image

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

def clamp8(x: float) -> int:
    return max(0, min(255, int(round(x))))

# ---------------- mapping 128x128 -> entity_id ----------------
def load_columns_from_excel(xlsx_path: str) -> List[List[int]]:
    """
    Construit une table columns[128][128] -> entity_id
    Hypothèse LAPS: chaque bande = 2 univers (U, U+1) => 2 colonnes visibles de 128 LED.
    On assemble par IP puis par univers croissant.
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
    while len(columns) < 128 and len(columns) > 0:
        columns.append(columns[-1])
    if not columns:
        columns = [[0]*128 for _ in range(128)]
    return columns

# ---------------- image → LEDs ----------------
def load_and_resize_image(path: str, size: int = 128, fit_mode: str = "cover", flip_y: bool = False) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    if img.width != size or img.height != size:
        if fit_mode == "cover":
            img = img.resize((size, size), Image.LANCZOS)
        else:
            bg = Image.new("RGBA", (size, size), (0,0,0,0))
            img.thumbnail((size, size), Image.LANCZOS)
            ox = (size - img.width)//2
            oy = (size - img.height)//2
            bg.paste(img, (ox, oy), img)
            img = bg
    if flip_y:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    return img

def apply_brightness_gamma(pixel: Tuple[int,int,int,int], brightness: float, gamma: float) -> Tuple[int,int,int]:
    r,g,b,a = pixel
    r = r*a//255; g = g*a//255; b = b*a//255
    r = clamp8(r*brightness); g = clamp8(g*brightness); b = clamp8(b*brightness)
    if gamma != 1.0:
        inv = 1.0/gamma
        r = clamp8((r/255.0)**inv*255.0)
        g = clamp8((g/255.0)**inv*255.0)
        b = clamp8((b/255.0)**inv*255.0)
    return r,g,b

def stream_image_to_ehub(img_path: str, excel: str, host: str, port: int,
                         seconds: float, fps: float,
                         brightness: float = 0.8, gamma: float = 2.2,
                         fit_mode: str = "cover", flip_y: bool = False,
                         chunk_size: int = 2048):
    columns = load_columns_from_excel(excel)
    img = load_and_resize_image(img_path, 128, fit_mode, flip_y)
    px = img.load()
    dt = 1.0/max(1e-3,fps)
    t_end = time.time()+seconds

    print(f"🖼️ projecting {os.path.basename(img_path)} for {seconds}s @ {fps} fps")

    while time.time()<t_end:
        ents: List[Tuple[int,int,int,int,int]] = []
        for x in range(128):
            col = columns[x]
            for y in range(128):
                eid = col[y]
                r,g,b = apply_brightness_gamma(px[x,y], brightness, gamma)
                ents.append((eid,r,g,b,0))
        # découpage
        u=0
        for chunk in chunked(ents,chunk_size):
            pkt=pack_update(universe=u,entities=chunk)
            send_udp(pkt,host,port)
            u+=1
        time.sleep(dt)
