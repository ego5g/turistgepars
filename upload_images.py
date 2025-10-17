import requests
import json
from pathlib import Path
import time

# === Настройки ===
API_KEY = "16ccb20b7d07ea5522785bbda2a2ca64"
IMG_DIR = Path("images_webp")
OUT_FILE = Path("uploaded_images.json")

API_URL = "https://api.imgbb.com/1/upload"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
}

def upload_image(filepath):
    """Загружает одно изображение на imgbb.io"""
    try:
        with open(filepath, "rb") as f:
            response = requests.post(
                API_URL,
                headers=HEADERS,
                params={"key": API_KEY},
                files={"image": f},
                timeout=30
            )
        data = response.json()
        if response.status_code == 200 and data.get("data"):
            return data["data"]["url"]
        else:
            print(f"⚠️ Ошибка: {data.get('error', {}).get('message', 'неизвестно')}")
            return None
    except Exception as e:
        print(f"❌ Не удалось загрузить {filepath.name}: {e}")
        return None

def main():
    images = sorted(IMG_DIR.glob("*"))
    results = []

    for i, img_path in enumerate(images, start=1):
        print(f"{i:02d}. Загружаю → {img_path.name}")
        link = upload_image(img_path)
        if link:
            print(f"✅ Успешно: {link}\n")
            results.append({"file": img_path.name, "url": link})
        else:
            print("❌ Ошибка загрузки\n")

        time.sleep(1)  # чтобы не перегружать API

    # Сохраняем JSON
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n📦 Готово! Ссылки сохранены в {OUT_FILE}")

if __name__ == "__main__":
    main()
