"""
CIS 731 — PS 6, Part 1: Index and Similarity Analysis.

Measures, rather than asserts, the IVF/HNSW trade-offs the spec asks for:
query latency, build cost, memory, and recall degradation against an exact
IndexFlatIP baseline.

HONESTY NOTE ON THE DATA
------------------------
The team's corpus has not been embedded yet, so this runs on synthetic
384-d vectors. They are NOT uniform random: uniform points on a sphere have
no cluster structure, which makes IVF look far worse than it is in practice
and would produce a flattering-to-HNSW table that does not transfer. The
generator draws from 200 Gaussian clusters and unit-normalizes, which mimics
the topical clustering a sentence-embedding space actually exhibits.

Recall figures therefore characterise THIS distribution. The latency and
memory figures are properties of the index and transfer directly; the recall
figures are indicative and are labelled as such in the report.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import faiss
import numpy as np

D = 384                 # all-MiniLM-L6-v2 embedding dimension
N = 120_000             # 12k documents x ~10 chunks/document
N_QUERY = 1_000
K = 10
N_CLUSTERS = 200
SPREAD = 0.35           # expected displacement from cluster centre, in units
                        # of the unit sphere (see make_corpus)
SEED = 20261027

OUT = Path("out/index_bench.json")


def make_corpus() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(SEED)
    centers = rng.normal(size=(N_CLUSTERS, D)).astype("float32")
    centers /= np.linalg.norm(centers, axis=1, keepdims=True)
    assign = rng.integers(0, N_CLUSTERS, size=N)

    # NOISE MUST BE SCALED BY 1/sqrt(D).
    #
    # A first version of this generator used `0.35 * rng.normal(size=(N, D))`.
    # In 384 dimensions that perturbation has expected norm 0.35*sqrt(384)
    # ~= 6.9, which utterly swamps the unit-norm cluster centre: after
    # normalization the points were uniform noise on the sphere with no
    # cluster structure at all. Both IVF and HNSW then measured 1-30% recall,
    # which is the correct answer for uniform high-dimensional data and a
    # completely misleading one for an embedding space.
    #
    # Dividing by sqrt(D) makes SPREAD the expected norm of the displacement,
    # so it is interpretable: 0.35 means a point sits ~0.35 away from its
    # centre on a unit sphere.
    sigma = SPREAD / np.sqrt(D)
    xb = centers[assign] + sigma * rng.normal(size=(N, D)).astype("float32")
    xb /= np.linalg.norm(xb, axis=1, keepdims=True)

    qa = rng.integers(0, N_CLUSTERS, size=N_QUERY)
    xq = centers[qa] + sigma * rng.normal(size=(N_QUERY, D)).astype("float32")
    xq /= np.linalg.norm(xq, axis=1, keepdims=True)
    return xb.astype("float32"), xq.astype("float32")


def timed_search(index, xq, k, reps=3) -> float:
    """Median per-query latency in milliseconds."""
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        index.search(xq, k)
        times.append((time.perf_counter() - t0) / len(xq) * 1000)
    return float(np.median(times))


def recall_at_k(approx_ids: np.ndarray, exact_ids: np.ndarray) -> float:
    """Mean fraction of the exact top-k that the approximate index returned."""
    hits = sum(len(set(a) & set(e)) for a, e in zip(approx_ids, exact_ids))
    return hits / (len(exact_ids) * exact_ids.shape[1])


def main() -> None:
    faiss.omp_set_num_threads(2)
    xb, xq = make_corpus()
    res: dict = {
        "config": {
            "d": D, "n_vectors": N, "n_queries": N_QUERY, "k": K,
            "n_clusters_synthetic": N_CLUSTERS, "seed": SEED,
            "faiss_version": faiss.__version__,
            "threads": 2,
        }
    }

    # ---------------------------------------------------------------- proof
    # Empirical backing for the analytic claim that cosine == inner product
    # on unit-normalized vectors. Not a substitute for the proof in the
    # report; a check that the implementation matches the algebra.
    a, b = xb[:500], xb[500:1000]
    ip = np.sum(a * b, axis=1)
    cos = ip / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1))
    res["cosine_equals_ip"] = {
        "max_abs_difference": float(np.max(np.abs(ip - cos))),
        "max_norm_deviation_from_1": float(
            np.max(np.abs(np.linalg.norm(xb, axis=1) - 1.0))
        ),
    }

    # ------------------------------------------------------------ IndexFlatIP
    flat = faiss.IndexFlatIP(D)
    t0 = time.perf_counter()
    flat.add(xb)
    flat_build = time.perf_counter() - t0
    flat_ms = timed_search(flat, xq, K)
    _, exact_ids = flat.search(xq, K)
    res["flat"] = {
        "index": "IndexFlatIP",
        "build_sec": round(flat_build, 3),
        "query_ms": round(flat_ms, 4),
        "memory_bytes": N * D * 4,
        "recall_at_10": 1.0,
        "note": "exhaustive; defines the ground truth",
    }

    # ----------------------------------------------------------- IndexIVFFlat
    res["ivf"] = []
    for nlist in (256, 1024):
        quant = faiss.IndexFlatIP(D)
        ivf = faiss.IndexIVFFlat(quant, D, nlist, faiss.METRIC_INNER_PRODUCT)
        t0 = time.perf_counter()
        ivf.train(xb)
        train_s = time.perf_counter() - t0
        t0 = time.perf_counter()
        ivf.add(xb)
        add_s = time.perf_counter() - t0
        for nprobe in (1, 4, 8, 16, 32):
            if nprobe > nlist:
                continue
            ivf.nprobe = nprobe
            ms = timed_search(ivf, xq, K)
            _, ids = ivf.search(xq, K)
            res["ivf"].append({
                "index": f"IndexIVFFlat(nlist={nlist})",
                "nlist": nlist, "nprobe": nprobe,
                "train_sec": round(train_s, 2),
                "add_sec": round(add_s, 2),
                "query_ms": round(ms, 4),
                "recall_at_10": round(recall_at_k(ids, exact_ids), 4),
                "memory_bytes": N * D * 4 + nlist * D * 4,
                "speedup_vs_flat": round(flat_ms / ms, 1),
            })

    # ---------------------------------------------------------- IndexHNSWFlat
    # HNSW UNDER BOTH METRICS.
    #
    # For unit-normalized vectors ||a-b||^2 = 2 - 2(a.b), so L2 distance is a
    # strictly decreasing function of inner product and the two induce the
    # SAME ranking. That equivalence is proved in the report; here it is
    # tested, because HNSW's graph construction assumes a metric and inner
    # product is not one (it violates the triangle inequality and a point is
    # not its own nearest neighbour under IP). If METRIC_L2 beats
    # METRIC_INNER_PRODUCT on identical data, the graph is the reason.
    res["hnsw"] = []
    for M, metric, mname in ((16, faiss.METRIC_INNER_PRODUCT, "IP"),
                             (16, faiss.METRIC_L2, "L2"),
                             (32, faiss.METRIC_L2, "L2")):
        hnsw = faiss.IndexHNSWFlat(D, M, metric)
        hnsw.hnsw.efConstruction = 40
        t0 = time.perf_counter()
        hnsw.add(xb)
        build_s = time.perf_counter() - t0
        # Layer 0 holds up to 2M neighbours per node, upper layers M. The
        # geometric decay of level sizes makes the upper layers a small
        # constant addition, so 2M + M is the right first-order link budget.
        link_bytes = N * (2 * M + M) * 4
        for ef in (16, 32, 64, 128):
            hnsw.hnsw.efSearch = ef
            ms = timed_search(hnsw, xq, K)
            _, ids = hnsw.search(xq, K)
            res["hnsw"].append({
                "index": f"IndexHNSWFlat(M={M}, {mname})",
                "metric": mname,
                "M": M, "efSearch": ef, "efConstruction": 40,
                "build_sec": round(build_s, 2),
                "query_ms": round(ms, 4),
                "recall_at_10": round(recall_at_k(ids, exact_ids), 4),
                "memory_bytes": N * D * 4 + link_bytes,
                "link_overhead_bytes": link_bytes,
                "speedup_vs_flat": round(flat_ms / ms, 1),
            })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
