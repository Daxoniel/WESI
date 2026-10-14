"""Explain observable patterns without claiming certainty or personal knowledge."""
from collections import Counter

DOMAINS = {'Cups': '情绪与关系', 'Swords': '判断与沟通', 'Wands': '动力与行动', 'Pentacles': '资源与现实安排'}
CONTEXTS = [
    ('工作与学习', ('工作','事业','职业','学习','项目','升职','考试'), '优先核对目标、资源、分工与反馈，不把趋势当作录用或考试结果。'),
    ('关系与沟通', ('感情','关系','伴侣','恋爱','分手','对方','朋友'), '把关于对方的主题转成可以沟通的问题，不替对方断定心意。'),
    ('资源与选择', ('钱','收入','财务','投资','选择','决定'), '结合实际成本、风险和退出条件核对，牌面不构成收益预测。'),
]

def identity(card):
    return f"{card['position']} · {card['name_zh']}（{'逆位' if card['reversed'] else '正位'}）"


def synthesize(entry):
    cards = entry['cards']
    context, framing = '开放反思', '问题不匹配预设主题时，以牌位和你能验证的事实为主。'
    for label, words, hint in CONTEXTS:
        if any(word in entry.get('question', '') for word in words):
            context, framing = label, hint
            break
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
    for a,b in pairs[:4]:
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
    return {'context': context, 'overview': f"围绕「{entry.get('spread_label',entry['spread'])}」探索{context}。{framing}",
            'themes': themes, 'relations': relations, 'actions': actions,
            'questions': ['哪些牌义与你能观察到的事实相符，哪些并不相符？', '如果改变一个可控行动，发展趋势可能怎样变化？'],
            'method': '离线规则：问题关键词归类、花色统计与牌位对照；不包含个性化推断。'}
