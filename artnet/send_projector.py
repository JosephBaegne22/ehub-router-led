import argparse
import time
from artnet import ArtNetSender

def parse_rgb(s: str):
    parts = [int(x) for x in s.split(",")]
    if len(parts) != 3:
        raise ValueError("Utilise R,G,B (ex: 255,0,0)")
    return tuple(max(0, min(255, v)) for v in parts)

def main():
    ap = argparse.ArgumentParser(
        description="Envoie une couleur unie au projecteur (univers 200, canaux 1–3)"
    )
    ap.add_argument("--ip", default="192.168.1.45",
                    help="IP du contrôleur (le projecteur est sur .45)")
    ap.add_argument("--universe", type=int, default=200,
                    help="Univers Art-Net du projecteur (défaut 200)")
    ap.add_argument("--color", default="0,255,0",
                    help="R,G,B (0..255). Exemple: 255,0,0 pour rouge")
    ap.add_argument("--seconds", type=float, default=3.0,
                    help="Durée d'envoi pour fiabiliser (en secondes)")
    ap.add_argument("--fps", type=float, default=10.0,
                    help="Fréquence d'envoi (images/s)")
    args = ap.parse_args()

    r, g, b = parse_rgb(args.color)

    # DMX512 = 512 octets. On utilise CH1=R, CH2=G, CH3=B pour le projecteur.
    dmx = bytearray(512)
    dmx[0] = r
    dmx[1] = g
    dmx[2] = b

    sender = ArtNetSender(args.ip)
    dt = 1.0 / max(args.fps, 1e-3)
    t_end = time.time() + max(0.1, args.seconds)

    print(f"🎯 Envoi RGB({r},{g},{b}) → {args.ip} univers {args.universe} "
          f"sur canaux 1–3 pendant {args.seconds}s @ {args.fps} fps")
    try:
        while time.time() < t_end:
            sender.send_dmx(args.universe, dmx)
            time.sleep(dt)
    except KeyboardInterrupt:
        pass
    finally:
        sender.close()
        print("✅ Terminé")

if __name__ == "__main__":
    main()
