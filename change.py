import json
import re

# === Пути к файлам ===
products_file = 'gorgia_products_full.json'
images_file = 'uploaded_images.json'
output_file = 'gorgia_products_updated.json'

# === Загружаем данные ===
with open(products_file, 'r', encoding='utf-8') as f:
    products = json.load(f)

with open(images_file, 'r', encoding='utf-8') as f:
    uploaded = json.load(f)

# === Создаем словарь file → url ===
uploaded_map = {}
for img in uploaded:
    # Извлекаем код вида BM-00012345
    match = re.search(r'(BM-\d+)', img['file'])
    if match:
        uploaded_map[match.group(1)] = img['url']

# === Обновляем продукты ===
for i, product in enumerate(products, start=1):
    product['id'] = i  # добавляем id
    match = re.search(r'(BM-\d+)', product.get('image_url', ''))
    if match:
        code = match.group(1)
        if code in uploaded_map:
            product['image_url'] = uploaded_map[code]

# === Сохраняем результат ===
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

print("✅ Ссылки заменены, ID добавлены, файл сохранён как", output_file)
