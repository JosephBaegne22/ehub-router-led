# faker/snake_player_cli.py
import argparse
from snake_player import run_snake

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Snake 32x32 pour mur 128x128 (flèches clavier)")
    ap.add_argument("--excel", default="faker/Ecran (2).xlsx")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=50000)
    ap.add_argument("--tick", type=float, default=8.0, help="vitesse de jeu (ticks/sec)")
    ap.add_argument("--seed", type=int, default=1234)
    args = ap.parse_args()

    run_snake(excel=args.excel, host=args.host, port=args.port,
              tick_hz=args.tick, seed=args.seed)
