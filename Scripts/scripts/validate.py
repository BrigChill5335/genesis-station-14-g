import os
import re
import yaml
from collections import defaultdict

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# --------- Сканирование всех Prototypes ----------

prototypes_files = []
for root, dirs, files in os.walk(REPO_ROOT):
    for d in dirs:
        if d.lower() == "prototypes":
            prototypes_dir = os.path.join(root, d)
            for prow, _, pfiles in os.walk(prototypes_dir):
                for pf in pfiles:
                    if pf.endswith(".yml"):
                        prototypes_files.append(os.path.join(prow, pf))

all_ids = defaultdict(list)
used_ids = set()

for path in prototypes_files:
    with open(path, encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
            if not isinstance(data, dict): continue
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

# --------- Сканирование всех Locale ----------

locale_ftl_files = []
for root, dirs, files in os.walk(REPO_ROOT):
    for d in dirs:
        if d.lower() == "locale":
            locale_dir = os.path.join(root, d)
            for lrow, _, lf in os.walk(locale_dir):
                for ftlfile in lf:
                    if ftlfile.endswith(".ftl"):
                        locale_ftl_files.append(os.path.join(lrow, ftlfile))

# Определяем язык по имени папки сразу под Locale:
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

# Дубликаты прототипов
for id_, paths in all_ids.items():
    if len(paths) > 1:
        errors.append({
            "type": "duplicate id",
            "desc": f"Дубликат прототипа '{id_}' встречается в нескольких файлах:",
            "id": id_,
            "paths": paths
        })

# ID без определения
for id_ in used_ids:
    if id_ not in all_ids:
        errors.append({
            "type": "no id",
            "desc": f"ID '{id_}' используется, но не определён ни в одном прототипе:",
            "id": id_,
            "paths": []
        })

# Дубликаты локалей внутри каждого языка
for lang, locale_ids in locale_ids_by_lang.items():
    for lid, paths in locale_ids.items():
        if len(paths) > 1:
            errors.append({
                "type": "duplicate locale",
                "desc": f"Дубликат локали '{lid}' найден в языке '{lang}':",
                "id": lid,
                "paths": paths
            })

# Нет локализации для существующих ID (только по en-US, иначе слишком много)
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

# --------- Финальный красивый вывод ---------

print("\n====== ИТОГ ВАЛИДАЦИИ ======\n")
if not errors:
    print("✔️ Всё отлично! Ошибок не найдено.\n")
else:
    # Группируем и нумеруем удобно
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
