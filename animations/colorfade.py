from .base import Animation

class ColorFade(Animation):
    """Transition linéaire entre deux couleurs RGB."""
    def __init__(self, start_color, end_color, duration):
        super().__init__("ColorFade", duration)
        self.start_color = start_color
        self.end_color = end_color

    def generate_frame(self, t):
        ratio = min(max(t / self.duration, 0), 1)
        return [int(self.start_color[i] + (self.end_color[i]-self.start_color[i]) * ratio) for i in range(3)]