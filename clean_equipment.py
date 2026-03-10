import json
import os

def clean_equipment_data(filename):
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        return

    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    changed = False
    for item in data:
        # For classes.json
        if "starting_equipment" in item:
            for opt in item["starting_equipment"]:
                if opt["items"].endswith("; or"):
                    opt["items"] = opt["items"][:-4]
                    changed = True
                elif opt["items"].endswith(";"):
                    opt["items"] = opt["items"][:-1]
                    changed = True
        
        # For backgrounds.json
        if "equipment" in item:
            for opt in item["equipment"]:
                if opt["items"].endswith("; or"):
                    opt["items"] = opt["items"][:-4]
                    changed = True
                elif opt["items"].endswith(";"):
                    opt["items"] = opt["items"][:-1]
                    changed = True

    if changed:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Updated {filename}")
    else:
        print(f"No changes needed for {filename}")

if __name__ == "__main__":
    clean_equipment_data('c:/VibeDnD/data/classes.json')
    clean_equipment_data('c:/VibeDnD/data/backgrounds.json')
