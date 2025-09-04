# faker/send_update_fill_all_5s.py
import argparse, struct, gzip, socket, pandas as pd, time

MAGIC = b"eHuB"

def pack_update(universe: int, entities):
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

def load_all_entities(xlsx_path: str):
    df = pd.read_excel(xlsx_path, sheet_name="eHuB")
    df = df.rename(columns={
        "Entity Start": "entity_start",
        "Entity End": "entity_end",
        "ArtNet IP": "ip",
        "ArtNet Universe": "universe",
        "Name": "name",
    })
    df = df[(df["universe"] >= 0) & (df["universe"] <= 127)].copy()
    entities = []
    for _, r in df.iterrows():
        a, b = int(r["entity_start"]), int(r["entity_end"])
        if a <= b:
            rng = range(a, b+1)
        else:
            rng = range(b, a+1)
        entities.extend(rng)
    return sorted(set(entities))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Send UPDATE filling ALL entities for N seconds")
    ap.add_argument("--excel", default="faker/Ecran (2).xlsx")
    ap.add_argument("--color", default="0,0,255")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=50000)
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--fps", type=float, default=20.0)
    args = ap.parse_args()

    r, g, b = [max(0, min(255, int(x))) for x in args.color.split(",")]
    ent_ids = load_all_entities(args.excel)
    ents = [(eid, r, g, b, 0) for eid in ent_ids]
    pkt = pack_update(universe=0, entities=ents)

    dt = 1.0 / args.fps
    t_end = time.time() + args.seconds
    print(f"📡 sending RGB=({r},{g},{b}) for {args.seconds}s at {args.fps} fps (entities={len(ents)})")
    while time.time() < t_end:
        send_udp(pkt, args.host, args.port)
        time.sleep(dt)
    print("✅ done")
