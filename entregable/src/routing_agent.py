# src/routing_agent.py
import re
from datetime import datetime
import math

class RoutingAgent:
    def __init__(self):
        # Mapa de coordenadas (lat, lon) para lugares conocidos
        self.mock_coords = {
            "centro": (-21.5353, -64.7339),
            "plaza luis de fuentes": (-21.5353, -64.7339),
            "plaza central": (-21.5353, -64.7339),
            "loma san juan": (-21.5072, -64.7375),
            "bodega campos de solana": (-21.4683, -64.7358),
            "bodega campos": (-21.4683, -64.7358),
            "terminal de buses": (-21.5234, -64.7350),
            "terminal": (-21.5234, -64.7350),
            "mercado central": (-21.5345, -64.7340),
            "mercado": (-21.5345, -64.7340),
        }

    def geocode(self, place_name):
        """Convierte un nombre de lugar a coordenadas (lat, lon)"""
        name = place_name.lower().strip()
        # Buscar coincidencia exacta o parcial
        for key, coord in self.mock_coords.items():
            if key in name:
                return coord
        # Si no se encuentra, devolver coordenadas del centro por defecto
        return (-21.5353, -64.7339)

    def get_route(self, origin, destination, mode="walking"):
        """
        Calcula una ruta simulada entre dos puntos.
        Devuelve un diccionario con distancia, duración, pasos, advertencias y coordenadas.
        """
        from_coords = self.geocode(origin)
        to_coords = self.geocode(destination)

        # Distancia euclidiana aproximada en km (1 grado ~ 111 km)
        dist_deg = math.sqrt((to_coords[0] - from_coords[0])**2 + (to_coords[1] - from_coords[1])**2)
        dist_km = dist_deg * 111

        # Duración estimada: caminando 5 min/km, en auto 2 min/km
        if mode == "walking":
            duration_min = dist_km * 5
        else:
            duration_min = dist_km * 2

        # Advertencias de seguridad basadas en la hora actual
        warnings = []
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 20:
            warnings.append("🌙 Es de noche. Camina por calles iluminadas y evita zonas solitarias.")

        return {
            "distance": f"{dist_km:.1f} km",
            "duration": f"{int(duration_min)} min",
            "steps": [f"Dirígete hacia {destination} por ruta {mode}."],
            "warnings": warnings,
            "origin_coords": from_coords,
            "destination_coords": to_coords,
            "origin_name": origin,
            "destination_name": destination 
        }

def integrate_routing_agent(query: str):
    """
    Función de alto nivel para extraer origen y destino de la consulta,
    calcular la ruta y devolver (route_dict, respuesta_texto).
    Si no se puede parsear, devuelve (None, mensaje_error).
    """
    agent = RoutingAgent()
    # Patrón para extraer "de X a Y"
    patron = r"de\s+([\w\s]+?)\s+a\s+([\w\s]+?)(?:\?|$)"
    match = re.search(patron, query.lower())
    if not match:
        return None, "No entendí desde dónde hasta dónde quieres ir. Ejemplo: '¿Cómo llegar de la plaza central a la bodega Campos de Solana?'"

    origin = match.group(1).strip()
    destination = match.group(2).strip()
    route = agent.get_route(origin, destination)

    # Construir respuesta textual
    respuesta = f"🗺️ **Ruta de {origin} a {destination}**\n"
    respuesta += f"Distancia: {route['distance']}\n"
    respuesta += f"Duración: {route['duration']}\n"
    respuesta += "**Pasos:**\n" + "\n".join(f"- {step}" for step in route['steps'])
    if route['warnings']:
        respuesta += "\n\n⚠️ **Advertencias:**\n" + "\n".join(f"- {w}" for w in route['warnings'])

    return route, respuesta