# src/safety_agent.py
import json
from pathlib import Path

class SafetyAgent:
    def __init__(self, zones_file="data/safety_zones.json"):
        self.zones_file = Path(__file__).parent.parent / zones_file
        self.load_zones()
    
    def load_zones(self):
        if self.zones_file.exists():
            with open(self.zones_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.zones = data.get("zonas_precaución", [])
        else:
            self.zones = []
    
    def check_zone(self, place_name, hora=12):
        """
        Busca si el nombre del lugar (place_name) coincide con alguna zona de precaución.
        Retorna una lista de alertas (strings).
        """
        alerts = []
        place_lower = place_name.lower()
        for zone in self.zones:
            if zone["nombre"].lower() in place_lower:
                if zone["horario"] == "noche" and (hora < 6 or hora > 20):
                    alerts.append(f"⚠️ Precaución en {zone['nombre']} (nivel {zone['nivel']}) después del atardecer.")
                else:
                    alerts.append(f"ℹ️ {zone['nombre']} es seguro durante el día, pero tenga cuidado de noche.")
        return alerts