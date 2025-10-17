import json

# === Пути к файлам ===
parsed_prices_file = 'products.json'               # файл, где новые цены
products_file = 'gorgia_products_updated.json'     # текущий массив товаров
output_file = 'gorgia_products_with_new_prices.json'

# === Загружаем данные ===
with open(parsed_prices_file, 'r', encoding='utf-8') as f:
    parsed = json.load(f)

with open(products_file, 'r', encoding='utf-8') as f:
    products = json.load(f)

# === Создаём словарь title -> price из новых данных ===
price_map = {p['title'].strip(): p['price'] for p in parsed if p.get('price')}

# === Обновляем цены в товарах ===
updated_count = 0
for p in products:
    title = p['title'].strip()
    if title in price_map:
        p['price'] = price_map[title]
        updated_count += 1

# === Сохраняем результат ===
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

print(f"✅ Обновлено {updated_count} цен. Файл сохранён как {output_file}")
