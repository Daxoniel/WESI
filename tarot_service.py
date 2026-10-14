"""Offline readings: program-owned draws, position lenses and durable snapshots."""
import base64
import copy
import json
import random
import threading
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from config import PROJECT_DIR, TAROT_DIR, TAROT_HISTORY_FILE
from storage import read_json, write_json
from utils import load_tarot_cards
from tarot_reading import synthesize
from tarot_reference import reference_for
import tarot_ai


def spread(label, description, positions, coordinates=None):
    return {"label": label, "description": description, "positions": positions,
            "coordinates": coordinates or [[i, 0] for i in range(len(positions))]}

SPREADS = {
    "single": spread("单张指引", "聚焦此刻的一个主题", ["此刻"]),
    "three": spread("时间三牌", "回顾过去、理解现在、探索发展趋势", ["过去", "现在", "未来趋势"]),
    "choice": spread("二选一", "对照两个选项，帮助梳理取舍", ["选项A", "选项B"]),
    "relationship": spread("关系镜像", "观察彼此的立场与互动", ["你", "对方", "关系"]),
    "guidance": spread("现状与建议", "适合具体问题的行动梳理", ["现状", "阻碍", "建议"]),
    "five": spread("五牌探索", "辨认背景、资源与下一步", ["现状", "阻碍", "支持", "建议", "可能发展"], [[1,0],[0,1],[2,1],[1,2],[1,1]]),
    "horseshoe": spread("七牌马蹄", "从背景到选择的完整观察", ["过去", "现在", "未来趋势", "建议", "外部影响", "阻碍", "可能发展"], [[0,0],[0,1],[1,2],[2,3],[3,2],[4,1],[4,0]]),
    "celtic": spread("凯尔特十字", "适合复杂问题，逐层观察内外因素", ["核心现状", "交叉挑战", "深层基础", "过去", "意识目标", "近期趋势", "你的立场", "外部环境", "期待与担忧", "可能发展"], [[1,1],[1,1],[1,2],[0,1],[1,0],[2,1],[3,3],[3,2],[3,1],[3,0]]),
}
LENSES = {
    "此刻": "把这张牌当作当前最值得留意的主题。", "过去": "回顾这一模式是否影响了当前处境，不必把过去当作必然重复的结局。",
    "现在": "观察这一主题在当前事实、感受或行动中如何出现。", "现状": "先用可观察的事实核对这张牌所提出的主题。", "核心现状": "先界定问题的核心，区分事实与自己的解释。",
    "未来趋势": "这是沿用当前模式时可探索的方向，行动与环境变化都会改变它。", "近期趋势": "观察近期可能需要应对的变化，先准备可调整的小步骤。", "可能发展": "把结果当作一种情境来准备，而不是已经确定的预言。",
    "阻碍": "检查这一主题是否表现为缺失、过度或难以落实的环节。", "交叉挑战": "与核心现状对照，寻找两种需求之间的拉扯。",
    "建议": "把牌义转化为一个自己可以执行、观察和调整的行动。", "支持": "辨认可用资源、技能和愿意支持你的人。",
    "你": "关注自己的感受、边界与沟通方式。", "对方": "将此视作需要沟通验证的视角，不替对方断定想法。", "关系": "观察共同建立的互动模式，而非只归因于某一个人。",
    "选项A": "针对选项A列出收益、成本和可验证的条件。", "选项B": "针对选项B使用同一标准核对，避免只比较想象中的结果。",
    "外部影响": "辨认环境条件与他人行为中哪些可以协商。", "外部环境": "区分外部事实与对他人动机的猜测。",
    "深层基础": "回看长期习惯、价值与现实条件对问题的影响。", "意识目标": "明确自己想得到什么，以及愿意承担哪些代价。",
    "你的立场": "检查自己的资源、边界和参与方式。", "期待与担忧": "区分希望与焦虑，核实它们各自依赖的事实。",
}


class TarotService:
    def __init__(self, history_path=TAROT_HISTORY_FILE, clock=datetime.now, rng=None):
        self.path = Path(history_path)
        self.clock = clock
        self.rng = rng or random.SystemRandom()
        self.lock = threading.RLock()
        self._pending_ai = {}
        self.deck = load_tarot_cards()
        self.meanings = json.loads((PROJECT_DIR / "data/tarot_meanings_zh.json").read_text(encoding="utf-8"))

    def catalog(self):
        return {"spreads": SPREADS, "deck_size": len(self.deck), "ai": tarot_ai.status()}

    def image(self, filename):
        path = TAROT_DIR / Path(filename).name
        if path.suffix.lower() not in (".jpg", ".png") or not path.is_file():
            return None
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()

    def draw(self, spread_key, question=""):
        with self.lock:
            if not isinstance(spread_key, str) or spread_key not in SPREADS or not isinstance(question, str) or len(question) > 500:
                return {"ok": False, "error": "请选择有效牌阵，问题不超过 500 字。"}
            layout = SPREADS[spread_key]
            if len(self.deck) < len(layout["positions"]):
                return {"ok": False, "error": "牌库不足，无法完成这个牌阵。"}
            cards = []
            for position, card in zip(layout["positions"], self.rng.sample(self.deck, len(layout["positions"]))):
                reverse = self.rng.choice([False, True])
                meaning = self.meanings.get(card["name_en"])
                if not meaning:
                    return {"ok": False, "error": "牌库存在未支持的牌名，请检查本地牌库。"}
                core = meaning["reversed" if reverse else "upright"]
                cards.append({**copy.deepcopy(card), "position": position, "reversed": reverse,
                    "desc": core, "reading": {"core": core, "position": LENSES[position],
                    "action": meaning["reversed_action" if reverse else "upright_action"],
                    "reflection": f"在「{position}」这个角度，你有哪些事实支持这一主题？哪些地方并不符合你的经历？"}, "reference": reference_for({**card,"reversed":reverse})})
            entry = {"id": uuid4().hex, "version": 2, "time": self.clock().strftime("%Y-%m-%d %H:%M:%S"),
                "question": question.strip(), "spread": spread_key, "spread_label": layout["label"],
                "layout": copy.deepcopy(layout), "cards": cards,
                "summary": "离线牌义提供反思线索，不会自动推断你的问题。逐张对照牌位，再检查不同主题之间的联系。"}
            entry["synthesis"] = synthesize(entry)
            try:
                history = read_json(self.path, [], list)
                history.append(entry)
                write_json(self.path, history)
            except OSError:
                return {"ok": False, "error": "历史保存失败，本次未确认记录，请检查目录权限。"}
            return {"ok": True, "entry": entry}

    def history(self):
        with self.lock:
            return list(reversed(read_json(self.path, [], list)))

    def ai_reading(self, entry_id):
        # Serialize generation to avoid duplicate provider charges for one entry.
        with self.lock:
            try:
                history = read_json(self.path, [], list)
                entry = next((item for item in history if isinstance(item, dict) and item.get('id') == entry_id), None)
                if not entry:
                    return {'ok': False, 'error': '阅读记录不存在，请从历史选择一条新版记录。'}
                if entry.get('ai_reading'):
                    return {'ok': True, 'entry': entry}
                report = self._pending_ai.get(entry_id)
                if report is None:
                    report = tarot_ai.interpret(copy.deepcopy(entry))
                    self._pending_ai[entry_id] = report
                updated = copy.deepcopy(history)
                target = next(item for item in updated if isinstance(item, dict) and item.get('id') == entry_id)
                target['ai_reading'] = report
                write_json(self.path, updated)
                self._pending_ai.pop(entry_id, None)
                return {'ok': True, 'entry': target}
            except OSError:
                return {'ok': False, 'error': 'AI 请求或历史保存失败；原阅读保留，请检查服务与目录权限。'}
            except (ValueError, KeyError, TypeError, IndexError):
                return {'ok': False, 'error': 'AI 配置或响应格式无效；原离线解读仍可使用。'}
