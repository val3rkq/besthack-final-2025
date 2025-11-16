from geocoder.model import SearchAddressModel

def main():
    print("Инициализация модели поиска адресов...")
    model = SearchAddressModel()
    print(f"Модель загружена. Размер датасета: {len(model.dataset)} записей")
    
    print("\n" + "="*50)
    print("ДЕМОНСТРАЦИЯ ПОИСКА АДРЕСОВ")
    print("="*50)
    
    test_queries = [
        # ".г Москва, ул. Тверская, д. 10, стр. 1"
        # "Ленина улица, дом 5, к.2"
        "пр-т Мира д 25 к.3"
        # "Москва, Садовая ул, д.5, с.1"
        # "наб. Фонтанки, дом 10"
    ]
    
    # with open("result.txt", "+w") as f:
    for query in test_queries:
        print(f"\nЗапрос: '{query}'")
        results = model.search(query, top_n=5)
        for i, (_, row) in enumerate(results.iterrows()):
            row_str = ' | '.join([f"{col}: {val}" for col, val in row.items()])
            print(f"{i+1}. {row_str}")
                # f.write(f"{i+1}. {row_str}\n")

if __name__ == '__main__':
    main()