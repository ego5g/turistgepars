#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup, NavigableString
import json
import urllib.parse
import time
from pathlib import Path
import base64

# === 🟢 Вводные переменные ===
CATEGORY_URL = "https://gorgia.ge/ka/bagi/"
PAGE_NUMBER = 4
START_ID = 91

# === Настройки ===
BASE_URL = "https://gorgia.ge"
IMGBB_API_KEY = "16ccb20b7d07ea5522785bbda2a2ca64"  # ключ imgbb
SAVE_DIR = Path("images_temp")
SAVE_DIR.mkdir(exist_ok=True)

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

        # === Фото ===
        img_tag = card.select_one(".ut2-gl__image img")
        image_url = urllib.parse.urljoin(BASE_URL, img_tag["src"]) if img_tag else None
        webp_url = convert_to_webp_url(image_url)

        # === Проверка наличия ===
        stock_tag = card.select_one(".ty-qty-in-stock")
        availability = "Неизвестно"
        in_stock = None
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

        # === Загрузка фото ===
        new_image_url = None
        if webp_url:
            filename = Path(webp_url.split("/")[-1])
            temp_path = SAVE_DIR / filename
            if download_image(webp_url, temp_path):
                uploaded = upload_to_imgbb(temp_path)
                if uploaded:
                    new_image_url = uploaded
                    print(f"📸 Загружено → {new_image_url}")
            time.sleep(0.5)

        products.append({
            "id": i,
            "category": "Сад",
            "title": title_ru,
            "price": price,
            "description": description_ru,
            "availability": availability,
            "in_stock": in_stock,
            "image_url": new_image_url or webp_url,
            "link": link
        })

        print(f"{i:03d}. {title_ru} — {price} ₾ — {availability}")
        time.sleep(1)

    return products

# === Основной запуск ===
if __name__ == "__main__":
    products = parse_page(CATEGORY_URL, PAGE_NUMBER, START_ID)
    output_name = f"gorgia_page_{PAGE_NUMBER}.json"
    with open(output_name, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Сохранено {len(products)} товаров в {output_name}")
