# receiver/router_all_bands_stable_cli.py
import argparse
from router_all_bands_stable import run_router_all_bands_stable

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Stable router (holds last state at fixed FPS)")
    ap.add_argument("--excel", default="faker/Ecran (2).xlsx")
    ap.add_argument("--fps", type=float, default=40.0)
    ap.add_argument("--listen_ip", default="0.0.0.0")
    ap.add_argument("--listen_port", type=int, default=50000)
    args = ap.parse_args()
    run_router_all_bands_stable(args.excel, args.listen_ip, args.listen_port, args.fps)
