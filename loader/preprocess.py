"""Parsea el corpus de FAQs de Parachute S.A. (texto plano) a una lista de
registros estructurados, listos para generar embeddings y cargarlos a
PostgreSQL.

El corpus tiene un bloque por FAQ, separado por líneas de guiones, con este
formato:

    ID: FAQ-001
    CATEGORÍA: Logística y Ubicación
    PREGUNTA: ¿Dónde se ubica la zona de salto?
    RESPUESTA: ...
    METADATA: {"empresa": "...", ...}
    ------------------------------------------------------------
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

_BLOCK_SEPARATOR = re.compile(r"^-{5,}$", re.MULTILINE)
_FIELD_PATTERN = re.compile(
    r"ID:\s*(?P<faq_code>.+?)\s*\n"
    r"CATEGORÍA:\s*(?P<category>.+?)\s*\n"
    r"PREGUNTA:\s*(?P<question>.+?)\s*\n"
    r"RESPUESTA:\s*(?P<answer>.+?)\s*\n"
    r"METADATA:\s*(?P<metadata>\{.*?\})\s*$",
    re.DOTALL,
)


@dataclass
class FaqRecord:
    faq_code: str
    category: str
    question: str
    answer: str
    metadata: dict


def parse_corpus(path: str | Path) -> list[FaqRecord]:
    """Lee el archivo del corpus y devuelve la lista de FAQs parseadas."""
    text = Path(path).read_text(encoding="utf-8")

    records: list[FaqRecord] = []
    for raw_block in _BLOCK_SEPARATOR.split(text):
        block = raw_block.strip()
        if not block:
            continue

        match = _FIELD_PATTERN.search(block)
        if not match:
            # Bloques sin un FAQ real (ej. el encabezado del documento, delimitado
            # con "=" en vez de "-"): se ignoran en vez de fallar.
            continue

        fields = match.groupdict()
        records.append(
            FaqRecord(
                faq_code=fields["faq_code"],
                category=fields["category"],
                question=fields["question"],
                answer=fields["answer"],
                metadata=json.loads(fields["metadata"]),
            )
        )

    return records


def write_jsonl(records: list[FaqRecord], out_path: str | Path) -> None:
    """Guarda los registros parseados en JSON Lines (un objeto por línea)."""
    out_path = Path(out_path)
    with out_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


if __name__ == "__main__":
    corpus_path = Path(__file__).resolve().parent.parent / "data" / "Corpus_FAQs_Parachute_SA_2026.txt"
    clean_path = Path(__file__).resolve().parent.parent / "data" / "faqs_clean.jsonl"

    parsed = parse_corpus(corpus_path)
    write_jsonl(parsed, clean_path)

    print(f"Se parsearon {len(parsed)} FAQs desde {corpus_path.name}")
    print(f"Guardado en {clean_path}")
