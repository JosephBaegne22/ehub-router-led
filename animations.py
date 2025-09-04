from faker.stars_player import play_starfield
from faker.animator_cli import run_animation

ANIMATIONS = {
    "stars": {
        "func": play_starfield,
        "params": [
            "excel", "host", "port", "seconds", "fps",
            "density", "seed", "bg", "chunk_size"
        ],
        "desc": "Ciel étoilé avec scintillement des étoiles"
    },
    "blink": {
        "func": run_animation,
        "params": [
            "mode", "excel", "host", "port",
            "seconds", "fps", "color1", "color2", "speed"
        ],
        "desc": "Animation clignotante rapide (couleur1 <-> couleur2)"
    },
    "wave": {
        "func": run_animation,
        "params": [
            "mode", "excel", "host", "port",
            "seconds", "fps", "color1", "color2", "speed"
        ],
        "desc": "Onde sinusoïdale sur toutes les LEDs (teinte définie par couleur1)"
    },
    "chase": {
        "func": run_animation,
        "params": [
            "mode", "excel", "host", "port",
            "seconds", "fps", "color1", "color2", "speed"
        ],
        "desc": "Effet de poursuite / comète basé sur couleur1"
    },
    "gradient": {
        "func": run_animation,
        "params": [
            "mode", "excel", "host", "port",
            "seconds", "fps", "color1", "color2", "speed"
        ],
        "desc": "Dégradé de couleurs statique ou animé (couleur1 -> couleur2)"
    },
    "solid": {
        "func": run_animation,
        "params": [
            "mode", "excel", "host", "port",
            "seconds", "fps", "color1", "color2", "speed"
        ],
        "desc": "Affichage couleur unie (basée sur couleur1)"
    }
}