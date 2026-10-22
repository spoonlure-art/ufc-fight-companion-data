import copy
import unittest
from validate_event import validate

def fixture():
    past = {'opponentName': 'Opponent', 'eventName': 'Card', 'eventHeadliners': 'A vs B', 'date': '2026-08-01', 'result': 'WIN', 'method': 'Decision'}
    fighter = {'id': 'a', 'firstName': 'A', 'lastName': 'Test', 'country': 'Georgia', 'record': {'wins': 1, 'losses': 0, 'draws': 0, 'noContests': 0}, 'victoryBreakdown': {'koTko': 0, 'submission': 0, 'decision': 1, 'other': 0}, 'lastTwoFights': [past]}
    b = copy.deepcopy(fighter); b.update(id='b', firstName='B')
    return {'id': 'event', 'name': 'Test', 'venue': 'Test venue', 'status': 'PUBLISHED', 'isSampleData': False, 'date': '2026-10-24', 'dataCutoffDate': '2026-10-22', 'fights': [{'id': 'bout', 'order': 1, 'cardType': 'MAIN_EVENT', 'cardTypeLabel': 'Main Event', 'isTitleFight': False, 'weightClass': 'Lightweight', 'scheduledRounds': 5, 'fighterA': fighter, 'fighterB': b}]}

class ValidationTests(unittest.TestCase):
    def test_valid(self): self.assertEqual([], validate(fixture(), True)[0])
    def test_draft_and_sample_blocked(self):
        for key, value in [('status', 'DRAFT'), ('status', 'TYPO'), ('isSampleData', True)]:
            event = fixture(); event[key] = value
            self.assertTrue(validate(event, True)[0])
    def test_exception_note_cannot_bypass_sum(self):
        event = fixture(); event['fights'][0]['fighterA']['victoryBreakdown'].update(koTko=50, exceptionalNote='ignore')
        self.assertTrue(validate(event, True)[0])
    def test_missing_headliner(self):
        event = fixture(); event['fights'][0]['fighterA']['lastTwoFights'][0].pop('eventHeadliners')
        self.assertTrue(validate(event, True)[0]); self.assertTrue(validate(event)[1])
    def test_invalid_dates_duplicates_and_numbers(self):
        event = fixture(); fight = event['fights'][0]
        fight['fighterB'] = copy.deepcopy(fight['fighterA']); fight['order'] = 2
        fight['fighterA']['record']['wins'] = -1
        fight['fighterA']['lastTwoFights'][0]['date'] = '2026-02-30'
        self.assertGreaterEqual(len(validate(event, True)[0]), 4)
    def test_boolean_record_is_not_an_integer(self):
        event = fixture(); event['fights'][0]['fighterA']['record']['wins'] = True
        self.assertTrue(validate(event, True)[0])
    def test_empty_and_malformed(self):
        for event in ({}, [], {'fights': [None]}): self.assertTrue(validate(event)[0])

if __name__ == '__main__': unittest.main()
