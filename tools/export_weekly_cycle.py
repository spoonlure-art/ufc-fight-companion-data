"""Generate isolated publication bytes for Android contract tests, never real manifest."""
import hashlib
import json
import tempfile
from pathlib import Path
from prepare_publication import prepare
from weekly_event import rollback, stage
from test_validate_event import fixture


def export(destination):
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root/'manifest.json').write_text(json.dumps(dict(schemaVersion=1,revision=0,publishedAt=None,currentEvent=None,events=[])))
        original = fixture()
        original.update(status='DRAFT', verification={'status':'VERIFIED','unresolvedCount':0},
                        sources=[{'url':'https://example.invalid/isolated-fixture','status':'TEST_ONLY'}])
        for index in (1, 2):
            original.update(id=f'isolated_week_{index}', name=f'Isolated week {index}')
            source=root/'input.json';source.write_text(json.dumps(original))
            draft, report, sha=stage(root,source)
            before=(root/'manifest.json').read_bytes()
            for actor, approved in [('bot',sha),('spoonlure-art','0'*64)]:
                try: prepare(root,str(draft.relative_to(root)),approved,actor)
                except ValueError: pass
                else: raise AssertionError('Approval bypass')
                assert (root/'manifest.json').read_bytes()==before
            entry=prepare(root,str(draft.relative_to(root)),sha,'spoonlure-art')
            (destination/f'manifest{index}.json').write_bytes((root/'manifest.json').read_bytes())
            (destination/f'event{index}.json').write_bytes((root/entry['path']).read_bytes())
            if index==1: first=entry
        rollback(root,first['path'],first['sha256'],'spoonlure-art')
        (destination/'manifest3.json').write_bytes((root/'manifest.json').read_bytes())
    return destination

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('destination',type=Path)
    export(parser.parse_args().destination)
