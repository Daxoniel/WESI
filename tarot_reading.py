"""Explain observable patterns without claiming certainty or personal knowledge."""
from collections import Counter

DOMAINS = {'Cups': '情绪与关系', 'Swords': '判断与沟通', 'Wands': '动力与行动', 'Pentacles': '资源与现实安排'}
CONTEXTS = [
    ('工作与学习', ('工作','事业','职业','学习','项目','升职','考试'), '优先核对目标、资源、分工与反馈，不把趋势当作录用或考试结果。'),
    ('关系与沟通', ('感情','关系','伴侣','恋爱','分手','对方','朋友'), '把关于对方的主题转成可以沟通的问题，不替对方断定心意。'),
    ('资源与选择', ('钱','收入','财务','投资','选择','决定'), '结合实际成本、风险和退出条件核对，牌面不构成收益预测。'),
]

def question_intent(question):
    timing = any(word in question for word in ('什么时候','何时','多久','几时','哪天','几个月','今年','明年','when','how long'))
    categories = [
        ('财务', ('钱','收入','财务','投资','工资','债务','回报','收益')),
        ('关系', ('感情','关系','伴侣','恋爱','分手','对方','朋友')),
        ('选择', ('选择','决定','选项','要不要','该不该')),
        ('工作与学习', ('工作','事业','职业','学习','项目','升职','考试')),
    ]
    domains = [label for label, words in categories if any(word in question for word in words)] or ['自我探索']
    return {'type': '时间' if timing else domains[0], 'domains': domains,
            'timing': timing, 'method': '显式关键词识别，不是完整语义理解'}


def conclude(cards, intent):
    groups = {
        '负担与消耗': ('负担','过重','耗竭','减负','疲惫'),
        '投入与回报失衡': ('回报不匹配','回报不成比例','投入与回报','学习停留','收获不如'),
        '行动受阻': ('拖延','停滞','受阻','延迟','前进缓慢'),
        '改变中的风险': ('冲动','风险','仓促','隐患'),
        '失望与恢复': ('失落','失望','遗憾','修复'),
    }
    clusters = []
    for theme, words in groups.items():
        evidence = [c for c in cards if any(word in c.get('desc','') for word in words)]
        if evidence:
            clusters.append((theme, evidence))
    clusters.sort(key=lambda item: (-len(item[1]), list(groups).index(item[0])))
    evidence = [f"{theme}：" + '；'.join(f"{identity(c)} → {c.get('desc','')}" for c in items) for theme, items in clusters[:3]]
    opening = '当前牌阵不能支持具体日期或等待时长的预测；这次阅读无法回答准确的“什么时候”。' if intent['timing'] else '这次阅读提供的是象征性问题梳理，不能单凭牌面确定现实结果。'
    if clusters:
        repeated = [theme for theme, items in clusters if len(items)>1]
        emphasis = '、'.join(repeated[:2] or [clusters[0][0]])
        middle = f"按已匹配的牌义，优先关注{emphasis}。" + ('这是多张牌重复出现的主题。' if repeated else '目前依据有限，不应把单张线索扩展成完整事实。')
    else:
        middle = '当前规则未识别出稳定的共同矛盾，不能为了形成故事强行归纳。请从核心牌位核对事实。'
    outcome = next((c for c in cards if c['position'] in ('可能发展','未来趋势','近期趋势')), None)
    tail = f"发展位 {identity(outcome)} 提供的线索是“{outcome.get('desc','')}”；这是当前模式下的反思方向，不是固定结局。" if outcome else '这个牌阵没有明确结果位，不能补造结果。'
    if intent['timing']:
        tail += '与其等待一个被预测的日期，可以观察负担是否减轻、投入是否产生可验证的反馈，以及行动条件是否发生改变。'
    if '财务' in intent['domains']:
        tail += '涉及财务时，用实际收支、投入成本和风险条件核对；不构成财务预测。'
    return opening + middle + tail, evidence


def identity(card):
    return f"{card['position']} · {card['name_zh']}（{'逆位' if card['reversed'] else '正位'}）"


def synthesize(entry):
    cards = entry['cards']
    context, framing = '开放反思', '问题不匹配预设主题时，以牌位和你能验证的事实为主。'
    for label, words, hint in CONTEXTS:
        if any(word in entry.get('question', '') for word in words):
            context, framing = label, hint
            break
    intent = question_intent(entry.get('question','').lower())
    conclusion, evidence = conclude(cards, intent)
    counts = Counter(c.get('suit') for c in cards if c.get('suit') in DOMAINS)
    themes = []
    if counts:
        maximum = max(counts.values())
        for suit, count in counts.items():
            if count == maximum:
                names = '、'.join(c['name_zh'] for c in cards if c.get('suit') == suit)
                themes.append(f"{DOMAINS[suit]}：{names}，共 {count} 张。这个主题可以优先核对，但张数本身不代表事情好坏。")
    majors = [c['name_zh'] for c in cards if c.get('arcana') == 'Major']
    if majors:
        themes.append(f"大阿卡纳 {len(majors)} 张（{'、'.join(majors)}），可作为价值与阶段转变的反思入口，不意味着事件更确定。")
    reversed_count = sum(bool(c['reversed']) for c in cards)
    themes.append(f"正位 {len(cards)-reversed_count} 张 / 逆位 {reversed_count} 张。逆位逐张阅读，不统一解释为坏结果。")
    pairs = [(i,i+1) for i in range(len(cards)-1)]
    if entry.get('spread') == 'celtic': pairs = [(0,1),(2,4),(6,7),(8,9)]
    elif entry.get('spread') == 'five': pairs = [(0,1),(1,2),(3,4)]
    relations = []
    for a,b in [(a,b) for a,b in pairs if a < len(cards) and b < len(cards)][:4]:
        left,right = cards[a],cards[b]
        suit_left,suit_right = left.get('suit'),right.get('suit')
        if suit_left in DOMAINS and suit_left == suit_right:
            link = f"同属{DOMAINS[suit_left]}，观察同一主题在两个牌位中如何变化。"
        elif suit_left in DOMAINS and suit_right in DOMAINS:
            link = f"将{DOMAINS[suit_left]}与{DOMAINS[suit_right]}放在一起，检查两类需求如何协调。"
        else:
            link = '将两张牌的主题对照，检查价值层面的考虑是否能落实为具体行动。'
        relations.append(f"{identity(left)} ↔ {identity(right)}：{left.get('desc','')} / {right.get('desc','')} {link}")
    suggested = [c for c in cards if c['position'] in ('建议','你的立场','此刻')] or cards[:2]
    actions = [f"{identity(c)}：{c.get('reading',{}).get('action', c.get('desc',''))}" for c in suggested]
    return {'intent': intent, 'conclusion': conclusion, 'evidence': evidence, 'context': context, 'overview': f"围绕「{entry.get('spread_label',entry['spread'])}」探索{context}。{framing}",
            'themes': themes, 'relations': relations, 'actions': actions,
            'questions': ['哪些牌义与你能观察到的事实相符，哪些并不相符？', '如果改变一个可控行动，发展趋势可能怎样变化？'],
            'method': '离线规则：问题关键词归类、花色统计与牌位对照；不包含个性化推断。'}
