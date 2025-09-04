# faker/send_config.py
from ehub_proto import pack_config, send_udp

if __name__ == "__main__":
    # deux plages d’exemple
    ranges = [
        (0,   100,  169,  269),
        (170, 300,  259,  389),
    ]
    pkt = pack_config(universe=0, ranges=ranges)
    send_udp(pkt, "127.0.0.1", 50000)
    print("📡 sent CONFIG with 2 ranges")
