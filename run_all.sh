#!/usr/bin/env bash
# CIS 731 PS 6 — reproduce every number in the report, from scratch.
#
#   ./run_all.sh
#
# Exits non-zero if schema validation or any contract test fails, so a stale
# or broken number fails the build instead of reaching the PDF.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out

echo "== 1. index benchmark (FAISS, measured) =="
python3 analysis/index_bench.py > out/index_bench.log 2>&1
python3 - <<'PY'
import json; r=json.load(open('out/index_bench.json'))
print(f"   flat {r['flat']['query_ms']:.4f} ms/query, recall 1.0000")
best_ivf=max(r['ivf'], key=lambda e:(e['recall_at_10'], e['speedup_vs_flat']))
print(f"   best IVF  nlist={best_ivf['nlist']} nprobe={best_ivf['nprobe']}: "
      f"recall {best_ivf['recall_at_10']:.4f} at {best_ivf['speedup_vs_flat']}x")
best_h=max(r['hnsw'], key=lambda e:e['recall_at_10'])
print(f"   best HNSW M={best_h['M']} ef={best_h['efSearch']}: "
      f"recall {best_h['recall_at_10']:.4f} at {best_h['speedup_vs_flat']}x")
PY

echo "== 2. chunking + re-ranking cost model =="
python3 analysis/cost_model.py > out/cost_model.log 2>&1
python3 - <<'PY'
import json; r=json.load(open('out/cost_model.json'))
c=r['chunk_length_cap']
print(f"   cap: min(model {c['model_ceiling_tokens']}, granularity "
      f"{c['granularity_ceiling_tokens']}) -> n={c['chosen_n']} s={c['chosen_s']}")
v=r['reranking_latency']['variants'][0]
print(f"   re-rank T={v['T_total_ms']} ms, cross-encoder share {v['cross_encoder_share']:.1%}")
PY

echo "== 3. FAISS IndexIDMap2 update/delete semantics =="
python3 schema/faiss_idmap.py > out/faiss_idmap.log 2>&1
python3 - <<'PY'
import json; r=json.load(open('out/faiss_idmap.json'))
print(f"   {r['collisions']} int64 collisions over {r['n_vectors']:,} ids")
print(f"   naive re-add: {r['naive_readd']['verdict']}")
print(f"   after correct update/delete, in bijection: {r['orphan_check']['in_bijection']}")
PY

echo "== 4. schema validation + contract tests =="
python3 schema/validate.py | tail -n 4

echo
echo "== 5. documents =="
python3 build_pdf.py
python3 build_genai.py
echo
echo "DONE. Artifacts: out/*.json, PS6_Abdulla_Mansoor.pdf, GenAI.pdf"
