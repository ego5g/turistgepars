import requests
from bs4 import BeautifulSoup, NavigableString
import json
import urllib.parse

BASE_URL = "https://gorgia.ge"
CATEGORY_URL = "https://gorgia.ge/ka/bagi/sapiknike-inventari/?features_hash="

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

def get_soup(url):
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def parse_product(card):
    # Название
    title_tag = card.select_one(".ut2-gl__name a")
    title = title_tag.get_text(strip=True) if title_tag else None

    # Ссылка
    link = urllib.parse.urljoin(BASE_URL, title_tag["href"]) if title_tag and title_tag.get("href") else None

    # Цена — только первая часть до <sup>
    price_tag = card.select_one(".ty-price-num")
    price = None
    if price_tag:
        # попробуем найти первый прямой текстовый узел (до любых вложенных тегов, например <sup>)
        first_text = None
        for child in price_tag.children:
            if isinstance(child, NavigableString):
                txt = str(child).strip()
                if txt:
                    first_text = txt
                    break
        # запасной вариант: взять весь текст и удалить содержимое sup (если прямой текст не найден)
        if not first_text:
            # удалим текст внутри всех sup, если есть, затем взять оставшийся
            sup_tags = price_tag.find_all('sup')
            for s in sup_tags:
                s.extract()
            first_text = price_tag.get_text(strip=True)
        if first_text:
            price = first_text + " ₾"

    # Фото
    img_tag = card.select_one(".ut2-gl__image img")
    image_url = urllib.parse.urljoin(BASE_URL, img_tag["src"]) if img_tag and img_tag.get("src") else None

    # Описание (если есть на карточке)
    desc_tag = card.select_one(".product-description")
    description = desc_tag.get_text(strip=True) if desc_tag else None

    return {
        "title": title,
        "price": price,
        "description": description,
        "image_url": image_url,
        "link": link
    }

def scrape_category():
    soup = get_soup(CATEGORY_URL)
    cards = soup.select(".ut2-gl__body")
    print(f"Найдено {len(cards)} товаров")
    data = [parse_product(card) for card in cards]
    return data

if __name__ == "__main__":
    products = scrape_category()
    with open("products.json", "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"✅ Сохранено {len(products)} товаров в products.json")
