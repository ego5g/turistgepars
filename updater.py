#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup, NavigableString
import json
import urllib.parse
import time
from pathlib import Path
import base64

# === Настройки ===
BASE_URL = "https://gorgia.ge"
IMGBB_API_KEY = "16ccb20b7d07ea5522785bbda2a2ca64"
SAVE_DIR = Path("images_temp")
SAVE_DIR_FALSE = SAVE_DIR / "false"
SAVE_DIR.mkdir(exist_ok=True)
SAVE_DIR_FALSE.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

# === Получение HTML страницы ===
def get_soup(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"❌ Ошибка загрузки {url}: {e}")
        return None

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
        print(f"  ❌ Ошибка скачивания {url}: {e}")
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
            print(f"  ⚠️ Ошибка загрузки на imgbb: {r.text}")
    except Exception as e:
        print(f"  ❌ Ошибка при загрузке на imgbb: {e}")
    return None

# === Получение цены со страницы ===
def get_price_from_page(soup):
    """Извлекает цену товара"""
    price_tag = soup.select_one(".ty-price-num")
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
    return price

# === Получение статуса наличия ===
def get_availability_from_page(soup):
    """Извлекает информацию о наличии"""
    stock_tag = soup.select_one(".ty-qty-in-stock")
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
    return availability, in_stock

# === Получение всех URL фото (без дублей) ===
def get_all_image_urls(soup):
    """Извлекает все уникальные URL фото товара"""
    image_urls = []
    seen_urls = set()
    
    # === Основное фото ===
    img_tag = soup.select_one(".ut2-gl__image img, .product-image img")
    if not img_tag:
        img_tag = soup.select_one("img[alt*='product']")
    
    if img_tag and "src" in img_tag.attrs:
        main_url = img_tag["src"]
        if main_url and main_url not in seen_urls:
            webp_url = convert_to_webp_url(main_url)
            if webp_url:
                image_urls.append(webp_url)
                seen_urls.add(webp_url)
    
    # === Дополнительные фото из data-атрибутов ===
    additional_items = soup.select(".item[data-ca-product-additional-image-src]")
    for item in additional_items:
        srcset = item.get("data-ca-product-additional-image-srcset")
        if srcset:
            url = srcset.split()[0].strip()
            if url and url not in seen_urls:
                image_urls.append(url)
                seen_urls.add(url)
        elif "data-ca-product-additional-image-src" in item.attrs:
            url = item["data-ca-product-additional-image-src"]
            if url and url not in seen_urls:
                image_urls.append(url)
                seen_urls.add(url)
    
    return image_urls

# === Обновление товара ===
def update_product(product):
    """Обновляет информацию о товаре со страницы"""
    link = product.get("link")
    
    if not link:
        print(f"❌ ID {product.get('id')}: Нет ссылки на товар")
        return None
    
    print(f"\n🔗 Обновляю: {product.get('title')} ({product.get('id')})")
    print(f"   Ссылка: {link}")
    
    soup = get_soup(link)
    if not soup:
        return None
    
    # === Получаем новые данные ===
    new_price = get_price_from_page(soup)
    new_availability, new_in_stock = get_availability_from_page(soup)
    new_image_urls_list = get_all_image_urls(soup)
    
    # === Логирование изменений ===
    changes = []
    
    if new_price and new_price != product.get("price"):
        changes.append(f"Цена: {product.get('price')} → {new_price}")
        product["price"] = new_price
    
    if new_availability != product.get("availability"):
        changes.append(f"Наличие: {product.get('availability')} → {new_availability}")
        product["availability"] = new_availability
    
    if new_in_stock != product.get("in_stock"):
        changes.append(f"В наличии: {product.get('in_stock')} → {new_in_stock}")
        product["in_stock"] = new_in_stock
    
    # === Обновляем дополнительные фото ===
    uploaded_additional_urls = []
    
    if new_image_urls_list and len(new_image_urls_list) > 1:
        # Пропускаем первое фото (основное не трогаем)
        for idx, img_url in enumerate(new_image_urls_list[1:], 2):
            try:
                filename = Path(img_url.split("/")[-1])
                filename = filename.with_stem(filename.stem + f"_{idx}")
                
                if new_in_stock:
                    temp_path = SAVE_DIR / filename
                    if download_image(img_url, temp_path):
                        uploaded = upload_to_imgbb(temp_path)
                        if uploaded:
                            uploaded_additional_urls.append(uploaded)
                            print(f"  📸 Фото {idx}: Загружено ✓")
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
        
        if uploaded_additional_urls:
            changes.append(f"Добавлены фото: {len(uploaded_additional_urls)}")
            product["image_urls"] = uploaded_additional_urls
    
    # === Вывод результатов ===
    if changes:
        print(f"   ✅ Изменения:")
        for change in changes:
            print(f"      • {change}")
    else:
        print(f"   ℹ️ Изменений не найдено")
    
    time.sleep(1)
    return product

# === Основной запуск ===
def main():
    # === Загружаем JSON файл ===
    input_file = input("Введите имя JSON файла (например: products.json): ").strip()
    
    if not Path(input_file).exists():
        print(f"❌ Файл {input_file} не найден")
        return
    
    with open(input_file, "r", encoding="utf-8") as f:
        products = json.load(f)
    
    print(f"\n📦 Загружено {len(products)} товаров\n")
    
    # === Обновляем каждый товар ===
    updated_products = []
    for i, product in enumerate(products, 1):
        updated = update_product(product)
        if updated:
            updated_products.append(updated)
        print(f"[{i}/{len(products)}]")
    
    # === Разделяем на файлы по наличию ===
    in_stock_products = [p for p in updated_products if p["in_stock"]]
    out_stock_products = [p for p in updated_products if not p["in_stock"]]
    
    # === Генерируем имена файлов ===
    base_name = Path(input_file).stem
    output_all = f"{base_name}_updated_all.json"
    output_in = f"{base_name}_updated_in_stock.json"
    output_out = f"{base_name}_updated_out_of_stock.json"
    
    # === Сохраняем файлы ===
    with open(output_all, "w", encoding="utf-8") as f:
        json.dump(updated_products, f, ensure_ascii=False, indent=2)
    
    with open(output_in, "w", encoding="utf-8") as f:
        json.dump(in_stock_products, f, ensure_ascii=False, indent=2)
    
    with open(output_out, "w", encoding="utf-8") as f:
        json.dump(out_stock_products, f, ensure_ascii=False, indent=2)
    
    # === Итоги ===
    print(f"\n" + "="*60)
    print(f"✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО")
    print(f"="*60)
    print(f"📦 Всего обновлено: {len(updated_products)}")
    print(f"✓ В наличии: {len(in_stock_products)} → {output_in}")
    print(f"✗ Нет в наличии: {len(out_stock_products)} → {output_out}")
    print(f"📄 Все товары: {output_all}")
    print(f"="*60)

if __name__ == "__main__":
    main()