# eHuB → ArtNet Router + Animations

## Lancer le routeur
```bash
python receiver/router_lookup_cli.py --excel "faker/Ecran (2).xlsx" --fps 40

Lancer une animation (exemples)

python faker/animator_cli.py --mode blink --seconds 10
python faker/stars_player.py --seconds 20 --density 0.01

UI Web
python webui/server.py
# Ouvrir http://localhost:8000

Dépendances
pip install -r requirements.txt


---

# 1) Initialise Git en local
Dans **le dossier du projet** :
```bash
git --version
git init
git config user.name "Ton Nom"
git config user.email "ton.email@exemple.com"
git add .
git commit -m "feat: routeur eHuB→ArtNet + animations + web UI"
