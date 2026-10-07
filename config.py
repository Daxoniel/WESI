from pathlib import Path
from typing import Any, Dict

APP_TITLE = "WESI（Wage Extraction & Survival Interface）"

# =========================
# Paths
# =========================
PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
ASSETS_DIR = PROJECT_DIR / "assets"
PET_DIR = ASSETS_DIR / "pets"
AVATAR_DIR = ASSETS_DIR / "avatars"
TAROT_DIR = ASSETS_DIR / "tarot"
D2DATA_DIR = DATA_DIR / "d2data_json"
TAROT_HISTORY_FILE = DATA_DIR / "tarot_history.json"
for folder in [DATA_DIR, ASSETS_DIR, PET_DIR, AVATAR_DIR, TAROT_DIR, D2DATA_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

DATA_FILE = DATA_DIR / "app_state.json"
QUOTES_FILE = DATA_DIR / "quotes_library.json"

TAROT_JSON_FILE = DATA_DIR / "tarot_cards_zh.json"
PET_ITEMS_FILE = DATA_DIR / "pet_items.json"
PET_EVENTS_FILE = DATA_DIR / "pet_events.json"
JINRISHICI_TOKEN_FILE = DATA_DIR / "jinrishici_token.txt"
BATTLE_ATTACK_POINT_FILE = DATA_DIR / "battle_attack_point.json"
BATTLE_BASE_GAME_WEAPONS_FILE = DATA_DIR / "battle_base_game_weapons.json"
BATTLE_DAMAGE_TYPES_FILE = DATA_DIR / "battle_damage_types.json"
BATTLE_REACTIONS_FILE = DATA_DIR / "battle_reactions.json"
BATTLE_REAL_WEAPONS_FILE = DATA_DIR / "battle_real_weapons.json"
BATTLE_WARM_MESSAGES_FILE = DATA_DIR / "battle_warm_messages.json"

# =========================
# Theme / constants
# =========================
THEME_PRESETS = [
    "darkly", "cyborg", "superhero", "solar", "vapor",
    "litera", "flatly", "minty", "pulse"
]
CUSTOM_COLOR_KEYS = ["accent", "money", "card_bg", "status", "bg"]

PET_ITEMS = [
    {"name": "破碎的护身符", "rarity": "common", "desc": "摸鱼途中捡到的碎片，边缘仍有微光。"},
    {"name": "旧工牌挂绳", "rarity": "common", "desc": "似乎来自某个已经散会的世界。"},
    {"name": "暗金小戒指", "rarity": "rare", "desc": "像是从地牢里遗落的战利品。"},
    {"name": "符文碎片", "rarity": "rare", "desc": "摸起来发冷，像某种尚未成形的命运。"},
    {"name": "传奇螺母", "rarity": "legendary", "desc": "它不该出现在这里。"},
]
PET_EVENTS = [
    "在茶水间尽头遇到一位抱着回形针的陌生人，双方交换了一个神秘螺母。",
    "沿着楼道边缘摸鱼时，它在窗边发现了一页被风吹开的旧地图。",
    "它在会议室门外短暂停留，随后带回一枚看上去很重要但没人认领的徽章。",
    "它在打印机旁结识了一个沉默的旅人，对方递来一张写着星象的纸片。",
]
QUOTE_LIBRARY = [
    {"text": "今天不需要每一秒都证明自己。", "source": "WESI", "type": "default"},
    {"text": "你不是机器，停一下也没关系。", "source": "WESI", "type": "default"},
]
RARITY_WEIGHTS = {"common": 70, "rare": 25, "legendary": 5}
SPREADS = {
    "single": ["此刻"],
    "three": ["过去", "现在", "未来"],
    "choice": ["选项A", "选项B"],
    "relationship": ["你", "对方", "关系"],
}
SPREAD_LABELS = {
    "single": "单张 / Single",
    "three": "三张 / Three-card",
    "choice": "二选一 / Choice",
    "relationship": "关系 / Relationship",
    }
# =========================
# Defaults / storage
# =========================
DEFAULT_STATE: Dict[str, Any] = {
    "income": {
        "monthly_net_salary": 2600.0,
        "employment_start": "2026-04-01 00:00:00",
        "window_geometry": "520x640+120+80",
    },
    "theme": {
        "name": "darkly",
        "colors": {
            "accent": "#5dd6ff",
            "money": "#37f2a3",
            "card_bg": "#171a21",
            "status": "#8aa4c8",
            "bg": "#0f1115",
        },
    },
    "battle": {
        "default_target": "Boss",
        "targets": [
            {"name": "Boss", "avatar": ""},
            {"name": "Weekly Meeting", "avatar": ""},
            {"name": "KPI", "avatar": ""},
        ],
        "stats": {"total_hits": 0, "kills": 0, "sessions": 0},
    },
    "quotes": {
        "all": [],
        "favorites": [],
        "last_index": -1,
    },
    "pet": {
        "name": "Mochi",
        "image_path": "",
        "mood": "neutral",
        "affinity": 0,
        "forage_count": 0,
        "history": [],
        "inventory": [],
        "encounters": [],
        "next_forage_at": None,
    },
    "tarot": {
        "history": [],
        "last_draw_at": None,
    },
    "achievements": {
        "unlocked": [],
    },
}

