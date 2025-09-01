# receiver/artnet_monitor_cli.py
import argparse
from artnet_monitor import run_artnet_monitor

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="ArtNet (OpDmx) monitor")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=6454)
    ap.add_argument("--channels", type=int, default=12, help="Nb de canaux à afficher (début de trame)")
    ap.add_argument("--universe", type=int, help="Filtrer sur un univers (Net<<8|SubUni)", default=None)
    args = ap.parse_args()
    run_artnet_monitor(args.host, args.port, args.channels, args.universe)
