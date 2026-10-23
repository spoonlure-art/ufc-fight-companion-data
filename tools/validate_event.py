"""Strict static publication checks. No network access, credentials or implicit approval."""
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

CARDS = {'EARLY_PRELIMS': 0, 'PRELIMS': 1, 'MAIN_CARD': 2, 'CO_MAIN_EVENT': 3, 'MAIN_EVENT': 4}
def date(value):
    return isinstance(value, str) and bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', value)) and _date(value)
def _date(value):
    try:
        return dt.date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False

def validate(event, publication=False):
    errors, warnings = [], []
    def check(ok, message):
        if not ok:
            errors.append(message)
    check(isinstance(event, dict), 'Event must be an object')
    if not isinstance(event, dict): return errors, warnings
    check(bool(re.fullmatch(r'[A-Za-z0-9_-]{1,100}', str(event.get('id', '')))), 'Invalid event ID')
    for key in ('id', 'name', 'venue', 'date', 'dataCutoffDate'):
        check(isinstance(event.get(key), str) and bool(event[key].strip()), f'Missing/invalid string: {key}')
    check(event.get('status') in ('DRAFT', 'PUBLISHED'), 'Invalid status')
    check(type(event.get('isSampleData')) is bool, 'isSampleData must be boolean')
    check(date(event.get('date')), 'Invalid event date')
    cutoff = event.get('dataCutoffDate')
    check(date(cutoff), 'Invalid cutoff date')
    if date(cutoff) and date(event.get('date')):
        check(cutoff <= event['date'], 'Cutoff after event')
    if publication:
        check(event.get('status') == 'PUBLISHED', 'Publication requires PUBLISHED')
        check(event.get('isSampleData') is False, 'Sample data cannot be published')
    fights = event.get('fights', [])
    check(isinstance(fights, list) and 1 <= len(fights) <= 30, 'Expected 1..30 fights')
    if not isinstance(fights, list): return errors, warnings
    ids, fighters, names = set(), set(), set()
    previous_card = -1
    main_count = co_count = 0
    for index, fight in enumerate(fights, 1):
        check(isinstance(fight, dict), 'Fight must be an object')
        if not isinstance(fight, dict): continue
        fid = fight.get('id')
        check(isinstance(fid, str) and bool(fid) and fid not in ids, 'Duplicate/missing fight ID')
        if isinstance(fid, str): ids.add(fid)
        check(type(fight.get('order')) is int and fight['order'] == index, f'Invalid order: {fid}')
        card = fight.get('cardType')
        rank = CARDS.get(card, -1) if isinstance(card, str) else -1
        check(rank >= previous_card and rank >= 0, f'Invalid card progression: {fid}')
        previous_card = rank
        main_count += card == 'MAIN_EVENT'
        co_count += card == 'CO_MAIN_EVENT'
        check(type(fight.get('scheduledRounds')) is int and fight['scheduledRounds'] in (3, 5), f'Invalid rounds: {fid}')
        check(type(fight.get('isTitleFight')) is bool, f'Invalid title flag: {fid}')
        check(not fight.get('isTitleFight') or fight.get('scheduledRounds') == 5, 'Title fight needs five rounds')
        for key in ('weightClass', 'cardTypeLabel'):
            check(isinstance(fight.get(key), str) and bool(fight[key].strip()), f'Missing/invalid {key}')
        for side in ('fighterA', 'fighterB'):
            fighter = fight.get(side, {})
            if not isinstance(fighter, dict):
                errors.append('Fighter must be an object'); continue
            check(all(isinstance(fighter.get(key), str) for key in ('firstName', 'lastName')), 'Invalid fighter name types')
            check(fighter.get('age') is None or (type(fighter['age']) is int and 16 <= fighter['age'] <= 65), 'Invalid age')
            name = (str(fighter.get('firstName', '')) + ' ' + str(fighter.get('lastName', ''))).strip()
            identity = fighter.get('id')
            check(isinstance(identity, str) and bool(identity) and identity not in fighters, f'Duplicate/missing fighter ID: {name}')
            if isinstance(identity, str): fighters.add(identity)
            check(bool(name) and name.casefold() not in names, f'Duplicate/missing name: {name}')
            names.add(name.casefold())
            record, breakdown = fighter.get('record', {}), fighter.get('victoryBreakdown', {})
            valid_record = isinstance(record, dict) and all(type(record.get(k)) is int and 0 <= record[k] <= 500 for k in ('wins', 'losses', 'draws', 'noContests'))
            valid_breakdown = isinstance(breakdown, dict) and all(type(breakdown.get(k)) is int and 0 <= breakdown[k] <= 500 for k in ('koTko', 'submission', 'decision', 'other'))
            check(valid_record, f'Invalid record: {name}')
            check(valid_breakdown, f'Invalid breakdown: {name}')
            if valid_record and valid_breakdown:
                check(sum(breakdown[k] for k in ('koTko', 'submission', 'decision', 'other')) == record['wins'], f'Win sum mismatch: {name}')
            history = fighter.get('lastTwoFights', [])
            check('lastTwoFights' in fighter and isinstance(history, list), f'History must be a list: {name}')
            if not isinstance(history, list): continue
            expected = min(2, sum(record.values())) if valid_record else 2
            check(len(history) == expected, f'Incorrect history length: {name}')
            prev = cutoff
            for past in history:
                if not isinstance(past, dict): errors.append(f'Invalid history object: {name}'); continue
                for key in ('opponentName', 'eventName', 'method'):
                    check(isinstance(past.get(key), str) and bool(past[key].strip()) and past[key] != 'N/A', f'Missing {key}: {name}')
                check(past.get('result') in ('WIN', 'LOSS', 'DRAW', 'NO_CONTEST'), f'Invalid result: {name}')
                check(past.get('round') is None or (type(past['round']) is int and 1 <= past['round'] <= 5), f'Invalid past round: {name}')
                past_date = past.get('date')
                check(date(past_date) and date(prev) and past_date <= prev and date(event.get('date')) and past_date < event['date'], f'Invalid chronology: {name}')
                prev = past_date
                if not past.get('eventHeadliners'):
                    (errors if publication else warnings).append(f'Missing headliners: {name} ({past_date})')
            if not fighter.get('country'): warnings.append(f'Missing country: {name}')
    check(main_count == 1 and bool(fights) and isinstance(fights[-1], dict) and fights[-1].get('cardType') == 'MAIN_EVENT', 'Exactly one final MAIN_EVENT required')
    check(co_count <= 1, 'Multiple co-main events')
    return errors, warnings

def validate_manifest(root):
    manifest = json.loads((root / 'manifest.json').read_text())
    assert type(manifest['schemaVersion']) is int and manifest['schemaVersion'] == 1, 'Invalid schema'
    revision = manifest['revision']
    assert type(revision) is int and revision >= 0, 'Invalid revision'
    if manifest['currentEvent'] is None:
        assert revision == 0 and manifest['events'] == [] and manifest['publishedAt'] is None
        return
    assert revision > 0
    stamp = manifest['publishedAt']
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', stamp)
    dt.datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%SZ')
    assert manifest['currentEvent'] in manifest['events'], 'Current event absent from event list'
    for entry in manifest['events']:
        assert re.fullmatch(r'events/[A-Za-z0-9_-]+\.json', entry['path']), 'Invalid event path'
        raw = (root / entry['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry['sha256'], 'Checksum mismatch'
        event = json.loads(raw)
        assert event['id'] == entry['id'], 'ID mismatch'
        approval = event.get('ownerApproval', {})
        if approval.get('knownLimitationsAccepted') is True:
            record_path = approval.get('approvalRecordPath', '')
            assert re.fullmatch(r'approvals/[A-Za-z0-9_-]+\.json', record_path), 'Invalid approval path'
            record_raw = (root / record_path).read_bytes()
            assert hashlib.sha256(record_raw).hexdigest() == approval.get('approvalRecordSha256'), 'Approval record checksum mismatch'
            record = json.loads(record_raw)
            assert record.get('actor') == approval.get('actor') == 'spoonlure-art'
            assert record.get('decision') == 'APPROVE_AND_PUBLISH' and record.get('acceptKnownLimitations') is True
            assert record.get('draftSha256') == approval.get('draftSha256') and record.get('eventId') == event['id']
            assert record.get('sourceVerificationStatus') == event.get('verification', {}).get('status')
            assert record.get('unresolvedCount') == event.get('verification', {}).get('unresolvedCount')
        errors, _ = validate(event, publication=True)
        assert not errors, '; '.join(errors)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path)
    parser.add_argument('--event', type=Path)
    parser.add_argument('--publication', action='store_true')
    args = parser.parse_args()
    if args.root:
        validate_manifest(args.root)
        print('Publication manifest validated')
    elif args.event:
        errors, warnings = validate(json.loads(args.event.read_text()), args.publication)
        print(json.dumps({'errors': errors, 'warnings': warnings}, indent=2, ensure_ascii=False))
        raise SystemExit(bool(errors))
    else: parser.error('Provide --root or --event')
