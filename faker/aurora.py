import struct, gzip, socket, time, random, math
from typing import List, Tuple

MAGIC = b"eHuB"

def pack_update(universe: int, entities: List[Tuple[int,int,int,int,int]]) -> bytes:
    payload = bytearray()
    for eid, r, g, b, w in entities:
        payload += struct.pack("<HBBBB", eid, r, g, b, w)
    comp = gzip.compress(bytes(payload))
    header = bytearray()
    header += MAGIC
    header += bytes([2])  # UPDATE
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

class AuroraRibbon:
    def __init__(self, width=128, height=128):
        self.width = width
        self.height = height
        self.offsets = [random.uniform(0, 2*math.pi) for _ in range(width)]
        self.colors = [(random.randint(0,255), random.randint(100,255), random.randint(200,255)) for _ in range(width)]

    def frame(self, t: float) -> List[Tuple[int,int,int,int,int]]:
        ents: List[Tuple[int,int,int,int,int]] = []
        for x in range(self.width):
            base = math.sin(t + self.offsets[x])
            for y in range(self.height):
                brightness = max(0, math.sin((y/128.0 + base)*math.pi)) 
                r = min(255, int(self.colors[x][0] * brightness))
                g = min(255, int(self.colors[x][1] * brightness))
                b = min(255, int(self.colors[x][2] * brightness))
                eid = x*128 + y
                ents.append((eid, r, g, b, 0))
        return ents

def play_aurora(excel: str, host: str, port: int, seconds: float, fps: float):
    width = 128
    height = 128
    aurora = AuroraRibbon(width, height)
    dt = 1.0 / fps
    t0 = time.time()

    while time.time() - t0 < seconds:
        t = time.time() - t0
        ents = aurora.frame(t)

        u = 0
        for chunk in chunked(ents, 3000):
            pkt = pack_update(u, chunk)
            send_udp(pkt, host, int(port))
            u += 1

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

    play_aurora(args.excel, args.host, args.port, args.seconds, args.fps)