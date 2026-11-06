"""Refresh static reading-time labels after editing blog articles.

Run from any directory: python3 scripts/update_blog_reading_time.py
Estimates use 400 CJK characters/minute plus 220 other words/minute.
Only .article-body text is counted, excluding navigation and metadata.
"""

from html.parser import HTMLParser
from pathlib import Path
import math
import re

ROOT = Path(__file__).resolve().parents[1]
VOID_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
             'link', 'meta', 'param', 'source', 'track', 'wbr'}


class ArticleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            return
        if self.depth:
            self.depth += 1
        elif 'article-body' in dict(attrs).get('class', '').split():
            self.depth = 1

    def handle_endtag(self, tag):
        if self.depth and tag not in VOID_TAGS:
            self.depth -= 1

    def handle_data(self, data):
        if self.depth:
            self.text.append(data)


def estimate(source):
    parser = ArticleText()
    parser.feed(source)
    text = ' '.join(parser.text)
    if not text.strip():
        raise ValueError('Missing article body')
    cjk_pattern = r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]'
    characters = len(re.findall(cjk_pattern, text))
    words = len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b", re.sub(cjk_pattern, ' ', text)))
    return max(1, math.ceil(characters / 400 + words / 220))


def main():
    minutes = {}
    for directory, language in [(ROOT / 'blog', 'zh'), (ROOT / 'blog/en', 'en')]:
        for path in directory.glob('*.html'):
            if path.name != 'index.html':
                minutes[(path.stem, language)] = estimate(path.read_text())
    for path in [ROOT / 'index.html', *sorted((ROOT / 'blog').rglob('*.html'))]:
        source = path.read_text()

        def replace(match):
            opening, slug, language = match.group(1, 2, 3)
            count = minutes[(slug, language)]
            label = f'About {count} min read' if language == 'en' else f'约 {count} 分钟'
            return f'{opening}{label}</span>'

        updated = re.sub(r'(<span data-reading-time="([^"]+)" data-reading-language="(zh|en)">)[^<]*</span>', replace, source)
        if updated != source:
            path.write_text(updated)
    for (slug, language), count in sorted(minutes.items()):
        print(f'{language} {slug}: {count} min')


if __name__ == '__main__':
    main()
