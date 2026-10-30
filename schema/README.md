# `schema/` — PS 6 deliverable

CIS **731** · Abdulla Mansoor · abdulla03@ksu.edu
Schema authority: **DERIVED** (INV-11 — the instructor ontology is not reused)

Submitted under Git tag `ps6-submission`.

| file | what it is |
|---|---|
| `chunk_record.schema.json` | JSON Schema **Draft 2020-12** for the provenance-bearing vector record. Extends the MP 5 chunk record. |
| `trope_ontology.json` | The derived 731 ontology: class hierarchy, relation types, cardinalities, granularity justification, seed instances. |
| `competency_questions.md` | Four competency questions with traversals, plus the questions the ontology deliberately cannot answer. |
| `contracts.py` | `admit_document` and `vdb_upsert` as `deal` contracts, implementing **EmbeddingCompleteness** and **NoOrphanEmbeddings**. |
| `faiss_idmap.py` | The FAISS int64 ↔ `chunk_id` mapping layer, with update and delete semantics demonstrated against a real `IndexIDMap2`. |
| `validate.py` | Test harness: validates examples, exercises every contract from both sides, checks the ontology is well-formed. |
| `examples/` | Generated valid records (VDB and ASR) and the 13 deliberately malformed ones. |
| `requirements.lock` | Pinned validator and toolchain. "The schema validates" is a claim about a specific validator. |

## Run it

```bash
python3 schema/validate.py     # 36 cases; exits non-zero on any failure
python3 schema/faiss_idmap.py  # IndexIDMap2 update/delete demonstration
../run_all.sh                  # everything, including the report PDFs
```

## The two invariants, in plain language

**EmbeddingCompleteness** — every chunk admitted to the corpus has exactly one
vector in the index. No admitted chunk is unretrievable.

**NoOrphanEmbeddings** — every vector in the index belongs to exactly one live,
admitted chunk record. Nothing is retrievable that cannot be traced to a
document whose licence was checked.

They are duals and both are required. Completeness alone permits a store full
of unattributable vectors; NoOrphan alone permits documents that were admitted
and then never embedded. Together they assert a bijection.

## Three things the schema cannot enforce

Listed in the schema's own `x-contract-enforced` block and handled in
`contracts.py` instead:

1. **Unit norm** — JSON Schema cannot compute an aggregate over an array.
   Checked in `vdb_upsert`, and it matters: cosine similarity equals inner
   product *only* on the unit sphere.
2. **Hash integrity** — the shape of a digest is checkable; that it is the
   *right* digest is not. `admit_document` recomputes it from the bytes.
3. **`chunk_id` derivation** — enforced so re-embedding replaces rather than
   duplicating.

`EmbeddingCompleteness` and `NoOrphanEmbeddings` are set-level and cannot be
stated about a single record at all.

## Known compliance gap

INV-9 limits corpus content to public-domain or instructor-provided material.
The team's PS 4 acquisition plan is the authenticated Genius REST API — Tier 2,
**not** public domain. `admit_document` is written to the invariant, not the
plan: it refuses `licensed_api` and `fair_use_excerpt`, and the harness asserts
both refusals. The corpus the pipeline is currently specified against would be
rejected by its own ingest gate. Flagged rather than worked around.
