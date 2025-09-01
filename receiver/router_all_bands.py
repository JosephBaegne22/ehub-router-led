# receiver/router_all_bands.py
import os, sys, socket
from typing import Dict, Tuple, List
import pandas as pd

# Import artnet
HERE = os.path.dirname(__file__)
ARTNET_DIR = os.path.abspath(os.path.join(HERE, "..", "artnet"))
if ARTNET_DIR not in sys.path:
    sys.path.insert(0, ARTNET_DIR)

from parser import parse_packet, UpdateFrame, ConfigFrame
from artnet import ArtNetSender

MappingRow = Tuple[int,int,str,int]  # (entity_start, entity_end, ip, universe)

def load_all_from_excel(xlsx_path: str) -> List[MappingRow]:
    df = pd.read_excel(xlsx_path, sheet_name="eHuB")
    df = df.rename(columns={
        "Entity Start": "entity_start",
        "Entity End": "entity_end",
        "ArtNet IP": "ip",
        "ArtNet Universe": "universe",
        "Name": "name",
    })
    # Garder les univers LEDs 0..127 (ignorer le projecteur 200)
    df = df[(df["universe"] >= 0) & (df["universe"] <= 127)].copy()
    rows: List[MappingRow] = []
    for _, r in df.iterrows():
        rows.append((int(r["entity_start"]), int(r["entity_end"]), str(r["ip"]), int(r["universe"])))
    # Tri par entity_start pour des recherches plus propres
    rows.sort(key=lambda x: x[0])
    return rows

def run_router_all_bands(excel_path: str, listen_ip="0.0.0.0", listen_port=50000):
    mappings = load_all_from_excel(excel_path)
    print(f"🛰️ eHuB listening on {listen_ip}:{listen_port}")
    print(f"🗺️  Loaded {len(mappings)} mapping rows from Excel")

    # Prépare un sender par IP (on réutilise pour éviter de recréer des sockets)
    senders: Dict[str, ArtNetSender] = {}

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((listen_ip, listen_port))

    while True:
        data, addr = sock.recvfrom(65535)
        frame, err = parse_packet(data)
        if err:
            continue

        if isinstance(frame, ConfigFrame):
            # Info : la vraie reconstruction index→entity viendra plus tard si besoin
            print(f"🧩 CONFIG u={frame.universe} ranges={len(frame.ranges)}")
            continue

        if isinstance(frame, UpdateFrame):
            # Buffers DMX par (ip, universe)
            dmx_by_target: Dict[Tuple[str,int], bytearray] = {}

            # Parcours des entités reçues
            for (eid, r, g, b, w) in frame.entities:
                # Trouver la/les plages qui contiennent eid (normalement 1 seule)
                # (Approche simple O(n); suffisant pour démarrer. On optimisera après.)
                for (start, end, ip, uni) in mappings:
                    if start <= eid <= end:
                        key = (ip, uni)
                        if key not in dmx_by_target:
                            dmx_by_target[key] = bytearray(512)  # 512 canaux DMX
                        dmx = dmx_by_target[key]
                        idx = eid - start      # index 0-based dans cette plage
                        ch = idx * 3           # 3 canaux/entité (R,G,B)
                        if ch + 2 < 512:
                            dmx[ch+0] = r
                            dmx[ch+1] = g
                            dmx[ch+2] = b
                        break  # eid mappé → passe à l'entité suivante

            # Envoi ArtNet pour tous les univers touchés
            for (ip, uni), dmx in dmx_by_target.items():
                if ip not in senders:
                    senders[ip] = ArtNetSender(ip)
                senders[ip].send_dmx(uni, dmx)

            if dmx_by_target:
                touched = ", ".join([f"{ip}/u{uni}" for (ip, uni) in dmx_by_target.keys()])
                print(f"📦 UPDATE → {touched} (entities={len(frame.entities)})")
