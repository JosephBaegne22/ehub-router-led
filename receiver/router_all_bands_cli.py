# receiver/router_all_bands_cli.py
import argparse
from router_all_bands import run_router_all_bands

def main():
    ap = argparse.ArgumentParser(description="Route ALL bands from Excel to LEDs")
    ap.add_argument("--excel", default="faker/Ecran (2).xlsx")
    ap.add_argument("--listen_ip", default="0.0.0.0")
    ap.add_argument("--listen_port", type=int, default=50000)
    args = ap.parse_args()
    run_router_all_bands(args.excel, args.listen_ip, args.listen_port)

if __name__ == "__main__":
    main()
