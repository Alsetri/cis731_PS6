import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (HRFlowable, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

_FD = "/usr/share/fonts/truetype/dejavu"
for n, f in (("DJ", "DejaVuSans.ttf"), ("DJ-Bold", "DejaVuSans-Bold.ttf"),
             ("DJ-Obl", "DejaVuSans-Oblique.ttf"),
             ("DJ-BoldObl", "DejaVuSans-BoldOblique.ttf"),
             ("DJMono", "DejaVuSansMono.ttf")):
    pdfmetrics.registerFont(TTFont(n, f"{_FD}/{f}"))
pdfmetrics.registerFontFamily("DJ", normal="DJ", bold="DJ-Bold",
                              italic="DJ-Obl", boldItalic="DJ-BoldObl")

OUT = "/mnt/user-data/outputs/GenAI_PS6.pdf"
va = json.loads(Path("out/validation.json").read_text())

S = getSampleStyleSheet()
title = ParagraphStyle("T", parent=S["Title"], fontName="DJ-Bold", fontSize=13.5, leading=16, spaceAfter=1)
sub = ParagraphStyle("ST", parent=S["Normal"], fontName="DJ", fontSize=8.8, leading=11,
                     alignment=1, textColor=colors.HexColor("#444444"), spaceAfter=8)
h = ParagraphStyle("H", parent=S["Heading2"], fontName="DJ-Bold", fontSize=10.5, leading=12.5,
                   spaceBefore=10, spaceAfter=4)
h3 = ParagraphStyle("H3", parent=S["Heading3"], fontName="DJ-BoldObl", fontSize=8.9,
                    leading=11, spaceBefore=7, spaceAfter=2)
b = ParagraphStyle("B", parent=S["Normal"], fontName="DJ", fontSize=8.5, leading=11.3,
                   alignment=TA_JUSTIFY, spaceAfter=5)
small = ParagraphStyle("S", parent=S["Normal"], fontName="DJ", fontSize=7.4, leading=9.3,
                       textColor=colors.HexColor("#555555"))

E = []
E.append(Paragraph("Generative AI Audit Log — PS 6", title))
E.append(Paragraph("CIS 731 — Fall 2026 — Semantic Search, Chunking & VDB Schema", sub))

hdr = [["Student", "Abdulla Mansoor (CIS 731) — abdulla03@ksu.edu"],
       ["Assignment", "PS 6: Semantic Search, Chunking, & VDB Schema"],
       ["Schema authority", "DERIVED (CIS 731, INV-11) — the instructor ontology is not reused"],
       ["Tool audited", "Claude (Anthropic) — conversational assistant"],
       ["Period covered", "27 October 2026"],
       ["Deliverables", "PS6_Abdulla_Mansoor.pdf; schema/ under Git tag ps6-submission"]]
t = Table(hdr, colWidths=[1.2 * inch, 5.3 * inch])
t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "DJ"),
                       ("FONTNAME", (0, 0), (0, -1), "DJ-Bold"),
                       ("FONTSIZE", (0, 0), (-1, -1), 8.3),
                       ("VALIGN", (0, 0), (-1, -1), "TOP"),
                       ("TOPPADDING", (0, 0), (-1, -1), 3),
                       ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                       ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#DDDDDD"))]))
E.append(t)
E.append(Spacer(1, 4))
E.append(HRFlowable(width="100%", thickness=0.7, color=colors.HexColor("#999999")))

E.append(Paragraph("1. Scope", h))
E.append(Paragraph(
    "Section 2 of the PS 6 specification directs students to use the Generative AI Kit across five stages, "
    "each paired with a verification duty: draft the cost model <i>then verify the arithmetic independently</i>; "
    "tabulate the index trade-offs <i>then check every claim against FAISS documentation</i>; generate the "
    "JSON Schema <i>then validate it with a validator recorded in the lockfile</i>; draft the contracts; and "
    "run an adversarial review for provenance holes. AI use here is instructed, not merely tolerated. This "
    "log records what the assistant did, what I verified, and — at greater length — what verification "
    "actually caught.", b))

E.append(Paragraph("2. Assistance by specification stage", h))
rows = [["Stage", "Assistant contribution", "My verification"],
        ["1 — Cost model",
         "Drafted the fixed-window / sentence-boundary / structure-aware derivations and the storage formula.",
         "Checked that 1/(1−ρ) and n/s agree, which is the arithmetic identity the spec implies; set L as a "
         "declared estimate with a sensitivity table rather than letting a point estimate stand unqualified."],
        ["2 — Index matrix",
         "Wrote the benchmark harness over IndexFlatIP, IndexIVFFlat and IndexHNSWFlat.",
         "Required the table be MEASURED rather than quoted. This is what exposed finding 3.1, which a "
         "documentation-only table would have missed entirely."],
        ["3 — Schema synthesis",
         "Generated the Draft 2020-12 schema including the if/then/else conditionals.",
         f"Validated with jsonschema {va['jsonschema_version']}, pinned in requirements.lock. Added 13 "
         "deliberately malformed records so the schema is tested for what it REJECTS, not only what it accepts."],
        ["4 — Contract drafting",
         "Drafted admit_document and vdb_upsert with deal decorators.",
         "Found finding 3.2 — the contracts were not running at all. Added negative tests for every "
         "precondition and both set-level invariants."],
        ["5 — Adversarial review",
         "Asked for provenance holes: orphan vectors, unlicensed documents, duplicate chunk_id.",
         "Findings 3.3–3.5 below. The licence hole is a real compliance gap in the team's plan, not a code bug."]]
t2 = Table(rows, colWidths=[0.95 * inch, 2.5 * inch, 3.05 * inch])
t2.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "DJ"),
                        ("FONTNAME", (0, 0), (-1, 0), "DJ-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 7.3),
                        ("LEADING", (0, 0), (-1, -1), 9.0),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFEFEF")),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#BBBBBB")),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4)]))
E.append(t2)

E.append(Paragraph("3. Findings — defects caught by running the work, not reading it", h))

E.append(Paragraph("3.1  The index benchmark was measuring nothing (methodology error, mine)", h3))
E.append(Paragraph(
    "The first benchmark run reported 1–30% recall@10 for <i>both</i> IVF and HNSW at every parameter "
    "setting. The reflex reading was that HNSW handles inner product badly. That was wrong. The synthetic "
    "corpus added per-coordinate Gaussian noise of 0.35 to unit-norm cluster centres; in 384 dimensions that "
    "perturbation has expected norm 0.35·√384 ≈ 6.9, so after normalization the points were uniform on the "
    "sphere with no cluster structure at all. Near-zero ANN recall is the <i>correct</i> result for uniform "
    "high-dimensional data and a meaningless one for an embedding space. Scaling the noise by 1/√d fixed it: "
    "IVF went to 0.9999 at nlist=256/nprobe=4 and HNSW to 0.9802 at M=32/ef=64. Had I accepted the first "
    "table, the report would have recommended exact search for a confidently stated and entirely false "
    "reason.", b))

E.append(Paragraph("3.2  The deal contracts were not being evaluated", h3))
E.append(Paragraph(
    "admit_document's preconditions were written as single-parameter lambdas on a two-parameter function. "
    "A deal validator is invoked with the guarded function's full argument list, so each one raised "
    "<font face='DJMono' size='7.5'>TypeError: &lt;lambda&gt;() takes 1 positional argument but 2 were "
    "given</font> instead of evaluating. The function still raised, so a careless harness that only asserted "
    "'bad input raises' would have passed — the contract would have appeared to work while checking nothing. "
    "The negative tests assert the specific exception type (deal.PreContractError), which is what made the "
    "difference visible.", b))

E.append(Paragraph("3.3  Duplicate chunk_id: IndexIDMap2.add_with_ids does not replace", h3))
E.append(Paragraph(
    "The adversarial prompt asked where a duplicate chunk_id could arise. Measured answer: calling "
    "add_with_ids with an id already present does not overwrite it — ntotal went from 20,000 to 20,001 and "
    "the index held two vectors under one key, with a search free to return the stale one. A re-embedding "
    "run would have silently doubled part of the index. Two fixes, both now specified: chunk_id is derived "
    "deterministically as SHA-256(doc_id|chunk_index|chunker_version) so re-chunking produces the same key "
    "rather than a fresh one; and update is remove_ids followed by add_with_ids, which also sweeps up any "
    "pre-existing duplicate because remove_ids deletes every copy.", b))

E.append(Paragraph("3.4  Orphan vectors: deletion order and the sidecar map", h3))
E.append(Paragraph(
    "Two orphan paths were identified. First, deleting the record before the vector leaves a window in which "
    "a vector is retrievable with no record behind it; deletion is now ordered vector-first, so a crash "
    "mid-delete yields a missing embedding — detectable by EmbeddingCompleteness and repairable by "
    "re-embedding — instead of an unattributable vector that no scan would notice. Second, removing an id "
    "from FAISS does not remove it from the int64→chunk_id sidecar; the demo asserts both sides return to "
    "bijection after a delete. NoOrphanEmbeddings and EmbeddingCompleteness are checked as a pair precisely "
    "because each alone permits one of these states.", b))

E.append(Paragraph("3.5  Unlicensed documents: an INV-9 gap in the team's own plan", h3))
E.append(Paragraph(
    "The review asked which documents could enter the corpus without a licence check. The answer was not a "
    "code bug: INV-9 restricts corpus content to public-domain or instructor-provided material, while the "
    "team's acquisition plan of record from PS 4 is the authenticated Genius REST API — Tier 2, not public "
    "domain. I wrote admit_document to the invariant rather than to the plan: licensed_api and "
    "fair_use_excerpt are refused, and the harness asserts both refusals. Those values remain in the schema "
    "enum on purpose, so non-conforming material can be named and rejected rather than quietly relabelled as "
    "something admissible. The consequence is stated plainly in the report: the corpus the pipeline is "
    "currently specified against would be rejected by its own ingest gate.", b))

E.append(Paragraph("3.6  The PDF silently corrupted its own mathematics", h3))
E.append(Paragraph(
    "The first typeset build used ReportLab's built-in Helvetica, which has no glyphs for the notation the "
    "report depends on. U+27E8/27E9 (angle brackets) and U+2308/2309 (ceiling) both fell back to a double-bar "
    "glyph, so the inner-product proof rendered as though it were about norms — ‖u,v‖ where ⟨u,v⟩ was "
    "written — and the chunking formula appeared to take a norm of a quotient. No error, no warning, and the "
    "corruption landed in exactly the two places where notation carries the argument. Caught by rendering "
    "the PDF to an image and reading it rather than trusting that the build succeeded. Fixed by registering "
    "DejaVu Sans.", b))

E.append(Paragraph("4. What AI was not used for", h))
E.append(Paragraph(
    "No measured value was generated, estimated or interpolated by AI: every number in Part 1 is emitted by "
    f"code in this repository and stored under out/, and ./run_all.sh regenerates all of it. The "
    f"{va['total_cases']} validation cases are executed, not described. Where a quantity could not be "
    "measured in this environment — mean tokens per document, and the encoder and cross-encoder latencies, "
    "because the model files could not be downloaded — it is labelled an estimate at the point of use in the "
    "report rather than presented as a result. No citation was invented. The ontology's class hierarchy, "
    "relation cardinalities and competency questions follow my PS 4 Task 5 design; the assistant formalised "
    "and stress-tested them.", b))

E.append(Paragraph("5. Attestation", h))
E.append(Paragraph(
    "I can defend each decision in the report without assistance: why the granularity ceiling binds before "
    "the model ceiling, why cosine and inner product coincide only on the unit sphere and what that implies "
    "for the unit-norm precondition, why Recall@k is not gradable on own data before INV-17, why attestedIn "
    "carries minimum cardinality 1, and why exact search is the right choice at this corpus scale despite "
    "the ANN analysis. Where verification changed a conclusion, §3 says so rather than presenting the "
    "corrected version as though it had been the first one.", b))
E.append(Spacer(1, 12))
E.append(Paragraph("Signed: ______________________________    Date: ______________", b))
E.append(Paragraph("Abdulla Mansoor — CIS 731", small))

doc = SimpleDocTemplate(OUT, pagesize=letter, leftMargin=0.85 * inch, rightMargin=0.85 * inch,
                        topMargin=0.65 * inch, bottomMargin=0.6 * inch,
                        title="GenAI Audit Log PS6 - Abdulla Mansoor", author="Abdulla Mansoor")
doc.build(E)
from pypdf import PdfReader
print("built", OUT, "pages:", len(PdfReader(OUT).pages))
