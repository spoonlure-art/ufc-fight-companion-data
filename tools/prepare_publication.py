"""Prepare a publication only for the exact SHA explicitly approved by the owner.
No network calls. Never called by push/PR validation workflows.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path
from validate_event import validate, validate_manifest

OWNER = 'spoonlure-art'
def owner_decision(root, approval_path, event, approved_sha, actor):
    """An explicit owner decision may accept known source limitations, never hide them."""
    source = (root / approval_path).resolve()
    if source.parent != (root / 'approvals').resolve() or source.suffix != '.json':
        raise ValueError('Approval must be a direct approvals/*.json record')
    raw = source.read_bytes()
    record = json.loads(raw)
    verification = event.get('verification', {})
    if (record.get('schemaVersion') != 1 or record.get('actor') != OWNER or actor != OWNER
        or record.get('decision') != 'APPROVE_AND_PUBLISH'
        or record.get('eventId') != event.get('id')
        or record.get('draftSha256') != approved_sha
        or record.get('acceptKnownLimitations') is not True
        or record.get('sourceVerificationStatus') != verification.get('status')
        or type(record.get('unresolvedCount')) is not int
        or record['unresolvedCount'] != verification.get('unresolvedCount')
        or not record.get('approvalEvidence')):
        raise ValueError('Owner acceptance must bind this exact draft and its known limitations')
    dt.datetime.strptime(record.get('approvedAt', ''), '%Y-%m-%dT%H:%M:%SZ')
    return record, hashlib.sha256(raw).hexdigest()

def prepare(root, draft_path, approved_sha, actor, owner_approval_path=None):
    if actor != OWNER: raise ValueError('Only the repository owner may approve publication')
    if not re.fullmatch(r'[a-f0-9]{64}', approved_sha): raise ValueError('Exact SHA-256 approval required')
    source = (root / draft_path).resolve()
    if source.parent != (root / 'drafts').resolve() or source.suffix != '.json':
        raise ValueError('Only a direct drafts/*.json input is allowed')
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != approved_sha: raise ValueError('Draft changed after approval')
    event = json.loads(raw)
    if event.get('status') != 'DRAFT' or event.get('isSampleData') is not False:
        raise ValueError('Input must be a non-sample DRAFT')
    verification = event.get('verification', {})
    acceptance = owner_decision(root, owner_approval_path, event, approved_sha, actor) if owner_approval_path else None
    if not acceptance and (verification.get('status') != 'VERIFIED' or verification.get('unresolvedCount') != 0):
        raise ValueError('Unresolved source verification prevents publication')
    event['status'] = 'PUBLISHED'
    errors, _ = validate(event, publication=True)
    if errors: raise ValueError('; '.join(errors))
    validate_manifest(root)
    manifest = json.loads((root / 'manifest.json').read_text())
    revision = manifest['revision'] + 1
    path = f"events/{event['id']}_r{revision}.json"
    if (root / path).exists(): raise ValueError('Immutable publication path already exists')
    timestamp = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    event['ownerApproval'] = {'actor': actor, 'draftSha256': approved_sha, 'approvedAt': timestamp}
    if acceptance:
        record, record_sha = acceptance
        event['ownerApproval'].update(approvedAt=record['approvedAt'],
            approvalRecordPath=owner_approval_path, approvalRecordSha256=record_sha,
            knownLimitationsAccepted=True, sourceVerificationStatus=verification.get('status'))
    payload = (json.dumps(event, ensure_ascii=False, indent=2) + '\n').encode()
    entry = {'id': event['id'], 'path': path, 'sha256': hashlib.sha256(payload).hexdigest()}
    (root / 'events').mkdir(exist_ok=True)
    (root / path).write_bytes(payload)
    manifest.update(revision=revision, publishedAt=timestamp, currentEvent=entry)
    manifest['events'].append(entry)
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    validate_manifest(root)
    return entry

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--draft', required=True)
    parser.add_argument('--approved-sha', required=True)
    parser.add_argument('--owner-approval', default=None)
    args = parser.parse_args()
    if os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch':
        parser.error('Publication is only available through an explicit manual owner dispatch')
    print(json.dumps(prepare(args.root, args.draft, args.approved_sha, os.environ.get('GITHUB_ACTOR', ''), args.owner_approval)))
