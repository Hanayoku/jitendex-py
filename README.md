# jitendex-py

Parse [Jitendex][1] dictionary files for Yomitan (JSON) and convert HTML-structured content to semantic dictionaries.

Useful if you want to use Jitendex without parsing mdict format files.

## Installation

```bash
pip install jitendex-py
```

If you are using uv,

```bash
uv add jitendex-py
```

## Quick Start

```python
from jitendex_py import parse_terms

# Parse from JSON string
with open('term_bank.json', 'r', encoding='utf-8') as f:
    data = f.read()
terms = parse_terms(data)

# Parse from file object
with open('term_bank.json', 'r', encoding='utf-8') as f:
    terms = parse_terms(f)

# Process results
for term in terms:
    print(f"{term['text']} [{term['reading']}]: {len(term['definitions'])} definitions")
```

## Input Format

Accepts Yomitan term bank v3 JSON files with entries as 8-element arrays:

```json
[
  ["text", "reading", "def_tags", "rules", score, [definitions], sequence, "term_tags"],
  ...
]
```

## Output Format

Returns list of dictionaries:

```python
{
    "text": str | None,           # Headword
    "reading": str | None,        # Reading (kana)
    "definition_tags": [str],     # Tags split by whitespace
    "rules": [str],               # Inflection rules
    "score": int,                 # Priority score
    "definitions": [dict],        # Parsed definitions
    "sequence": int,              # Entry ID
    "term_tags": [str]            # Term-level tags
}
```

### Definition Types

Definitions can be one of:

**Text:**
```python
{"type": "text", "content": "gloss text"}
```

**Structured (HTML stripped):**
```python
{
    "type": "structured",
    "content": [
        {"type": "sense-group", "content": [...]},
        {"type": "part-of-speech-info", "tag": "noun", "code": "n", "content": "n"},
        {"type": "glossary", "content": "gloss text"},
        {"type": "cross-reference", "href": "?query=...", "text": "見る"}
    ]
}
```

**Image:**
```python
{"type": "image", "path": "image.png", "width": 100, "height": 200}
```

**Deinflection:**
```python
{
    "type": "deinflection",
    "source_term": "食べた",
    "source_rules": "past",
    "inflection_rules": "v1",
    "definition": {...}
}
```

## Features

- **HTML stripping**: Converts HTML tags to semantic types (`sense-group`, `glossary`, `part-of-speech-info`, etc.)
- **Ruby parsing**: Extracts kanji readings from `<ruby>` annotations as `一(いち)`
- **Cross-references**: Internal links (`?query=...`) become structured references
- **Flexible input**: Accepts JSON strings or file objects

## Example: Processing Entries

```python
from jitendex_py import parse_terms

with open('term_bank.json', 'r', encoding='utf-8') as f:
    terms = parse_terms(f)

# Extract glossary
for term in terms:
    text = term['text']
    for def_obj in term['definitions']:
        if def_obj['type'] == 'structured':
            content = def_obj['content']
            if isinstance(content, list):
                for item in content:
                    if item.get('type') == 'glossary':
                        print(f"{text}: {item['content']}")
```

## License

MIT License

Copyright (c) 2026 Perch Labs Pte Ltd

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

[1]: https://jitendex.org/
