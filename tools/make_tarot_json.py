import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_DIR / "data/tarot-images.json"
OUTPUT_FILE = PROJECT_DIR / "data/tarot_cards_zh.json"

MAJOR_ARCANA = {
    "The Fool": {
        "name_zh": "愚者",
        "keywords": ["开始", "冒险", "自由"],
        "desc": "新的起点，未知的旅程"
    },
    "The Magician": {
        "name_zh": "魔术师",
        "keywords": ["行动", "创造", "掌控"],
        "desc": "意志与行动的结合"
    },
    "The High Priestess": {
        "name_zh": "女祭司",
        "keywords": ["直觉", "神秘", "内在"],
        "desc": "内心的声音与隐藏知识"
    },
    "The Empress": {
        "name_zh": "皇后",
        "keywords": ["丰盛", "滋养", "创造"],
        "desc": "生命力与成长"
    },
    "The Emperor": {
        "name_zh": "皇帝",
        "keywords": ["秩序", "权威", "结构"],
        "desc": "规则与掌控"
    },
    "The Hierophant": {
        "name_zh": "教皇",
        "keywords": ["传统", "信仰", "规范"],
        "desc": "社会规则与精神指引"
    },
    "The Lovers": {
        "name_zh": "恋人",
        "keywords": ["选择", "关系", "连接"],
        "desc": "情感与抉择"
    },
    "The Chariot": {
        "name_zh": "战车",
        "keywords": ["意志", "前进", "胜利"],
        "desc": "控制与突破"
    },
    "Strength": {
        "name_zh": "力量",
        "keywords": ["勇气", "控制", "内在力量"],
        "desc": "柔性的力量"
    },
    "The Hermit": {
        "name_zh": "隐者",
        "keywords": ["独处", "思考", "寻找"],
        "desc": "向内探索"
    },
    "Wheel of Fortune": {
        "name_zh": "命运之轮",
        "keywords": ["变化", "循环", "命运"],
        "desc": "不可控的转变"
    },
    "Justice": {
        "name_zh": "正义",
        "keywords": ["公平", "判断", "平衡"],
        "desc": "因果与衡量"
    },
    "The Hanged Man": {
        "name_zh": "倒吊人",
        "keywords": ["牺牲", "视角", "暂停"],
        "desc": "换个角度看世界"
    },
    "Death": {
        "name_zh": "死神",
        "keywords": ["结束", "转变", "重生"],
        "desc": "旧的结束带来新的开始"
    },
    "Temperance": {
        "name_zh": "节制",
        "keywords": ["平衡", "融合", "调和"],
        "desc": "中庸与整合"
    },
    "The Devil": {
        "name_zh": "恶魔",
        "keywords": ["束缚", "欲望", "依赖"],
        "desc": "被困与执念"
    },
    "The Tower": {
        "name_zh": "高塔",
        "keywords": ["崩塌", "冲击", "觉醒"],
        "desc": "突然的改变"
    },
    "The Star": {
        "name_zh": "星星",
        "keywords": ["希望", "治愈", "指引"],
        "desc": "黑暗中的光"
    },
    "The Moon": {
        "name_zh": "月亮",
        "keywords": ["迷惑", "潜意识", "不安"],
        "desc": "未知与幻想"
    },
    "The Sun": {
        "name_zh": "太阳",
        "keywords": ["成功", "快乐", "能量"],
        "desc": "清晰与生命力"
    },
    "Judgement": {
        "name_zh": "审判",
        "keywords": ["觉醒", "复苏", "评判"],
        "desc": "自我觉察"
    },
    "The World": {
        "name_zh": "世界",
        "keywords": ["完成", "整合", "圆满"],
        "desc": "阶段的终结与完成"
    },
}

SUIT_ZH = {
    "Cups": "圣杯",
    "Swords": "宝剑",
    "Wands": "权杖",
    "Pentacles": "星币",
}

RANK_ZH = {
    "Ace": "一",
    "Two": "二",
    "Three": "三",
    "Four": "四",
    "Five": "五",
    "Six": "六",
    "Seven": "七",
    "Eight": "八",
    "Nine": "九",
    "Ten": "十",
    "Page": "侍从",
    "Knight": "骑士",
    "Queen": "王后",
    "King": "国王",
}

SUIT_KEYWORDS = {
    "Cups": ["情感", "关系", "感受"],
    "Swords": ["思维", "冲突", "判断"],
    "Wands": ["行动", "热情", "意志"],
    "Pentacles": ["物质", "现实", "积累"],
}

RANK_DESC = {
    "Ace": "新的开端，能量初现",
    "Two": "平衡、选择与互动",
    "Three": "成长、合作与扩展",
    "Four": "稳定、停滞或守成",
    "Five": "冲突、缺失或不安",
    "Six": "过渡、调整与回流",
    "Seven": "评估、挑战与坚持",
    "Eight": "推进、专注与修炼",
    "Nine": "成熟、收获与临界点",
    "Ten": "完成、满溢或终局",
    "Page": "信息、起步与学习",
    "Knight": "推进、行动与冲劲",
    "Queen": "内化、掌控与滋养",
    "King": "成熟、主导与定型",
}


def make_minor_arcana_translation(name_en: str, suit: str):
    # 例如: Ace of Cups / Queen of Swords
    rank = name_en.split(" of ")[0]
    suit_zh = SUIT_ZH[suit]
    rank_zh = RANK_ZH[rank]
    name_zh = f"{suit_zh}{rank_zh}"
    keywords = SUIT_KEYWORDS[suit]
    desc = f"{suit_zh}领域中的{RANK_DESC[rank]}"
    return name_zh, keywords, desc


def convert_cards(src):
    """Normalize the bundled deck or the optional image-enriched deck."""
    out_cards = []

    for card in src["cards"]:
        name_en = card["name"]
        arcana_raw = card["arcana"]
        suit = card.get("suit")
        prefix = {"Cups": "c", "Swords": "s", "Wands": "w", "Pentacles": "p"}.get(suit, "m")
        img = card.get("img") or f"{prefix}{int(card['number']):02d}.jpg"

        if arcana_raw == "Major Arcana":
            extra = MAJOR_ARCANA[name_en]
            out_cards.append({
                "name_en": name_en,
                "name_zh": extra["name_zh"],
                "arcana": "Major",
                "suit": None,
                "keywords": extra["keywords"],
                "desc": extra["desc"],
                "img": img
            })
        else:
            name_zh, keywords, desc = make_minor_arcana_translation(name_en, suit)
            out_cards.append({
                "name_en": name_en,
                "name_zh": name_zh,
                "arcana": "Minor",
                "suit": suit,
                "keywords": keywords,
                "desc": desc,
                "img": img
            })

    return out_cards


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build WESI's translated tarot deck.")
    parser.add_argument("--input", type=Path, default=INPUT_FILE if INPUT_FILE.exists() else PROJECT_DIR / "data/tarot.json")
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE)
    args = parser.parse_args()
    with args.input.open(encoding="utf-8") as stream:
        cards = convert_cards(json.load(stream))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"cards": cards}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Done: {args.output} ({len(cards)} cards)")


if __name__ == "__main__":
    main()
