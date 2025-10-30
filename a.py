import unicodedata

file_path = "a.txt"

# Список категорий символов, которые могут быть «подозрительными»
suspicious_categories = ['Ll', 'Lu', 'Lo', 'Lm', 'Lt']  # буквы
suspicious_ranges = [
    (0x0400, 0x04FF),  # Кириллица
        (0x0370, 0x03FF),  # Греческие символы
            (0x1D400, 0x1D7FF),  # Математические алфавиты
            ]

            def is_suspicious(char):
                code = ord(char)
                    category = unicodedata.category(char)
                        if category in suspicious_categories:
                                for start, end in suspicious_ranges:
                                            if start <= code <= end:
                                                            return True
                                                                return False

                                                                with open(file_path, encoding="utf-8") as f:
                                                                    for lineno, line in enumerate(f, 1):
                                                                            for col, char in enumerate(line, 1):
                                                                                        if is_suspicious(char):
                                                                                                        print(f"Line {lineno}, Col {col}: {char} ({unicodedata.name(char, 'UNKNOWN')})")
                                                                                                        