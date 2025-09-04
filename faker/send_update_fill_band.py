# faker/send_update_fill_band.py
import argparse, struct, gzip, socket, pandas as pd

MAGIC = b"eHuB"

def pack_update(universe: int, entities):
    payload = bytearray()
    for eid, r, g, b, w in entities:
        payload += struct.pack("<HBBBB", eid, r, g, b, w)
    comp = gzip.compress(bytes(payload))
    header = bytearray()
    header += MAGIC
    header += bytes([2])                    # type UPDATE
    header += bytes([universe & 0xFF])      # eHuB universe (1 byte)
    header += struct.pack("<H", len(entities))
    header += struct.pack("<H", len(comp))
    return bytes(header) + comp

def send_udp(packet: bytes, host="127.0.0.1", port=50000):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet, (host, port))

def load_band_range(xlsx_path: str, universe: int):
    df = pd.read_excel(xlsx_path, sheet_name="eHuB")
    df = df.rename(columns={
        "Entity Start": "entity_start",
        "Entity End": "entity_end",
        "ArtNet IP": "ip",
        "ArtNet Universe": "universe",
        "Name": "name",
    })
    row = df[df["universe"] == universe].head(1)
    if row.empty:
        raise ValueError(f"Aucune ligne Excel pour l'univers {universe}")
    r = row.iloc[0]
    return int(r["entity_start"]), int(r["entity_end"])

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Send UPDATE filling one band from Excel")
    ap.add_argument("--excel", default="faker/Ecran (2).xlsx")
    ap.add_argument("--universe", type=int, default=0)
    ap.add_argument("--color", default="0,0,255")  # bleu
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=50000)
    args = ap.parse_args()

    r, g, b = [max(0, min(255, int(x))) for x in args.color.split(",")]
    start_eid, end_eid = load_band_range(args.excel, args.universe)
    entities = [(eid, r, g, b, 0) for eid in range(start_eid, end_eid + 1)]

    pkt = pack_update(universe=0, entities=entities)  # eHuB universe 0 dans notre pipeline
    send_udp(pkt, args.host, args.port)
    print(f"📡 sent UPDATE filling band [{start_eid}..{end_eid}] with RGB=({r},{g},{b})")
