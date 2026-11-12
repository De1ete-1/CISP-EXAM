"""Validate the final bank and its self-contained HTML; source check is optional."""
import argparse
import base64
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path)
args=parser.parse_args()
bank=json.loads((ROOT/'data/questions.json').read_text())
html=(ROOT/'index.html').read_text()
assert len(bank)==522
assert [q['id'] for q in bank]==list(range(1,523))
for q in bank:
    assert len(q['options'])==4 and all(x.strip() for x in q['options']),q['id']
    assert q['answer'] in 'ABCD' and len(q['explanation'])>8,q['id']
    assert 1<=q['sourcePage']<=138,q['id']
    for im in q['images']:
        raw=base64.b64decode(im['src'].split(',',1)[1],validate=True)
        assert raw[:4]==b'RIFF' and raw[8:12]==b'WEBP',q['id']
        assert im['role'] in ['question','explanation']
embedded=re.search(r'<script id="question-data" type="application/json">(.*?)</script>',html,re.S)[1]
assert json.loads(embedded)==bank,'Embedded bank is stale'
assert '__QUESTION_DATA__' not in html
assert not re.search(r'<(?:script|link)[^>]+(?:src|href)=["\']https?://',html)
source_hash=None
if args.source:
    from pypdf import PdfReader
    pages=[p.extract_text() or '' for p in PdfReader(args.source).pages]
    text='\n'.join(pages)
    headings=[]
    expected=1
    for m in re.finditer(r'(?m)^\s*(\d{1,3})[．.、]',text):
        if int(m[1])==expected:
            headings.append(m);expected+=1
    assert len(headings)==522
    page_ends=[];offset=0
    for p in pages:
        page_ends.append(offset+len(p));offset+=len(p)+1
    for i,m in enumerate(headings):
        raw=text[m.end():headings[i+1].start() if i<521 else len(text)]
        marker=re.search(r'答\s*案',raw)
        tail=raw[marker.end():]
        ex=re.search(r'解\s*析',tail)
        answer_text=unicodedata.normalize('NFKC',tail[:ex.start()] if ex else tail)
        answer=re.search('[ABCDabcd]',answer_text)[0].upper()
        assert answer==bank[i]['answer'],(i+1,'answer mismatch')
        actual_page=next(n+1 for n,end in enumerate(page_ends) if end>=m.start(1))
        assert bank[i]['sourcePage']==actual_page,(i+1,'page mismatch')
    source_hash=hashlib.sha256(args.source.read_bytes()).hexdigest()
report=dict(questions=len(bank),sourceAnswerChecks=522 if args.source else None,sourcePageChecks=522 if args.source else None,figures=sum(len(q['images']) for q in bank),supplementedExplanations=sum(q['explanationSource']=='学习补充' for q in bank),originalExplanations=sum(q['explanationSource']=='题库原解析' for q in bank),notedQuestions=[q['id'] for q in bank if q['note']],answerDistribution={c:sum(q['answer']==c for q in bank) for c in 'ABCD'},questionPdfSha256=source_hash,htmlSha256=hashlib.sha256(html.encode()).hexdigest(),selfContained=True)
(ROOT/'data/validation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
