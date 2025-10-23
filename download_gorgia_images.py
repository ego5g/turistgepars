import requests
import json
import time
from pathlib import Path
import urllib.parse

# === Настройки ===
JSON_FILE = "sad1.json"
SAVE_DIR = Path("images_webp")
SAVE_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": "https://gorgia.ge/"
}

def convert_to_webp_url(old_url):
    """
    Преобразует ссылку формата:
    https://gorgia.ge/images/thumbnails/240/240/detailed/73/BM-00206082.jpg
    в
    https://gorgia.ge/images/ab__webp/thumbnails/1100/900/detailed/73/BM-00206082_jpg.webp
    """
    if not old_url:
        return None

    new_url = (
        old_url
        .replace("/images/thumbnails/240/240/", "/images/ab__webp/thumbnails/1100/900/")
        .replace(".jpg", "_jpg.webp")
        .replace(".JPG", "_jpg.webp")
        .replace(".jpeg", "_jpg.webp")
        .replace(".png", "_jpg.webp")
    )
    return new_url

def download_image(url, out_path):
    try:
        r = requests.get(url, headers=HEADERS, stream=True, timeout=20)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(1024 * 32):
                    f.write(chunk)
            return True
        else:
            print(f"⚠️ {url} → {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка при загрузке {url}: {e}")
        return False

def main():
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        products = json.load(f)

    for i, p in enumerate(products, start=1):
        old_url = p.get("image_url")
        if not old_url:
            continue

        webp_url = convert_to_webp_url(old_url)
        filename = urllib.parse.unquote(webp_url.split("/")[-1])
        save_path = SAVE_DIR / filename

        print(f"{i:02d}. Скачиваю → {filename}")

        if download_image(webp_url, save_path):
            print("✅ Успешно сохранено\n")
        else:
            print("❌ Не удалось скачать\n")

        time.sleep(0.5)

if __name__ == "__main__":
    main()
