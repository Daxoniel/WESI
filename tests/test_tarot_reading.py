import copy
import json
import os
import unittest
from unittest.mock import patch, Mock
import test_tarot_service as tarot_tests
from tarot_reading import synthesize
import tarot_ai


class SynthesisTests(unittest.TestCase):
    def test_explains_actual_pairs_and_question_context_without_mutating_cards(self):
        entry={'spread':'guidance','spread_label':'现状与建议','question':'工作项目', 'cards':[
            {'name_zh':'圣杯一','position':'现状','suit':'Cups','reversed':False,'desc':'感受','reading':{'action':'表达'}},
            {'name_zh':'宝剑二','position':'阻碍','suit':'Swords','reversed':True,'desc':'判断'},
            {'name_zh':'权杖三','position':'建议','suit':'Wands','reversed':False,'desc':'行动','reading':{'action':'小尝试'}}]}
        before=copy.deepcopy(entry)
        result=synthesize(entry)
        self.assertEqual(result['context'],'工作与学习')
        self.assertIn('圣杯一',result['relations'][0])
        self.assertIn('宝剑二',result['relations'][0])
        self.assertIn('小尝试',result['actions'][0])
        self.assertEqual(entry,before)


class AIServiceTests(unittest.TestCase):
    setUp = tarot_tests.TarotServiceTests.setUp
    def test_ai_persists_once_and_does_not_redraw(self):
        entry=self.service.draw('guidance','工作')['entry']
        cards=copy.deepcopy(entry['cards'])
        report={'overview':'解释','relations':['关系'],'actions':['行动'],'questions':['核实'],'model':'test'}
        with patch('tarot_service.tarot_ai.interpret',return_value=report) as provider:
            result=self.service.ai_reading(entry['id'])
            self.assertTrue(result['ok'])
            self.assertTrue(self.service.ai_reading(entry['id'])['ok'])
            provider.assert_called_once()
        self.assertEqual(result['entry']['cards'],cards)
        self.assertEqual(self.service.history()[0]['ai_reading'],report)

    def test_disk_failure_retries_cached_report_and_provider_failure_keeps_history(self):
        entry=self.service.draw('single')['entry']
        before=self.path.read_bytes()
        with patch('tarot_service.tarot_ai.interpret',side_effect=ValueError('invalid')):
            self.assertFalse(self.service.ai_reading(entry['id'])['ok'])
        self.assertEqual(self.path.read_bytes(),before)
        with patch('tarot_service.tarot_ai.interpret',return_value={'overview':'ok'}) as provider:
            with patch('tarot_service.write_json',side_effect=OSError('disk')):
                self.assertFalse(self.service.ai_reading(entry['id'])['ok'])
            self.assertEqual(self.path.read_bytes(),before)
            self.assertTrue(self.service.ai_reading(entry['id'])['ok'])
            provider.assert_called_once()
        self.assertFalse(self.service.ai_reading('missing')['ok'])


class AITransportTests(unittest.TestCase):
    def test_request_contains_frozen_cards_and_validates_response(self):
        report={'overview':'总览','relations':['牌位对照'],'actions':['步骤'],'questions':['事实']}
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        response.read.return_value=json.dumps({'choices':[{'message':{'content':json.dumps(report)}}]}).encode()
        opener=Mock();opener.open.return_value=response
        entry={'question':'问题','spread':'single','cards':[{'name_zh':'愚者','position':'此刻','reversed':True}]}
        with patch.dict(os.environ,{'WESI_TAROT_AI_MODEL':'test','WESI_TAROT_AI_KEY':'dummy'},clear=True),patch('tarot_ai.build_opener',return_value=opener):
            result=tarot_ai.interpret(entry)
            request=opener.open.call_args.args[0]
            payload=json.loads(request.data)
            self.assertTrue(json.loads(payload['messages'][1]['content'])['cards'][0]['reversed'])
            self.assertEqual(result['overview'],'总览')
            response.read.return_value=json.dumps({'choices':[{'message':{'content':None}}]}).encode()
            with self.assertRaises(ValueError):tarot_ai.interpret(entry)
            response.read.return_value=b'{}'
            with self.assertRaises(KeyError):tarot_ai.interpret(entry)

    def test_disabled_and_insecure_remote_url_never_contacts_provider(self):
        with patch.dict(os.environ,{},clear=True),patch('tarot_ai.build_opener') as network:
            self.assertFalse(tarot_ai.status()['available'])
            with self.assertRaises(ValueError):tarot_ai.interpret({})
            network.assert_not_called()
        with patch.dict(os.environ,{'WESI_TAROT_AI_MODEL':'test','WESI_TAROT_AI_BASE':'http://example.com/v1'},clear=True),patch('tarot_ai.build_opener') as network:
            with self.assertRaises(ValueError):tarot_ai.interpret({})
            network.assert_not_called()

class QuestionSynthesisTests(unittest.TestCase):
    def test_time_and_finance_are_both_recognized_and_no_date_is_invented(self):
        from tarot_reading import question_intent
        intent=question_intent('什么时候才能摆脱金钱焦虑？')
        self.assertTrue(intent['timing'])
        self.assertIn('财务',intent['domains'])
        entry={'question':'什么时候才能摆脱金钱焦虑？','spread':'celtic','cards':[
            {'name_zh':'权杖十','position':'核心现状','reversed':False,'desc':'责任过重，需要减负'},
            {'name_zh':'星币骑士','position':'交叉挑战','reversed':True,'desc':'拖延阻碍进展'},
            {'name_zh':'星币七','position':'深层基础','reversed':True,'desc':'投入与回报不匹配'},
            {'name_zh':'星币侍从','position':'你的立场','reversed':True,'desc':'学习停留在想法'},
            {'name_zh':'圣杯五','position':'可能发展','reversed':False,'desc':'承认失落，留意支持'}]}
        result=synthesize(entry)
        self.assertIn('不能支持具体日期',result['conclusion'])
        self.assertIn('投入与回报失衡',result['conclusion'])
        self.assertIn('圣杯五',result['conclusion'])
        self.assertTrue(any('星币七' in e and '星币侍从' in e for e in result['evidence']))

    def test_seven_and_ten_of_pentacles_have_correct_independent_meanings(self):
        from config import PROJECT_DIR
        meanings=json.loads((PROJECT_DIR/'data/tarot_meanings_zh.json').read_text())
        self.assertIn('投入与回报',meanings['Seven of Pentacles']['reversed'])
        self.assertIn('长期安排',meanings['Ten of Pentacles']['reversed'])
        self.assertNotEqual(meanings['Seven of Pentacles'],meanings['Ten of Pentacles'])

    def test_no_matching_theme_does_not_invent_conflict_or_result(self):
        result=synthesize({'question':'我该怎样看待现在？','spread':'single','cards':[
            {'name_zh':'星星','position':'此刻','reversed':False,'desc':'希望与恢复','reading':{'action':'小步骤'}}]})
        self.assertIn('未识别出稳定的共同矛盾',result['conclusion'])
        self.assertIn('没有明确结果位',result['conclusion'])
