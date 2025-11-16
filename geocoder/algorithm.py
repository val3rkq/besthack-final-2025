import pandas as pd
from typing import List, Optional, Tuple, Dict, Any
from geocoder.model import SearchAddressModel

class GeocoderAlgorithm:
    def __init__(self):
        self.model = SearchAddressModel()

    def search(
        self,
        query: str,
        top_n: int = 5,
        weights: Optional[Dict[str, float]] = None
    ):
        w1 = 1.0
        w2 = 1.0

        if weights:
            w1 = float(weights.get("dl", w1))
            w2 = float(weights.get("bm25", w2))

        if w1 == 0 and w2 == 0:
            return []

        df = self.model.search(query, top_n=top_n, w1=w1, w2=w2)

        objects = []
        for _, row in df.iterrows():
            address_str = str(row["address"])
            locality = ""
            street = ""
            number = ""
            building = ""
            parts = address_str.split(' ')
            i = 0
            while i < len(parts):
                part = parts[i]
                if part == 'город' and i + 1 < len(parts):
                    locality = parts[i + 1].capitalize()
                    i += 2
                elif part == 'улица' and i + 1 < len(parts):
                    street_parts = []
                    i += 1
                    while i < len(parts):
                        if (parts[i].startswith("дом") or parts[i].startswith("корпус")):
                            break
                        for elem in parts[i].capitalize().split('_'):
                            street_parts.append(elem)
                        i += 1
                    street = " ".join(street_parts)
                elif part.startswith('дом'):
                    num = part[3:]
                    if not num and i + 1 < len(parts):
                        number = parts[i + 1]
                        i += 2
                    else:
                        number = num
                        i += 1
                elif part.startswith('корпус'):
                    bldg = part[6:]
                    if not bldg and i + 1 < len(parts):
                        building = parts[i + 1]
                        i += 2
                    else:
                        building = bldg
                        i += 1
                else:
                    i += 1
            full_number = number
            if building:
                full_number = f"{number} корп.{building}" if number else f"корп.{building}"

            objects.append({
                "locality": locality or "Москва",
                "street": street,
                "number": full_number,
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "name": row["name"] if row["name"] else '',
                "score": float(row["score"]),
            })

        return objects


    def reverse(
        self,
        lat: float,
        lon: float,
        top_n: int = 1,
        radius_m: float = 200.0,
    ) -> List[Dict[str, Any]]:
        """
        Ищем ближайшие адреса к точке (lat, lon).
        Здесь используем тот же dataset и формулу Haversine.
        """
        candidates: List[str] = []
        for i in range(top_n):
            candidates.append(self.model.address_by_coords(lat, lon))

        candidates.sort(key=lambda x: x[0])
        candidates = candidates[:top_n]

        objects: List[Dict[str, Any]] = []
        for dist_m, row in candidates:
            objects.append(
                {
                    "locality": "Москва",
                    "street": str(row["address"]),
                    "number": "",
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "score": None,
                    "distance_m": float(dist_m),
                }
            )

        return objects

    def get_best_candidate(
        self,
        query: str,
        weights: Optional[Dict[str, float]] = None,
        algorithms: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Берём top_n=1 из search() и возвращаем одну запись.
        """
        results = self.search(query=query, top_n=1)
        if not results:
            return None
        return results[0]

    def haversine_distance_m(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Возвращает расстояние между двумя координатами в МЕТРАХ.
        Использует ту же формулу, что и внутри модели (км -> м).
        """
        d_km = self.model._SearchAddressModel__haversine(lat1, lon1, lat2, lon2)
        return d_km * 1000.0
