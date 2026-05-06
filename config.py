import json
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name("findnote_config.json")

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {"search_paths": [], "width": 80}
