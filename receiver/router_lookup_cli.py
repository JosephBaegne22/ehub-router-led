# receiver/router_lookup_cli.py
import argparse
from router_lookup import run_router_lookup
from config_yaml import load_config

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="eHuB→ArtNet (lookup + continuous send) + DMX monitor + config + patch-map"
    )
    ap.add_argument("--config", help="Fichier config.yaml (optionnel)")
    ap.add_argument("--excel", help="Excel de mapping (écrase la config)")
    ap.add_argument("--fps", type=float, help="FPS d'envoi (écrase la config)")
    ap.add_argument("--order", choices=["RGB","GRB"], help="Ordre couleurs (écrase la config)")
    ap.add_argument("--listen_ip", help="IP locale eHuB (écrase la config)")
    ap.add_argument("--listen_port", type=int, help="Port eHuB (écrase la config)")
    ap.add_argument("--dmx-monitor", action="store_true", help="Active le moniteur DMX")
    ap.add_argument("--monitor-every", type=int, help="Afficher toutes les N frames")
    ap.add_argument("--monitor-channels", type=int, help="Nombre de canaux à afficher")
    ap.add_argument("--patch", help="patch.csv (optionnel)")
    args = ap.parse_args()

    cfg = load_config(args.config)

    # overrides CLI > config file
    if args.excel: cfg["excel"] = args.excel
    if args.fps is not None: cfg["fps"] = args.fps
    if args.order: cfg["order"] = args.order
    if args.listen_ip: cfg["listen_ip"] = args.listen_ip
    if args.listen_port is not None: cfg["listen_port"] = args.listen_port
    if args.dmx_monitor: cfg["dmx_monitor"] = True
    if args.monitor_every is not None: cfg["monitor_every"] = args.monitor_every
    if args.monitor_channels is not None: cfg["monitor_channels"] = args.monitor_channels
    if args.patch: cfg["patch_csv"] = args.patch

    run_router_lookup(
        cfg["excel"],
        cfg["listen_ip"],
        cfg["listen_port"],
        cfg["fps"],
        cfg["order"],
        monitor_enabled=cfg["dmx_monitor"],
        monitor_every=cfg["monitor_every"],
        monitor_channels=cfg["monitor_channels"],
        patch_csv=cfg["patch_csv"],
    )
