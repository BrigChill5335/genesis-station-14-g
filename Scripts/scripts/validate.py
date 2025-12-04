import os
import re
import yaml
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROTOTYPES_DIR = os.path.join(SCRIPT_DIR, '..', '..', 'Resources', 'Prototypes')
LOCALE_DIR = os.path.join(SCRIPT_DIR, '..', '..', 'Resources', 'Locale')

def dir_list_or_warn(path):
    if not os.path.isdir(path):
        print(f"Warning: No '{path}' directory found!")
        return []
    else:
        print(f"'{path}' folder contents: {os.listdir(path)}")
        return os.listdir(path)

print("Current working directory:", os.getcwd())
print("Script DIR:", SCRIPT_DIR)
print("Prototypes DIR:", PROTOTYPES_DIR)
print("Locale DIR:", LOCALE_DIR)

# 1. Проверка прототипов
all_ids = defaultdict(list)
used_ids = set()
for root, _, files in os.walk(PROTOTYPES_DIR):
    for file in files:
        if file.endswith(".yml"):
            path = os.path.join(root, file)
            with open(path, encoding="utf-8") as f:
                try:
                    data = yaml.safe_load(f)
                    if not isinstance(data, dict):
                        continue
                    for item in data.get("prototypes", []):
                        id_ = item.get("id")
                        if id_:
                            all_ids[id_].append(path)
                    f.seek(0)
                    content = f.read()
                    found_ids = re.findall(r'id:\s*([a-zA-Z0-9_-]+)', content)
                    used_ids.update(found_ids)
                except Exception as e:
                    print(f"Failed to parse {path}: {e}")

# 2. Проверка локалей (по языковым папкам)
locale_ids_by_lang = defaultdict(lambda: defaultdict(list))
if os.path.isdir(LOCALE_DIR):
    for lang in os.listdir(LOCALE_DIR):
        lang_dir = os.path.join(LOCALE_DIR, lang)
        if not os.path.isdir(lang_dir): continue
        for root, _, files in os.walk(lang_dir):
            for file in files:
                if file.endswith(".ftl"):
                    path = os.path.join(root, file)
                    with open(path, encoding="utf-8") as f:
                        for line_no, line in enumerate(f, start=1):
                            match = re.match(r'([a-zA-Z0-9_-]+)\s*=', line)
                            if match:
                                lid = match.group(1)
                                locale_ids_by_lang[lang][lid].append(f"{path}:{line_no}")

# 3. Сбор ошибок с нормальным выводом
errors = []

# --- Дубликаты прототипов ---
for id_, paths in all_ids.items():
    if len(paths) > 1:
        errors.append({
            "type": "duplicate id",
            "desc": f"Дубликат прототипа '{id_}' встречается в нескольких файлах:",
            "id": id_,
            "paths": paths
        })

# --- ID без определения ---
for id_ in used_ids:
    if id_ not in all_ids:
        errors.append({
            "type": "no id",
            "desc": f"ID '{id_}' используется, но не определён ни в одном прототипе:",
            "id": id_,
            "paths": []
        })

# --- Дубликаты локалей только внутри одной языковой папки! ---
for lang, locale_ids in locale_ids_by_lang.items():
    for lid, paths in locale_ids.items():
        if len(paths) > 1:
            errors.append({
                "type": "duplicate locale",
                "desc": f"Дубликат локали '{lid}' найден в языке '{lang}':",
                "id": lid,
                "paths": paths
            })

# --- Отсутствие локалей для существующих ID (берём только по какой-нибудь из папок, например, en-US) ---
main_lang = "en-US" if "en-US" in locale_ids_by_lang else next(iter(locale_ids_by_lang), None)
if main_lang:
    locale_ids_mainlang = locale_ids_by_lang[main_lang]
    for id_ in all_ids:
        if id_ not in locale_ids_mainlang:
            errors.append({
                "type": "invalid locale",
                "desc": f"Для id '{id_}' нет локали в '{main_lang}':",
                "id": id_,
                "paths": []
            })

# --- Красивый финальный вывод ---
print("\n====== ИТОГ ВАЛИДАЦИИ ======\n")
if not errors:
    print("✔️ Всё отлично! Ошибок не найдено.\n")
else:
    # Группируем по типу ошибки и нумеруем внутри
    grouped = defaultdict(list)
    for err in errors:
        grouped[err['type']].append(err)

    num = 1
    for err_type, err_list in grouped.items():
        type_title = {
            "duplicate id": "Дубликат ID прототипа",
            "no id": "ID используется, но не определён",
            "duplicate locale": "Дубликат локали внутри языка",
            "invalid locale": f"Нет локализации для ID (в {main_lang})"
        }.get(err_type, err_type)

        print(f"{num}. {type_title}")
        for i, err in enumerate(err_list, 1):
            print(f"   {num}.{i}) {err['desc']}")
            print(f"       ID: {err['id']}")
            for path in err["paths"]:
                print(f"          -> {path}")
        print("--------------------------------------------------")
        num += 1

    print("\n❌ Всего проблем: %d\n" % len(errors))
    exit(1)
