import unittest
from unittest.mock import patch, Mock
import json
import os
from utils import load_tarot_cards
from tarot_reference import reference_for
import tarot_ai

class ReferenceTests(unittest.TestCase):
    def test_all_cards_map_both_directions_and_light_is_not_direction(self):
        deck=load_tarot_cards()
        self.assertEqual(len(deck),78)
        for card in deck:
            upright=reference_for(card|{'reversed':False})
            reversed_=reference_for(card|{'reversed':True})
            self.assertTrue(upright['direction_meanings'])
            self.assertTrue(reversed_['direction_meanings'])
            self.assertNotEqual(upright['direction_meanings'],reversed_['direction_meanings'])
            self.assertEqual(upright['constructive'],reversed_['constructive'])
            self.assertEqual(upright['shadow'],reversed_['shadow'])
        self.assertEqual(reference_for(deck[0]|{'img':'custom.png','reversed':True}),reference_for(deck[0]|{'reversed':True}))
        seven=next(c for c in deck if c['name_en']=='Seven of Pentacles')
        source=reference_for(seven|{'reversed':True})
        self.assertTrue(any('reward' in text or 'success' in text or 'work' in text for text in source['direction_meanings']))

    def test_model_receives_reference_even_for_pre_reference_history(self):
        card=load_tarot_cards()[0]|{'position':'此刻','reversed':True}
        report={'overview':'测试','relations':['测试'],'actions':['测试'],'questions':['测试']}
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        response.read.return_value=json.dumps({'choices':[{'message':{'content':json.dumps(report)}}]}).encode()
        opener=Mock();opener.open.return_value=response
        with patch.dict(os.environ,{'WESI_TAROT_AI_MODEL':'test'},clear=True),patch('tarot_ai.build_opener',return_value=opener):
            tarot_ai.interpret({'question':'什么时候','spread':'single','cards':[card]})
        payload=json.loads(opener.open.call_args.args[0].data)
        evidence=json.loads(payload['messages'][1]['content'])
        self.assertEqual(evidence['cards'][0]['reference']['direction'],'reversed')
        self.assertNotIn('offline_evidence',evidence)
        self.assertIn('不要按顺序罗列',payload['messages'][0]['content'])
