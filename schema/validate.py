"""
CIS 731 — PS 6: schema validation and contract test harness.

Generates example records, validates them against chunk_record.schema.json
with the pinned validator in requirements.lock, and exercises every contract
in contracts.py from both sides — a valid call that must succeed and a
deliberately broken call that must be refused.

A contract that is only ever shown accepting good input proves nothing. Each
negative case below names the specific failure it provokes.

Exits non-zero if any case does not behave as specified.
"""

from __future__ import annotations

import hashlib
import json
import sys
from importlib.metadata import version
from pathlib import Path

import numpy as np
from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parent))

import deal  # noqa: E402

from contracts import (  # noqa: E402
    INV9_ADMISSIBLE_LICENCES,
    NON_ADMISSIBLE_LICENCES,
    admit_document,
    assert_bijection,
    check_embedding_completeness,
    check_no_orphan_embeddings,
    delete_chunk,
    derive_chunk_id,
    vdb_upsert,
)

HERE = Path(__file__).resolve().parent
SCHEMA = json.loads((HERE / "chunk_record.schema.json").read_text())
EXAMPLES = HERE / "examples"
OUT = HERE.parent / "out" / "validation.json"

RESULTS: list[dict] = []
FAILED = 0


def case(name: str, ok: bool, detail: str = "") -> None:
    global FAILED
    RESULTS.append({"case": name, "ok": ok, "detail": detail})
    if not ok:
        FAILED += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def unit_vector(seed: int, d: int = 384) -> list[float]:
    rng = np.random.default_rng(seed)
    v = rng.normal(size=d)
    v /= np.linalg.norm(v)
    return [round(float(x), 6) for x in v]


def make_record(
    doc_id: str = "librivox:doc000001",
    chunk_index: int = 0,
    chunker_version: str = "v1.0.0",
    license_class: str = "public_domain",
    seed: int = 1,
    **over,
) -> dict:
    vec = unit_vector(seed)
    # Rounding to 6 dp perturbs the norm; renormalize so the record is
    # genuinely unit-length rather than approximately so.
    arr = np.array(vec)
    arr /= np.linalg.norm(arr)
    vec = [float(x) for x in arr]
    rec = {
        "chunk_id": derive_chunk_id(doc_id, chunk_index, chunker_version),
        "doc_id": doc_id,
        "chunk_index": chunk_index,
        "chunker_version": chunker_version,
        "source_hash": hashlib.sha256(b"raw document bytes").hexdigest(),
        "license_class": license_class,
        "corpus_type": "lyrics",
        "release_year": 1997,
        "trope_ids": ["LEX-0001", "SON-0003"],
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "embedding_dim": 384,
        "vector": vec,
        "text": "sample chunk text standing in for an admitted verse",
        "token_count": 171,
        "created_ts": "2026-10-27T12:00:00Z",
        "provenance_verified": True,
    }
    rec.update(over)
    return rec


def main() -> None:
    validator = Draft202012Validator(SCHEMA)
    EXAMPLES.mkdir(parents=True, exist_ok=True)

    print("\n=== 0. Schema is itself a legal Draft 2020-12 schema ===")
    try:
        Draft202012Validator.check_schema(SCHEMA)
        case("chunk_record.schema.json is a valid Draft 2020-12 schema", True,
             f"jsonschema {version('jsonschema')}")
    except Exception as e:  # noqa: BLE001
        case("chunk_record.schema.json is a valid Draft 2020-12 schema",
             False, str(e))

    print("\n=== 1. Valid records validate ===")
    valid = make_record()
    errs = list(validator.iter_errors(valid))
    case("canonical VDB (lyrics) record validates", not errs,
         errs[0].message if errs else "")
    (EXAMPLES / "valid_vdb_chunk.json").write_text(json.dumps(valid, indent=2))

    asr = make_record(doc_id="instructor:seg000012", seed=2,
                      license_class="instructor_provided",
                      corpus_type="asr_transcript",
                      broadcast_ts="2026-10-19T14:00:00Z")
    asr.pop("release_year")
    errs = list(validator.iter_errors(asr))
    case("ASR record with broadcast_ts validates", not errs,
         errs[0].message if errs else "")
    (EXAMPLES / "valid_asr_chunk.json").write_text(json.dumps(asr, indent=2))

    print("\n=== 2. Schema REJECTS what it is supposed to reject ===")
    negatives = [
        ("release_year present on an ASR record",
         {**asr, "release_year": 2026}),
        ("ASR record missing broadcast_ts",
         {k: v for k, v in asr.items() if k != "broadcast_ts"}),
        ("VDB record missing release_year",
         {k: v for k, v in valid.items() if k != "release_year"}),
        ("unlisted source prefix in doc_id",
         make_record(doc_id="pastebin:doc000001")),
        ("licence outside the enum",
         make_record(license_class="unknown")),
        ("embedding_dim disagrees with embedding_model",
         make_record(embedding_dim=768)),
        ("vector length disagrees with the model",
         make_record(vector=unit_vector(3, 256))),
        ("token_count above the model max sequence length",
         make_record(token_count=400)),
        ("malformed trope id",
         make_record(trope_ids=["LEXICAL-1"])),
        ("duplicate trope ids",
         make_record(trope_ids=["LEX-0001", "LEX-0001"])),
        ("source_hash not a sha256 digest",
         make_record(source_hash="deadbeef")),
        ("unknown extra property",
         make_record(notes="should be rejected")),
        ("empty text",
         make_record(text="")),
    ]
    for label, bad in negatives:
        errs = list(validator.iter_errors(bad))
        case(f"rejects: {label}", bool(errs),
             "ACCEPTED — schema hole" if not errs else "")
    (EXAMPLES / "invalid_examples.json").write_text(
        json.dumps({label: rec for label, rec in negatives}, indent=2)
    )

    print("\n=== 3. admit_document contract ===")
    raw = b"raw document bytes"
    doc = {"doc_id": "librivox:doc000001", "license_class": "public_domain",
           "source_hash": hashlib.sha256(raw).hexdigest()}
    try:
        out = admit_document(doc, raw)
        case("admits public_domain and sets provenance_verified",
             out["provenance_verified"] is True)
        case("recomputes source_hash from the bytes admitted",
             out["source_hash"] == hashlib.sha256(raw).hexdigest())
    except Exception as e:  # noqa: BLE001
        case("admits public_domain", False, repr(e))

    for lic in sorted(NON_ADMISSIBLE_LICENCES):
        bad = {**doc, "license_class": lic}
        try:
            admit_document(bad, raw)
            case(f"INV-9 refuses license_class={lic}", False,
                 "ADMITTED — invariant hole")
        except deal.PreContractError:
            case(f"INV-9 refuses license_class={lic}", True)

    try:
        admit_document({**doc, "source_hash": "nothex"}, raw)
        case("refuses a malformed source_hash", False, "ADMITTED")
    except deal.PreContractError:
        case("refuses a malformed source_hash", True)

    print("\n=== 4. vdb_upsert contract ===")
    index: dict = {}
    rec = make_record()
    vdb_upsert(index, rec)
    case("upsert inserts one vector", len(index) == 1)
    vdb_upsert(index, rec)
    case("re-upserting the same chunk_id does NOT duplicate", len(index) == 1,
         f"index holds {len(index)}")

    unverified = make_record(seed=5, provenance_verified=False)
    try:
        vdb_upsert(index, unverified)
        case("refuses a record that never cleared admit_document", False,
             "INDEXED — this is how an unlicensed vector gets in")
    except deal.PreContractError:
        case("refuses a record that never cleared admit_document", True)

    forged = make_record(seed=6)
    forged["chunk_id"] = "0" * 64
    try:
        vdb_upsert(index, forged)
        case("refuses a chunk_id that is not the derived digest", False,
             "INDEXED")
    except deal.PreContractError:
        case("refuses a chunk_id that is not the derived digest", True)

    unnormalized = make_record(seed=7)
    unnormalized["vector"] = [x * 2.0 for x in unnormalized["vector"]]
    try:
        vdb_upsert(index, unnormalized)
        case("refuses a vector that is not unit-normalized", False,
             "INDEXED — every cosine score it touches is now wrong")
    except deal.PreContractError:
        case("refuses a vector that is not unit-normalized", True)

    print("\n=== 5. EmbeddingCompleteness and NoOrphanEmbeddings ===")
    records = [make_record(doc_id=f"librivox:doc{i:06d}", seed=100 + i)
               for i in range(5)]
    idx: dict = {}
    for r in records:
        vdb_upsert(idx, r)
    try:
        assert_bijection(records, idx)
        case("a clean corpus satisfies both invariants", True,
             f"{len(records)} records, {len(idx)} vectors")
    except Exception as e:  # noqa: BLE001
        case("a clean corpus satisfies both invariants", False, repr(e))

    # Completeness violation: a record admitted but never embedded.
    extra = make_record(doc_id="librivox:doc000099", seed=200)
    missing = check_embedding_completeness(records + [extra], idx)
    case("detects an admitted chunk with no vector", len(missing) == 1,
         f"found {len(missing)}")

    # Orphan violation: delete the record but leave the vector.
    orphan_idx = dict(idx)
    survivors = records[1:]
    orphans = check_no_orphan_embeddings(survivors, orphan_idx)
    case("detects a vector with no live record", len(orphans) == 1,
         f"found {len(orphans)}")

    # The safe deletion order repairs both sides at once.
    recs2, idx2 = list(records), dict(idx)
    delete_chunk(idx2, recs2, records[0]["chunk_id"])
    try:
        assert_bijection(recs2, idx2)
        case("delete_chunk leaves the corpus in bijection", True,
             f"{len(recs2)} records, {len(idx2)} vectors")
    except Exception as e:  # noqa: BLE001
        case("delete_chunk leaves the corpus in bijection", False, repr(e))

    print("\n=== 6. Ontology is well-formed and DERIVED (INV-11) ===")
    onto = json.loads((HERE / "trope_ontology.json").read_text())
    case("ontology declares authority DERIVED",
         onto["authority"] == "DERIVED", onto["authority"])
    case("every relation declares domain, range and cardinality",
         all({"domain", "range", "cardinality"} <= set(v)
             for v in onto["relations"].values()))
    case("attestedIn has minimum cardinality 1 (no unevidenced trope)",
         onto["relations"]["attestedIn"]["cardinality"] == "1..*")
    prefixes = {c["id_prefix"] for c in onto["classes"].values()
                if "id_prefix" in c}
    case("trope id prefixes match the record schema pattern",
         {"LEX", "THM", "SON", "NAR"} <= prefixes)
    regions = {r["id"] for r in onto["closed_sets"]["Region"]}
    case("every seeded micro-genre originates in a declared region",
         all(m["originatesIn"] in regions
             for m in onto["seed_instances"]["MicroGenre"]))
    eras = {e["id"] for e in onto["seed_instances"]["Era"]}
    case("every micro-genre's active eras exist",
         all(set(m["activeDuring"]) <= eras
             for m in onto["seed_instances"]["MicroGenre"]))

    summary = {
        "jsonschema_version": version("jsonschema"),
        "deal_version": version("deal"),
        "numpy_version": version("numpy"),
        "total_cases": len(RESULTS),
        "passed": len(RESULTS) - FAILED,
        "failed": FAILED,
        "result": "PASS" if FAILED == 0 else "FAIL",
        "cases": RESULTS,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2))

    print(f"\n{'=' * 62}")
    print(f"VALIDATION: {summary['result']} "
          f"({summary['passed']}/{summary['total_cases']} cases)")
    print(f"{'=' * 62}")
    sys.exit(0 if FAILED == 0 else 1)


if __name__ == "__main__":
    main()
