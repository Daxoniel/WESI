from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Tuple
import urllib.request
import urllib.error
import json
import random
import time
import shutil
from uuid import uuid4
from storage import read_json, write_json
from tools.make_tarot_json import convert_cards

from PIL import Image, ImageOps, ImageTk, ImageDraw

from config import (
    TAROT_JSON_FILE,
    PROJECT_DIR,
    QUOTES_FILE,
    QUOTE_LIBRARY,
    PET_ITEMS_FILE,
    PET_EVENTS_FILE,
    D2DATA_DIR,
    PET_ITEMS,
    PET_EVENTS,
    RARITY_WEIGHTS,
    TAROT_HISTORY_FILE,
    JINRISHICI_TOKEN_FILE,
    BATTLE_ATTACK_POINT_FILE,
    BATTLE_BASE_GAME_WEAPONS_FILE,
    BATTLE_DAMAGE_TYPES_FILE,
    BATTLE_REACTIONS_FILE,
    BATTLE_REAL_WEAPONS_FILE,
    BATTLE_WARM_MESSAGES_FILE,
 
)

# =========================
# Helpers
# =========================
def load_json_file(path, default=None):
    return read_json(path, default)


def load_tarot_cards():
    data = read_json(TAROT_JSON_FILE, {}, dict)
    cards = data.get("cards", [])
    required = {"name_en", "name_zh", "img", "desc"}
    if isinstance(cards, list) and cards and all(
        isinstance(c, dict) and required <= c.keys()
        and all(isinstance(c[k], str) for k in required)
        and isinstance(c.get("keywords", []), list)
        for c in cards
    ):
        return cards
    source = read_json(PROJECT_DIR / "data/tarot.json", {"cards": []}, dict)
    return convert_cards(source)


def load_tarot_history():
    return read_json(TAROT_HISTORY_FILE, [], list)


def save_tarot_history(history):
    write_json(TAROT_HISTORY_FILE, history)


def load_quote_library():
    data = read_json(QUOTES_FILE, QUOTE_LIBRARY, list)
    valid = [item for item in data if isinstance(item, dict)
             and isinstance(item.get("text"), str) and item["text"].strip()
             and isinstance(item.get("source"), str)]
    return valid or json.loads(json.dumps(QUOTE_LIBRARY, ensure_ascii=False))


def load_pet_items() -> List[Dict[str, Any]]:
    data = load_json_file(PET_ITEMS_FILE, PET_ITEMS)
    valid = [item for item in data if isinstance(item, dict)
             and all(isinstance(item.get(key), str) for key in ("name", "rarity", "desc"))] if isinstance(data, list) else []
    return valid or json.loads(json.dumps(PET_ITEMS, ensure_ascii=False))


def load_pet_events() -> List[str]:
    data = load_json_file(PET_EVENTS_FILE, PET_EVENTS)
    valid = [item for item in data if isinstance(item, str) and item.strip()] if isinstance(data, list) else []
    return valid or list(PET_EVENTS)


def import_d2_names_from_local_json() -> List[str]:
    names = set()
    candidate_keys = {"name", "Name", "namestr", "Namestr", "title", "Title"}
    for path in D2DATA_DIR.rglob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        def walk(obj: Any):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in candidate_keys and isinstance(v, str):
                        cleaned = v.strip()
                        if 1 < len(cleaned) <= 80:
                            names.add(cleaned)
                    walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)

        walk(data)
    return sorted(names)[:400]
def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            base[key] = deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def parse_dt(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def format_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def month_start(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def next_month_start(dt: datetime) -> datetime:
    if dt.month == 12:
        return dt.replace(year=dt.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return dt.replace(month=dt.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)


def day_start(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def year_start(dt: datetime) -> datetime:
    return dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)


def seconds_in_month(dt: datetime) -> float:
    return (next_month_start(dt) - month_start(dt)).total_seconds()


def monthly_rate_per_second(monthly_salary: float, dt: datetime) -> float:
    return monthly_salary / seconds_in_month(dt)


def earnings_between(start_dt: datetime, end_dt: datetime, monthly_salary: float) -> float:
    if end_dt <= start_dt:
        return 0.0
    total = 0.0
    cursor = start_dt
    while cursor < end_dt:
        month_end = next_month_start(cursor)
        segment_end = min(month_end, end_dt)
        total += (segment_end - cursor).total_seconds() * monthly_rate_per_second(monthly_salary, cursor)
        cursor = segment_end
    return total


def choose_weighted(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    weights = [RARITY_WEIGHTS.get(item.get("rarity", "common"), 1) for item in items]
    return random.choices(items, weights=weights, k=1)[0]


def safe_copy_image(path: str, target_dir: Path) -> str:
    src = Path(path)
    if not src.exists():
        return ""
    with Image.open(src) as image:
        image.verify()
    target_dir.mkdir(parents=True, exist_ok=True)
    dst = target_dir / f"{uuid4().hex}_{src.name}"
    shutil.copy2(src, dst)
    return str(dst)


def make_rounded_image(path: str, size: Tuple[int, int], radius: int = 20):
    if not Image:
        return None
    try:
        img = Image.open(path).convert("RGBA")
        img = ImageOps.fit(img, size, method=Image.Resampling.LANCZOS)
        mask = Image.new("L", size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
        img.putalpha(mask)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def rotate_image_for_tarot(path: str, reversed_card: bool, size: Tuple[int, int]):
    if not Image:
        return None
    try:
        img = Image.open(path).convert("RGBA")
        img = ImageOps.fit(img, size, method=Image.Resampling.LANCZOS)
        if reversed_card:
            img = img.rotate(180)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None
def get_jinrishici_token() -> str | None:
    # 先读本地 token
    if JINRISHICI_TOKEN_FILE.exists():
        try:
            token = JINRISHICI_TOKEN_FILE.read_text(encoding="utf-8").strip()
            if token:
                return token
        except Exception:
            pass

    # 没有就去申请一个新的
    try:
        with urllib.request.urlopen("https://v2.jinrishici.com/token", timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

        token = data.get("data", "").strip()
        if token:
            JINRISHICI_TOKEN_FILE.write_text(token, encoding="utf-8")
            return token
    except Exception:
        return None

    return None


def get_jinrishici_quote() -> dict | None:
    token = get_jinrishici_token()
    if not token:
        return None

    try:
        req = urllib.request.Request(
            url="https://v2.jinrishici.com/sentence",
            headers={
                "X-User-Token": token,
                "User-Agent": "WESI/1.0"
            },
            method="GET",
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))

        data = result.get("data", {})
        content = data.get("content", "").strip()

        origin = data.get("origin", {})
        author = origin.get("author", "").strip()
        title = origin.get("title", "").strip()

        if not content:
            return None

        source = ""
        if author and title:
            source = f"{author}《{title}》"
        elif title:
            source = title
        elif author:
            source = author
        else:
            source = "今日诗词"

        return {
            "text": content,
            "source": source,
            "type": "poetry"
        }

    except Exception:
        return None
    
def _load_strings(path, fallback):
    data = read_json(path, [], list)
    return [value for value in data if isinstance(value, str) and value.strip()] or list(fallback)


def load_battle_attack_points():
    return _load_strings(BATTLE_ATTACK_POINT_FILE, ["肩膀"])


def load_battle_base_game_weapons():
    return _load_strings(BATTLE_BASE_GAME_WEAPONS_FILE, ["泡沫锤"])


def load_battle_damage_types():
    return _load_strings(BATTLE_DAMAGE_TYPES_FILE, ["解压"])


def load_battle_reactions():
    return _load_strings(BATTLE_REACTIONS_FILE, ["压力散去了一点。"])


def load_battle_real_weapons():
    return _load_strings(BATTLE_REAL_WEAPONS_FILE, ["抱枕"])


def load_battle_warm_messages():
    return _load_strings(BATTLE_WARM_MESSAGES_FILE, ["休息一下，照顾好自己。"])
