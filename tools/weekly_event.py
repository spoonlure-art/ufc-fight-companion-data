"""Offline weekly preparation and rollback. Never pushes or manufactures owner consent."""
import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from validate_event import validate, validate_manifest


def review(raw):
    event = json.loads(raw)
    errors, warnings = validate(event)
    verification = event.get('verification', {})
    if verification.get('status') != 'VERIFIED' or verification.get('unresolvedCount') != 0:
        errors.append('Source verification incomplete; explicit owner acceptance required for known limitations')
    sources = event.get('sources', [])
    if not isinstance(sources, list) or not sources:
        warnings.append('No event-level sources recorded')
    lines = ['# Weekly event review', '', f"Event: {event.get('name', 'UNKNOWN')}",
             f"Draft SHA-256: `{hashlib.sha256(raw).hexdigest()}`", '',
             '**DRAFT — preparation is not approval or publication.**', '',
             f"Structural errors: {len(validate(event)[0])}; warnings: {len(warnings)}", '',
             '## Checks requiring attention', '']
    lines.extend('- ' + item for item in errors + warnings)
    if not errors and not warnings: lines.append('- Automated checks passed; owner review is still required.')
    lines.extend(['', '## Fight order', ''])
    for fight in event.get('fights', []):
        if not isinstance(fight, dict): continue
        names = [' '.join(str(fight.get(side, {}).get(k, '')) for k in ('firstName', 'lastName')).strip()
                 for side in ('fighterA', 'fighterB') if isinstance(fight.get(side, {}), dict)]
        lines.append(f"- {fight.get('order')}: {' vs '.join(names)} ({fight.get('cardType')})")
    lines.extend(['', '## Fighter review', ''])
    for fight in event.get('fights', []):
        if not isinstance(fight, dict): continue
        for side in ('fighterA', 'fighterB'):
            fighter = fight.get(side, {})
            if not isinstance(fighter, dict): continue
            lines.extend(['### ' + ' '.join(str(fighter.get(k, '')) for k in ('firstName', 'lastName')), '',
                          '```json', json.dumps({k: fighter.get(k) for k in
                           ('record', 'victoryBreakdown', 'lastTwoFights', 'sources', 'verification')},
                           ensure_ascii=False, indent=2), '```', ''])
    lines.extend(['', '## Sources', '', '```json', json.dumps(sources, ensure_ascii=False, indent=2), '```', '',
                  'Owner decision must quote this exact SHA. Any subsequent edit requires fresh review.',
                  'Missing or conflicting facts must remain unresolved; never infer them from an empty field.', ''])
    return '\n'.join(lines)


def stage(root, source):
    event = json.loads(source.read_bytes())
    identity = event.get('id', '')
    if not isinstance(identity, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', identity):
        raise ValueError('Safe event ID required')
    event['status'] = 'DRAFT'
    event.pop('ownerApproval', None)
    # Do not relabel sample or unverified data as real/verified.
    event.setdefault('isSampleData', False)
    event.setdefault('verification', {'status': 'UNVERIFIED', 'unresolvedCount': 1})
    event.setdefault('sources', [])
    raw = (json.dumps(event, ensure_ascii=False, indent=2) + '\n').encode()
    draft = root / 'drafts' / f'{identity}_DRAFT.json'
    report = root / 'reviews' / f'{identity}_REVIEW.md'
    if draft.exists() or report.exists(): raise ValueError('Review version exists; use a new version ID or explicitly review edits')
    draft.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    draft.write_bytes(raw)
    report.write_text(review(raw))
    return draft, report, hashlib.sha256(raw).hexdigest()


def rollback(root, path, approved_sha, actor):
    # A rollback is another explicit owner decision and always increases revision.
    if actor != 'spoonlure-art': raise ValueError('Owner decision required')
    validate_manifest(root)
    manifest_path = root / 'manifest.json'
    manifest = json.loads(manifest_path.read_bytes())
    target = next((e for e in manifest['events'] if e['path'] == path and e['sha256'] == approved_sha), None)
    if target is None: raise ValueError('Rollback must name an existing validated immutable version and exact SHA')
    manifest.update(revision=manifest['revision'] + 1, currentEvent=target,
                    publishedAt=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    validate_manifest(root)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    sub = parser.add_subparsers(dest='command', required=True)
    prepare = sub.add_parser('stage'); prepare.add_argument('source', type=Path)
    inspect = sub.add_parser('review'); inspect.add_argument('draft', type=Path)
    # Rollback deliberately remains a library function: caller must authenticate owner,
    # bind explicit consent to target SHA and commit manifest with a head lease.
    args = parser.parse_args()
    if args.command == 'stage': print(stage(args.root, args.source))
    else: print(review(args.draft.read_bytes()))
