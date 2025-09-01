# faker/image_player_cli.py
import argparse
from image_player import stream_image_to_ehub

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Projeter une image 128x128 sur le mur via eHuB")
    ap.add_argument("--image", required=True, help="Chemin PNG/JPG (ex: assets/ryu.png)")
    ap.add_argument("--excel", default="faker/Ecran (2).xlsx")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=50000)
    ap.add_argument("--seconds", type=float, default=8.0)
    ap.add_argument("--fps", type=float, default=12.0)
    ap.add_argument("--brightness", type=float, default=0.7)
    ap.add_argument("--gamma", type=float, default=2.0)
    ap.add_argument("--fit", choices=["fit","cover"], default="cover")
    ap.add_argument("--flip-y", action="store_true", help="inverser verticalement si besoin")
    args = ap.parse_args()

    stream_image_to_ehub(
        img_path=args.image,
        excel=args.excel,
        host=args.host,
        port=args.port,
        seconds=args.seconds,
        fps=args.fps,
        brightness=args.brightness,
        gamma=args.gamma,
        fit_mode=args.fit,
        flip_y=args.flip_y
    )
