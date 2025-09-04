# faker/ehub_proto.py
import struct, gzip, socket

MAGIC = b"eHuB"

def pack_config(universe: int, ranges):
    payload = bytearray()
    for s_idx, s_eid, e_idx, e_eid in ranges:
        payload += struct.pack("<HHHH", s_idx, s_eid, e_idx, e_eid)
    comp = gzip.compress(bytes(payload))

    header = bytearray()
    header += MAGIC
    header += struct.pack("B", 1)               # type CONFIG
    header += struct.pack("B", universe & 0xFF)
    header += struct.pack("<H", len(ranges))
    header += struct.pack("<H", len(comp))
    return bytes(header) + comp

def send_udp(packet: bytes, host="127.0.0.1", port=50000):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet, (host, port))
