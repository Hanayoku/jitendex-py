"""Parser for Jitendex (Yomitan format) dictionary files."""

import json
from io import IOBase
from typing import IO, Union


class JitendexError(Exception):
    """Base exception for jitendex-py."""

    pass


class ParseError(JitendexError):
    """Failed to parse entry or definition."""

    pass


class ValidationError(JitendexError):
    """Entry structure validation failed."""

    pass


def parse_terms(source: Union[str, IO]) -> list[dict]:
    """Parse Yomitan term bank entries from JSON.

    Args:
        source: JSON data as string or file-like object

    Returns:
        List of parsed term dictionaries with stripped HTML

    Raises:
        ParseError: If JSON is invalid or cannot be parsed
        ValidationError: If entry structure is invalid
    """
    data = _load_json(source)

    if not isinstance(data, list):
        raise ValidationError(f"Expected JSON array, got {type(data).__name__}")

    return [_parse_entry(entry, i) for i, entry in enumerate(data)]


def _load_json(source: Union[str, IO]) -> list:
    """Load JSON data from various source types."""
    if isinstance(source, str):
        try:
            return json.loads(source)
        except json.JSONDecodeError as e:
            raise ParseError(
                f"Invalid JSON: {e.msg} at line {e.lineno}, column {e.colno}"
            ) from e
    elif isinstance(source, IOBase) or hasattr(source, "read"):
        try:
            return json.load(source)
        except json.JSONDecodeError as e:
            raise ParseError(
                f"Invalid JSON: {e.msg} at line {e.lineno}, column {e.colno}"
            ) from e
    else:
        raise TypeError(f"Unsupported source type: {type(source).__name__}")


def _parse_entry(entry: list, index: int) -> dict:
    """Parse a single term bank entry (8-element array).

    Yomitan format: [text, reading, def_tags, rules, score, definitions, sequence, term_tags]

    Args:
        entry: The entry array to parse
        index: Entry index for error reporting

    Raises:
        ValidationError: If entry structure is invalid
    """
    if not isinstance(entry, list):
        raise ValidationError(
            f"Entry {index}: Expected list, got {type(entry).__name__}"
        )

    if len(entry) != 8:
        raise ValidationError(
            f"Entry {index}: Expected 8 elements "
            f"[text, reading, def_tags, rules, score, definitions, sequence, term_tags], "
            f"got {len(entry)}"
        )

    text, reading, def_tags, rules, score, definitions, sequence, term_tags = entry

    # Validate types
    if not isinstance(score, (int, float)):
        raise ValidationError(
            f"Entry {index}: score must be numeric, got {type(score).__name__}"
        )

    if not isinstance(sequence, int):
        raise ValidationError(
            f"Entry {index}: sequence must be int, got {type(sequence).__name__}"
        )

    if not isinstance(definitions, list):
        raise ValidationError(
            f"Entry {index}: definitions must be list, got {type(definitions).__name__}"
        )

    return {
        "text": text or None,
        "reading": reading or None,
        "definition_tags": _split_tags(def_tags, index, "definition_tags"),
        "rules": _split_tags(rules, index, "rules"),
        "score": int(score),
        "definitions": [
            _parse_definition(d, index, i) for i, d in enumerate(definitions)
        ],
        "sequence": sequence,
        "term_tags": _split_tags(term_tags, index, "term_tags"),
    }


def _split_tags(tags: Union[str, None], entry_index: int, field_name: str) -> list[str]:
    """Split space-separated tags into list."""
    if tags is None or tags == "":
        return []
    if not isinstance(tags, str):
        raise ValidationError(
            f"Entry {entry_index}: {field_name} must be string, got {type(tags).__name__}"
        )
    return tags.split()


def _parse_definition(
    definition: Union[str, dict, list], entry_idx: int, def_idx: int
) -> dict:
    """Parse a definition object.

    Args:
        definition: Definition to parse
        entry_idx: Entry index for error reporting
        def_idx: Definition index for error reporting

    Raises:
        ValidationError: If definition structure is invalid
    """
    context = f"Entry {entry_idx}, definition {def_idx}"

    if isinstance(definition, str):
        return {"type": "text", "content": definition}

    if isinstance(definition, list):
        # Deinflection array: [source_term, source_rules, inflection_rules, definition]
        if len(definition) == 4:
            return {
                "type": "deinflection",
                "source_term": definition[0],
                "source_rules": definition[1],
                "inflection_rules": definition[2],
                "definition": _parse_definition(definition[3], entry_idx, def_idx),
            }
        return {
            "type": "list",
            "content": [
                _parse_definition(d, entry_idx, i) for i, d in enumerate(definition)
            ],
        }

    if not isinstance(definition, dict):
        raise ValidationError(
            f"{context}: Definition must be string, list, or dict, got {type(definition).__name__}"
        )

    def_type = definition.get("type", "unknown")

    if def_type == "text":
        return {
            "type": "text",
            "content": definition.get("text", ""),
        }

    elif def_type == "structured-content":
        return {
            "type": "structured",
            "content": _parse_structured_content(definition.get("content")),
        }

    elif def_type == "image":
        return {
            "type": "image",
            "path": definition.get("path", ""),
            "width": definition.get("width"),
            "height": definition.get("height"),
            "title": definition.get("title"),
            "alt": definition.get("alt"),
            "description": definition.get("description"),
        }

    else:
        return {
            "type": def_type,
            "content": str(definition),
        }


def _parse_structured_content(
    content: Union[str, list, dict, None],
) -> Union[str, list, dict]:
    """Parse structured content (HTML-like) and strip tags while preserving semantic meaning.

    Converts HTML structure into semantic types based on data.content field:
    - sense-group, sense, glossary, extra-info, xref, part-of-speech-info, etc.
    - Preserves text and ruby annotations
    """
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        results = [_parse_structured_content(item) for item in content]
        # Flatten and filter out empty strings
        return _flatten_results(results)

    if not isinstance(content, dict):
        return str(content)

    # Get semantic type from data.content
    semantic_type = _get_semantic_type(content)

    # Handle ruby annotations specially
    if content.get("tag") == "ruby":
        return _parse_ruby(content)

    # Handle cross-references
    if content.get("tag") == "a":
        return _parse_anchor(content)

    # Handle line breaks
    if content.get("tag") == "br":
        return {"type": "break"}

    # Handle images
    if content.get("tag") == "img":
        return {
            "type": "image",
            "path": content.get("path", ""),
            "alt": content.get("alt", ""),
        }

    # Process child content
    child_content = content.get("content")
    if child_content is None:
        return {"type": semantic_type, "content": []}

    parsed_child = _parse_structured_content(child_content)

    # Build result based on semantic type
    result: dict[str, Union[str, list, dict]] = {"type": semantic_type}

    # Add semantic attributes
    if semantic_type == "part-of-speech-info":
        result["tag"] = content.get("title", "")
        result["code"] = (
            content.get("data", {}).get("code", "")
            if isinstance(content.get("data"), dict)
            else ""
        )

    if semantic_type == "xref":
        result["href"] = content.get("href", "")

    # Set content
    if isinstance(parsed_child, list) and len(parsed_child) == 1:
        result["content"] = parsed_child[0]
    else:
        result["content"] = parsed_child

    return result


def _get_semantic_type(content: dict) -> str:
    """Extract semantic type from data.content field or tag name."""
    data = content.get("data", {})

    if isinstance(data, dict):
        semantic = data.get("content", "")
        if semantic:
            return semantic

    # Fallback to tag name
    tag = content.get("tag", "container")
    return tag


def _parse_ruby(content: dict) -> str:
    """Parse ruby annotation and return plain text with reading."""
    ruby_content = content.get("content", [])
    if not isinstance(ruby_content, list):
        return str(ruby_content)

    # Extract base text and reading
    base_text = ""
    reading = ""

    for item in ruby_content:
        if isinstance(item, str):
            base_text += item
        elif isinstance(item, dict) and item.get("tag") == "rt":
            rt_content = item.get("content", "")
            if isinstance(rt_content, list):
                reading += "".join(str(x) for x in rt_content if isinstance(x, str))
            else:
                reading += str(rt_content)

    # Return plain text with reading in parentheses
    if reading:
        return f"{base_text}({reading})"
    return base_text


def _parse_anchor(content: dict) -> dict:
    """Parse anchor tag into cross-reference or link structure."""
    href = content.get("href", "")
    link_content = _parse_structured_content(content.get("content", []))

    # Cross-reference (starts with ?)
    if href.startswith("?"):
        return {
            "type": "cross-reference",
            "href": href,
            "text": link_content,
        }

    # External link
    return {
        "type": "link",
        "href": href,
        "text": link_content,
    }


def _flatten_results(results: list) -> list:
    """Flatten nested lists and filter empty strings."""
    flat = []
    for item in results:
        if isinstance(item, list):
            flat.extend(_flatten_results(item))
        elif item not in (None, ""):
            flat.append(item)
    return flat
