"""Attach portable, curated textbook references to the question bank."""
import json


def attach_textbook_sources(bank, root):
    manifest = json.loads((root / 'data/textbook-sources.json').read_text())
    sources = manifest['questions']
    assert set(sources) == {str(q['id']) for q in bank}, 'Incomplete textbook source map'
    sections = {s['code'] + ' ' + s['title'] for s in manifest['sections']}
    offset = manifest['book']['printedPageOffset']
    for q in bank:
        refs = sources[str(q['id'])]
        assert refs, q['id']
        for ref in refs:
            assert ref['kind'] in ['knowledge', 'related'], q['id']
            assert ref['section'] in sections, q['id']
            assert 1 <= ref['page'] <= ref['endPage'] <= 427, q['id']
            assert ref['pdfPage'] == ref['page'] + offset, q['id']
            assert ref['pdfEndPage'] == ref['endPage'] + offset, q['id']
            assert ref['pdfEndPage'] <= manifest['book']['pdfPageCount'], q['id']
            if ref['kind'] == 'related':
                assert any(r.get('note') for r in refs), q['id']
        q['textbookSources'] = refs
    return manifest
