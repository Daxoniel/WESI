import copy
import json
import random
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from tarot_service import TarotService, SPREADS, LENSES
from storage import read_json


class TarotServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'history.json'
        self.service = TarotService(self.path, clock=lambda: datetime(2026, 10, 14, 12), rng=random.Random(7))

    def test_complete_meanings_and_position_lenses(self):
        self.assertEqual(len(self.service.deck), 78)
        self.assertEqual(len(self.service.meanings), 78)
        for card in self.service.deck:
            meaning = self.service.meanings[card['name_en']]
            self.assertNotEqual(meaning['upright'], meaning['reversed'])
            self.assertTrue(self.service.image(card['img']).startswith('data:image/'))
        for layout in SPREADS.values():
            self.assertEqual(len(layout['positions']), len(layout['coordinates']))
            for position in layout['positions']:
                self.assertIn(position, LENSES)

    def test_all_spreads_unique_draw_and_saved_reading_snapshot(self):
        for key, layout in SPREADS.items():
            result = self.service.draw(key, '测试 <script> 问题')
            self.assertTrue(result['ok'])
            cards = result['entry']['cards']
            self.assertEqual(len(cards), len(layout['positions']))
            self.assertEqual(len({card['name_en'] for card in cards}), len(cards))
            for card in cards:
                self.assertEqual(card['reading']['core'], self.service.meanings[card['name_en']]['reversed' if card['reversed'] else 'upright'])
        stored = copy.deepcopy(self.service.history())
        self.service.meanings.clear()
        self.assertEqual(self.service.history(), stored)
        self.assertEqual(len(stored), 8)

    def test_invalid_and_disk_failure_do_not_append(self):
        self.assertFalse(self.service.draw('bad')['ok'])
        self.assertFalse(self.service.draw('single', 'x'*501)['ok'])
        self.service.draw('single')
        before = self.path.read_bytes()
        with patch('tarot_service.write_json', side_effect=OSError('disk')):
            self.assertFalse(self.service.draw('three')['ok'])
        self.assertEqual(self.path.read_bytes(), before)

    def test_legacy_history_is_preserved(self):
        old = {'time':'2025-01-01', 'spread':'three', 'question':'旧问题', 'cards':[{'name_zh':'愚者','desc':'旧解读'}]}
        self.path.write_text(json.dumps([old]))
        self.service.draw('single')
        self.assertEqual(self.service.history()[-1], old)
        self.assertIsNone(self.service.image('missing.png'))
