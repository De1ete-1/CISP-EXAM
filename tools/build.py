"""Build a self-contained HTML file; only Python's standard library is needed."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent.parent
bank=json.loads((ROOT/'data/questions.json').read_text())
assert len(bank)==522
assert [q['id'] for q in bank]==list(range(1,523))
assert all(len(q['options'])==4 and all(q['options']) and q['answer'] in 'ABCD' and len(q['explanation'])>8 for q in bank)
data=json.dumps(bank,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
template=(ROOT/'src/index.template.html').read_text()
assert template.count('__QUESTION_DATA__')==1
(ROOT/'index.html').write_text(template.replace('__QUESTION_DATA__',data))
print(f'Built index.html: {(ROOT/"index.html").stat().st_size:,} bytes; {len(bank)} questions.')
