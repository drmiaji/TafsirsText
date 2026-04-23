import json

INVENTORY_FILE = r"D:\Quran_v4\TafsirsText\inventory\tafsirs\tafsirs_merged.json"
OUTPUT_FILE    = r"D:\Quran_v4\TafsirsText\inventory\tafsirs\tafsir_keys.json"

DEFAULT_VALUE = 1  # change per key below if needed

with open(INVENTORY_FILE, "r", encoding="utf-8") as f:
    inventory = json.load(f)

result = {}
for lang_entries in inventory["tafsirs"].values():
    for entry in lang_entries:
        key = entry.get("key", "")
        if key:
            result[key] = DEFAULT_VALUE

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"Written {len(result)} keys to {OUTPUT_FILE}")