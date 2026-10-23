import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from export_weekly_cycle import export
from test_validate_event import fixture
from weekly_event import stage, rollback

class WeeklyTests(unittest.TestCase):
    def test_stage_never_publishes_or_preserves_stale_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'input.json'
            event=fixture();event['ownerApproval']={'actor':'spoonlure-art'}
            source.write_text(json.dumps(event));draft,report,sha=stage(root,source)
            result=json.loads(draft.read_bytes())
            self.assertEqual('DRAFT',result['status']);self.assertNotIn('ownerApproval',result)
            self.assertEqual('UNVERIFIED',result['verification']['status'])
            self.assertIn(sha,report.read_text());self.assertFalse((root/'manifest.json').exists())
            with self.assertRaises(ValueError):stage(root,source)
    def test_isolated_full_cycle_and_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            root=export(Path(directory))
            manifests=[json.loads((root/f'manifest{i}.json').read_bytes()) for i in (1,2,3)]
            self.assertEqual([1,2,3],[m['revision'] for m in manifests])
            self.assertEqual(manifests[0]['currentEvent'],manifests[2]['currentEvent'])
            self.assertNotEqual(manifests[0]['currentEvent'],manifests[1]['currentEvent'])
            for i in (1,2):
                self.assertEqual(manifests[i-1]['currentEvent']['sha256'],hashlib.sha256((root/f'event{i}.json').read_bytes()).hexdigest())
    def test_stage_rejects_path_escape_and_keeps_sample(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'input.json';event=fixture();event['id']='../escape'
            source.write_text(json.dumps(event))
            with self.assertRaises(ValueError):stage(root,source)
            event.update(id='sample',isSampleData=True);source.write_text(json.dumps(event))
            draft,_,_=stage(root,source);self.assertTrue(json.loads(draft.read_bytes())['isSampleData'])
    def test_rollback_rejects_nonowner(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):rollback(Path(directory),'events/x.json','0'*64,'bot')
