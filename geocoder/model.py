import math
import numpy as np
import pandas as pd
import re
from rapidfuzz import distance
from rank_bm25 import BM25Okapi
from typing import List, Optional, Tuple
from geocoder.utils import *

class SearchAddressModel:
    def __init__(self):
        self.dataset = pd.read_csv("./data/" + DATASET_NAME)
        self.dataset.iloc[:, 5] = self.dataset.iloc[:, 5].fillna('')
        self.tokenized_dataset = self.__preprocess_dataset()
        self.bm25 = BM25Okapi(self.tokenized_dataset)
    
    def __preprocess_dataset(self) -> List[List[str]]:
        """Препроцессинг адресов для BM25"""
        tokenized = []
        for address in self.dataset.iloc[:, 5]:
            processed_addr = self.__preprocess_address(str(address))
            tokenized.append(self.__tokenize_address(processed_addr))
        return tokenized
    
    def __tokenize_address(self, address: str, k: int = 3) -> List[str]:
        """Токенизация адреса с n-граммами"""
        if not isinstance(address, str):
            address = str(address) if not pd.isna(address) else ''
        return [address[n - k:n] for n in range(k, len(address) + 1)]
        
    def __preprocess_address(self, address: str) -> str:
        """
        Парсит и нормализует русский адрес в формат:
        город_москва_улица_{название_улицы}_дом{номер}_{дополнительная_информация}
        
        Примеры:
        "Ленина улица, дом 5, корпус 2" -> "город_москва_улица_ленина_дом5_корпус2"
        ".г Москва, ул. Тверская, д. 10, стр. 1" -> "город_москва_улица_тверская_дом10_строение1"
        "пр-т Мира д 25 к.3" -> "город_москва_улица_проспект_мира_дом25_корпус3"
        "наб. Фонтанки, дом 10 лит. А" -> "город_москва_улица_наб_фонтанки_дом10_литераА"
        """
        street_type_abbrevs = {
            'ул.': 'улица', 'ул': 'улица', 'улица': 'улица',
            'пр-т': 'проспект', 'пр.': 'проспект', 'пр': 'проспект', 'проспект': 'проспект',
            'наб.': 'наб', 'наб': 'наб', 'набережная': 'набережная',
            'пер.': 'переулок', 'переулок': 'переулок',
            'б-р': 'бульвар', 'бульвар': 'бульвар',
            'пл.': 'площадь', 'площадь': 'площадь',
            'ш.': 'шоссе', 'шоссе': 'шоссе',
            'проезд': 'проезд',
            'аллея': 'аллея', 'ал.': 'аллея',
        }
        
        street_type_expansions = {
            'пр-т': 'проспект',
            'пр.': 'проспект',
            'пр': 'проспект',
            'наб.': 'наб',
            'наб': 'наб',
        }
        
        house_abbrevs = {
            'д.': 'дом', 'д': 'дом', 'дом': 'дом',
        }
        
        building_abbrevs = {
            'к.': 'корпус', 'к': 'корпус', 'корпус': 'корпус', 'корп.': 'корпус',
            'стр.': 'строение', 'стр': 'строение', 'с.': 'строение', 'строение': 'строение',
            'лит.': 'литера', 'лит': 'литера', 'литера': 'литера',
        }
        
        city_abbrevs = {
            'г.': 'город', 'г': 'город', '.г': 'город', 'город': 'город',
            'москва': 'москва', 'мск': 'москва',
        }
        
        processed = address.strip().lower()
        # Обрабатываем специальные случаи (например, ".г" в начале)
        processed = re.sub(r'^\.г\s+', 'г. ', processed)

        # к.5 -> к. 5, д.10 -> д. 10, г.Москва -> г. Москва
        processed = re.sub(r'(\w\.)((?!\s))', r'\1 \2', processed)

        processed = re.sub(r'\s+', ' ', processed)
        processed = processed.strip()
        
        processed = processed.replace(',', ' , ')
        processed = re.sub(r'\s+', ' ', processed)
        words = processed.split()
        
        city = 'москва'
        street_name_parts = []
        house_number = None
        building_info = []
        
        i = 0
        while i < len(words):
            word = words[i]
            word_clean = word.rstrip('.,')
            
            if word == ',':
                i += 1
                continue
            
            if word_clean in city_abbrevs or word_clean == 'москва':
                city = 'москва'
                i += 1
                continue
            
            if word_clean in street_type_abbrevs:
                if word_clean in street_type_expansions:
                    street_name_parts.append(street_type_expansions[word_clean])
                elif word_clean in ['ул.', 'ул', 'улица']:
                    pass
                else:
                    street_name_parts.append(word_clean.rstrip('.'))
                
                i += 1
                while i < len(words):
                    next_word = words[i]
                    if next_word == ',':
                        i += 1
                        continue
                    next_clean = next_word.rstrip('.,')
                    if (next_clean in house_abbrevs or 
                        next_clean in building_abbrevs or
                        (next_clean.replace('.', '').isdigit() and house_number is None)):
                        break
                    street_name_parts.append(next_clean)
                    i += 1
                continue
            
            if word_clean in house_abbrevs:
                i += 1
                if i < len(words):
                    house_word = words[i].rstrip('.,')
                    house_num = re.search(r'\d+', house_word)
                    if house_num:
                        house_number = house_num.group()
                        i += 1
                continue
            
            if word_clean in building_abbrevs:
                building_type = building_abbrevs[word_clean]
                i += 1
                if i < len(words):
                    building_word = words[i].rstrip('.,')
                    building_value = building_word
                    if building_value:
                        building_info.append(f"{building_type}{building_value}")
                        i += 1
                continue
            
            if house_number is None and word_clean.replace('.', '').isdigit():
                if street_name_parts or i > 0:
                    house_number = word_clean.replace('.', '')
                    i += 1
                    continue
            
            if i + 1 < len(words):
                next_word = words[i + 1].rstrip('.,')
                if next_word in street_type_abbrevs:
                    street_name_parts.append(word_clean)
                    i += 2
                    continue
            
            if street_name_parts and house_number is None:
                street_name_parts.append(word_clean)
                i += 1
                continue
            
            if not street_name_parts and house_number is None:
                if not word_clean.replace('.', '').isdigit():
                    street_name_parts.append(word_clean)
                i += 1
                continue
            
            i += 1
        
        result_parts = ['город', city, 'улица']
        
        if street_name_parts:
            street_name = '_'.join(street_name_parts)
            result_parts.append(street_name)
        
        if house_number:
            result_parts.append(f'дом{house_number}')
        
        result_parts.extend(building_info)
        return '_'.join(result_parts)
    
    def __damerau_levenshtein(self, query: str, top_n: int) -> List[Tuple[int, float]]:
        """
        Оптимизированная версия - сравнивает адреса как целые строки
        """
        query_formatted = self.__preprocess_address(query)
        
        scores = []
        for line in self.dataset.iloc[:, 5]:
            line_formatted = self.__preprocess_address(str(line))
            dist = distance.DamerauLevenshtein.distance(query_formatted, line_formatted)
            scores.append(dist)
        
        if len(scores) == 0:
            return []
        
        min_dist = min(scores)
        max_dist = max(scores)
        
        if max_dist == min_dist:
            normalized_scores = [0.5] * len(scores)
        else:
            normalized_scores = [1.0 - (s - min_dist) / (max_dist - min_dist) for s in scores]
        
        sorted_indices = np.argsort(scores)
        top_k = min(top_n, len(self.dataset))
        result_top_n = []
        for idx in sorted_indices[:top_k]:
            if normalized_scores[idx] > 0:
                result_top_n.append((idx, normalized_scores[idx]))
                if len(result_top_n) >= top_n:
                    break
        
        return result_top_n
    
    def __bm25(self, query: str, top_n: int) -> List[Tuple[int, float]]:
        query = self.__preprocess_address(query)
        print("preprocessed query: " + query)
        
        query_tokens = self.__tokenize_address(query)
        scores = self.bm25.get_scores(query_tokens)
        max_score = max(scores)
        top_k = min(top_n, len(self.dataset))
        sorted_indices = np.argsort(scores)[::-1]
        
        result_top_n = []
        for idx in sorted_indices[:top_k]:
            if scores[idx] > 0:
                result_top_n.append([idx, scores[idx]])
                if len(result_top_n) >= top_n:
                    break
        
        for i in range(len(result_top_n)):
            result_top_n[i][1] /= max_score
        return result_top_n
    
    def __score(self, query: str, top_n: int, w1: float = 1.0, w2: float = 1.0) -> List[Tuple[int, float]]:
        """Объединение результатов двух алгоритмов"""
        combined_scores = {}
        
        for idx, dist_score in self.__damerau_levenshtein(query, top_n * 5):
            if idx in combined_scores:
                combined_scores[idx][0] += dist_score * w1
                combined_scores[idx][1] += 1
            else:
                combined_scores[idx] = [dist_score * w1, 1]
        
        for idx, bm25_score in self.__bm25(query, top_n * 5):
            if idx in combined_scores:
                combined_scores[idx][0] += bm25_score * w2
                combined_scores[idx][1] += 1
            else:
                combined_scores[idx] = [bm25_score * w2, 1]
        
        result = [(idx, score[0] / score[1]) for idx, score in combined_scores.items()]
        return sorted(result, key=lambda x: x[1], reverse=True)[:top_n]
    
    def search(self, query: str, top_n: int, w1: float = 1.0, w2: float = 1.0) -> pd.DataFrame:
        """Возвращает DataFrame с результатами и столбцом score"""
        scored_indices = self.__score(query, top_n, w1, w2)
        
        results = []
        for idx, score in scored_indices:
            row_data = self.dataset.iloc[idx].copy()
            row_data['score'] = score
            results.append(row_data)
        
        return pd.DataFrame(results)
    
    def __find_nearest_address(self, lat: float, lon: float) -> str:
        """Находит ближайший адрес по координатам"""
        min_distance = float('inf')
        nearest_address = ''
        
        for _, row in self.dataset.iterrows():
            if pd.isna(row['lat']) or pd.isna(row['lon']):
                continue
                
            dist = self.__haversine(lat, lon, row['lat'], row['lon'])
            if dist < min_distance:
                min_distance = dist
                nearest_address = str(row.iloc[5])
        
        return nearest_address
    
    def __haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Вычисляет расстояние между двумя точками на Земле по формуле Haversine"""        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def address_by_coords(self, lat: float, lon: float, is_optional: bool = True) -> Optional[str]:
        try:
            address = self.__find_nearest_address(lat, lon)
            return address if address else None
        except (ValueError, KeyError):
            return None if is_optional else ''
    
    def haversine_distance(self, address1: str, address2: str) -> float:
        result1 = self.search(address1, top_n=1)
        result2 = self.search(address2, top_n=1)
        
        if len(result1) == 0 or len(result2) == 0:
            raise ValueError("Нельзя найти координаты!")
        
        if pd.isna(result1.iloc[0]['lat']) or pd.isna(result1.iloc[0]['lon']) or \
           pd.isna(result2.iloc[0]['lat']) or pd.isna(result2.iloc[0]['lon']):
            raise ValueError("Нельзя найти координаты!")
        
        coords1 = (result1.iloc[0]['lat'], result1.iloc[0]['lon'])
        coords2 = (result2.iloc[0]['lat'], result2.iloc[0]['lon'])
        return self.__haversine(coords1[0], coords1[1], coords2[0], coords2[1])
