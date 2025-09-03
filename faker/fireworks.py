import struct, gzip, socket, time, random, math
from typing import List, Tuple

MAGIC = b"eHuB"

# ---------------- Helpers eHuB ----------------
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

class Spark:
    __slots__ = ("x","y","vx","vy","r","g","b","ttl")
    def __init__(self, x, y, vx, vy, r, g, b, ttl):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.r, self.g, self.b = r, g, b
        self.ttl = ttl 

class Firework:
    def __init__(self, start_x, start_y, color):
        self.x = start_x
        self.y = start_y
        self.vy = -0.8 - random.random()*0.5 
        self.exploded = False
        self.sparks: List[Spark] = []
        self.color = color

    def update(self, dt):
        ents: List[Tuple[int,int,int,int,int]] = []
        if not self.exploded:
            self.y += self.vy * dt * 30
            if self.vy + dt*0.05 >= 0 or self.y < 30:
                # explosion
                self.exploded = True
                for _ in range(random.randint(30, 60)):
                    angle = random.uniform(0, 2*math.pi)
                    speed = random.uniform(0.5, 2.5)
                    r = random.randint(128, 255)
                    g = random.randint(128, 255)
                    b = random.randint(128, 255)
                    ttl = random.uniform(0.5, 1.5)
                    self.sparks.append(Spark(self.x, self.y, math.cos(angle)*speed, math.sin(angle)*speed, r, g, b, ttl))
            else:
                ents.append((int(self.x), int(abs(self.y)), self.color[0], self.color[1], self.color[2], 0))
        else:
            for spark in self.sparks:
                if spark.ttl <= 0:
                    continue
                spark.x += spark.vx * dt * 30
                spark.y += spark.vy * dt * 30
                spark.vy += 0.05 * dt * 30 
                spark.ttl -= dt
                ents.append((int(spark.x), int(abs(spark.y)), spark.r, spark.g, spark.b, 0))
        return ents

def play_fireworks(excel: str, host: str, port: int, seconds: float, fps: float):
    import pandas as pd
    columns = [[x*128 + y for y in range(128)] for x in range(128)]

    fireworks: List[Firework] = []
    t0 = time.time()
    dt = 1.0 / fps
    frame_count = 0

    while time.time() - t0 < seconds:
        ents: List[Tuple[int,int,int,int,int]] = []

        if random.random() < 0.05:
            x = random.randint(20, 108)
            color = (random.randint(128,255), random.randint(128,255), random.randint(128,255))
            fireworks.append(Firework(x, 127, color))

        for fw in fireworks:
            ents += fw.update(dt)

        u = 0
        for chunk in chunked(ents, 3000):
            pkt = pack_update(u, chunk)
            send_udp(pkt, host, int(port))
            u += 1

        frame_count += 1
        # log chaque frame pour WebUI
        print(f"[FIREWORK] Frame {frame_count}, Sparks={len(ents)}", flush=True)
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

    play_fireworks(args.excel, args.host, args.port, args.seconds, args.fps)