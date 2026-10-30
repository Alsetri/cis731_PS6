"""
CIS 731 — PS 6, Part 1: Chunking cost model and re-ranking latency model.

Everything here is a derivation from declared inputs. The inputs are declared
as inputs, not smuggled in as findings:

  d, max_seq      properties of all-MiniLM-L6-v2 (fixed, checkable)
  N_docs          team corpus target from PS 4 (10k-14k tracks)
  L               mean tokens per document -- NOT measured. The corpus has
                  not been acquired yet, and the HuggingFace tokenizer could
                  not be downloaded in this environment, so tokens-per-word
                  could not be measured either. L is estimated and a
                  sensitivity table is given so the conclusion can be checked
                  against the range rather than resting on the point estimate.
  T_enc, T_ce     literature estimates for CPU inference; flagged as such.
                  T_ann is MEASURED (analysis/index_bench.py).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

D = 384              # all-MiniLM-L6-v2 embedding dimension
MAX_SEQ = 256        # all-MiniLM-L6-v2 max sequence length (tokens)
BYTES_PER_FLOAT = 4

N_DOCS = 12_000      # midpoint of the PS 4 target of 10,000-14,000 tracks

# L: mean tokens per song. Basis: a typical rap lyric runs ~550 words; English
# WordPiece averages ~1.3 tokens/word, and regional slang and proper nouns
# fragment more than general English, so ~1.35 is the working figure.
# 550 * 1.35 = 742 -> 740.
L_MEAN = 740
L_RANGE = (400, 740, 1100)

OUT = Path("out/cost_model.json")


def fixed_window(L: int, n: int, s: int) -> dict:
    """Fixed-window chunking: window n tokens, stride s tokens."""
    if s > n:
        raise ValueError("stride may not exceed window")
    # First chunk covers [0, n); each subsequent stride advances by s.
    chunks = max(1, math.ceil((L - n) / s) + 1) if L > n else 1
    rho = 1 - s / n                      # overlap fraction
    inflation = 1 / (1 - rho)            # == n/s
    return {
        "strategy": f"fixed-window(n={n}, s={s})",
        "n": n, "s": s,
        "overlap_rho": round(rho, 4),
        "inflation_1_over_1_minus_rho": round(inflation, 4),
        "inflation_check_n_over_s": round(n / s, 4),
        "chunks_per_doc": chunks,
        "tokens_emitted_per_doc": chunks * n,
        "token_amplification": round(chunks * n / L, 3),
    }


def sentence_boundary(L: int, n: int, eta: float = 0.85) -> dict:
    """Greedy packing of whole sentences/lines into windows of at most n.

    A sentence is never split, so the last sentence that would overflow the
    window is pushed to the next chunk and the window closes early. eta is the
    mean fill ratio that results. 0.85 corresponds to a mean line length of
    roughly 0.15n -- for n=192 that is ~29 tokens, about one rap bar.
    """
    effective = eta * n
    chunks = max(1, math.ceil(L / effective))
    return {
        "strategy": f"sentence-boundary(cap n={n}, packing eta={eta})",
        "n": n, "packing_efficiency": eta,
        "effective_window_tokens": round(effective, 1),
        "overlap_rho": 0.0,
        "inflation_1_over_1_minus_rho": 1.0,
        "chunks_per_doc": chunks,
        "tokens_emitted_per_doc": L,
        "token_amplification": 1.0,
    }


def structure_aware(L: int, sections: float = 6.5) -> dict:
    """Stanza/section chunking: one chunk per verse or hook.

    A typical track is ~3 verses + ~3.5 hook/bridge sections. The chunk is a
    semantic unit, which is the point: a trope is a property of a verse, not
    of an arbitrary 192-token span.
    """
    chunks = math.ceil(sections)
    mean_section = L / sections
    return {
        "strategy": f"structure-aware(sections~{sections})",
        "sections_per_doc": sections,
        "mean_section_tokens": round(mean_section, 1),
        "exceeds_max_seq": mean_section > MAX_SEQ,
        "overlap_rho": 0.0,
        "inflation_1_over_1_minus_rho": 1.0,
        "chunks_per_doc": chunks,
        "tokens_emitted_per_doc": L,
        "token_amplification": 1.0,
    }


def storage(n_chunks: int) -> dict:
    raw = n_chunks * D * BYTES_PER_FLOAT
    return {
        "n_chunks": n_chunks,
        "formula": "N_chunks * d * 4",
        "bytes": raw,
        "mib": round(raw / 2**20, 2),
    }


def main() -> None:
    res: dict = {
        "inputs": {
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "d": D, "max_seq_len": MAX_SEQ, "bytes_per_float": BYTES_PER_FLOAT,
            "n_docs": N_DOCS, "L_mean_tokens_per_doc": L_MEAN,
            "L_status": "ESTIMATED, not measured -- see sensitivity",
        }
    }

    # ----------------------------------------------- chunk-length cap
    # Two independent ceilings; the binding one is the smaller.
    #   (a) model: tokens beyond max_seq are silently truncated, so any chunk
    #       longer than 256 loses its tail from the vector entirely.
    #   (b) granularity: a trope is evidenced by a slang term IN CONTEXT. A
    #       chunk spanning several verses dilutes that evidence across an
    #       averaged vector; a chunk shorter than a bar loses the context.
    #       A verse is ~16 bars at ~12 tokens/bar ~= 192 tokens.
    res["chunk_length_cap"] = {
        "model_ceiling_tokens": MAX_SEQ,
        "model_ceiling_reason":
            "all-MiniLM-L6-v2 truncates at 256 tokens; a longer chunk is "
            "silently half-embedded and its tail is unretrievable.",
        "granularity_ceiling_tokens": 192,
        "granularity_reason":
            "a verse is ~16 bars x ~12 tokens = ~192 tokens; one verse is the "
            "smallest span that carries a trope with its context.",
        "binding_cap_tokens": min(MAX_SEQ, 192),
        "chosen_n": 192,
        "chosen_s": 128,
        "headroom_tokens": MAX_SEQ - 192,
        "headroom_reason":
            "64 tokens of slack absorbs the prompt/special tokens and the "
            "variance in bar length without hitting truncation.",
    }

    # ----------------------------------------------- strategy comparison
    strategies = [
        fixed_window(L_MEAN, 192, 128),
        fixed_window(L_MEAN, 192, 192),   # stride == window: no overlap
        fixed_window(L_MEAN, 256, 128),   # at the model ceiling
        sentence_boundary(L_MEAN, 192),
        structure_aware(L_MEAN),
    ]
    for s in strategies:
        total = s["chunks_per_doc"] * N_DOCS
        s["corpus"] = storage(total)
    res["strategies"] = strategies

    # ----------------------------------------------- sensitivity to L
    sens = []
    for L in L_RANGE:
        row = {"L": L}
        for fn, key in (
            (lambda x: fixed_window(x, 192, 128), "fixed_192_128"),
            (lambda x: sentence_boundary(x, 192), "sentence_192"),
            (lambda x: structure_aware(x), "structure_aware"),
        ):
            s = fn(L)
            row[key] = {
                "chunks_per_doc": s["chunks_per_doc"],
                "corpus_mib": storage(s["chunks_per_doc"] * N_DOCS)["mib"],
            }
        sens.append(row)
    res["sensitivity_to_L"] = sens

    # ----------------------------------------------- re-ranking latency
    # T = T_enc + T_ann + k * T_ce, retrieve k=50 then re-rank to 10.
    bench = json.loads(Path("out/index_bench.json").read_text())
    ivf = next(e for e in bench["ivf"]
               if e["nlist"] == 256 and e["nprobe"] == 4)
    t_ann_flat = bench["flat"]["query_ms"]
    t_ann_ivf = ivf["query_ms"]

    T_ENC = 8.0    # ms, MiniLM-L6 bi-encoder, 1 short query, CPU (estimate)
    T_CE = 22.0    # ms, ms-marco-MiniLM-L-6-v2 cross-encoder, 1 pair, CPU
    K_RETRIEVE, K_FINAL = 50, 10

    def budget(t_ann: float, label: str, k: int = K_RETRIEVE) -> dict:
        total = T_ENC + t_ann + k * T_CE
        return {
            "index": label,
            "T_enc_ms": T_ENC,
            "T_ann_ms": round(t_ann, 4),
            "k": k, "T_ce_ms": T_CE,
            "k_times_T_ce_ms": round(k * T_CE, 1),
            "T_total_ms": round(total, 1),
            "cross_encoder_share": round(k * T_CE / total, 4),
            "ann_share": round(t_ann / total, 6),
        }

    res["reranking_latency"] = {
        "model": "T = T_enc + T_ann + k * T_ce",
        "k_retrieve": K_RETRIEVE, "k_final": K_FINAL,
        "T_ann_source": "MEASURED, analysis/index_bench.py",
        "T_enc_T_ce_source":
            "ESTIMATED from published CPU benchmarks; the models could not be "
            "downloaded in this environment, so these are not measured.",
        "variants": [
            budget(t_ann_flat, "IndexFlatIP (exact)"),
            budget(t_ann_ivf, "IndexIVFFlat(nlist=256, nprobe=4)"),
            budget(t_ann_flat, "IndexFlatIP, k=20", k=20),
            budget(t_ann_flat, "IndexFlatIP, no re-rank", k=0),
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
