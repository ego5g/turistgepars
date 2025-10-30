#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup, NavigableString
import json
import urllib.parse
import time
from pathlib import Path
import base64

# === 🟢 Категории ===
CATEGORY = "Мебель"
SUB_CATEGORY = "Столы"  # Может быть пустым

# === 🟢 Вводные переменные ===
CATEGORY_URL = "https://gorgia.ge/ka/aveji/magidebi-da-merxebi"
PAGE_NUMBER = 3
START_ID = 341

# === Настройки ===
BASE_URL = "https://gorgia.ge"
IMGBB_API_KEY = "ea604eb5723e81ae9239838ad3396984"
SAVE_DIR = Path("images_temp")
SAVE_DIR_FALSE = SAVE_DIR / "false"
SAVE_DIR.mkdir(exist_ok=True)
SAVE_DIR_FALSE.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

# === Перевод текста (грузинский → русский) ===
def translate_text(text, target_lang="ru"):
    if not text:
        return ""
    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "ka",
                "tl": target_lang,
                "dt": "t",
                "q": text,
            },
            timeout=10,
        )
        if r.status_code == 200:
            result = r.json()
            return "".join([t[0] for t in result[0]])
    except Exception as e:
        print(f"⚠️ Ошибка перевода: {e}")
    return text

# === Получение HTML страницы ===
def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

# === Конвертация ссылки в webp ===
def convert_to_webp_url(old_url):
    if not old_url:
        return None
    return (
        old_url
        .replace("/images/thumbnails/240/240/", "/images/ab__webp/thumbnails/1100/900/")
        .replace(".jpg", "_jpg.webp")
        .replace(".JPG", "_jpg.webp")
        .replace(".jpeg", "_jpg.webp")
        .replace(".png", "_jpg.webp")
    )

# === Скачивание фото ===
def download_image(url, out_path):
    try:
        r = requests.get(url, headers=HEADERS, stream=True, timeout=20)
        if r.status_code == 200:
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(1024 * 32):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"❌ Ошибка скачивания {url}: {e}")
    return False

# === Загрузка на imgbb ===
def upload_to_imgbb(image_path):
    try:
        with open(image_path, "rb") as f:
            img_base64 = base64.b64encode(f.read())
        r = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMGBB_API_KEY, "image": img_base64},
            timeout=30
        )
        if r.status_code == 200:
            data = r.json()
            return data["data"]["url"]
        else:
            print(f"⚠️ Ошибка загрузки на imgbb: {r.text}")
    except Exception as e:
        print(f"❌ Ошибка при загрузке на imgbb: {e}")
    return None

# === Получение всех URL фото (без дублей) ===
def get_all_image_urls(card):
    """Извлекает все уникальные URL фото товара"""
    image_urls = []
    seen_urls = set()
    
    # === Основное фото ===
    img_tag = card.select_one(".ut2-gl__image img")
    if img_tag and "src" in img_tag.attrs:
        main_url = img_tag["src"]
        if main_url and main_url not in seen_urls:
            webp_url = convert_to_webp_url(main_url)
            if webp_url:
                image_urls.append(webp_url)
                seen_urls.add(webp_url)
    
    # === Дополнительные фото из data-атрибутов ===
    additional_items = card.select(".item[data-ca-product-additional-image-src]")
    for item in additional_items:
        # Проверяем srcset (высокое качество)
        srcset = item.get("data-ca-product-additional-image-srcset")
        if srcset:
            # Берем первую часть srcset (обычно это URL без 2x суффикса)
            url = srcset.split()[0].strip()
            if url and url not in seen_urls:
                image_urls.append(url)
                seen_urls.add(url)
        # Если srcset не найден, берем основной атрибут
        elif "data-ca-product-additional-image-src" in item.attrs:
            url = item["data-ca-product-additional-image-src"]
            if url and url not in seen_urls:
                image_urls.append(url)
                seen_urls.add(url)
    
    return image_urls

# === Парсинг карточек товаров ===
def parse_page(category_url, page_number=1, start_id=1):
    if page_number > 1:
        url = f"{category_url}?page={page_number}" if category_url.endswith("/") else f"{category_url}/?page={page_number}"
    else:
        url = category_url

    print(f"\n🔗 Парсим страницу: {url}")
    soup = get_soup(url)
    cards = soup.select(".ut2-gl__body")
    print(f"Найдено {len(cards)} товаров\n")

    products = []

    for i, card in enumerate(cards, start=start_id):
        title_tag = card.select_one(".ut2-gl__name a")
        title = title_tag.get_text(strip=True) if title_tag else ""
        link = urllib.parse.urljoin(BASE_URL, title_tag["href"]) if title_tag else None

        # === Цена ===
        price_tag = card.select_one(".ty-price-num")
        price = None
        if price_tag:
            first_text = None
            for child in price_tag.children:
                if isinstance(child, NavigableString):
                    txt = str(child).strip()
                    if txt:
                        first_text = txt
                        break
            if not first_text:
                for s in price_tag.find_all('sup'):
                    s.extract()
                first_text = price_tag.get_text(strip=True)
            if first_text:
                try:
                    num_str = first_text.replace(",", ".").replace("₾", "").strip()
                    price = int(float(num_str))
                except ValueError:
                    price = None

        # === Получаем ВСЕ фото ===
        image_urls_list = get_all_image_urls(card)
        uploaded_image_urls = []
        
        # === Проверка наличия ===
        stock_tag = card.select_one(".ty-qty-in-stock")
        availability = "Неизвестно"
        in_stock = False
        if stock_tag:
            stock_text = stock_tag.get_text(strip=True)
            if "მარაგშია" in stock_text:
                availability = "В наличии"
                in_stock = True
            elif "მარაგი იწურება" in stock_text:
                availability = "Нет в наличии"
                in_stock = False

        # === Перевод ===
        title_ru = translate_text(title)
        description_ru = translate_text(
            card.select_one(".product-description").get_text(strip=True)
            if card.select_one(".product-description") else ""
        )

        # === Обработка всех фото ===
        for idx, img_url in enumerate(image_urls_list, 1):
            try:
                filename = Path(img_url.split("/")[-1])
                # Добавляем индекс к имени файла (кроме первого)
                if idx > 1:
                    filename = filename.with_stem(filename.stem + f"_{idx}")

                if in_stock:
                    temp_path = SAVE_DIR / filename
                    if download_image(img_url, temp_path):
                        uploaded = upload_to_imgbb(temp_path)
                        if uploaded:
                            uploaded_image_urls.append(uploaded)
                            print(f"  📸 Фото {idx}: {uploaded}")
                        # Удаляем временный файл
                        try:
                            temp_path.unlink()
                        except:
                            pass
                else:
                    txt_path = SAVE_DIR_FALSE / filename.with_suffix(".txt")
                    with open(txt_path, "w", encoding="utf-8") as f:
                        f.write(img_url)
                
                time.sleep(0.3)
            except Exception as e:
                print(f"  ⚠️ Ошибка обработки фото {idx}: {e}")

        # === Основное фото (или первое из загруженных) ===
        main_image_url = uploaded_image_urls[0] if uploaded_image_urls else image_urls_list[0] if image_urls_list else None

        # === Формируем image_urls без дублирования основного фото ===
        additional_images = []
        if uploaded_image_urls and len(uploaded_image_urls) > 1:
            # Если есть дополнительные фото (кроме первого)
            additional_images = uploaded_image_urls[1:]
        elif image_urls_list and len(image_urls_list) > 1:
            # Если фото не загружались на imgbb, используем оригинальные URL без первого
            additional_images = image_urls_list[1:]
        
        products.append({
            "id": i,
            "category": CATEGORY,
            "sub_category": SUB_CATEGORY or None,
            "title": title_ru,
            "price": price,
            "description": description_ru,
            "availability": availability,
            "in_stock": in_stock,
            "image_url": main_image_url,
            "image_urls": additional_images,  # Только дополнительные фото (без основного)
            "link": link
        })

        print(f"{i:03d}. {title_ru} — {price} ₾ — {availability} ({len(image_urls_list)} фото)\n")
        time.sleep(1)

    return products

# === Основной запуск ===
if __name__ == "__main__":
    products = parse_page(CATEGORY_URL, PAGE_NUMBER, START_ID)

    # === Генерация имени по ссылке ===
    parsed_url = urllib.parse.urlparse(CATEGORY_URL)
    clean_name = parsed_url.path.strip("/").replace("/", "_") or "category"

    output_all = f"gorgia_{clean_name}_page_{PAGE_NUMBER}_all.json"
    output_in = f"gorgia_{clean_name}_page_{PAGE_NUMBER}_in_stock.json"
    output_out = f"gorgia_{clean_name}_page_{PAGE_NUMBER}_out_of_stock.json"

    # === Сохраняем все товары ===
    with open(output_all, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    # === Отдельные списки ===
    in_stock_products = [p for p in products if p["in_stock"]]
    out_stock_products = [p for p in products if not p["in_stock"]]

    with open(output_in, "w", encoding="utf-8") as f:
        json.dump(in_stock_products, f, ensure_ascii=False, indent=2)

    with open(output_out, "w", encoding="utf-8") as f:
        json.dump(out_stock_products, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Всего товаров: {len(products)}")
    print(f"📦 В наличии: {len(in_stock_products)} → {output_in}")
    print(f"🚫 Нет в наличии: {len(out_stock_products)} → {output_out}")
    print(f"🗂 Все товары сохранены в {output_all}")