# 🎇 EHUB → ARTNET Router + LED Animations

Projet scolaire réalisé avec le **protocole eHuB** (Unity → LEDs), un **routeur Python** vers ArtNet/DMX (contrôleurs BC216), et une suite de **fakers/animations** pour tester un mur LED de 128×128.

---

## 🚀 Fonctionnalités

- Réception des paquets **eHuB** (`CONFIG` + `UPDATE`)
- Conversion en **ArtNet/DMX** avec lookup (Excel fourni)
- Anti-flicker (rafraîchissement continu @ FPS fixe)
- Moniteurs :
  - eHuB monitor (logs CONFIG)
  - DMX monitor (aperçu canaux envoyés)
  - ArtNet monitor (reçoit & affiche paquets OpDmx)
- Sauvegarde/chargement config (`config.yaml`)
- Patch-map (`patch.csv`) pour reroutage rapide
- Animations intégrées : `blink`, `wave`, `chase`, `gradient`, `solid`, `stars`
- Projection **d’images 128×128** (ex: `Ryu.png`)
- Interface **Web UI Flask** avec boutons pour lancer animations et images

---

## 📦 Installation

Cloner le projet et installer les dépendances :

```bash
git clone https://github.com/<ton-user>/ehub-router-led.git
cd ehub-router-led
pip install -r requirements.txt
Requirements
Python 3.10+ (testé sous Windows)

Modules : pandas, openpyxl, Flask, PyYAML, Pillow

⚙️ Arborescence
arduino
Copier le code
EHUB-ROUTER/
 ├── artnet/                  # envoi ArtNet
 ├── faker/                   # générateurs eHuB (animations, images, tests)
 │    ├── animator_cli.py
 │    ├── stars_player.py
 │    ├── image_player.py
 │    └── image_player_cli.py
 ├── receiver/                # routeur eHuB -> ArtNet
 │    ├── router_lookup.py
 │    ├── router_lookup_cli.py
 │    └── ...
 ├── webui/                   # interface web Flask
 │    ├── index.html
 │    └── server.py
 ├── assets/                  # images projetées (Ryu, Ken, Guile…)
 ├── config.yaml              # config routeur (FPS, monitor, patch…)
 ├── patch.csv                # reroutage rapide (optionnel)
 └── requirements.txt
🛰️ 1. Lancer le routeur
Basique :
bash
Copier le code
python receiver/router_lookup_cli.py --excel "faker/Ecran (2).xlsx" --fps 40
Avec DMX monitor :
bash
Copier le code
python receiver/router_lookup_cli.py --excel "faker/Ecran (2).xlsx" --fps 40 \
  --dmx-monitor --monitor-every 10 --monitor-channels 12
🎬 2. Tester des animations (faker)
Blink rouge ↔ bleu
bash
Copier le code
python faker/animator_cli.py --mode blink --seconds 10 --fps 25 \
  --color1 255,0,0 --color2 0,0,255
Chase (comète verte)
bash
Copier le code
python faker/animator_cli.py --mode chase --color1 0,255,0 --seconds 12 --fps 30
Wave (onde bleue)
bash
Copier le code
python faker/animator_cli.py --mode wave --color1 0,0,255 --seconds 12 --fps 30
Gradient rouge → bleu
bash
Copier le code
python faker/animator_cli.py --mode gradient --color1 255,0,0 --color2 0,0,255 --seconds 8
Ciel étoilé
bash
Copier le code
python faker/stars_player.py --seconds 20 --fps 20 --density 0.01 --bg 4,8,16
🖼️ 3. Projeter une image (ex: Ryu)
Placer l’image dans assets/ryu.png.

bash
Copier le code
python faker/image_player_cli.py --image assets/ryu.png --seconds 10 --fps 12 \
  --brightness 0.7 --gamma 2.0 --fit cover
Options utiles :

--flip-y si l’image est inversée

--brightness (0.5–0.9)

--gamma (1.6–2.2)

🌐 4. Interface Web UI
Lancer le serveur Flask :

bash
Copier le code
python webui/server.py
Ouvrir http://localhost:8000.

Boutons disponibles :
Animations : Blink, Wave, Chase, Gradient, Solid, Stars

Personnages : Ryu, Ken, Guile

STOP : arrête l’animation courante

📡 5. ArtNet monitor (E9)
Pour voir les paquets ArtNet reçus par ton PC :

bash
Copier le code
python receiver/artnet_monitor_cli.py --channels 12
⚠️ Pense à rediriger un univers vers l’IP de ton PC pour voir les paquets.

🔧 6. Patch-map (E8)
Exemple patch.csv :

csv
Copier le code
ip,universe,from_channel,to_channel
192.168.1.45,0,1,389
192.168.1.45,0,2,390
Active-le via config.yaml :

yaml
Copier le code
patch_csv: "patch.csv"
🧪 7. Scénario de test rapide
Connecte-toi au Wi-Fi GLASS_RESEAUX (mdp: networks)

Lance le routeur :

bash
Copier le code
python receiver/router_lookup_cli.py --excel "faker/Ecran (2).xlsx" --fps 40
Lance une animation :

bash
Copier le code
python faker/animator_cli.py --mode blink --seconds 5
👉 le mur doit clignoter rouge/bleu.

Lance l’UI :

bash
Copier le code
python webui/server.py
👉 clique sur Ryu → le visage s’affiche.

✨ Améliorations possibles
Transitions (fondu entre images/animations)

Ajout d’autres personnages

Logging DMX dans un fichier

UI améliorée (aperçu images, sliders de paramètres)

👥 Auteurs
Projet encadré par le Groupe LAPS (spécialistes lumière & son)

Développé par : [ton Joseph BAEGNE et Maxime Desrut/ Groupe 8 ] (année 2025)