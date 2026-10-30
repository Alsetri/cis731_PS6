# Competency Questions — Derived Trope Ontology v0.1.0

CIS 731 (INV-11: derived, not instructor-provided) · Abdulla Mansoor

A competency question is a question the ontology must be able to answer. They
are the acceptance test for the class hierarchy: if a question cannot be
expressed as a traversal, the ontology is missing a class or a relation, and
the fix is to the ontology rather than to the query. Each question below gives
the traversal that answers it and the downstream deliverable that needs it.

---

### CQ-1 — Slang diffusion across regions and time

> *Which lexical tropes originate in a Memphis-rap context before 2000 and
> are later attested in Southern trap after 2010?*

**Traversal**

```
LexicalTrope
  --characteristicOf--> MicroGenre(MIC-0003 Memphis)
  MicroGenre --activeDuring--> Era(ERA-0001, start < 2000)
  MicroGenre --diffusedTo--> Region, where first_attested_year > 2010
  Trope --attestedIn--> Chunk   (>= 1 required)
```

**What it exercises.** `originatesIn` being 1..1 while `diffusedTo` is 0..*
is what makes "originate" and "appear later" distinguishable. If a micro-genre
could have several origins, the question would be unaskable — this is the
question that forced that cardinality choice.

**Downstream.** This is the temporal half of the team research question from
PS 4.

---

### CQ-2 — What separates two scenes, and on what evidence

> *Which sonic and lexical tropes distinguish G-Funk from Boom Bap, and which
> retrievable chunks attest each one?*

**Traversal**

```
{SonicTrope, LexicalTrope} --characteristicOf--> MicroGenre(MIC-0004 G-Funk)
                                                 with strength
minus the same set for MicroGenre(MIC-0006 Boom Bap)
each surviving Trope --attestedIn--> Chunk --chunkOf--> Work
```

**What it exercises.** The trope subtypes. With one undifferentiated `Trope`
class the answer could not be split into "they talk about different things"
versus "they sound different" — and `characteristicOf` carrying a `strength`
is what stops a trope shared by both scenes from being forced into one.

**Downstream.** MP 7 consumes the lexical/sonic split as separate feature
families for few-shot classification.

---

### CQ-3 — Auditing a single retrieved answer

> *For a chunk the retriever just returned, which tropes does it attest, what
> work and artist is it from, and was its source document licence-admissible?*

**Traversal**

```
Chunk(chunk_id)
  <--attestedIn-- Trope
  --chunkOf--> Work --performedBy--> Artist --affiliatedWith--> Region
                                                 with confidence
Chunk --(chunk_id join)--> VdbChunkRecord.license_class, .source_hash
```

**What it exercises.** The join between the ontology and
`chunk_record.schema.json` through `chunk_id`, and the `confidence` attribute
on `affiliatedWith` — the region of an artist is an inference from fuzzy
matching, and this question is the one that would otherwise launder it into a
fact.

**Downstream.** This is the attribution-rate metric from PS 4: the share of
generated claims traceable to a retrieved chunk. It is also the licence audit
path, so an unlicensed document surfacing in an answer is detectable.

---

### CQ-4 — Where the ontology is thin

> *Which regions and eras have fewer than N chunk attestations per trope, and
> which tropes have exactly the minimum one attestation?*

**Traversal**

```
for each Trope: count(attestedIn)
group by characteristicOf --> MicroGenre --originatesIn--> Region
                              MicroGenre --activeDuring--> Era
report cells below threshold N
```

**What it exercises.** `attestedIn` having minimum cardinality 1 makes the
count meaningful — a trope with zero attestations cannot exist, so a count of
1 genuinely means "barely evidenced" rather than "not yet filled in".

**Downstream.** The coverage metric and the per-region Recall@5 slice from
PS 4, and the honest basis for the limitations statement: this question is
designed to find the ontology's own weak spots rather than to flatter it.

---

## Questions the ontology deliberately cannot answer

Stating these matters as much as the ones above, because an ontology that
claims to answer everything is not scoped.

- *Is this lyric sincere or ironic?* No class models speaker stance. Adding
  one would require annotation the project cannot validate.
- *Which artist influenced which?* There is no influence relation. Influence
  is not observable from a lyric corpus, and `diffusedTo` deliberately records
  only that a trope appears later elsewhere — co-occurrence in time, never
  causation.
- *What is the commercial performance of a work?* Out of scope; no chart or
  sales data enters the corpus.
