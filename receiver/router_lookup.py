# receiver/router_lookup.py
import os, sys, socket, threading, time
from typing import Dict, Tuple, List, Optional
import pandas as pd

# Import ArtNet + parser
HERE = os.path.dirname(__file__)
ARTNET_DIR = os.path.abspath(os.path.join(HERE, "..", "artnet"))
if ARTNET_DIR not in sys.path:
    sys.path.insert(0, ARTNET_DIR)

from parser import parse_packet, UpdateFrame, ConfigFrame
from artnet import ArtNetSender
from patch_map import load_patch_csv, apply_patch  # <-- patch-map

Target = Tuple[str, int]  # (ip, universe)

class LookupRouter:
    """
    Routeur eHuB → ArtNet avec:
      - table de correspondance entité → (IP, univers, offset DMX)
      - envoi continu à FPS fixe (anti-flicker)
      - DMX monitor optionnel
      - patch-map optionnel (duplication/reroutage de canaux)
    """
    def __init__(
        self,
        excel_path: str,
        listen_ip: str = "0.0.0.0",
        listen_port: int = 50000,
        send_fps: float = 40.0,
        order: str = "RGB",
        monitor_enabled: bool = False,
        monitor_every: int = 20,
        monitor_channels: int = 12,
    ):
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.dt = 1.0 / max(1e-3, send_fps)
        self.order = order.upper().strip()  # "RGB" ou "GRB"

        # ---- DMX monitor ----
        self.monitor_enabled = bool(monitor_enabled)
        self.monitor_every = max(1, int(monitor_every))          # afficher toutes les N frames
        self.monitor_channels = max(1, min(512, int(monitor_channels)))
        self._frame_count = 0

        # 1) lookup + buffers
        self.lookup: Dict[int, Tuple[Target, int]] = {}  # entity_id -> ((ip,univ), dmx_offset)
        self.targets: Dict[Target, bytearray] = {}       # (ip,univ) -> DMX512
        self.senders: Dict[str, ArtNetSender] = {}       # ip -> sender
        self._build_lookup_from_excel(excel_path)

        # 2) mutex
        self._lock = threading.Lock()

        # 3) patch-map (chargé via set_patch_table)
        self.patch_table = {}
        self._has_patch = False

    # ---------- Construction du lookup depuis l’Excel ----------
    def _build_lookup_from_excel(self, excel_path: str):
        """
        Lecture feuille eHuB → mapping direct entité->(ip,univ,offset DMX).
        Hypothèse LAPS:
          - chaque bande physique = 2 univers consécutifs (U, U+1)
          - 1 ligne Excel par univers (entity_start..entity_end)
        On concatène les entités des 2 univers d'une bande, puis on SPLIT:
          indices 0..169  -> univers U,   offsets DMX 0..(170*3-1)
          indices 170..   -> univers U+1, offsets DMX 0..((len-170)*3-1)
        """
        df = pd.read_excel(excel_path, sheet_name="eHuB")
        df = df.rename(columns={
            "Entity Start": "entity_start",
            "Entity End": "entity_end",
            "ArtNet IP": "ip",
            "ArtNet Universe": "universe",
            "Name": "name",
        })
        # garder les univers LEDs 0..127 (ignorer 200 = projecteur)
        df = df[(df["universe"] >= 0) & (df["universe"] <= 127)].copy()
        df = df.sort_values(["ip", "universe"]).reset_index(drop=True)

        def ensure_target(ip: str, uni: int):
            key = (ip, uni)
            if key not in self.targets:
                self.targets[key] = bytearray(512)

        # grouper par IP et traiter par paires (U, U+1)
        for ip, g in df.groupby("ip"):
            g = g.sort_values("universe")
            universes = list(g["universe"].astype(int))
            for u in universes:
                if u % 2 != 0:
                    continue
                rowA = g[g["universe"] == u]
                if rowA.empty:
                    continue
                rowA = rowA.iloc[0]

                rowB: Optional[pd.Series] = None
                if (u + 1) in universes:
                    rB = g[g["universe"] == (u + 1)]
                    if not rB.empty:
                        rowB = rB.iloc[0]

                # entités U
                a0, a1 = int(rowA["entity_start"]), int(rowA["entity_end"])
                listA = list(range(min(a0, a1), max(a0, a1) + 1))

                # entités U+1 (si présent)
                listB: List[int] = []
                if rowB is not None:
                    b0, b1 = int(rowB["entity_start"]), int(rowB["entity_end"])
                    listB = list(range(min(b0, b1), max(b0, b1) + 1))

                band_entities = listA + listB  # ~259 ids
                head = band_entities[:170]
                tail = band_entities[170:]

                ensure_target(ip, u)
                if tail:
                    ensure_target(ip, u + 1)

                # indexation compacte: offset = index*3 (3 canaux par LED)
                for idx, eid in enumerate(head):
                    self.lookup[eid] = ((ip, u), idx * 3)
                for idx, eid in enumerate(tail):
                    self.lookup[eid] = ((ip, u + 1), idx * 3)

        print(f"🗺️ lookup construit : {len(self.lookup)} entités, {len(self.targets)} univers DMX alloués.")

    # ---------- Patch-map ----------
    def set_patch_table(self, path: Optional[str]):
        self.patch_table = load_patch_csv(path)
        self._has_patch = bool(self.patch_table)
        if self._has_patch:
            rules = sum(len(v) for v in self.patch_table.values())
            print(f"🩹 Patch-map chargé ({rules} règle(s)).")

    # ---------- Application d'un UPDATE dans les buffers DMX ----------
    def _apply_update(self, ents: List[Tuple[int,int,int,int,int]]):
        order = self.order
        with self._lock:
            for (eid, r, g, b, w) in ents:
                hit = self.lookup.get(eid)
                if not hit:
                    continue
                (ip, uni), off = hit
                dmx = self.targets[(ip, uni)]
                if off + 2 >= 512:
                    continue
                if order == "RGB":
                    dmx[off+0] = r; dmx[off+1] = g; dmx[off+2] = b
                elif order == "GRB":
                    dmx[off+0] = g; dmx[off+1] = r; dmx[off+2] = b
                else:
                    dmx[off+0] = r; dmx[off+1] = g; dmx[off+2] = b

    # ---------- Thread de réception eHuB ----------
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
                print(f"🧩 CONFIG u={frame.universe} ranges={len(frame.ranges)}")
            elif isinstance(frame, UpdateFrame):
                self._apply_update(frame.entities)

    # ---------- Thread d'envoi ArtNet + DMX monitor ----------
    def _sender_loop(self):
        while True:
            t0 = time.time()
            self._frame_count += 1
            lines_to_print: List[str] = []

            with self._lock:
                for (ip, uni), dmx in self.targets.items():
                    # appliquer patch (si présent) avant envoi
                    buf = dmx
                    if self._has_patch:
                        buf = apply_patch(ip, uni, dmx, self.patch_table)

                    if ip not in self.senders:
                        self.senders[ip] = ArtNetSender(ip)
                    self.senders[ip].send_dmx(uni, buf)

                    # DMX monitor (aperçu)
                    if self.monitor_enabled and (self._frame_count % self.monitor_every == 0):
                        N = self.monitor_channels
                        head = buf[:N]
                        preview = " ".join(f"{v:3d}" for v in head)
                        lines_to_print.append(f"u{uni:03d}@{ip}  ch1..{N}: {preview}")

            if lines_to_print:
                print("🔎 DMX monitor:")
                for line in lines_to_print:
                    print("   " + line)

            dt = self.dt - (time.time() - t0)
            if dt > 0:
                time.sleep(dt)

    # ---------- Lancement ----------
    def run(self):
        rx = threading.Thread(target=self._receiver_loop, daemon=True)
        tx = threading.Thread(target=self._sender_loop, daemon=True)
        rx.start(); tx.start()
        print(f"🚀 maintien d’état @ {1.0/self.dt:.1f} fps — order={self.order}, monitor={'ON' if self.monitor_enabled else 'OFF'}")
        rx.join(); tx.join()


def run_router_lookup(
    excel_path: str,
    listen_ip: str = "0.0.0.0",
    listen_port: int = 50000,
    send_fps: float = 40.0,
    order: str = "RGB",
    monitor_enabled: bool = False,
    monitor_every: int = 20,
    monitor_channels: int = 12,
    patch_csv: Optional[str] = None,
):
    router = LookupRouter(
        excel_path,
        listen_ip,
        listen_port,
        send_fps,
        order,
        monitor_enabled=monitor_enabled,
        monitor_every=monitor_every,
        monitor_channels=monitor_channels,
    )
    router.set_patch_table(patch_csv)
    router.run()
