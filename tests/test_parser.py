"""Tests for Jitendex parser."""

import json
from io import StringIO

import pytest

from jitendex_py import ParseError, ValidationError, parse_terms


class TestParseTerms:
    """Test the main parse_terms function."""

    def test_parse_from_string(self, sample_data):
        """Test parsing from JSON string."""
        result = parse_terms(json.dumps(sample_data))
        assert isinstance(result, list)
        assert len(result) == len(sample_data)

    def test_parse_from_file_object(self, sample_data):
        """Test parsing from file object."""
        json_str = json.dumps(sample_data)
        file_obj = StringIO(json_str)

        result = parse_terms(file_obj)
        assert isinstance(result, list)
        assert len(result) == len(sample_data)

    def test_parse_invalid_json(self):
        """Test error handling for invalid JSON."""
        with pytest.raises(ParseError, match="Invalid JSON"):
            parse_terms("not valid json")

    def test_parse_non_list(self):
        """Test error handling for non-list JSON."""
        with pytest.raises(ValidationError, match="Expected JSON array"):
            parse_terms('{"key": "value"}')


class TestEntryParsing:
    """Test individual entry parsing."""

    def test_entry_structure(self, sample_data):
        """Test that entries have correct structure."""
        result = parse_terms(json.dumps(sample_data))
        entry = result[0]

        assert "text" in entry
        assert "reading" in entry
        assert "definition_tags" in entry
        assert "rules" in entry
        assert "score" in entry
        assert "definitions" in entry
        assert "sequence" in entry
        assert "term_tags" in entry

    def test_entry_with_reading(self, sample_data):
        """Test entry with text and reading."""
        result = parse_terms(json.dumps(sample_data))
        entry = result[0]
        original_entry = sample_data[0]

        assert entry["text"] == original_entry[0]
        assert entry["reading"] == original_entry[1]
        assert entry["sequence"] == original_entry[6]

    def test_entry_tags_as_list(self):
        """Test that tags are converted to lists."""
        # Create test data with tags
        test_entry = [
            "word",
            "reading",
            "tag1 tag2",
            "v1 vk",
            100,
            ["definition"],
            1,
            "term1 term2",
        ]
        result = parse_terms(json.dumps([test_entry]))
        entry = result[0]

        assert entry["definition_tags"] == ["tag1", "tag2"]
        assert entry["rules"] == ["v1", "vk"]
        assert entry["term_tags"] == ["term1", "term2"]

    def test_entry_empty_tags(self):
        """Test that empty tags become empty lists."""
        test_entry = ["word", "reading", "", "", 100, ["definition"], 1, ""]
        result = parse_terms(json.dumps([test_entry]))
        entry = result[0]

        assert entry["definition_tags"] == []
        assert entry["rules"] == []
        assert entry["term_tags"] == []

    def test_entry_empty_text(self):
        """Test that empty text becomes None."""
        test_entry = ["", "reading", "", "", 0, ["def"], 1, ""]
        result = parse_terms(json.dumps([test_entry]))
        entry = result[0]

        assert entry["text"] is None


class TestDefinitionParsing:
    """Test definition parsing."""

    def test_simple_string_definition(self):
        """Test simple string definition."""
        test_entry = ["word", "reading", "", "", 0, ["simple definition"], 1, ""]
        result = parse_terms(json.dumps([test_entry]))

        assert result[0]["definitions"][0] == {
            "type": "text",
            "content": "simple definition",
        }

    def test_text_object_definition(self):
        """Test text object definition."""
        test_entry = [
            "word",
            "reading",
            "",
            "",
            0,
            [{"type": "text", "text": "definition text"}],
            1,
            "",
        ]
        result = parse_terms(json.dumps([test_entry]))

        assert result[0]["definitions"][0] == {
            "type": "text",
            "content": "definition text",
        }

    def test_deinflection_definition(self):
        """Test deinflection array definition."""
        test_entry = [
            "word",
            "reading",
            "",
            "",
            0,
            [["source", "past", "v1", {"type": "text", "text": "original"}]],
            1,
            "",
        ]
        result = parse_terms(json.dumps([test_entry]))

        def_obj = result[0]["definitions"][0]
        assert def_obj["type"] == "deinflection"
        assert def_obj["source_term"] == "source"
        assert def_obj["source_rules"] == "past"
        assert def_obj["inflection_rules"] == "v1"
        assert def_obj["definition"]["content"] == "original"

    def test_image_definition(self):
        """Test image definition."""
        test_entry = [
            "word",
            "reading",
            "",
            "",
            0,
            [
                {
                    "type": "image",
                    "path": "test.png",
                    "width": 100,
                    "height": 200,
                    "title": "Image",
                }
            ],
            1,
            "",
        ]
        result = parse_terms(json.dumps([test_entry]))

        img_def = result[0]["definitions"][0]
        assert img_def["type"] == "image"
        assert img_def["path"] == "test.png"
        assert img_def["width"] == 100
        assert img_def["height"] == 200
        assert img_def["title"] == "Image"


class TestStructuredContentParsing:
    """Test structured content parsing and HTML stripping."""

    def test_simple_text_content(self):
        """Test simple text in structured content."""
        content = "simple text"
        test_entry = [
            "word",
            "reading",
            "",
            "",
            0,
            [{"type": "structured-content", "content": content}],
            1,
            "",
        ]
        result = parse_terms(json.dumps([test_entry]))

        structured = result[0]["definitions"][0]["content"]
        assert structured == "simple text"

    def test_semantic_types_from_data_content(self):
        """Test that data.content determines semantic type."""
        test_entry = [
            "word",
            "reading",
            "",
            "",
            0,
            [
                {
                    "type": "structured-content",
                    "content": {
                        "tag": "div",
                        "data": {"content": "sense-group"},
                        "content": "test",
                    },
                }
            ],
            1,
            "",
        ]
        result = parse_terms(json.dumps([test_entry]))

        structured = result[0]["definitions"][0]["content"]
        assert structured["type"] == "sense-group"

    def test_part_of_speech_info(self):
        """Test part-of-speech-info parsing."""
        test_entry = [
            "word",
            "reading",
            "",
            "",
            0,
            [
                {
                    "type": "structured-content",
                    "content": {
                        "tag": "span",
                        "title": "noun",
                        "data": {
                            "class": "tag",
                            "code": "n",
                            "content": "part-of-speech-info",
                        },
                        "content": "noun",
                    },
                }
            ],
            1,
            "",
        ]
        result = parse_terms(json.dumps([test_entry]))

        pos_info = result[0]["definitions"][0]["content"]
        assert pos_info["type"] == "part-of-speech-info"
        assert pos_info["tag"] == "noun"
        assert pos_info["code"] == "n"

    def test_ruby_annotation_parsing(self):
        """Test ruby annotation parsing."""
        test_entry = [
            "word",
            "reading",
            "",
            "",
            0,
            [
                {
                    "type": "structured-content",
                    "content": {
                        "tag": "ruby",
                        "content": ["一", {"tag": "rt", "content": "いち"}],
                    },
                }
            ],
            1,
            "",
        ]
        result = parse_terms(json.dumps([test_entry]))

        ruby_text = result[0]["definitions"][0]["content"]
        assert "一(いち)" == ruby_text

    def test_cross_reference_parsing(self):
        """Test cross-reference parsing."""
        test_entry = [
            "word",
            "reading",
            "",
            "",
            0,
            [
                {
                    "type": "structured-content",
                    "content": {
                        "tag": "a",
                        "href": "?query=test",
                        "content": "reference",
                    },
                }
            ],
            1,
            "",
        ]
        result = parse_terms(json.dumps([test_entry]))

        xref = result[0]["definitions"][0]["content"]
        assert xref["type"] == "cross-reference"
        assert xref["href"] == "?query=test"
        assert xref["text"] == "reference"

    def test_external_link_parsing(self):
        """Test external link parsing."""
        test_entry = [
            "word",
            "reading",
            "",
            "",
            0,
            [
                {
                    "type": "structured-content",
                    "content": {
                        "tag": "a",
                        "href": "https://example.com",
                        "content": "link",
                    },
                }
            ],
            1,
            "",
        ]
        result = parse_terms(json.dumps([test_entry]))

        link = result[0]["definitions"][0]["content"]
        assert link["type"] == "link"
        assert link["href"] == "https://example.com"

    def test_nested_content_flattening(self):
        """Test that nested lists are flattened."""
        test_entry = [
            "word",
            "reading",
            "",
            "",
            0,
            [
                {
                    "type": "structured-content",
                    "content": [
                        [{"tag": "span", "content": "item1"}],
                        [{"tag": "span", "content": "item2"}],
                    ],
                }
            ],
            1,
            "",
        ]
        result = parse_terms(json.dumps([test_entry]))

        content = result[0]["definitions"][0]["content"]
        # Should be flattened to single list
        assert isinstance(content, list)
        assert len(content) == 2


class TestValidationErrors:
    """Test validation error handling."""

    def test_entry_wrong_length(self):
        """Test error for entry with wrong number of elements."""
        test_entry = ["word", "reading", "", ""]  # Only 4 elements
        with pytest.raises(ValidationError, match="Entry 0: Expected 8 elements"):
            parse_terms(json.dumps([test_entry]))

    def test_entry_not_a_list(self):
        """Test error for entry that is not a list."""
        with pytest.raises(ValidationError, match="Entry 0: Expected list"):
            parse_terms(json.dumps(["not a list"]))

    def test_entry_score_not_numeric(self):
        """Test error for non-numeric score."""
        test_entry = ["word", "reading", "", "", "not a number", [], 1, ""]
        with pytest.raises(ValidationError, match="Entry 0: score must be numeric"):
            parse_terms(json.dumps([test_entry]))

    def test_entry_sequence_not_int(self):
        """Test error for non-integer sequence."""
        test_entry = ["word", "reading", "", "", 100, [], "not an int", ""]
        with pytest.raises(ValidationError, match="Entry 0: sequence must be int"):
            parse_terms(json.dumps([test_entry]))

    def test_entry_definitions_not_list(self):
        """Test error for definitions not being a list."""
        test_entry = ["word", "reading", "", "", 100, "not a list", 1, ""]
        with pytest.raises(ValidationError, match="Entry 0: definitions must be list"):
            parse_terms(json.dumps([test_entry]))

    def test_entry_tags_not_string(self):
        """Test error for tags field not being a string."""
        test_entry = ["word", "reading", 123, "", 100, [], 1, ""]
        with pytest.raises(
            ValidationError, match="Entry 0: definition_tags must be string"
        ):
            parse_terms(json.dumps([test_entry]))

    def test_definition_not_valid_type(self):
        """Test error for definition with invalid type."""
        test_entry = ["word", "reading", "", "", 100, [42], 1, ""]
        with pytest.raises(
            ValidationError,
            match="Entry 0, definition 0: Definition must be string, list, or dict",
        ):
            parse_terms(json.dumps([test_entry]))


class TestRealData:
    """Tests with real sample data."""

    def test_parse_real_sample(self):
        """Test parsing the test_terms.json file."""
        import os

        test_file = os.path.join(os.path.dirname(__file__), "test_terms.json")
        with open(test_file, "r", encoding="utf-8") as f:
            data = f.read()

        result = parse_terms(data)
        assert len(result) == 10

        # Check first entry structure
        first = result[0]
        assert first["text"] is not None
        assert first["reading"] is not None
        assert first["sequence"] > 0
        assert len(first["definitions"]) >= 1

        # Check structured content
        def1 = first["definitions"][0]
        assert def1["type"] in ["structured", "text"]
        assert isinstance(def1["content"], (list, str))


# Fixtures


@pytest.fixture
def sample_data():
    """Sample test data loaded from test_terms.json."""
    import os

    test_file = os.path.join(os.path.dirname(__file__), "test_terms.json")
    with open(test_file, "r", encoding="utf-8") as f:
        return json.load(f)
