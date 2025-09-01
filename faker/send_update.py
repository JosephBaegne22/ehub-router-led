# faker/send_update.py
import struct, gzip, socket

MAGIC = b"eHuB"

def pack_update(universe: int, entities):
    """
    entities = list of tuples (entity_id, r, g, b, w), 0..255
    """
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

if __name__ == "__main__":
    # 4 entités de test : (id, R, G, B, W)
    ents = [
        (100, 255, 0,   0,   0),  # rouge
        (101, 0,   255, 0,   0),  # vert
        (102, 0,   0,   255, 0),  # bleu
        (103, 255, 255, 0,   0),  # jaune
    ]
    pkt = pack_update(universe=0, entities=ents)
    send_udp(pkt, "127.0.0.1", 50000)
    print("📡 sent one UPDATE with 4 entities")
