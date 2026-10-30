import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (HRFlowable, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# FONTS: reportlab's built-in Helvetica/Courier use a Latin-1-ish encoding and
# have no glyphs for the mathematical notation this report depends on. With
# Helvetica, U+27E8/27E9 (angle brackets) and U+2308/2309 (ceiling) both fell
# back to a double-bar glyph, so the inner-product proof rendered as if it were
# about norms and the chunking formula appeared to take a norm of a quotient.
# Silent, and wrong in exactly the places precision matters. DejaVu covers the
# Greek, the operators, the brackets and the super/subscripts.
_FD = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("DJ", f"{_FD}/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DJ-Bold", f"{_FD}/DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DJ-Obl", f"{_FD}/DejaVuSans-Oblique.ttf"))
pdfmetrics.registerFont(TTFont("DJ-BoldObl", f"{_FD}/DejaVuSans-BoldOblique.ttf"))
pdfmetrics.registerFont(TTFont("DJMono", f"{_FD}/DejaVuSansMono.ttf"))
pdfmetrics.registerFontFamily("DJ", normal="DJ", bold="DJ-Bold",
                              italic="DJ-Obl", boldItalic="DJ-BoldObl")

OUT = "/mnt/user-data/outputs/PS6_Abdulla_Mansoor.pdf"
cm = json.loads(Path("out/cost_model.json").read_text())
ib = json.loads(Path("out/index_bench.json").read_text())
fm = json.loads(Path("out/faiss_idmap.json").read_text())
va = json.loads(Path("out/validation.json").read_text())

S = getSampleStyleSheet()
title = ParagraphStyle("T", parent=S["Title"], fontName="DJ-Bold", fontSize=13, leading=16, spaceAfter=1)
sub = ParagraphStyle("ST", parent=S["Normal"], fontName="DJ", fontSize=8.6, leading=11.5, alignment=1,
                     textColor=colors.HexColor("#444444"), spaceAfter=7)
h = ParagraphStyle("H", parent=S["Heading2"], fontName="DJ-Bold", fontSize=10.5, leading=13,
                   spaceBefore=9, spaceAfter=4, textColor=colors.HexColor("#111111"))
h3 = ParagraphStyle("H3", parent=S["Heading3"], fontName="DJ-BoldObl", fontSize=8.9, leading=11,
                    spaceBefore=6, spaceAfter=2, textColor=colors.HexColor("#333333"))
b = ParagraphStyle("B", parent=S["Normal"], fontName="DJ", fontSize=8.3, leading=11.4,
                   alignment=TA_JUSTIFY, spaceAfter=4.5)
mono = ParagraphStyle("M", parent=S["Normal"], fontName="DJMono", fontSize=7.0,
                      leading=9.6, leftIndent=8, spaceAfter=4,
                      textColor=colors.HexColor("#222222"))
small = ParagraphStyle("S", parent=S["Normal"], fontName="DJ", fontSize=7.2, leading=9.4,
                       textColor=colors.HexColor("#555555"), spaceAfter=4)

E = []


def tbl(data, widths, fs=7.5, lead=9.2, align_right=None):
    t = Table(data, colWidths=widths)
    st = [("FONTNAME", (0, 0), (-1, -1), "DJ"),
          ("FONTNAME", (0, 0), (-1, 0), "DJ-Bold"),
          ("FONTSIZE", (0, 0), (-1, -1), fs), ("LEADING", (0, 0), (-1, -1), lead),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ECECEC")),
          ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BBBBBB")),
          ("TOPPADDING", (0, 0), (-1, -1), 2.2),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
          ("LEFTPADDING", (0, 0), (-1, -1), 3.5)]
    if align_right:
        for c in align_right:
            st.append(("ALIGN", (c, 1), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(st))
    return t


E.append(Paragraph("PS 6: Semantic Search, Chunking, & VDB Schema", title))
E.append(Paragraph("Abdulla Mansoor · CIS <b>731</b> · abdulla03@ksu.edu · Track 2 (VDB) · "
                   "Schema authority: <b>DERIVED</b> (INV-11)", sub))
E.append(HRFlowable(width="100%", thickness=0.7, color=colors.HexColor("#888888")))
E.append(Paragraph(
    "<b>Artifacts.</b> Git tag <font face='DJMono' size='8'>ps6-submission</font>; "
    "<font face='DJMono' size='8'>schema/</font> holds the JSON Schema, the derived ontology, the "
    "<font face='DJMono' size='8'>deal</font> contracts, the FAISS id-mapping layer, worked examples and "
    "<font face='DJMono' size='8'>requirements.lock</font>. "
    f"<font face='DJMono' size='8'>./run_all.sh</font> reproduces every number here and exits non-zero on any "
    f"failure; it currently reports <b>{va['passed']}/{va['total_cases']} validation cases passing</b>. "
    "Index figures are measured on this machine (faiss-cpu "
    f"{ib['config']['faiss_version']}, 2 threads); inputs that are estimates are labelled as estimates where "
    "they appear.", b))

# ========================================================== 1
E.append(Paragraph("Chunking Cost Model", h))
inp = cm["inputs"]
E.append(Paragraph(
    f"Model <font face='DJMono' size='8'>{inp['embedding_model']}</font>: "
    f"d = {inp['d']}, max sequence length = {inp['max_seq_len']} tokens, float32. "
    f"Corpus N_docs = {inp['n_docs']:,} tracks (midpoint of the PS 4 target of 10k–14k). "
    f"Mean tokens per document L = {inp['L_mean_tokens_per_doc']}. "
    "<b>L is an estimate, not a measurement</b>: the corpus has not been acquired and the model's tokenizer "
    "could not be downloaded in this environment, so tokens-per-word could not be counted. The basis is "
    "~550 words per track × ~1.35 WordPiece tokens/word (slang and proper nouns fragment more than general "
    "English). A sensitivity table follows so the conclusion can be checked against a range rather than "
    "resting on the point estimate.", b))

E.append(Paragraph("Derivations", h3))
E.append(Paragraph(
    "Fixed window of n tokens with stride s: the first window covers [0, n) and each later window advances "
    "by s, so chunks per document is c = ⌈(L − n)/s⌉ + 1 for L &gt; n, else 1. The overlap fraction is "
    "ρ = 1 − s/n, and overlap inflation is 1/(1 − ρ) = 1/(s/n) = <b>n/s</b> — the two expressions the spec "
    "names are the same quantity, which is the check that the algebra is right. Sentence-boundary chunking "
    "never splits a line, so a line that would overflow pushes the window closed early; with mean fill ratio "
    "η the effective window is ηn and c = ⌈L/(ηn)⌉. η = 0.85 corresponds to a mean line of ~0.15n ≈ 29 tokens "
    "at n = 192, about one bar. Structure-aware chunking emits one chunk per verse or hook, ~6.5 sections per "
    "track, independent of L. Index storage is N_chunks × d × 4 bytes in every case.", b))

cap = cm["chunk_length_cap"]
E.append(Paragraph("Chunk-length cap", h3))
E.append(Paragraph(
    f"Two independent ceilings apply and the smaller binds. <b>Model:</b> {cap['model_ceiling_tokens']} tokens — "
    "beyond this the encoder truncates silently, so a longer chunk is half-embedded and its tail is "
    f"unretrievable while still occupying an index slot. <b>Granularity:</b> {cap['granularity_ceiling_tokens']} "
    "tokens — a trope is evidenced by a term <i>in context</i>; a chunk spanning several verses dilutes that "
    "evidence across an averaged vector, and a chunk shorter than a bar loses the context that makes the term "
    "interpretable. A verse is ~16 bars × ~12 tokens ≈ 192. The granularity ceiling binds, so "
    f"<b>n = {cap['chosen_n']}, s = {cap['chosen_s']}</b> (ρ = 1/3, inflation 1.5), leaving "
    f"{cap['headroom_tokens']} tokens of headroom for special tokens and bar-length variance before truncation.", b))

rows = [["Strategy", "chunks /doc", "ρ", "1/(1−ρ)", "N_chunks", "Storage MiB", "Token amp."]]
for s in cm["strategies"]:
    rows.append([s["strategy"].replace("sentence-boundary(cap n=192, packing eta=0.85)", "sentence-boundary(n=192, \u03b7=0.85)").replace("structure-aware(sections~6.5)", "structure-aware(~6.5 sections)"), str(s["chunks_per_doc"]), f"{s['overlap_rho']:.3f}",
                 f"{s['inflation_1_over_1_minus_rho']:.2f}", f"{s['corpus']['n_chunks']:,}",
                 f"{s['corpus']['mib']:.1f}", f"{s.get('token_amplification', 1.0):.2f}×"])
E.append(tbl(rows, [2.42*inch, .66*inch, .46*inch, .62*inch, .78*inch, .86*inch, .66*inch],
             align_right=[1, 2, 3, 4, 5, 6]))
E.append(Spacer(1, 3))

rows = [["L (tokens/doc)", "fixed(192,128)", "sentence(192)", "structure-aware"]]
for r in cm["sensitivity_to_L"]:
    rows.append([str(r["L"]),
                 f"{r['fixed_192_128']['chunks_per_doc']} ch · {r['fixed_192_128']['corpus_mib']:.0f} MiB",
                 f"{r['sentence_192']['chunks_per_doc']} ch · {r['sentence_192']['corpus_mib']:.0f} MiB",
                 f"{r['structure_aware']['chunks_per_doc']} ch · {r['structure_aware']['corpus_mib']:.0f} MiB"])
E.append(tbl(rows, [1.25*inch, 1.45*inch, 1.45*inch, 1.45*inch], align_right=[1, 2, 3]))
E.append(Paragraph(
    "The whole index is 70–160 MiB across the entire plausible range of L. <b>Storage is not a constraint at "
    "this corpus size</b>, so the chunking choice should be made on retrieval quality, not bytes — which "
    "inverts the usual framing of a cost model. Structure-aware chunking costs 17% more than fixed-window at "
    "L = 740 and is the only strategy whose chunk boundaries coincide with the unit a trope actually inhabits; "
    "that is worth 18 MiB. Its weakness is that it depends on section markers being present in the scraped "
    "text, which for lyrics is unreliable — the fallback is fixed(192,128).", b))

# ========================================================== 2
E.append(Paragraph("Index and Similarity Analysis", h))
E.append(Paragraph("Cosine equals inner product on unit vectors", h3))
E.append(Paragraph(
    "By definition cos(u,v) = ⟨u,v⟩ / (‖u‖‖v‖). If ‖u‖ = ‖v‖ = 1 the denominator is 1 and "
    "cos(u,v) = ⟨u,v⟩. ∎ Consequently a maximum-inner-product search over unit vectors <i>is</i> a maximum-"
    "cosine search, and no separate normalization step is needed at query time provided both sides were "
    f"normalized at write time. Measured on {ib['config']['n_queries']} vector pairs, "
    f"max |⟨u,v⟩ − cos(u,v)| = {ib['cosine_equals_ip']['max_abs_difference']:.2e} (float32 round-off).", b))
E.append(Paragraph(
    "A second consequence is used below: ‖u − v‖² = ‖u‖² − 2⟨u,v⟩ + ‖v‖² = 2 − 2⟨u,v⟩ for unit vectors, so "
    "L2 distance is a strictly decreasing function of inner product and <b>the two induce identical rankings</b>. "
    "This matters because HNSW's graph construction assumes a metric and inner product is not one. I expected "
    "METRIC_L2 to outperform METRIC_INNER_PRODUCT for that reason; measured recall was identical to four "
    "decimal places at every efSearch (0.7666 / 0.8826 / 0.9442 / 0.9701 at M = 16 under both). The prediction "
    "was wrong and the equivalence above is why.", b))
E.append(Paragraph(
    f"<b>IndexFlatIP is exact</b> because it computes ⟨q,v⟩ against every stored vector with no quantization "
    f"and no pruning, then takes the top-k of the true score list: cost Θ(N·d) per query, no recall parameter "
    f"to tune, and nothing to train. Measured {ib['flat']['query_ms']:.3f} ms/query at N = "
    f"{ib['config']['n_vectors']:,}, d = {ib['config']['d']}.", b))

E.append(Paragraph("IVF versus HNSW", h3))
E.append(Paragraph(
    "<b>IVF</b> partitions the space into nlist Voronoi cells by k-means, then scans only the nprobe cells "
    "nearest the query: query cost Θ((nlist + nprobe·N/nlist)·d), minimised near nlist ≈ √(N·nprobe); build "
    "cost is k-means, Θ(iters·N·nlist·d); memory is N·d·4 + nlist·d·4, i.e. the vectors plus a negligible "
    "centroid table. Recall degrades when a true neighbour lies in an unprobed cell — a cell-boundary effect, "
    "so it worsens as nlist rises at fixed nprobe. <b>HNSW</b> builds a navigable small-world graph and "
    "greedy-descends it, expected Θ(M·log N·d) per query with a beam of efSearch; build is "
    "Θ(N·efConstruction·M·d·log N); memory is N·d·4 plus roughly N·3M·4 bytes of links, which is additive "
    "overhead IVF does not pay. Recall degrades as efSearch narrows the beam and the descent is pruned early.", b))

rows = [["Index", "recall@10", "ms/query", "speedup", "build (s)", "memory"]]
rows.append([ib["flat"]["index"] + " (exact)", "1.0000", f"{ib['flat']['query_ms']:.4f}", "1.0×",
             f"{ib['flat']['build_sec']:.2f}", f"{ib['flat']['memory_bytes']/1e6:.0f} MB"])
for e in ib["ivf"]:
    if (e["nlist"], e["nprobe"]) in ((256, 1), (256, 4), (1024, 1), (1024, 8)):
        rows.append([f"IVFFlat nlist={e['nlist']} nprobe={e['nprobe']}", f"{e['recall_at_10']:.4f}",
                     f"{e['query_ms']:.4f}", f"{e['speedup_vs_flat']}×",
                     f"{e['train_sec']:.2f}", f"{e['memory_bytes']/1e6:.0f} MB"])
for e in ib["hnsw"]:
    if (e["M"], e["metric"], e["efSearch"]) in ((16, "L2", 64), (32, "L2", 64), (32, "L2", 128)):
        rows.append([f"HNSW M={e['M']} ef={e['efSearch']}", f"{e['recall_at_10']:.4f}",
                     f"{e['query_ms']:.4f}", f"{e['speedup_vs_flat']}×",
                     f"{e['build_sec']:.2f}", f"{e['memory_bytes']/1e6:.0f} MB"])
E.append(tbl(rows, [1.68*inch, .68*inch, .68*inch, .62*inch, .66*inch, .72*inch],
             align_right=[1, 2, 3, 4, 5]))
E.append(Paragraph(
    f"Measured on {ib['config']['n_vectors']:,} synthetic unit vectors drawn from "
    f"{ib['config']['n_clusters_synthetic']} Gaussian clusters, d = {ib['config']['d']}, "
    f"{ib['config']['n_queries']:,} queries, k = 10, ground truth from IndexFlatIP. <b>The data is synthetic "
    "because the corpus is not yet embedded.</b> Latency and memory are index properties and transfer; the "
    "recall column characterises this distribution and is indicative only. Cluster spread was set to 0.35 of "
    "the unit sphere — an earlier run that scaled noise per-coordinate rather than by 1/√d produced effectively "
    "uniform points and measured 1–30% recall for <i>both</i> families, which is the right answer for uniform "
    "high-dimensional data and a badly misleading one for an embedding space.", small))
E.append(Paragraph(
    "IVF at nlist = 256, nprobe = 4 reaches 0.9999 recall at 12× the speed of exact search, trains in 2.8 s and "
    "adds 0.4 MB over the raw vectors. HNSW at M = 32 needs 230 MB and 9.3 s to build and still returns 0.9802 "
    "at ef = 64. At this scale IVF dominates on every axis except the extreme low-latency corner. "
    "<b>The operative recommendation, though, is to use neither.</b> Exact search costs 1.55 ms/query on 120k "
    "vectors; the entire ANN apparatus buys ~1.4 ms, and §2 below shows that is 0.1% of the query budget. "
    "ANN becomes worth its tuning surface and its recall risk somewhere above ~10⁶ vectors — roughly an order "
    "of magnitude more than this project will hold.", b))

E.append(Paragraph("Re-ranking latency", h3))
rr = cm["reranking_latency"]
E.append(Paragraph(
    f"T = T_enc + T_ann + k·T_ce, retrieving k = {rr['k_retrieve']} and re-ranking to {rr['k_final']}. "
    f"T_ann is measured. T_enc = 8 ms (bi-encoder, one short query, CPU) and T_ce = 22 ms (cross-encoder, one "
    "pair, CPU) are <b>literature estimates</b> — the models could not be downloaded here, so they are not "
    "measured and are flagged as such.", b))
rows = [["Configuration", "T_enc", "T_ann", "k·T_ce", "T total", "cross-enc. share"]]
for v in rr["variants"]:
    rows.append([v["index"], f"{v['T_enc_ms']:.1f}", f"{v['T_ann_ms']:.3f}", f"{v['k_times_T_ce_ms']:.0f}",
                 f"{v['T_total_ms']:.1f} ms", f"{v['cross_encoder_share']:.1%}"])
E.append(tbl(rows, [1.82*inch, .52*inch, .55*inch, .58*inch, .72*inch, .85*inch],
             align_right=[1, 2, 3, 4, 5]))
E.append(Paragraph(
    "The cross-encoder is 99% of the budget and the index is 0.01–0.14% of it. Swapping exact search for IVF "
    "changes end-to-end latency by 0.1%; dropping k from 50 to 20 more than halves it. <b>Any effort spent "
    "tuning nlist/nprobe before tuning k is misallocated.</b> One caveat on the model itself: k·T_ce assumes "
    "pairs are scored serially, which is pessimistic — batching 50 pairs through a cross-encoder amortises "
    "the fixed per-call cost and in practice lands well below 50×T_ce. The linear form is the spec's and is "
    "the right <i>upper</i> bound; the conclusion that the re-ranker dominates survives either way.", b))

E.append(PageBreak())

# ========================================================== 3
E.append(Paragraph("Retrieval Evaluation Protocol", h))
E.append(Paragraph(
    "Let q be a query, R_q the set of chunks genuinely relevant to it, and r_1…r_k the ranked results. "
    "<b>P@k</b> = |{r_1…r_k} ∩ R_q| / k, the share of the shown results that are relevant. "
    "<b>Recall@k</b> = |{r_1…r_k} ∩ R_q| / |R_q|, the share of all relevant chunks that surfaced. "
    "<b>MRR</b> over a query set Q is (1/|Q|)·Σ 1/rank_q, where rank_q is the position of the first relevant "
    "result (0 if none in the top k). P@k and MRR need judgements only on <i>returned</i> items; Recall@k "
    "needs |R_q|, a property of the whole corpus.", b))

E.append(Paragraph("What counts as relevant", h3))
E.append(Paragraph(
    "Few-shot trope retrieval needs a graded judgement, because 'from the right scene' and 'actually attests "
    "the trope' are different things and collapsing them hides the system's real failure mode — returning "
    "plausibly regional text that evidences nothing.", b))
rows = [["Grade", "Criterion", "Example"],
        ["2 — attests", "The chunk contains the trope's surface form, or for a non-lexical trope explicitly "
         "enacts it, such that a reader could cite this chunk alone as evidence.",
         "Query 'hyphy slang'; chunk uses the term in a Bay-Area context."],
        ["1 — contextual", "Same scene, micro-genre or era, and supports interpretation, but does not itself "
         "attest the trope.", "Same artist and period, no occurrence of the term."],
        ["0 — not relevant", "Neither. Includes topically similar text from the wrong scene.",
         "Any region, term absent and context unrelated."]]
E.append(tbl(rows, [.78*inch, 2.65*inch, 2.0*inch], fs=7.4, lead=9.0))
E.append(Paragraph(
    "P@k and Recall@k binarise at grade ≥ 1; a strict variant at grade = 2 is reported alongside, and the gap "
    "between them is the quantity of interest — it is exactly the rate at which the retriever returns "
    "atmosphere instead of evidence. MRR uses grade = 2, since the first result a generator reads should be "
    "one that can be cited. <b>Protocol:</b> judgements are pooled over the top-10 of all three systems "
    "(TF-IDF baseline, bi-encoder, bi-encoder + cross-encoder), presented blind to system identity and in "
    "randomised order; 20% of the pool is double-annotated and Cohen's κ is reported with the results rather "
    "than after adjudication; ties are adjudicated by a third pass against the written criteria, never by "
    "discussion. This protocol is the input to the MP 9 gold-standard codebook.", b))

E.append(Paragraph("Which metrics are gradable, and when", h3))
rows = [["Metric", "Before an own gold set (INV-12)", "After INV-17"],
        ["P@k", "Computable on own queries — needs judgements only on returned items. Comparable across "
         "systems only if the pool is shared.", "Unchanged; now comparable to the instructor baseline."],
        ["MRR", "Computable on own queries, same caveat.", "Unchanged."],
        ["Recall@k", "<b>Not gradable on own data.</b> |R_q| is unknown: unjudged chunks are not known to be "
         "irrelevant, so any Recall figure is an upper bound on an unknown denominator. Gradable only against "
         "instructor sets, which supply R_q.",
         "Gradable as <i>recall-within-pool</i>. The pool is not the corpus, so the bias is bounded but not "
         "removed, and it must be reported under that name."]]
E.append(tbl(rows, [.68*inch, 2.75*inch, 2.0*inch], fs=7.4, lead=9.0))
E.append(Paragraph(
    "The per-region Recall@5 slice promised in PS 4 therefore cannot be reported as an absolute number until "
    "the gold set exists, and even then it is recall-within-pool. Until INV-17 is satisfied the honest report "
    "is P@5 and MRR with κ, plus the attribution rate, which needs no corpus-wide denominator at all and is "
    "the metric least damaged by this limitation.", b))

# ========================================================== 4
E.append(Paragraph("Record Schema and ID Mapping", h))
E.append(Paragraph(
    "<font face='DJMono' size='8'>schema/chunk_record.schema.json</font> is JSON Schema Draft 2020-12, "
    f"validated with jsonschema {va['jsonschema_version']} as pinned in "
    "<font face='DJMono' size='8'>requirements.lock</font> — 'the schema validates' is a claim about a "
    "specific validator, not a universal one. It extends the MP 5 CorpusChunk: MP 5 fixed record_id, "
    "source_id, the event-time bounds, text, ingest_ts and license_class; this record carries those forward "
    "and adds the embedding, the ontology linkage and the provenance digest.", b))
rows = [["Field", "Type / constraint", "Why it is shaped this way"],
        ["chunk_id", "^[0-9a-f]{64}$", "SHA-256 of doc_id|chunk_index|chunker_version. Deterministic so that "
         "re-embedding REPLACES; a random uuid would make every re-run orphan its predecessor."],
        ["doc_id", "^(genius|rym|spotify|librivox|pd|instructor):…$",
         "Source prefix carries provenance in the key, so an unlisted source is detectable without a join "
         "(MP 5 INV-10)."],
        ["source_hash", "SHA-256 hex", "Digest of the raw document as acquired; detects upstream edits that "
         "would silently make a chunk stale."],
        ["license_class", "enum of 5", "Non-admissible values are representable precisely so they can be "
         "rejected rather than relabelled. See §5."],
        ["corpus_type", "enum of 4", "Selects release_year vs broadcast_ts via if/then/else."],
        ["release_year / broadcast_ts", "conditional, mutually exclusive",
         "Draft 2020-12 if/then/else: ASR requires broadcast_ts and forbids release_year; every other corpus "
         "the reverse. Neither may appear with the other."],
        ["trope_ids[]", "^(LEX|THM|SON|NAR)-[0-9]{4}$, unique",
         "Keys into the derived ontology. May be empty: most chunks attest nothing, and a non-empty "
         "requirement would push annotators to invent labels."],
        ["embedding_model / _dim / vector", "enum; const; length-bound",
         "Dim and vector length are constrained <i>against</i> the model by if/then, so a 384-vector cannot be "
         "filed as mpnet. Mixed-model vectors in one index corrupt every score silently."],
        ["token_count", "1…256", "The ceiling is the model's max sequence length; a larger value means the "
         "tail was truncated and the vector does not represent the text."],
        ["provenance_verified", "boolean", "Postcondition of admit_document; vdb_upsert refuses anything "
         "where it is not true."]]
E.append(tbl(rows, [1.25*inch, 1.5*inch, 2.68*inch], fs=7.3, lead=8.9))
E.append(Paragraph(
    f"The harness runs {va['total_cases']} cases, including 13 deliberately malformed records — ASR with a "
    "release_year, a vector of the wrong length, a pastebin: doc_id, duplicate trope ids, an unknown extra "
    f"property — each asserted to be <i>rejected</i>. All {va['passed']} pass. A schema only ever shown "
    "accepting good input demonstrates nothing.", b))
E.append(Paragraph(
    "Three properties JSON Schema structurally cannot express are listed in the schema's own "
    "<font face='DJMono' size='8'>x-contract-enforced</font> block and enforced in code instead: unit norm "
    "(no aggregate over an array), hash integrity (shape of a digest is checkable, correctness is not), and "
    "chunk_id derivation. EmbeddingCompleteness and NoOrphanEmbeddings are set-level and cannot be stated "
    "about a single record at all.", b))

E.append(Paragraph("FAISS int64 ↔ chunk_id mapping", h3))
E.append(Paragraph(
    "FAISS addresses vectors by non-negative int64; chunk_id is a 256-bit digest. The bridge is "
    "faiss_id = int(chunk_id[:16], 16) &amp; 0x7FFF_FFFF_FFFF_FFFF — the leading 64 bits masked to 63, because "
    f"FAISS reserves negatives for 'not found'. Birthday collision probability at N = {inp['n_docs']*6:,} is "
    "≈ N²/2⁶⁴ ≈ 8×10⁻¹⁰: small, not zero, and a silent collision returns the wrong document with full "
    f"confidence — so build_idmap <i>checks</i> rather than trusting the estimate "
    f"({fm['distinct_faiss_ids']:,} distinct ids, {fm['collisions']} collisions over {fm['n_vectors']:,} "
    "vectors). A sidecar int64 → chunk_id map carries the reverse direction.", b))
E.append(Paragraph(
    f"<b>Update and delete semantics, measured on IndexIDMap2.</b> add_with_ids does <i>not</i> replace an "
    f"existing id: re-adding one id took ntotal from {fm['n_vectors']:,} to "
    f"{fm['naive_readd']['ntotal']:,}, leaving two vectors under one key and a search free to return the "
    "stale one. The correct update is remove_ids then add_with_ids; remove_ids deletes <i>every</i> copy, so "
    f"it also repairs the duplicate (ntotal back to {fm['correct_update']['ntotal_after_readd']:,}, "
    "reconstruct returns the new vector). Delete must also drop the sidecar entry — forgetting that second "
    f"step is exactly how an orphan is born. After delete: ntotal {fm['orphan_check']['faiss_ntotal']:,}, "
    f"sidecar {fm['orphan_check']['sidecar_size']:,}, in bijection.", b))

E.append(PageBreak())

# ========================================================== 5
E.append(Paragraph("Contracts and Ontology", h))
E.append(Paragraph("The two invariants, in plain language", h3))
E.append(Paragraph(
    "<b>EmbeddingCompleteness:</b> every chunk admitted to the corpus has exactly one vector in the index — "
    "no admitted chunk is unretrievable. <b>NoOrphanEmbeddings:</b> every vector in the index belongs to "
    "exactly one live, admitted chunk — nothing is retrievable that cannot be traced to a document whose "
    "licence was checked. They are duals and both are needed: completeness alone permits a store full of "
    "unattributable vectors, NoOrphan alone permits documents admitted and then never embedded. Together they "
    "assert a bijection between the record set and the vector set.", b))

E.append(Paragraph("admit_document", h3))
E.append(Paragraph(
    "<b>Precondition</b> — license_class ∈ {public_domain, cc_by, instructor_provided}. "
    "<b>Postcondition</b> — the returned record has provenance_verified = True and a source_hash equal to the "
    "SHA-256 of the bytes actually admitted. The hash is <i>recomputed</i> inside the contract rather than "
    "trusted from the caller, because a caller-supplied digest certifies nothing.", b))
E.append(Paragraph(
    "@deal.pre(lambda doc, _raw: doc[\"license_class\"] in INV9_ADMISSIBLE_LICENCES)<br/>"
    "@deal.post(lambda result: result[\"provenance_verified\"] is True)<br/>"
    "@deal.ensure(lambda doc, raw_bytes, result: result[\"source_hash\"] == sha256(raw_bytes).hexdigest())", mono))

E.append(Paragraph("vdb_upsert", h3))
E.append(Paragraph(
    "<b>Precondition</b> — the record cleared admit_document; its chunk_id equals the derived digest; its "
    "vector length, embedding_dim and embedding_model agree; and ‖vector‖₂ = 1 ± 10⁻⁵. "
    "<b>Postcondition</b> — the index holds exactly one vector for this chunk_id. In plain language: a chunk "
    "may be embedded as often as we like and the index will never hold two vectors for it, nor zero.", b))
E.append(Paragraph(
    "@deal.pre(lambda index, record: record[\"provenance_verified\"] is True)<br/>"
    "@deal.pre(lambda index, record: record[\"chunk_id\"] == derive_chunk_id(…))<br/>"
    "@deal.pre(lambda index, record: abs(l2_norm(record[\"vector\"]) − 1.0) &lt;= 1e-5)<br/>"
    "@deal.ensure(lambda index, record, result: sum(1 for c in result if c == record[\"chunk_id\"]) == 1)", mono))
E.append(Paragraph(
    "The unit-norm precondition is not decoration: §2 proves cosine equals inner product <i>only</i> on the "
    "unit sphere, so an unnormalized vector corrupts every score it participates in while producing no error. "
    "Deletion is ordered vector-first, record-second; the reverse order leaves a window in which a vector is "
    "retrievable with no record — an orphan. Dying between the two steps in this order yields a missing "
    "embedding, which is detectable and repairable by re-embedding, rather than an unattributable vector, "
    "which is invisible without a full scan.", b))
E.append(Paragraph(
    f"The harness exercises each contract from both sides: records that never cleared admission, forged "
    f"chunk_ids, unnormalized vectors and both non-admissible licences are each asserted to be <i>refused</i>; "
    f"a seeded completeness violation and a seeded orphan are each asserted to be <i>detected</i>. "
    f"{va['passed']}/{va['total_cases']} cases pass (deal {va['deal_version']}).", b))

E.append(Paragraph("Derived ontology (CIS 731, INV-11)", h3))
E.append(Paragraph(
    "<b>Classes.</b> Trope (abstract) → LexicalTrope | ThematicTrope | SonicTrope | NarrativeTrope; "
    "Scene (abstract) → Region | MicroGenre; plus Era, Artist, Work, Chunk. "
    "<b>Relations and cardinalities.</b> originatesIn: MicroGenre→Region 1..1 · diffusedTo: MicroGenre→Region "
    "0..* {first_attested_year, attesting_chunk_id} · attestedIn: Trope→Chunk <b>1..*</b> · characteristicOf: "
    "Trope→MicroGenre 0..* {strength} · activeDuring: MicroGenre→Era 1..* · performedBy: Work→Artist 1..* · "
    "affiliatedWith: Artist→Region 0..* {confidence, method} · chunkOf: Chunk→Work 1..1.", b))
E.append(Paragraph(
    "<b>Granularity.</b> Four trope subtypes rather than one, because a single undifferentiated class cannot "
    "answer whether regional identity is carried lexically or sonically, and MP 7 needs that split as separate "
    "feature families; finer granularity — a class per word sense — would demand disambiguation unvalidatable "
    "at 12k documents. Attestation is at <i>chunk</i> level, not track level, because retrieval returns chunks: "
    "attesting at track level would break the chain between a retrieved passage and the claim it supports, and "
    "that chain is precisely what the attribution-rate metric measures. MicroGenre sits between Region and "
    "Trope because attaching tropes straight to Region conflates origin with spread and makes diffusion "
    "inexpressible. Era is <i>derived</i> from release_year rather than asserted, so an era boundary cannot "
    "contradict the record it describes.", b))
E.append(Paragraph(
    "<b>attestedIn has minimum cardinality 1</b> — a trope with zero attestations is inadmissible, because it "
    "would be an assertion about the corpus the corpus does not support. This is the ontology's provenance "
    "teeth and what makes the coverage metric meaningful: a count of 1 means 'barely evidenced', not 'not yet "
    "filled in'.", b))
E.append(Paragraph(
    "<b>Competency questions</b> (full traversals in schema/competency_questions.md): "
    "<b>CQ-1</b> which lexical tropes originate in Memphis rap pre-2000 and are attested in Southern trap "
    "post-2010 — the question that forces originatesIn to be 1..1 while diffusedTo is 0..*; "
    "<b>CQ-2</b> which sonic and lexical tropes separate G-Funk from Boom Bap and which chunks attest each — "
    "the question that justifies the subtypes and the strength attribute; "
    "<b>CQ-3</b> for a chunk just retrieved, which tropes it attests, from which work and artist, and whether "
    "its source licence was admissible — the join to the record schema and the attribution-rate path; "
    "<b>CQ-4</b> which regions and eras fall below N attestations per trope — the coverage and fairness slice. "
    "Three questions are deliberately <i>out</i> of scope: speaker stance, artist influence (diffusedTo records "
    "co-occurrence in time, never causation), and commercial performance.", b))

E.append(Paragraph("A compliance gap I am flagging rather than hiding", h3))
E.append(Paragraph(
    "INV-9 limits corpus content to public-domain or instructor-provided material. The team's acquisition plan "
    "of record, from PS 4, is the authenticated Genius REST API — Tier 2, and <b>not</b> public domain. The "
    "contract above is written to the invariant rather than to the plan: admit_document refuses "
    "licensed_api and fair_use_excerpt, and the test harness asserts both refusals. Those two values exist in "
    "the enum precisely so non-conforming material can be named and rejected instead of being relabelled as "
    "something it is not. The practical consequence is that the corpus the pipeline is currently specified "
    "against would be rejected by its own ingest gate, and the team must either secure instructor-provided "
    "lyrics, substitute a public-domain corpus, or obtain an explicit exemption. I would rather surface that "
    "now than discover it at HW 12.", b))

# ========================================================== 6
E.append(Paragraph("GenAI Audit", h))
E.append(Paragraph(
    "Yes — the Generative AI Kit was used, as Section 2 of the specification directs. <b>GenAI.pdf is "
    "included</b> and logs the five prescribed stages together with the adversarial-review findings required "
    "by Stage 5. In summary: the Kit drafted the cost-model derivations, the index trade-off matrix, the JSON "
    "Schema and the contract scaffolding, and drafted this report. I verified the arithmetic independently, "
    "and every claim about FAISS in §2 and §4 is a measurement from code in this repository rather than a "
    "quotation from documentation. Four defects were found by running the work rather than reading it — a "
    "noise-scaling error that made both index families look broken, deal validator signatures that raised "
    "TypeError instead of failing contracts, the add_with_ids duplicate-id trap, and the INV-9 licence gap "
    "above — and all four are documented in GenAI.pdf with their fixes.", b))

doc = SimpleDocTemplate(OUT, pagesize=letter, leftMargin=0.72*inch, rightMargin=0.72*inch,
                        topMargin=0.6*inch, bottomMargin=0.55*inch,
                        title="PS6 Semantic Search, Chunking & VDB Schema - Abdulla Mansoor",
                        author="Abdulla Mansoor")
doc.build(E)
from pypdf import PdfReader
print("built", OUT, "pages:", len(PdfReader(OUT).pages))
