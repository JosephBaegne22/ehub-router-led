# receiver/router_one_band_cli.py
import argparse
from router_one_band import run_router_one_band

def main():
    ap = argparse.ArgumentParser(description="Route ONE band from Excel to LEDs")
    ap.add_argument("--excel", default="faker/Ecran (2).xlsx", help="Chemin vers l'Excel")
    ap.add_argument("--universe", type=int, default=0, help="Univers Art-Net (ligne Excel) à router")
    ap.add_argument("--listen_ip", default="0.0.0.0")
    ap.add_argument("--listen_port", type=int, default=50000)
    args = ap.parse_args()
    run_router_one_band(args.excel, args.universe, args.listen_ip, args.listen_port)

if __name__ == "__main__":
    main()
