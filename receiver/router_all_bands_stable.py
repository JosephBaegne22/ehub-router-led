# receiver/router_all_bands_stable.py
import os, sys, socket, threading, time
from typing import Dict, Tuple, List
import pandas as pd

# Import artnet
HERE = os.path.dirname(__file__)
ARTNET_DIR = os.path.abspath(os.path.join(HERE, "..", "artnet"))
if ARTNET_DIR not in sys.path:
    sys.path.insert(0, ARTNET_DIR)

from parser import parse_packet, UpdateFrame, ConfigFrame
from artnet import ArtNetSender

Target = Tuple[str, int]  # (ip, universe)

class StableRouter:
    def __init__(self, excel_path: str, listen_ip="0.0.0.0", listen_port=50000, send_fps=40.0):
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.send_interval = 1.0 / max(1e-3, send_fps)

        # Charge Excel et prépare l'index compacté (PAS de ch = (eid-start)*3)
        self.row_entities: Dict[Target, List[int]] = {}   # pour chaque (ip,uni) : [eid0,eid1,...] compactés
        self.targets: List[Target] = []
        self._build_compact_index(excel_path)

        # Dernier état DMX pour chaque cible
        self.dmx_by_target: Dict[Target, bytearray] = {t: bytearray(512) for t in self.targets}
        self._lock = threading.Lock()

        # ArtNet senders (un par IP)
        self.senders: Dict[str, ArtNetSender] = {}

    def _build_compact_index(self, excel_path: str):
        df = pd.read_excel(excel_path, sheet_name="eHuB")
        df = df.rename(columns={
            "Entity Start": "entity_start",
            "Entity End": "entity_end",
            "ArtNet IP": "ip",
            "ArtNet Universe": "universe",
            "Name": "name",
        })
        # garder seulement les univers 0..127 (LEDs), ignorer 200 (projecteur)
        df = df[(df["universe"] >= 0) & (df["universe"] <= 127)].copy()
        # IMPORTANT : on construit une liste COMPACTE d'entités par ligne (0,1,2,...)
        for _, r in df.iterrows():
            a, b = int(r["entity_start"]), int(r["entity_end"])
            ip, uni = str(r["ip"]), int(r["universe"])
            target: Target = (ip, uni)

            # si start > end, on corrige, puis on crée la plage CONTIGUË
            if a <= b:
                ids = list(range(a, b + 1))
            else:
                ids = list(range(b, a + 1))

            self.row_entities[target] = ids
            self.targets.append(target)

        # dédoublonner l’ordre des cibles
        self.targets = sorted(list(set(self.targets)), key=lambda t: (t[0], t[1]))
        print(f"🗺️  Index prêt : {len(self.targets)} univers, compactage par ligne Excel activé.")

    def _receiver_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.listen_ip, self.listen_port))
        print(f"🛰️ eHuB listening on {self.listen_ip}:{self.listen_port}")
        while True:
            data, addr = sock.recvfrom(65535)
            frame, err = parse_packet(data)
            if err:
                continue
            if isinstance(frame, ConfigFrame):
                # info utile
                print(f"🧩 CONFIG u={frame.universe} ranges={len(frame.ranges)}")
                continue
            if isinstance(frame, UpdateFrame):
                # applique les valeurs dans les buffers, en COMPACTANT par position
                with self._lock:
                    # on crée un lookup rapide : pour chaque target, dict eid->position
                    # (optimisable en pré-calcul, mais suffisant pour démarrer)
                    pos_cache: Dict[Target, Dict[int, int]] = {}
                    for target, ids in self.row_entities.items():
                        pos_cache[target] = {eid: i for i, eid in enumerate(ids)}

                    for (eid, r, g, b, w) in frame.entities:
                        for target, pos_map in pos_cache.items():
                            pos = pos_map.get(eid)
                            if pos is None:
                                continue
                            dmx = self.dmx_by_target[target]
                            ch = pos * 3  # RGB compacté
                            if ch + 2 < 512:
                                dmx[ch+0] = r
                                dmx[ch+1] = g
                                dmx[ch+2] = b
                    # pas d’envoi ici → l’envoi régulier est fait dans le sender_loop

    def _sender_loop(self):
        # ré-émettre EN CONTINU le dernier état (anti-flicker)
        while True:
            t0 = time.time()
            with self._lock:
                for (ip, uni), dmx in self.dmx_by_target.items():
                    if ip not in self.senders:
                        self.senders[ip] = ArtNetSender(ip)
                    self.senders[ip].send_dmx(uni, dmx)
            dt = self.send_interval - (time.time() - t0)
            if dt > 0:
                time.sleep(dt)

    def run(self):
        rx = threading.Thread(target=self._receiver_loop, daemon=True)
        tx = threading.Thread(target=self._sender_loop, daemon=True)
        rx.start()
        tx.start()
        print(f"🚀 stable send @ {1.0/self.send_interval:.1f} fps — maintien d’état activé (anti-flicker).")
        rx.join(); tx.join()

def run_router_all_bands_stable(excel_path: str, listen_ip="0.0.0.0", listen_port=50000, send_fps=40.0):
    router = StableRouter(excel_path, listen_ip, listen_port, send_fps)
    router.run()
