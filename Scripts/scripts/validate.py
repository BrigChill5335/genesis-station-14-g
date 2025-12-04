import os
import re
import yaml
from collections import defaultdict

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# --------- Сканируем все прототипные YAML ---------
prototypes_files = []
for root, dirs, files in os.walk(REPO_ROOT):
    for file in files:
        if file.endswith(".yml"):
            prototypes_files.append(os.path.join(root, file))

all_ids = defaultdict(list)
used_proto_ids = set()  # ссылки на другие прототипы

yaml_id_key = "id"

for path in prototypes_files:
    with open(path, encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
            items = []
            # Если это словарь с ключом 'prototypes', работаем с его содержимым.
            if isinstance(data, dict) and "prototypes" in data and isinstance(data["prototypes"], list):
                items = data["prototypes"]
            # Если просто список, работаем напрямую.
            elif isinstance(data, list):
                items = data
            # Если это словарь и он сам прототип — оборачиваем в список.
            elif isinstance(data, dict):
                items = [data]

            for item in items:
                if not isinstance(item, dict):
                    continue
                # Считываем id (только верхний уровень!)
                id_value = item.get(yaml_id_key)
                if id_value:  # учитываем только если id есть
                    all_ids[id_value].append(path)

                # Находим ссылки на другие id (proto/prototype)
                # Смотрим в каждый ключ этого объекта
                for k, v in item.items():
                    # proto, prototype: string или список
                    # Обычно ключ называется proto или prototype
                    # Важно: не ищем дубликаты по этим ссылкам!
                    if k in ("proto", "prototype") and isinstance(v, str):
                        used_proto_ids.add(v)
                    elif k in ("proto", "prototype") and isinstance(v, list):
                        for vv in v:
                            if isinstance(vv, str):
                                used_proto_ids.add(vv)
            # А ещё ищем "id:" в сыром тексте (например, в parent), но не считаем их как id, а только как ссылки:
            # Можно добавить отдельную проверку при необходимости!
        except Exception as e:
            print(f"Failed to parse {path}: {e}")

# --------- Сканируем все Locale (по всем языкам) ---------
locale_ftl_files = []
for root, dirs, files in os.walk(REPO_ROOT):
    for file in files:
        if file.endswith(".ftl"):
            locale_ftl_files.append(os.path.join(root, file))

def get_lang(path):
    parts = path.replace("\\", "/").split("/")
    if "Locale" in parts:
        idx = parts.index("Locale")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return "unknown"

locale_ids_by_lang = defaultdict(lambda: defaultdict(list))
for path in locale_ftl_files:
    lang = get_lang(path)
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            match = re.match(r'([a-zA-Z0-9_-]+)\s*=', line)
            if match:
                lid = match.group(1)
                locale_ids_by_lang[lang][lid].append(f"{path}:{line_no}")

# --------- Проверки ----------

errors = []

# 1. Дубликаты прототипов по id (только верхний уровень словаря!)
for id_, paths in all_ids.items():
    if len(paths) > 1:
        errors.append({
            "type": "duplicate id",
            "desc": f"Дубликат прототипа (ID = {id_}), встречается в нескольких файлах:",
            "id": id_,
            "paths": paths
        })

# 2. Ссылки на несуществующие id (proto/prototype)
for p_id in used_proto_ids:
    if p_id not in all_ids:
        errors.append({
            "type": "missing proto id",
            "desc": f"ID '{p_id}' указан в proto/prototype, но не найден среди прототипов:",
            "id": p_id,
            "paths": []
        })

# 3. Дубликаты локалей (по языкам)
for lang, locale_ids in locale_ids_by_lang.items():
    for lid, paths in locale_ids.items():
        if len(paths) > 1:
            errors.append({
                "type": "duplicate locale",
                "desc": f"Дубликат локали '{lid}' найден в языке '{lang}':",
                "id": lid,
                "paths": paths
            })

# 4. Нет локализации для существующих id (только en-US, чтобы избежать спама)
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

# --------- Красивый финальный вывод ---------
print("\n====== ИТОГ ВАЛИДАЦИИ ======\n")
if not errors:
    print("✔️ Всё отлично! Ошибок не найдено.\n")
else:
    grouped = defaultdict(list)
    for err in errors:
        grouped[err['type']].append(err)

    num = 1
    for err_type, err_list in grouped.items():
        type_title = {
            "duplicate id": "1. Дубликат ID прототипа",
            "missing proto id": "2. Не найден целевой proto/prototype ID",
            "duplicate locale": "3. Дубликат локали внутри языка",
            "invalid locale": f"4. Нет локализации для ID (в {main_lang})"
        }.get(err_type, err_type)

        print(type_title)
        for i, err in enumerate(err_list, 1):
            print(f"   {num}.{i}) {err['desc']}")
            print(f"       ID: {err['id']}")
            for path in err["paths"]:
                print(f"          -> {path}")
        print("--------------------------------------------------")
        num += 1
    print(f"\n❌ Всего проблем: {len(errors)}\n")
    exit(1)
