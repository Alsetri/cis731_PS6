# CIS 731 — PS 6: Semantic Search, Chunking, & VDB Schema

Abdulla Mansoor · abdulla03@ksu.edu · Track 2 (VDB)
**Schema authority: DERIVED** (CIS 731, INV-11 — the instructor ontology is not reused)

Submitted under Git tag `ps6-submission`. The graded PDF is
`PS6_Abdulla_Mansoor.pdf` (6 pages, limit 8); `GenAI.pdf` is the audit log.

## Reproduce

```bash
./run_all.sh
```

Runs the FAISS benchmark, the chunking and latency cost model, the
`IndexIDMap2` semantics demo, the schema and contract test suite, and rebuilds
both PDFs. **Exits non-zero if any validation case fails**, so a stale number
cannot reach the report.

## Layout

| path | what it is |
|---|---|
| `PS6_Abdulla_Mansoor.pdf` | **The submission.** Six required sections. |
| `GenAI.pdf` | Generative AI audit log, including the Stage-5 adversarial review. |
| `schema/` | **The tagged deliverable.** JSON Schema, derived ontology, contracts, id mapping, examples, lockfile. See `schema/README.md`. |
| `analysis/index_bench.py` | Measures IVF/HNSW recall, latency, build cost and memory against an exact baseline. |
| `analysis/cost_model.py` | Chunking derivations, storage, and the re-ranking latency model. |
| `out/` | Every measured figure as JSON. The report reads from here; nothing is typed by hand. |

## Headline results

```
Chunking   cap = min(model 256, granularity 192) -> n=192, s=128, rho=1/3, inflation 1.5
           whole index 70-160 MiB across the plausible range of L -> storage is not a constraint

Index      IndexFlatIP    recall 1.0000   1.55 ms/query   184 MB   (exact)
           IVF  256/4     recall 0.9999   0.13 ms         12x
           HNSW M=32/64   recall 0.9802   0.10 ms         16x      230 MB
           -> at 120k vectors, use exact search; ANN earns its risk above ~1e6

Latency    T = T_enc + T_ann + k*T_ce = 1109.5 ms, cross-encoder 99.1%, index 0.14%
           -> tuning nlist/nprobe before tuning k is misallocated effort

Contracts  36/36 validation cases pass (jsonschema 4.26.0, deal 4.24.6)
```

## Known compliance gap

INV-9 limits corpus content to public-domain or instructor-provided material;
the team's PS 4 plan is the authenticated Genius REST API (Tier 2, not public
domain). `admit_document` is written to the invariant rather than the plan and
refuses it. Documented in both PDFs rather than worked around.
