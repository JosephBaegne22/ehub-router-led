# faker/send_update_color.py
import argparse
import struct, gzip, socket

MAGIC = b"eHuB"

def pack_update(universe: int, entities):
    payload = bytearray()
    for eid, r, g, b, w in entities:
        payload += struct.pack("<HBBBB", eid, r, g, b, w)
    comp = gzip.compress(bytes(payload))
    header = bytearray()
    header += MAGIC
    header += bytes([2])                    # type UPDATE
    header += bytes([universe & 0xFF])      # eHuB universe (1 octet)
    header += struct.pack("<H", len(entities))
    header += struct.pack("<H", len(comp))
    return bytes(header) + comp

def send_udp(packet: bytes, host="127.0.0.1", port=50000):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet, (host, port))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Send one UPDATE with a single entity/color")
    ap.add_argument("--eid", type=int, default=100, help="entity id")
    ap.add_argument("--color", default="255,0,0", help="R,G,B (0..255)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=50000)
    args = ap.parse_args()

    r, g, b = [max(0, min(255, int(x))) for x in args.color.split(",")]
    ents = [(args.eid, r, g, b, 0)]
    pkt = pack_update(universe=0, entities=ents)
    send_udp(pkt, args.host, args.port)
    print(f"📡 sent UPDATE: eid={args.eid} RGB=({r},{g},{b}) to {args.host}:{args.port}")
