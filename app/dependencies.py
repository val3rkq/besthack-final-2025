from functools import lru_cache
from geocoder.algorithm import GeocoderAlgorithm


@lru_cache
def get_geocoder() -> GeocoderAlgorithm:
    return GeocoderAlgorithm()
