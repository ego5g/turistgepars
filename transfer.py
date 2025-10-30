import json

def transfer_descriptions():
    """
    Переносит описания (description) из файла up.json в targegorgia_ka_aveji_magidebi-da-merxebi_page_1_in_stock.jsont_file
    и сохраняет результат в descr.json.
    Старое описание перезаписывается новым.
    """
    source_file = 'up.json'
    target_file = 'gorgia_ka_aveji_magidebi-da-merxebi_page_1_in_stock.json'
    output_file = 'descr.json'

    try:
        # Чтение файлов
        print("📖 Чтение файлов...")
        with open(source_file, 'r', encoding='utf-8') as f:
            source_data = json.load(f)
        
        with open(target_file, 'r', encoding='utf-8') as f:
            target_data = json.load(f)
        
        print(f"✓ Источник: {len(source_data)} товаров")
        print(f"✓ Цель: {len(target_data)} товаров")
        
        # Создаем словарь описаний по ID
        descriptions_map = {item['id']: item['description'] for item in source_data if 'id' in item and 'description' in item}
        print(f"✓ Найдено описаний в источнике: {len(descriptions_map)}")
        
        # Переносим описания в целевой файл
        transferred = 0
        not_found = []

        for item in target_data:
            item_id = item.get('id')
            if item_id in descriptions_map:
                item['description'] = descriptions_map[item_id]
                transferred += 1
                print(f"✓ ID {item_id}: описание перенесено")
            else:
                not_found.append(item_id)
        
        # Сохраняем результат
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(target_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*60}")
        print(f"✅ ПЕРЕНОС ЗАВЕРШЕН")
        print(f"{'='*60}")
        print(f"Перенесено описаний: {transferred}")
        print(f"Не найдено в источнике: {len(not_found)}")
        if not_found and len(not_found) <= 10:
            print(f"Отсутствующие ID: {not_found}")
        elif not_found:
            print(f"Отсутствующих ID: {len(not_found)} (первые 10: {not_found[:10]})")
        
        print(f"Результат сохранен: {output_file}")
        print(f"{'='*60}\n")
        
        return True

    except FileNotFoundError as e:
        print(f"❌ Ошибка: файл не найден - {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка: некорректный JSON - {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при переносе: {str(e)}")
        return False


# Вызов функции
transfer_descriptions()
