class Animation:
    """Classe de base pour toutes les animations."""
    def __init__(self, name, duration):
        self.name = name
        self.duration = duration  # en secondes

    def generate_frame(self, t):
        """Retourne la frame (liste de valeurs) pour l'instant t"""
        raise NotImplementedError("Doit être implémenté dans la sous-classe")