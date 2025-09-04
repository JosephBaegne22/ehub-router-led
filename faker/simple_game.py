# faker/simple_game.py
import time, threading, random, sys

# Remplacez par votre module pour piloter l'écran LED
from faker.fake_led import LEDMatrix  

FPS = 5
led = LEDMatrix()
width, height = led.width, led.height

# Joueur
player = [width//2, height//2]
# Cible
target = [random.randint(0, width-1), random.randint(0, height-1)]
score = 0

# Direction initiale
direction = [0, 0]

def draw():
    led.clear()
    led.set_pixel(player[0], player[1], (0,255,0))  # joueur vert
    led.set_pixel(target[0], target[1], (255,0,0))  # cible rouge
    led.show()

def move():
    global score, target
    player[0] = (player[0] + direction[0]) % width
    player[1] = (player[1] + direction[1]) % height

    if player == target:
        score += 1
        print(f"Score: {score}")
        target = [random.randint(0, width-1), random.randint(0, height-1)]

# Lecture des touches clavier
def key_listener():
    global direction
    try:
        import msvcrt  # Windows
        while True:
            if msvcrt.kbhit():
                key = msvcrt.getch().decode().lower()
                if key == 'w': direction = [0, -1]
                elif key == 's': direction = [0, 1]
                elif key == 'a': direction = [-1, 0]
                elif key == 'd': direction = [1, 0]
    except ImportError:
        print("Clavier non supporté sur cette plateforme")

threading.Thread(target=key_listener, daemon=True).start()

try:
    while True:
        move()
        draw()
        time.sleep(1/FPS)
except KeyboardInterrupt:
    led.clear()
    led.show()
    print(f"Jeu terminé. Score final: {score}")