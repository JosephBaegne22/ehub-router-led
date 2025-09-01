# receiver/artnet_monitor.py
import socket
from typing import Tuple

ARTNET_PORT = 6454
ARTNET_ID = b"Art-Net\x00"
OP_OUTPUT = 0x5000  # OpDmx

def _u16le(b: bytes) -> int:
    return b[0] | (b[1] << 8)

def parse_artnet_packet(pkt: bytes) -> Tuple[int, int, bytes] | None:
    """
    Retourne (universe, length, dmx_payload) si paquet OpDmx valide, sinon None.
    Format (RFC Art-Net 4):
      0..7   : "Art-Net\0"
      8..9   : OpCode (little-endian) = 0x5000 (OpDmx)
     10..11  : ProtVer (big-endian)   (>=14 typiquement)
     12      : Sequence
     13      : Physical
     14      : SubUni (LSB)
     15      : Net (MSB)
     16..17  : Length (big-endian)
     18..    : DMX data (length octets)
    """
    if len(pkt) < 18 or pkt[:8] != ARTNET_ID:
        return None
    opcode = _u16le(pkt[8:10])
    if opcode != OP_OUTPUT:
        return None
    # ProtVer = pkt[10:12] (BE) — peu critique ici
    subuni = pkt[14]
    net = pkt[15]
    length = (pkt[16] << 8) | pkt[17]
    if length < 0 or length > 512:
        return None
    if len(pkt) < 18 + length:
        return None
    dmx = pkt[18:18+length]
    # Universe complet = Net<<8 | SubUni (convention Art-Net)
    universe = (net << 8) | subuni
    return (universe, length, dmx)

def run_artnet_monitor(host: str = "0.0.0.0", port: int = ARTNET_PORT,
                       show_channels: int = 12, only_universe: int | None = None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"👂 ArtNet monitor listening on {host}:{port} (OpDmx)")
    print(f"   Affiche les {show_channels} premiers canaux. Filtre univers: "
          f"{only_universe if only_universe is not None else 'aucun'}")

    while True:
        data, addr = sock.recvfrom(65535)
        res = parse_artnet_packet(data)
        if not res:
            continue
        universe, length, dmx = res
        if only_universe is not None and universe != only_universe:
            continue
        n = max(1, min(show_channels, len(dmx)))
        preview = " ".join(f"{v:3d}" for v in dmx[:n])
        print(f"u{universe:03d} from {addr[0]} len={length}  ch1..{n}: {preview}")
