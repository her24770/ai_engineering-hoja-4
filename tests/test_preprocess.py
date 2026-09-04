"""Tests unitarios del parser del corpus (no requieren base de datos)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "loader"))

from preprocess import parse_corpus  # noqa: E402

CORPUS_PATH = Path(__file__).resolve().parent.parent / "data" / "Corpus_FAQs_Parachute_SA_2026.txt"


def test_parses_all_faqs():
    records = parse_corpus(CORPUS_PATH)
    assert len(records) == 120


def test_faq_codes_are_unique():
    records = parse_corpus(CORPUS_PATH)
    codes = [r.faq_code for r in records]
    assert len(codes) == len(set(codes))


def test_required_fields_are_not_empty():
    records = parse_corpus(CORPUS_PATH)
    for record in records:
        assert record.faq_code.startswith("FAQ-")
        assert record.category.strip()
        assert record.question.strip().endswith("?")
        assert record.answer.strip()
        assert isinstance(record.metadata, dict)
        assert "empresa" in record.metadata
