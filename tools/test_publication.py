import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from prepare_publication import prepare
from test_validate_event import fixture
from validate_event import validate_manifest

class PublicationTests(unittest.TestCase):
    def setup_root(self, directory):
        root = Path(directory)
        (root / 'drafts').mkdir()
        (root / 'manifest.json').write_text(json.dumps({'schemaVersion':1,'revision':0,'publishedAt':None,'currentEvent':None,'events':[]}))
        event = fixture(); event.update(status='DRAFT', verification={'status':'VERIFIED','unresolvedCount':0})
        raw = json.dumps(event).encode(); (root / 'drafts/test.json').write_bytes(raw)
        return root, hashlib.sha256(raw).hexdigest()
    def test_owner_exact_hash_and_immutable_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root, sha = self.setup_root(directory)
            first = prepare(root, 'drafts/test.json', sha, 'spoonlure-art')
            second = prepare(root, 'drafts/test.json', sha, 'spoonlure-art')
            self.assertNotEqual(first['path'], second['path'])
            self.assertTrue((root / first['path']).exists())
            self.assertEqual(2, json.loads((root/'manifest.json').read_text())['revision'])
            validate_manifest(root)
    def test_wrong_actor_hash_sample_and_unresolved_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root, sha = self.setup_root(directory)
            for actor, value in [('bot',sha),('spoonlure-art','0'*64)]:
                with self.assertRaises(ValueError): prepare(root,'drafts/test.json',value,actor)
            event = json.loads((root/'drafts/test.json').read_text())
            for key, value in [('isSampleData',True),('verification',{'status':'PARTIALLY_VERIFIED','unresolvedCount':2})]:
                modified = dict(event); modified[key]=value
                raw=json.dumps(modified).encode(); (root/'drafts/test.json').write_bytes(raw)
                with self.assertRaises(ValueError): prepare(root,'drafts/test.json',hashlib.sha256(raw).hexdigest(),'spoonlure-art')
            self.assertEqual(0, json.loads((root/'manifest.json').read_text())['revision'])
    def test_traversal_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root, sha = self.setup_root(directory)
            with self.assertRaises(ValueError): prepare(root,'../test.json',sha,'spoonlure-art')

    def test_explicit_owner_acceptance_preserves_source_uncertainty(self):
        with tempfile.TemporaryDirectory() as directory:
            root, _ = self.setup_root(directory)
            event = json.loads((root/'drafts/test.json').read_text())
            event['verification'] = {'status':'PARTIALLY_VERIFIED','unresolvedCount':2}
            raw=json.dumps(event).encode(); (root/'drafts/test.json').write_bytes(raw)
            sha=hashlib.sha256(raw).hexdigest()
            (root/'approvals').mkdir()
            record={'schemaVersion':1,'actor':'spoonlure-art','decision':'APPROVE_AND_PUBLISH',
                'eventId':event['id'],'draftSha256':sha,'acceptKnownLimitations':True,
                'sourceVerificationStatus':'PARTIALLY_VERIFIED','unresolvedCount':2,
                'approvalEvidence':'Explicit owner acceptance and publication instruction',
                'approvedAt':'2026-10-23T10:00:00Z'}
            target=root/'approvals/owner.json'; target.write_text(json.dumps(record))
            for field, value in [('actor','bot'),('draftSha256','0'*64),('acceptKnownLimitations',False),
                                 ('unresolvedCount',0),('eventId','different')]:
                changed=dict(record);changed[field]=value;target.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    prepare(root,'drafts/test.json',sha,'spoonlure-art','approvals/owner.json')
            target.write_text(json.dumps(record))
            sample=dict(event);sample['isSampleData']=True
            sample_raw=json.dumps(sample).encode();(root/'drafts/test.json').write_bytes(sample_raw)
            sample_sha=hashlib.sha256(sample_raw).hexdigest()
            sample_record=dict(record);sample_record['draftSha256']=sample_sha
            target.write_text(json.dumps(sample_record))
            with self.assertRaises(ValueError):
                prepare(root,'drafts/test.json',sample_sha,'spoonlure-art','approvals/owner.json')
            (root/'drafts/test.json').write_bytes(raw);target.write_text(json.dumps(record))
            with self.assertRaises(ValueError):
                prepare(root,'drafts/test.json',sha,'spoonlure-art','../owner.json')
            entry=prepare(root,'drafts/test.json',sha,'spoonlure-art','approvals/owner.json')
            published=json.loads((root/entry['path']).read_text())
            self.assertEqual(event['verification'],published['verification'])
            self.assertTrue(published['ownerApproval']['knownLimitationsAccepted'])
            self.assertEqual('PUBLISHED',published['status'])
            self.assertEqual(1,json.loads((root/'manifest.json').read_text())['revision'])
            validate_manifest(root)
            target.write_text(json.dumps(dict(record,acceptKnownLimitations=False)))
            with self.assertRaises(AssertionError): validate_manifest(root)
