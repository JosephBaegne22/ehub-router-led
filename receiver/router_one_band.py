# receiver/router_one_band.py
import os, sys, socket
from typing import Tuple

# importer artnet/artnet.py
HERE = os.path.dirname(__file__)
ARTNET_DIR = os.path.abspath(os.path.join(HERE, "..", "artnet"))
if ARTNET_DIR not in sys.path:
    sys.path.insert(0, ARTNET_DIR)

from parser import parse_packet, UpdateFrame, ConfigFrame
from artnet import ArtNetSender
from config_loader import load_band_from_excel

def run_router_one_band(excel_path: str, target_universe: int, listen_ip="0.0.0.0", listen_port=50000):
    # Charger la ligne de mapping pour l'univers choisi
    band = load_band_from_excel(excel_path, target_universe)
    e_start = band["entity_start"]
    e_end   = band["entity_end"]
    out_ip  = band["ip"]
    out_uni = band["universe"]
    name    = band["name"]

    print(f"🛰️ eHuB listening on {listen_ip}:{listen_port}")
    print(f"🎯 Routing ONE band: {name} | entities [{e_start}..{e_end}] "
          f"→ {out_ip} (universe {out_uni}) channels 1..")

    # Sockets
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((listen_ip, listen_port))

    sender = ArtNetSender(out_ip)

    while True:
        data, addr = sock.recvfrom(65535)
        frame, err = parse_packet(data)
        if err: 
            continue

        if isinstance(frame, ConfigFrame):
            # Info : on l'ignore pour le routage mono-bande V1
            print(f"🧩 CONFIG u={frame.universe} ranges={len(frame.ranges)}")
            continue

        if isinstance(frame, UpdateFrame):
            # Construire un DMX512 en RGB, start_channel = 1
            dmx = bytearray(512)
            # Pour chaque entité reçue, si elle est dans [e_start..e_end], on mappe
            for (eid, r, g, b, w) in frame.entities:
                if e_start <= eid <= e_end:
                    idx = eid - e_start  # index 0-based dans la bande
                    ch = idx * 3         # 3 canaux par entité (R,G,B)
                    if ch + 2 < 512:
                        dmx[ch + 0] = r
                        dmx[ch + 1] = g
                        dmx[ch + 2] = b
            # Envoi ArtNet
            sender.send_dmx(out_uni, dmx)
            # Log léger (toutes les ~20 updates si besoin : ici on affiche un bref message)
            print(f"📦 UPDATE → {out_ip}/u{out_uni} (mapped entities in {e_start}..{e_end})")
