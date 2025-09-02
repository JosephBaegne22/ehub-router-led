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

def hsv_to_rgb(h, s, v):
    i = int(h*6)
    f = h*6 - i
    p = int(255*v*(1 - s))
    q = int(255*v*(1 - f*s))
    t = int(255*v*(1 - (1 - f)*s))
    v = int(255*v)
    i %= 6
    if i == 0: return v, t, p
    if i == 1: return q, v, p
    if i == 2: return p, v, t
    if i == 3: return p, q, v
    if i == 4: return t, p, v
    if i == 5: return v, p, q

def build_plasma(columns: List[List[int]], t: float) -> List[Tuple[int,int,int,int,int]]:
    ents = []
    for x in range(128):
        col = columns[x]
        for y in range(128):
            eid = col[y]
            # effet plasma combinant sin/cos pour chaque LED
            h = (math.sin(x*0.1 + t) + math.cos(y*0.15 + t) + math.sin((x+y)*0.05 + t))/4 + 0.5
            rgb = hsv_to_rgb(h % 1.0, 1.0, 0.9)
            ents.append((eid, *rgb, 0))
    return ents

def play_plasma(excel: str, host: str, port: str, seconds: float, fps: float):
    import pandas as pd
    df = pd.read_excel(excel, sheet_name="eHuB")
    columns = []
    for x in range(128):
        columns.append(list(range(x*128, x*128+128))) 

    dt = 1.0 / fps
    t0 = time.time()
    while time.time() - t0 < seconds:
        t = time.time() - t0
        ents = build_plasma(columns, t)
        u = 0
        for chunk in chunked(ents, 3000):
            pkt = pack_update(u, chunk)
            send_udp(pkt, host, int(port))
            u += 1
        time.sleep(dt)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--excel", required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", default="50000")
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--fps", type=float, default=30.0)
    args = ap.parse_args()
    play_plasma(args.excel, args.host, args.port, args.seconds, args.fps)