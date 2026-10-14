"""Pinned external meanings, matched by suit and rank rather than display names."""
import copy
import json
from config import PROJECT_DIR

ROOT = PROJECT_DIR/'data/tarot_reference'
RANKS = {11:'page',12:'knight',13:'queen',14:'king'}


def load_reference():
    traditional = json.loads((ROOT/'tarot.json').read_text())['cards']
    reflections = json.loads((ROOT/'corpora_interpretations.json').read_text())['tarot_interpretations']
    return ({(c['suit'],c['rank']):c for c in traditional}, {(c['suit'],c['rank']):c for c in reflections})

TRADITIONAL, REFLECTIONS = load_reference()
CANONICAL = {c['name']:c for c in json.loads((PROJECT_DIR/'data/tarot.json').read_text())['cards']}


def reference_for(card):
    canonical = CANONICAL[card['name_en']]
    if canonical['arcana'] == 'Major Arcana':
        suit,rank='major',int(canonical['number'])
    else:
        suit={'Cups':'cups','Swords':'swords','Wands':'wands','Pentacles':'coins'}[canonical['suit']]
        number=int(canonical['number']);rank=RANKS.get(number,number)
    traditional=TRADITIONAL[('pentacles' if suit=='coins' else suit,rank)]
    reflection=REFLECTIONS[(suit,rank)]
    direction='reversed' if card['reversed'] else 'upright'
    return {'direction':direction,'direction_meanings':copy.deepcopy(traditional['meanings'][direction]),
        'constructive':copy.deepcopy(reflection['meanings']['light']),
        'shadow':copy.deepcopy(reflection['meanings']['shadow']),
        'sources':['LindseyB/tarot-api (MIT)','dariusk/corpora — Mark McElroy (CC0)'],
        'note':'light/shadow 是建设性与失衡视角，不直接等于正位/逆位；fortune_telling 预测条目不用于解读。'}
