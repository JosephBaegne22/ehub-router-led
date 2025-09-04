import socket

ARTNET_PORT = 6454

class ArtNetSender:
    def __init__(self, target_ip: str, port: int = ARTNET_PORT):
        self.addr = (target_ip, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sequence = 0  # peut rester à 0 si non utilisé

    def _build_header(self, universe: int, length: int = 512) -> bytearray:
        """
        Construit l'entête Art-Net OpDmx (0x5000).
        Universe est codé LSB puis MSB (SubUni, Net).
        Length est big-endian.
        """
        pb = bytearray(b'Art-Net\x00')          # ID
        pb += bytearray([0x00, 0x50])           # OpOutput/OpDmx (LE: 0x5000)
        pb += bytearray([0x00, 0x0E])           # ProtVer 14
        pb += bytearray([self.sequence & 0xFF]) # Sequence
        pb += bytearray([0x00])                 # Physical
        pb += bytearray([universe & 0xFF, (universe >> 8) & 0xFF])  # SubUni, Net
        pb += bytearray([(length >> 8) & 0xFF, length & 0xFF])      # Length (big-endian)
        return pb

    def send_dmx(self, universe: int, dmx512: bytes):
        """
        Envoie un paquet DMX512 (512 octets) sur l'univers donné.
        """
        if len(dmx512) != 512:
            raise ValueError("Le payload DMX doit faire exactement 512 octets.")
        pkt = self._build_header(universe, 512) + dmx512
        try:
            self.sock.sendto(pkt, self.addr)
        except Exception as e:
            print(f"❌ Erreur sendto: {e}")
        self.sequence = (self.sequence + 1) % 256

    def close(self):
        try:
            self.sock.close()
        except:
            pass
