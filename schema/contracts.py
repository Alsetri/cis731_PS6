"""
CIS 731 — PS 6, Part 2: deal contracts for admit_document and vdb_upsert.

Two named invariants, stated in plain language before they are stated in code:

  EmbeddingCompleteness
      Every chunk record admitted to the corpus has exactly one vector in the
      index. No admitted chunk is unretrievable.

  NoOrphanEmbeddings
      Every vector in the index belongs to exactly one live, admitted chunk
      record. No vector is retrievable that cannot be traced to a document
      whose licence was checked.

They are duals, and both are needed. Completeness alone permits a store full
of vectors nobody can attribute; NoOrphan alone permits a corpus whose
documents were admitted and then silently never embedded. Together they say
the record set and the vector set are in bijection.

Neither is a property of a single record, which is why neither can live in
chunk_record.schema.json: JSON Schema validates one document at a time and
cannot quantify over an index.
"""

from __future__ import annotations

import hashlib
import math
from typing import Iterable, Sequence

import deal

# INV-9: corpus content is limited to public-domain or instructor-provided
# material. The other licence classes are representable in the schema purely
# so that non-conforming material can be NAMED and REJECTED rather than
# relabelled; they are not admissible.
INV9_ADMISSIBLE_LICENCES = frozenset({
    "public_domain", "cc_by", "instructor_provided",
})

NON_ADMISSIBLE_LICENCES = frozenset({
    "licensed_api", "fair_use_excerpt",
})

MODEL_DIMS = {
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "sentence-transformers/all-mpnet-base-v2": 768,
}

UNIT_NORM_TOL = 1e-5


class ProvenanceError(ValueError):
    """Raised when a document fails the INV-9 licence gate."""


class OrphanVectorError(ValueError):
    """Raised when the index and the record set disagree."""


# ---------------------------------------------------------------------------
# chunk_id derivation
# ---------------------------------------------------------------------------

def derive_chunk_id(doc_id: str, chunk_index: int, chunker_version: str) -> str:
    """chunk_id = SHA-256('doc_id|chunk_index|chunker_version').

    Deterministic on purpose. A random id would make re-embedding the same
    chunk produce a NEW key, so the upsert would insert instead of replace and
    the old vector would become an orphan -- violating NoOrphanEmbeddings on
    every re-run. Determinism is what makes the pipeline idempotent.
    """
    payload = f"{doc_id}|{chunk_index}|{chunker_version}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def l2_norm(vector: Sequence[float]) -> float:
    return math.sqrt(sum(float(x) * float(x) for x in vector))


# ---------------------------------------------------------------------------
# admit_document
# ---------------------------------------------------------------------------

# NOTE ON deal SIGNATURES: a @deal.pre validator is called with the SAME
# argument list as the function it guards, so a one-parameter lambda on a
# two-parameter function raises TypeError at call time rather than failing the
# contract. The `_raw` parameters below are unused by the predicate and
# present only to match the signature.
@deal.pre(
    lambda doc, _raw: isinstance(doc.get("license_class"), str),
    message="license_class must be present and a string",
)
@deal.pre(
    lambda doc, _raw: doc["license_class"] in INV9_ADMISSIBLE_LICENCES,
    message="INV-9: only public_domain, cc_by or instructor_provided "
            "material may enter the corpus",
)
@deal.pre(
    lambda doc, _raw: isinstance(doc.get("source_hash"), str)
    and len(doc["source_hash"]) == 64
    and all(c in "0123456789abcdef" for c in doc["source_hash"]),
    message="source_hash must be a lowercase SHA-256 hex digest",
)
@deal.post(
    lambda result: result["provenance_verified"] is True,
    message="postcondition: an admitted document is provenance_verified",
)
@deal.ensure(
    lambda doc, raw_bytes, result:
        result["source_hash"] == hashlib.sha256(raw_bytes).hexdigest(),
    message="postcondition: source_hash matches the bytes actually admitted",
)
def admit_document(doc: dict, raw_bytes: bytes) -> dict:
    """Admit a source document to the corpus.

    Precondition  — license_class is in the INV-9 admissible set.
    Postcondition — the returned record carries provenance_verified = True and
                    a source_hash that is the digest of the bytes admitted.

    In plain language: nothing enters the corpus unless we know its licence
    permits it and we have fixed the exact bytes we are claiming to have read.
    The hash is recomputed here rather than trusted from the caller, because a
    caller-supplied hash certifies nothing.
    """
    out = dict(doc)
    out["source_hash"] = hashlib.sha256(raw_bytes).hexdigest()
    out["provenance_verified"] = True
    return out


# ---------------------------------------------------------------------------
# vdb_upsert
# ---------------------------------------------------------------------------

@deal.pre(
    lambda index, record: record.get("provenance_verified") is True,
    message="a record that has not cleared admit_document cannot be indexed",
)
@deal.pre(
    lambda index, record:
        record["chunk_id"] == derive_chunk_id(
            record["doc_id"], record["chunk_index"], record["chunker_version"]
        ),
    message="chunk_id must be the derived digest, or upsert is not idempotent",
)
@deal.pre(
    lambda index, record:
        len(record["vector"]) == MODEL_DIMS[record["embedding_model"]]
        == record["embedding_dim"],
    message="vector length, embedding_dim and embedding_model must agree",
)
@deal.pre(
    lambda index, record: abs(l2_norm(record["vector"]) - 1.0) <= UNIT_NORM_TOL,
    message="vector must be unit-normalized: inner product only equals cosine "
            "similarity on the unit sphere, so an unnormalized vector "
            "silently corrupts every score it participates in",
)
@deal.ensure(
    lambda index, record, result:
        sum(1 for cid in result if cid == record["chunk_id"]) == 1,
    message="EmbeddingCompleteness/NoOrphanEmbeddings: exactly one vector "
            "per chunk_id after the upsert",
)
def vdb_upsert(index: dict, record: dict) -> dict:
    """Insert or replace the vector for one chunk.

    Precondition  — the record cleared admit_document, its chunk_id is the
                    derived digest, and its vector is unit-normalized and of
                    the dimension its model declares.
    Postcondition — the index holds exactly one vector for this chunk_id.

    In plain language: a chunk may be embedded again as often as we like, and
    the index will never end up with two vectors for it, nor zero.

    `index` is a plain dict here so the contract is testable without FAISS;
    faiss_idmap.py demonstrates the same semantics against a real
    IndexIDMap2.
    """
    index[record["chunk_id"]] = record["vector"]
    return index


# ---------------------------------------------------------------------------
# Set-level invariants
# ---------------------------------------------------------------------------

def check_embedding_completeness(
    records: Iterable[dict], index: dict
) -> list[str]:
    """Return the chunk_ids of admitted records that have no vector."""
    return sorted(
        r["chunk_id"] for r in records
        if r.get("provenance_verified") is True and r["chunk_id"] not in index
    )


def check_no_orphan_embeddings(
    records: Iterable[dict], index: dict
) -> list[str]:
    """Return the chunk_ids present in the index with no live record."""
    live = {
        r["chunk_id"] for r in records
        if r.get("provenance_verified") is True
    }
    return sorted(cid for cid in index if cid not in live)


def assert_bijection(records: Iterable[dict], index: dict) -> None:
    """Both invariants at once. Raises on the first violation found."""
    records = list(records)
    missing = check_embedding_completeness(records, index)
    if missing:
        raise OrphanVectorError(
            f"EmbeddingCompleteness violated: {len(missing)} admitted "
            f"chunk(s) have no vector, first={missing[0]}"
        )
    orphans = check_no_orphan_embeddings(records, index)
    if orphans:
        raise OrphanVectorError(
            f"NoOrphanEmbeddings violated: {len(orphans)} vector(s) have no "
            f"live record, first={orphans[0]}"
        )


def delete_chunk(index: dict, records: list[dict], chunk_id: str) -> None:
    """Delete a chunk from BOTH sides, in the order that cannot orphan.

    Vector first, then record. The reverse order leaves a window in which the
    vector is retrievable while its record is gone -- precisely an orphan. If
    the process dies between the two steps here, the result is a missing
    embedding (detectable, repairable by re-embedding) rather than an
    unattributable vector (undetectable without a full scan).
    """
    index.pop(chunk_id, None)
    records[:] = [r for r in records if r["chunk_id"] != chunk_id]
