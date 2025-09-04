# faker/send_raw.py
import socket

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    payload = b"hello"
    sock.sendto(payload, ("127.0.0.1", 50000))
    print("📡 sent 'hello' to 127.0.0.1:50000")

if __name__ == "__main__":
    main()
