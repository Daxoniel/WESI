"""Fixed cases for manual semantic evaluation; --ai explicitly contacts configured service."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from utils import load_tarot_cards
from tarot_reference import reference_for
import tarot_ai

CASES = [
    ('finance-time','什么时候才能摆脱金钱焦虑？',[
        ('Ten of Wands','核心现状',False),('Knight of Pentacles','交叉挑战',True),
        ('Page of Pentacles','深层基础',True),('Seven of Pentacles','意识目标',True),
        ('The Fool','外部环境',True),('Five of Cups','可能发展',False)],
        '必须回应时间限制，区分负担/执行/投入回报，不假定有债务；环境风险和结果失望修正结论。此例为六牌节选，不得补造其余四牌。'),
    ('relationship','怎样改善我们最近的沟通？',[
        ('Two of Cups','你',False),('Queen of Swords','对方',False),('Five of Wands','关系',True)],
        '关系连接、清晰边界和冲突管理需联结；不把王后解释成对方真实身份，不断言对方内心。'),
    ('choice','要不要离开现在的工作，去一个不熟悉的新行业？',[
        ('Eight of Pentacles','选项A',False),('The Fool','选项B',True)],
        '同一标准比较熟练积累与新行业风险，明确事实不足；不强行替用户做选择，也不把逆位判为禁令。'),
]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ai',action='store_true',help='发送合成案例到配置的 AI 服务，可能产生费用')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    deck={c['name_en']:c for c in load_tarot_cards()}
    results=[]
    for key,question,positions,rubric in CASES:
        cards=[deck[name]|{'position':position,'reversed':reverse} for name,position,reverse in positions]
        for card in cards:card['reference']=reference_for(card)
        entry={'question':question,'spread':'evaluation','spread_label':'固定评估案例（不是随机抽牌）','cards':cards}
        item={'case':key,'rubric':rubric,'input':entry,'model_output':None,'human_review':'未评审'}
        if args.ai:item['model_output']=tarot_ai.interpret(entry)
        results.append(item)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    print('固定案例已导出；工程测试不替代人工语义评审。')
if __name__=='__main__':main()
