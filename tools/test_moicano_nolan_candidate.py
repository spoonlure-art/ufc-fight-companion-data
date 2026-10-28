"""Regression checks for the researched October 31 candidate; never publishes."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from prepare_publication import prepare
from validate_event import validate

ROOT = Path(__file__).resolve().parents[1]
EVENT_ID = 'ufcfn_moicano_nolan_20261031'
DRAFT = Path('drafts') / f'{EVENT_ID}_DRAFT.json'
REPORT = Path('reports') / f'{EVENT_ID}_VERIFICATION.json'


class MoicanoNolanCandidateTests(unittest.TestCase):
    def setUp(self):
        self.raw = (ROOT / DRAFT).read_bytes()
        self.event = json.loads(self.raw)
        self.report = json.loads((ROOT / REPORT).read_bytes())

    def test_existing_schema_and_publication_structural_preflight(self):
        self.assertEqual(([], []), validate(self.event))
        published = dict(self.event, status='PUBLISHED')
        self.assertEqual(([], []), validate(published, publication=True))
        self.assertEqual('DRAFT', self.event['status'])
        self.assertFalse(self.event['isSampleData'])
        self.assertNotIn('ownerApproval', self.event)

    def test_exact_review_report_hash_and_existing_workflow_binding(self):
        sha = hashlib.sha256(self.raw).hexdigest()
        self.assertEqual(sha, self.report['draftSha256'])
        self.assertEqual(DRAFT.as_posix(), self.report['draftPath'])
        self.assertIn(sha, (ROOT / 'reviews' / f'{EVENT_ID}_REVIEW.md').read_text())
        self.assertFalse(self.report['winStreak']['supported'])
        self.assertFalse(self.report['winStreak']['schemaChanged'])

    def test_pairing_order_matches_independently_captured_ufc_card(self):
        fights = self.event['fights']
        self.assertEqual(12, len(fights))
        self.assertEqual(list(range(1, 13)), [f['order'] for f in fights])
        names = lambda f: [' '.join((f[side]['firstName'], f[side]['lastName'])) for side in ('fighterA', 'fighterB')]
        captured = self.report['eventEvidence']['ufcObservedCard']
        self.assertEqual(list(reversed(captured['prelims-card'])), [names(f) for f in fights[:7]])
        self.assertEqual(list(reversed(captured['main-card'])), [names(f) for f in fights[7:]])
        self.assertEqual(['PRELIMS'] * 7 + ['MAIN_CARD'] * 3 + ['CO_MAIN_EVENT', 'MAIN_EVENT'], [f['cardType'] for f in fights])

    def test_all_24_fighters_and_48_completed_professional_histories_have_evidence(self):
        fighters = [f[side] for f in self.event['fights'] for side in ('fighterA', 'fighterB')]
        self.assertEqual(24, len({f['id'] for f in fighters}))
        reports = {f['id']: f for f in self.report['fighters']}
        for fighter in fighters:
            observed = reports[fighter['id']]
            self.assertEqual(fighter['record'], observed['recordEvidence']['selected'])
            self.assertEqual(fighter['victoryBreakdown'], observed['victoryEvidence']['selected'])
            self.assertEqual(fighter['lastTwoFights'], [h['selected'] for h in observed['historyEvidence']])
            self.assertEqual(2, len(fighter['lastTwoFights']))
            self.assertTrue(fighter['sources'])
            self.assertTrue(all(u.startswith('https://') for u in fighter['sources']))
            self.assertNotIn('winStreak', fighter)
            for history in fighter['lastTwoFights']:
                self.assertTrue(history['eventHeadliners'])
                self.assertNotIn('The Ultimate Fighter', history['eventName'])
        self.assertEqual(48, sum(len(f['lastTwoFights']) for f in fighters))

    def test_documented_uncertainty_cannot_publish_without_real_owner_acceptance(self):
        count = sum(len(item['fields']) for item in self.report['limitations'])
        self.assertEqual(12, count)
        self.assertEqual(count, self.event['verification']['unresolvedCount'])
        self.assertEqual('PARTIALLY_VERIFIED', self.event['verification']['status'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'drafts').mkdir()
            (root / DRAFT).write_bytes(self.raw)
            sha = hashlib.sha256(self.raw).hexdigest()
            with self.assertRaisesRegex(ValueError, 'Unresolved source verification'):
                prepare(root, DRAFT.as_posix(), sha, 'spoonlure-art')
            self.assertFalse((root / 'manifest.json').exists())
            self.assertFalse((root / 'events').exists())


if __name__ == '__main__':
    unittest.main()
