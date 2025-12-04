import os
import re
import yaml
from collections import defaultdict

# Абсолютные пути к папкам относительно скрипта
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROTOTYPES_DIR = os.path.join(SCRIPT_DIR, '..', '..', 'Resources', 'Prototypes')
LOCALE_DIR = os.path.join(SCRIPT_DIR, '..', '..', 'Resources', 'Locale')

print("Current working directory:", os.getcwd())
print("Script DIR:", SCRIPT_DIR)
print("Prototypes DIR:", PROTOTYPES_DIR)
print("Locale DIR:", LOCALE_DIR)
if not os.path.isdir(PROTOTYPES_DIR):
    print(f"Warning: No '{PROTOTYPES_DIR}' directory found!")
else:
    print(f"'{PROTOTYPES_DIR}' folder contents: {os.listdir(PROTOTYPES_DIR)}")
if not os.path.isdir(LOCALE_DIR):
    print(f"Warning: No '{LOCALE_DIR}' directory found!")
else:
    print(f"'{LOCALE_DIR}' folder contents: {os.listdir(LOCALE_DIR)}")

# 1. Проверка ID
all_ids = defaultdict(list)
used_ids = set()
print("Scanning Prototypes...")
for root, _, files in os.walk(PROTOTYPES_DIR):
    for file in files:
        if file.endswith(".yml"):
            path = os.path.join(root, file)
            print(f"  Found prototype file: {path}")
            with open(path, encoding="utf-8") as f:
                try:
                    data = yaml.safe_load(f)
                    if not isinstance(data, dict):
                        print(f"    Warning: {path} is not a dict, got {type(data)}")
                        continue
                    for item in data.get("prototypes", []):
                        id_ = item.get("id")
                        if id_:
                            all_ids[id_].append(path)
                    f.seek(0)
                    content = f.read()
                    # Более узкая регулярка поиска id
                    found_ids = re.findall(r'id:\s*([a-zA-Z0-9_-]+)', content)
                    used_ids.update(found_ids)
                except Exception as e:
                    print(f"Failed to parse {path}: {e}")

errors = []

for id_, paths in all_ids.items():
    if len(paths) > 1:
        errors.append({"type": "duplicate id", "id": id_, "paths": paths})

for id_ in used_ids:
    if id_ not in all_ids:
        errors.append({"type": "no id", "id": id_, "paths": []})

# 4. Проверка локалей
locale_ids = defaultdict(list)
print("Scanning Locale...")
for root, _, files in os.walk(LOCALE_DIR):
    for file in files:
        if file.endswith(".ftl"):
            path = os.path.join(root, file)
            print(f"  Found locale file: {path}")
            with open(path, encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    match = re.match(r'([a-zA-Z0-9_-]+)\s*=', line)
                    if match:
                        lid = match.group(1)
                        locale_ids[lid].append(f"{path}:{line_no}")

for lid, paths in locale_ids.items():
    if len(paths) > 1:
        errors.append({"type": "duplicate locale", "id": lid, "paths": paths})

for id_ in all_ids:
    if id_ not in locale_ids:
        errors.append({"type": "invalid locale", "id": id_, "paths": []})

print(f"Total prototype IDs: {len(all_ids)}")
print(f"Total used IDs found: {len(used_ids)}")
print(f"Total locale IDs: {len(locale_ids)}")

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
