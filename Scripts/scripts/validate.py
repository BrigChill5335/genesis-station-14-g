import os
import re
import yaml
from collections import defaultdict

# Настройки путей
PROTOTYPES_DIR = "Prototypes"
LOCALE_DIR = "Locale"

# --- 1. Проверка ID ---
all_ids = defaultdict(list)
used_ids = set()

for root, _, files in os.walk(PROTOTYPES_DIR):
    for file in files:
        if file.endswith(".yml"):
            path = os.path.join(root, file)
            with open(path, encoding="utf-8") as f:
                try:
                    data = yaml.safe_load(f)
                    for item in data.get("prototypes", []):
                        id_ = item.get("id")
                        if id_:
                            all_ids[id_].append(path)
                    # Найти все упоминания ID в файле (для проверки ссылок)
                    content = f.read()
                    found_ids = re.findall(r'\b([a-z0-9-]+)\b', content)
                    used_ids.update(found_ids)
                except Exception as e:
                    print(f"Failed to parse {path}: {e}")

# --- 2. Проверка дубликатов ID ---
errors = []

for id_, paths in all_ids.items():
    if len(paths) > 1:
        errors.append({
            "type": "duplicate id",
            "id": id_,
            "paths": paths
        })

# --- 3. Проверка отсутствующих ID (упоминаются, но нет определения) ---
for id_ in used_ids:
    if id_ not in all_ids:
        errors.append({
            "type": "no id",
            "id": id_,
            "paths": []  # тут можно добавить файл, где упоминался
        })

# --- 4. Проверка локалей ---
locale_ids = defaultdict(list)
for root, _, files in os.walk(LOCALE_DIR):
    for file in files:
        if file.endswith(".ftl"):
            path = os.path.join(root, file)
            with open(path, encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    match = re.match(r'([a-z0-9-]+)\s*=', line)
                    if match:
                        lid = match.group(1)
                        locale_ids[lid].append(f"{path}:{line_no}")

# --- 5. Дубликаты локалей ---
for lid, paths in locale_ids.items():
    if len(paths) > 1:
        errors.append({
            "type": "duplicate locale",
            "id": lid,
            "paths": paths
        })

# --- 6. Отсутствующие локали для определенных ID ---
for id_ in all_ids:
    if id_ not in locale_ids:
        errors.append({
            "type": "invalid locale",
            "id": id_,
            "paths": []
        })

# --- 7. Итоговый вывод ---
if errors:
    print("=== Validation Errors ===")
    for e in errors:
        print(f"[{e['type'].upper()}] {e['id']}")
        if e["paths"]:
            for p in e["paths"]:
                print(f"   -> {p}")
    exit(1)
else:
    print("All checks passed!")
