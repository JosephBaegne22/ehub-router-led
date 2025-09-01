import socket
from parser import parse_packet, ConfigFrame, UpdateFrame

def run_receiver(host="0.0.0.0", port=50000):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"🛰️ listening on {host}:{port}")
    while True:
        data, addr = sock.recvfrom(65535)
        frame, err = parse_packet(data)
        if err:
            print(f"⚠️ from {addr} : {err} (len={len(data)})")
            continue

        if isinstance(frame, ConfigFrame):
            print(f"🧩 CONFIG u={frame.universe} ranges={len(frame.ranges)} ex={frame.ranges[:2]}")
        elif isinstance(frame, UpdateFrame):
            preview = ", ".join([f"{e[0]}:{e[1]},{e[2]},{e[3]}" for e in frame.entities[:5]])
            print(f"📦 UPDATE u={frame.universe} n={len(frame.entities)} first5={preview}")
