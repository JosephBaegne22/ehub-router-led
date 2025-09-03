import struct, gzip, socket, time, math
from typing import List, Tuple

MAGIC = b"eHuB"

def pack_update(universe: int, entities: List[Tuple[int,int,int,int,int]]) -> bytes:
    payload = bytearray()
    for eid, r, g, b, w in entities:
        payload += struct.pack("<HBBBB", eid, r, g, b, w)
    comp = gzip.compress(bytes(payload))
    header = bytearray()
    header += MAGIC
    header += bytes([2])
    header += bytes([universe & 0xFF])
    header += struct.pack("<H", len(entities))
    header += struct.pack("<H", len(comp))
    return bytes(header) + comp

def send_udp(packet: bytes, host="127.0.0.1", port=50000):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet, (host, port))

def chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

def lava_frame(t: float, width=128, height=128) -> List[Tuple[int,int,int,int,int]]:
    ents: List[Tuple[int,int,int,int,int]] = []
    for x in range(width):
        for y in range(height):
            flow = math.sin(x*0.15 + t*2) + math.cos(y*0.1 + t*1.5)
            v = max(0, min(1, (flow+2)/4))
            r = int(255 * v)
            g = int(80 * v)
            b = int(30 * v)
            eid = x*128 + y
            ents.append((eid, r, g, b, 0))
    return ents

def play_lava(excel: str, host: str, port: str, seconds: float, fps: float):
    dt = 1.0 / fps
    t0 = time.time()
    frame_count = 0
    while time.time() - t0 < seconds:
        t = time.time() - t0
        ents = lava_frame(t)

        u = 0
        for chunk in chunked(ents, 3000):
            pkt = pack_update(u, chunk)
            send_udp(pkt, host, int(port))
            u += 1

        frame_count += 1
        # log chaque frame pour WebUI
        print(f"[LAVA] Frame {frame_count}, t={t:.2f}, LEDs={len(ents)}", flush=True)
        time.sleep(dt)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--excel", default="faker/Ecran (2).xlsx")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", default="50000")
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--fps", type=float, default=25.0)
    args = ap.parse_args()

    play_lava(args.excel, args.host, args.port, args.seconds, args.fps)