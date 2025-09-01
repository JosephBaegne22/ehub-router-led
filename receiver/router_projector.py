# receiver/router_projector.py
import socket
import sys
from typing import Optional, Tuple

# permettre d'importer artnet/artnet.py depuis ../artnet
import os
HERE = os.path.dirname(__file__)
ARTNET_DIR = os.path.abspath(os.path.join(HERE, "..", "artnet"))
if ARTNET_DIR not in sys.path:
    sys.path.insert(0, ARTNET_DIR)

from parser import parse_packet, UpdateFrame, ConfigFrame  # réutilise ton parser existant
from artnet import ArtNetSender

PROJECTOR_IP = "192.168.1.45"
PROJECTOR_UNIVERSE = 200  # le projecteur écoute ici, ch 1–3 = R,G,B

def run_router_projector(listen_ip: str = "0.0.0.0", listen_port: int = 50000):
    # socket UDP eHuB
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((listen_ip, listen_port))
    print(f"🛰️ eHuB listening on {listen_ip}:{listen_port}")

    # ArtNet vers projecteur
    sender = ArtNetSender(PROJECTOR_IP)
    print(f"🎯 ArtNet target: {PROJECTOR_IP} universe {PROJECTOR_UNIVERSE} (ch 1–3)")

    while True:
        data, addr = sock.recvfrom(65535)
        frame, err = parse_packet(data)
        if err:
            # on ignore ce qui n'est pas eHuB
            continue

        if isinstance(frame, ConfigFrame):
            # info utile pour debug
            print(f"🧩 CONFIG u={frame.universe} ranges={len(frame.ranges)}")
            continue

        if isinstance(frame, UpdateFrame):
            # prendre la 1ʳᵉ entité seulement (test simple)
            if not frame.entities:
                continue
            eid, r, g, b, w = frame.entities[0]

            # fabriquer un DMX512 avec ch1=R, ch2=G, ch3=B
            dmx = bytearray(512)
            dmx[0] = r
            dmx[1] = g
            dmx[2] = b

            # envoyer au projecteur
            sender.send_dmx(PROJECTOR_UNIVERSE, dmx)
            print(f"📦 UPDATE → Projecteur: entity {eid} RGB=({r},{g},{b})")
