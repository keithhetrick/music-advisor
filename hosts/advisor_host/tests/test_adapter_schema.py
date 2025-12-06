import pytest
from advisor_host.adapter.adapter import ParseError, parse_helper_text, parse_payload
from advisor_host.schema.schema import validate_reply_shape


def test_parse_helper_text_success():
    txt = "/audio import {\"foo\": 1}"
    obj = parse_helper_text(txt)
    assert obj["foo"] == 1


def test_parse_helper_text_failure():
    with pytest.raises(ParseError):
        parse_helper_text("no marker here")


def test_parse_payload_failure():
    with pytest.raises(ParseError):
        parse_payload("not a dict")


def test_validate_reply_shape_missing():
    with pytest.raises(ValueError):
        validate_reply_shape({"reply": "hi"})
