# faker/animator_cli.py
import argparse
from animator import run_animation

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Animations eHuB (blink/chase/wave/gradient)")
    ap.add_argument("--mode", choices=["blink","chase","wave","gradient","solid"], default="blink")
    ap.add_argument("--excel", default="faker/Ecran (2).xlsx")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=50000)
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--color1", default="255,0,0", help="R,G,B (ex: 255,0,0)")
    ap.add_argument("--color2", default="0,0,255", help="R,G,B (ex: 0,0,255) pour gradient/blink")
    ap.add_argument("--speed", type=float, default=1.0, help="vitesse de l’animation")
    args = ap.parse_args()

    run_animation(args.mode, args.excel, args.host, args.port,
                  args.seconds, args.fps, args.color1, args.color2, args.speed)
