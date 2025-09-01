# faker/animator.py
import struct, gzip, socket, time, math, argparse
from typing import List, Tuple
import pandas as pd

MAGIC = b"eHuB"

def pack_update(universe: int, entities: List[Tuple[int,int,int,int,int]]) -> bytes:
    payload = bytearray()
    for eid, r, g, b, w in entities:
        payload += struct.pack("<HBBBB", eid, r, g, b, w)
    comp = gzip.compress(bytes(payload))
    header = bytearray()
    header += MAGIC
    header += bytes([2])                       # type UPDATE
    header += bytes([universe & 0xFF])         # eHuB universe (on reste sur 0 pour tout router)
    header += struct.pack("<H", len(entities))
    header += struct.pack("<H", len(comp))
    return bytes(header) + comp

def send_udp(packet: bytes, host="127.0.0.1", port=50000):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet, (host, port))

def load_entities_from_excel(xlsx_path: str) -> List[int]:
    """
    Charge toutes les entités LEDs (univers 0..127) depuis la feuille eHuB.
    Retourne une liste unique triée d’entity_ids.
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
    ent: List[int] = []
    for _, r in df.iterrows():
        a, b = int(r["entity_start"]), int(r["entity_end"])
        if a <= b:
            ent.extend(range(a, b+1))
        else:
            ent.extend(range(b, a+1))
    return sorted(set(ent))

def clamp(v: int) -> int:
    return max(0, min(255, v))

def color_tuple(s: str) -> Tuple[int,int,int]:
    r, g, b = [clamp(int(x)) for x in s.split(",")]
    return r, g, b

def lerp(a: int, b: int, t: float) -> int:
    return clamp(int(a + (b - a) * t))

def run_animation(mode: str, excel: str, host: str, port: int,
                  seconds: float, fps: float,
                  color1: str, color2: str, speed: float):
    ent_ids = load_entities_from_excel(excel)
    if not ent_ids:
        print("⚠️ aucune entité trouvée dans l'Excel (univers 0..127)")
        return

    r1, g1, b1 = color_tuple(color1)
    r2, g2, b2 = color_tuple(color2)
    dt = 1.0 / max(1e-3, fps)
    t_end = time.time() + seconds
    print(f"🎬 mode={mode} seconds={seconds} fps={fps} entities={len(ent_ids)}")

    # Pour les effets positionnels, on normalise l’index [0..1]
    N = len(ent_ids)
    norm = [i / max(1, N-1) for i in range(N)]

    frame = 0
    while time.time() < t_end:
        t = time.time()
        ents: List[Tuple[int,int,int,int,int]] = []

        if mode == "blink":
            # alterne color1 / color2 chaque 0.5/speed secondes
            phase = int((t * speed) % 2)  # 0 ou 1
            cr, cg, cb = (r1, g1, b1) if phase == 0 else (r2, g2, b2)
            for eid in ent_ids:
                ents.append((eid, cr, cg, cb, 0))

        elif mode == "chase":
            # "comète" de largeur W qui se déplace
            width = max(8, int(0.03 * N))          # ~3% de la longueur
            head = int((t * speed * 10) % N)       # vitesse
            for i, eid in enumerate(ent_ids):
                # distance circulaire
                d = (i - head) % N
                # intensité décroissante
                k = max(0.0, 1.0 - d / width)
                cr = lerp(0, r1, k); cg = lerp(0, g1, k); cb = lerp(0, b1, k)
                ents.append((eid, cr, cg, cb, 0))

        elif mode == "wave":
            # onde sinusoïdale sur toute la longueur (palette color1)
            for i, eid in enumerate(ent_ids):
                s = 0.5 + 0.5 * math.sin(2 * math.pi * (norm[i] * 1.0 - t * speed))
                cr = lerp(0, r1, s); cg = lerp(0, g1, s); cb = lerp(0, b1, s)
                ents.append((eid, cr, cg, cb, 0))

        elif mode == "gradient":
            # dégradé fixe color1 → color2 sur la hauteur, sans animation
            k = min(1.0, frame / max(1, fps))  # fade-in 1s
            for i, eid in enumerate(ent_ids):
                r = lerp(r1, r2, norm[i])
                g = lerp(g1, g2, norm[i])
                b = lerp(b1, b2, norm[i])
                # petit fade-in (optionnel)
                ents.append((eid, lerp(0, r, k), lerp(0, g, k), lerp(0, b, k), 0))

        else:
            # défaut : plein color1
            for eid in ent_ids:
                ents.append((eid, r1, g1, b1, 0))

        pkt = pack_update(universe=0, entities=ents)
        send_udp(pkt, host, port)
        frame += 1
        # cadence
        time.sleep(dt)
