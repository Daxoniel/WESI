import copy
import tempfile
import threading
import unittest
from datetime import datetime,timedelta
from pathlib import Path
from unittest.mock import patch
from pet_game import PetGame
from storage import DataStore

class PetGameTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'state.json';self.store=DataStore(self.path)
        self.now=datetime(2026,10,14,12);self.game=PetGame(self.store,threading.RLock(),lambda:self.now)
    def test_offline_task_settles_once_after_reopening(self):
        before=copy.deepcopy(self.store.state['income'])
        self.assertTrue(self.game.dispatch('park')['ok'])
        self.assertFalse(self.game.dispatch('woods')['ok'])
        self.now+=timedelta(days=2)
        reopened=PetGame(DataStore(self.path),threading.RLock(),lambda:self.now)
        snap=reopened.snapshot();self.assertEqual(snap['game']['xp'],5)
        self.assertEqual(snap['game']['materials']['干粮'],4)
        self.assertEqual(reopened.snapshot()['game']['xp'],5)
        self.assertEqual(len(snap['game']['log']),1)
        self.assertEqual(reopened.store.state['income'],before)
    def test_disk_failure_does_not_dispatch_consume_or_reward(self):
        before=copy.deepcopy(self.store.state)
        with patch.object(self.store,'save',side_effect=OSError('disk')):
            self.assertFalse(self.game.dispatch('park')['ok'])
            self.assertFalse(self.game.interact('feed')['ok'])
        self.assertEqual(self.store.state,before)
        self.game.dispatch('woods');self.now+=timedelta(minutes=6)
        task=copy.deepcopy(self.store.state)
        with patch.object(self.store,'save',side_effect=OSError('disk')):
            self.assertFalse(self.game.snapshot()['ok'])
        self.assertEqual(self.store.state,task)
        self.assertEqual(self.game.snapshot()['game']['xp'],15)
    def test_interaction_cooldown_and_food_exhaustion(self):
        self.assertTrue(self.game.interact('feed')['ok'])
        self.assertFalse(self.game.interact('feed')['ok'])
        for _ in range(2):
            self.now+=timedelta(minutes=2);self.assertTrue(self.game.interact('feed')['ok'])
        self.now+=timedelta(minutes=2);self.assertFalse(self.game.interact('feed')['ok'])
        self.assertFalse(self.game.dispatch('invalid')['ok'])
        self.assertTrue(self.game.interact('pet')['ok'])

    def test_home_upgrade_spends_materials_and_only_bonuses_future_task(self):
        self.assertFalse(self.game.upgrade_home()['ok'])
        self.store.state['pet_game']['materials'].update({'树枝':2,'石片':1})
        self.game.dispatch('park')
        self.assertTrue(self.game.upgrade_home()['ok'])
        self.assertEqual(self.store.state['pet_game']['materials']['树枝'],0)
        self.assertEqual(self.store.state['pet_game']['task']['xp'],5)
        self.now+=timedelta(minutes=2);self.game.snapshot();self.game.dispatch('park')
        self.assertEqual(self.store.state['pet_game']['task']['xp'],7)
