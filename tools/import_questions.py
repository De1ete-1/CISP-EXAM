"""Import the supplied PDFs. No network or external runtime is needed by the HTML."""
import argparse
import base64
import io
import json
import re
import unicodedata
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium
from pypdf import PdfReader
from source_data import attach_textbook_sources

ROOT = Path(__file__).resolve().parent.parent


def clean(text):
    text = re.sub(r'练习题第[一二三四五六七八九十]+卷', '', text)
    text = re.sub(r'(?<=[\u4e00-\u9fff，。；：、（）])\s*\n\s*(?=[\u4e00-\u9fff，。；：、（）])', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def main():
    parser = argparse.ArgumentParser(description='从指定的题库 PDF 导入题目。')
    parser.add_argument('--source', type=Path, required=True, help='题库 PDF 的文件路径')
    source = parser.parse_args().source
    if not source.is_file():
        parser.error('找不到指定的题库 PDF 文件')
    pages = [p.extract_text() or '' for p in PdfReader(source).pages]
    text = '\n'.join(pages)
    starts = []
    expected = 1
    for match in re.finditer(r'(?m)^\s*(\d{1,3})[．.、]', text):
        if int(match[1]) == expected:
            starts.append(match)
            expected += 1
    assert len(starts) == 522
    supplements = json.loads((ROOT / 'data/supplements.json').read_text())
    bank = []
    for index, match in enumerate(starts):
        raw = text[match.end():starts[index + 1].start() if index < 521 else len(text)]
        answer_marker = re.search(r'答\s*案', raw)
        assert answer_marker, index + 1
        question_part = raw[:answer_marker.start()]
        explanation_marker = re.search(r'解\s*析\s*[：:；;]?', raw[answer_marker.end():])
        tail = raw[answer_marker.end():]
        answer_text = tail[:explanation_marker.start()] if explanation_marker else tail
        answer = re.search(r'[ABCDabcd]', unicodedata.normalize('NFKC', answer_text))[0].upper()
        options = list(re.finditer(r'(?m)^\s*([ABCD])[.．、：:]\s*', question_part))
        assert [x[1] for x in options] == list('ABCD'), (index + 1, question_part)
        original_explanation = clean(tail[explanation_marker.end():]) if explanation_marker else ''
        page = 1
        offset = 0
        for page_index, page_text in enumerate(pages):
            if offset + len(page_text) >= match.start(1):
                page = page_index + 1
                break
            offset += len(page_text) + 1
        ref_pages = [int(x) for x in re.findall(r'[Pp]\s*(\d+)', original_explanation)]
        supplement = supplements.get(str(index + 1), {})
        refs = [dict(page=p, pdfPage=p + 5) for p in ref_pages if 1 <= p <= 435]
        bank.append(dict(
            id=index + 1,
            stem=clean(question_part[:options[0].start()]),
            options=[clean(question_part[m.end():options[i + 1].start() if i < 3 else len(question_part)]).lstrip('.') for i, m in enumerate(options)],
            answer=answer,
            explanation=supplement.get('explanation') or original_explanation,
            originalExplanation=original_explanation,
            explanationSource='学习补充' if supplement.get('explanation') else '题库原解析',
            sourcePage=page,
            references=refs,
            links=supplement.get('links', []),
            note=supplement.get('note', '') or (clean(answer_text) if '题库' in answer_text else ''),
            images=[],
        ))
        if index + 1 == 155:
            bank[-1]['references'] = [dict(page=304, pdfPage=309)]
    # Preserve figures, including diagrams embedded between options or in explanations.
    document = pdfium.PdfDocument(str(source))
    current = 0
    role = 'question'
    with pdfplumber.open(source) as pdf:
        for page_index, page in enumerate(pdf.pages):
            events = []
            for line in page.extract_text_lines():
                events.append((line['top'], 'line', line['text']))
            events.extend((img['top'], 'image', img) for img in page.images)
            pil = document[page_index].render(scale=2).to_pil().convert('RGB') if page.images else None
            for _, kind, value in sorted(events, key=lambda e: e[0]):
                if kind == 'line':
                    m = re.match(r'\s*(\d{1,3})[．.、]', value)
                    if m and int(m[1]) == current + 1:
                        current += 1
                        role = 'question'
                    if re.match(r'答\s*案|解\s*析', value):
                        role = 'explanation'
                    continue
                img = value
                qid = current
                assert 1 <= qid <= 522, (page_index, qid)
                box = (max(0, int(img['x0'] * 2) - 4), max(0, int(img['top'] * 2) - 4), min(pil.width, int(img['x1'] * 2) + 4), min(pil.height, int(img['bottom'] * 2) + 4))
                out = io.BytesIO()
                pil.crop(box).save(out, format='WEBP', quality=90)
                bank[qid - 1]['images'].append(dict(src='data:image/webp;base64,' + base64.b64encode(out.getvalue()).decode(), role=role, page=page_index + 1))
    assert current == 522, current
    for q in bank:
        assert len(q['explanation']) > 8, (q['id'], q['explanation'])
    attach_textbook_sources(bank, ROOT)
    (ROOT / 'data/questions.json').write_text(json.dumps(bank, ensure_ascii=False, indent=2) + '\n')
    print(f"Imported {len(bank)} questions, {sum(len(q['images']) for q in bank)} figures; {sum(q['explanationSource'] == '学习补充' for q in bank)} explanations supplemented.")


if __name__ == '__main__':
    main()
