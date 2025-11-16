from pydantic import BaseModel
from typing import List, Optional


class Weights(BaseModel):
    dl: float = 1.0
    bm25: float = 1.0 


class AddressObject(BaseModel):
    locality: str
    street: str
    number: str
    lon: float
    lat: float
    score: Optional[float] = None
    distance_m: Optional[float] = None


class AddressObject2(BaseModel):
    address: str
    lon: float
    lat: float


class SearchRequest(BaseModel):
    query: str
    top_n: int = 5
    weights: Optional[Weights] = None
    algorithms: Optional[List[str]] = None


class SearchResponse(BaseModel):
    searched_address: str
    objects: List[AddressObject]


class ReverseResponse(BaseModel):
    query_point_lat: float
    query_point_lon: float
    objects: List[AddressObject2]


class CompareRequest(BaseModel):
    address_1: str
    address_2: str
    weights: Optional[Weights] = None
    algorithms: Optional[List[str]] = None


class CompareResponse(BaseModel):
    address_1: str
    address_2: str
    distance_m: Optional[float]
    similarity: Optional[float]
    point_1: Optional[AddressObject]
    point_2: Optional[AddressObject]
