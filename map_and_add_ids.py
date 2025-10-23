#!/usr/bin/env python3
import json
import re
import shutil
from pathlib import Path
from collections import Counter

# === Настройки файлов ===
PRODUCTS_FILE = Path("sad1.json")
UPLOADED_FILE = Path("uploaded_images.json")
OUTPUT_FILE = Path("gorgia_products_updated.json")
BACKUP_FILE = PRODUCTS_FILE.with_suffix(".backup.json")

# === Проверка наличия файлов ===
if not PRODUCTS_FILE.exists():
    raise FileNotFoundError(f"Не найден {PRODUCTS_FILE}. Помести файл и повтори.")
if not UPLOADED_FILE.exists():
    raise FileNotFoundError(f"Не найден {UPLOADED_FILE}. Помести файл и повтори.")

# === Загрузка данных ===
with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
    products = json.load(f)

with open(UPLOADED_FILE, "r", encoding="utf-8") as f:
    uploaded = json.load(f)

# === Создаём lookup по токенам имён файлов ===
lookup = {}
for item in uploaded:
    fname = item.get("file") or ""
    url = item.get("url")
    if not fname or not url:
        continue
    no_ext = re.sub(r'\.[^.]+$', '', fname).lower()
    tokens = [no_ext] + re.split(r'[_\-\s]+', no_ext)
    for tk in tokens:
        if not tk:
            continue
        lookup.setdefault(tk, []).append(url)

# === Извлечение ключа из image_url ===
def extract_key_from_url(img_url):
    if not img_url:
        return None
    last = img_url.split("/")[-1]
    last_noext = re.sub(r'\.[^.]+$', '', last).lower()
    parts = re.split(r'[_\-\s]+', last_noext)
    for p in parts:
        if p and len(p) >= 2:
            return p
    return last_noext or None

# === Основная логика замены ссылок ===
shutil.copy(PRODUCTS_FILE, BACKUP_FILE)
print(f"Создан бэкап: {BACKUP_FILE}")

used_urls = set()
stats = Counter(found=0, not_found=0, replaced=0)

for i, prod in enumerate(products, start=1):
    orig_img = prod.get("image_url", "") or ""
    key = extract_key_from_url(orig_img)
    matched_url = None

    if key and key in lookup:
        candidates = lookup[key]
        for c in candidates:
            if c not in used_urls:
                matched_url = c
                break
        if not matched_url:
            matched_url = candidates[0]
    else:
        if key:
            for tk in lookup:
                if tk in key or key in tk:
                    candidates = lookup[tk]
                    for c in candidates:
                        if c not in used_urls:
                            matched_url = c
                            break
                    if not matched_url:
                        matched_url = candidates[0]
                    break

    # Замена только image_url (id не трогаем)
    if matched_url:
        prod["image_url"] = matched_url
        used_urls.add(matched_url)
        stats["found"] += 1
        stats["replaced"] += 1
    else:
        prod["image_url_error"] = "no_match_found"
        stats["not_found"] += 1

# === Сохранение результата ===
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

print(f"✅ Готово. Сохранено: {OUTPUT_FILE}")
print(f"📊 Статистика: найдено и заменено = {stats['replaced']}, не найдено = {stats['not_found']}")
