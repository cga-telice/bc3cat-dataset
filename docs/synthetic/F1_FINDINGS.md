# F1 Pilot — Findings and Recommendations

**Date:** 2026-07-05
**Concept under pilot:** `OEB070$` (OBRA CIVIL — canalización de polietileno)
**Model:** `llama3.1:8b` (Ollama, temperature 0, seed 7)
**Corpus:** 48 placeholder-clean variants after Sprint 29 process fixes; 43 distinct modifications in [`F1_PILOT_REVIEW_DIGEST.md`](F1_PILOT_REVIEW_DIGEST.md); ~128 leaves per variant
**Scope of this note:** analysis of the F1-review gate against the objectives in
[`RESEARCH_PROPOSAL.md`](RESEARCH_PROPOSAL.md). No code, prompt, or config changes.
Recommendations are recorded for a future sprint to act on.

---

## 1. What F1 was supposed to validate

The proposal ([`RESEARCH_PROPOSAL.md`](RESEARCH_PROPOSAL.md) §1.1, §3) sets an
explicit contract for every synthetic item. The premise is *controlled linguistic
variability that preserves parametric meaning*, with full traceability back to the
generation rules. Stage D of the pipeline (§3) is the manual-validation gate; it
checks four things per item:

1. Grammatical Spanish.
2. Preservation of parametric meaning.
3. `new_param` axes that are semantically distinguishable from originals.
4. Metadata that accurately describes what changed.

F1 was designed as the empirical test of these criteria on a single concept
(`OEB070$`) — a *quality* gate on top of the *process* pilot that Sprints 28–29
completed. It is also the input for Open Question #2 (model choice), since the
transport / recording seam is now stable.

## 2. What works

The end-to-end machinery is solid and matches the proposal's Stages B–C:

- **Generation → materialization → coverage.** `f1_pilot.py` produces 62 recorded
  transcripts, 48 materialized variant files under `data/synthetic/intermediate/OEB070$/`,
  a variant catalog under `data/synthetic/variants/`, and a 100%-coverage review
  queue with 4560 items.
- **Traceability metadata** is present per item (`item_key`, `original_key`,
  `variante_id`, `modification_types`, `modification_count`, `modifications`) —
  exactly the schema the proposal §2.3 asks for.
- **Deterministic replay** works: content-addressed cache under
  `data/synthetic/llm_cache/OEB070$/` + `RecordingClient` / `ReplayClient` +
  temperature 0. Any subsequent measurement can be reproduced offline for free.
- **Process fixes from Sprint 29 held.** JSON extraction now recovers prose- and
  fence-wrapped payloads; L3 placeholder guards catch reorder/omission corruptions
  (3 broken variants were correctly rejected); schema-key alignment (`"synonyms"`
  / `"numerals"`) cleared 24 spurious `schema_fail`s; the verbatim-original
  instruction cleared most `unmatched_original` skips.
- **A minority of L2 variants are usable.** Digest entries #14, #17
  (`Nocturno→Noche`), #19 (`Volumen escaso→Volumen limitado`), #34
  (`Cualquier franja horaria excepcional→Horarios fuera del horario normal`),
  #40 (`Cualquier condición de ejecución→Ejecución bajo cualquier condición`)
  are meaning-preserving and register-appropriate. Roughly 6–8 of the 43 clear
  the Stage-D bar unconditionally.

## 3. The centerpiece: resumen/texto is a per-axis surface mapping, not an L1/L2 split

A first-pass reading of the digest suggested the desynchronisations followed a
clean rule — L1 mods change texto only, L2 mods change resumen only. That rule
is wrong. The correct picture is a **per-axis surface mapping** determined by
how the `OEB070` templates reference each parameter, together with a **redundant
dual encoding** of three of the four axes.

### 3.1 The two templates and the four axes

From `data/intermediate/OBRA CIVIL/OBRA CIVIL.json`:

```
RESUMEN:  Suministro y ejecución de canalización de $A tubo(s) de polietileno
          110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))

TEXTO:    Suministro y ejecución de canalización de $A tubo(s) de polietileno
          110 mm 5 At. con topo bajo vías.
          Trabajo: $B  Banda de mantenimiento: $C  Condiciones de ejecución: $D
```

The two templates draw each axis from a *different* variable:

| Axis | Label | Resumen source | Texto source | Same variable? |
|------|-------|----------------|--------------|-----------------|
| A | Nº TUBOS | `$A` | `$A` | **Yes** |
| B | TRABAJO | `$L(%B)` — text variable | `$B` — raw parameter value | No |
| C | BANDA DE MANTENIMIENTO | `$M(%C)` — text variable | `$C` — raw parameter value | No |
| D | CONDICIONES DE EJECUCIÓN | `$N(%D)` — text variable | `$D` — raw parameter value | No |

The text variables `$L`, `$M`, `$N` re-encode the same labels the parameters
already carry. Their fragments are literal strings that *coincide* with the
parameter values in the original catalog but are not derived from them at render
time — they are independent copies.

### 3.2 Consequences observed in the pilot

Because the two surfaces read the same axis from independent sources, a
single-layer modification touches only one side and leaves the other unchanged:

- **Axis A (shared `$A`) — modifications propagate symmetrically.**
  Digest #4 (`code_expansion[A]`), #5 (`num_to_text[A]`), #10
  (`unit_conversion[A]`), #12 (`unit_expansion[A]`) change *both* resumen and
  texto. Grammatically the result is broken (see §4), but the propagation is
  symmetric.

- **Axes B / C / D — modifications are asymmetric.**
  - L1 on the parameter value changes `$B/$C/$D` in texto only.
    Empirical proof: `single_L1_synonym_label_9468265cff` modifies axis B
    (`Diurno → "Horario de luz solar"`). The materialized leaf `OEB070aaaa`
    renders `Trabajo: Horario de luz solar` in texto and `(Diurno/…)` in
    resumen. Texto changed; resumen did not.
  - L2 on the text variable changes `$L/$M/$N` in resumen only.
    Digest examples: #30 (`expansion[L %B=a]` expands only the resumen),
    #36 (`paraphrase[N %D=a] "Volumen relevante → Volumen de excavación"`
    appears in resumen; texto still reads `Volumen relevante`),
    #39 (`paraphrase[L %B=a] "Diurno → Día"` appears in resumen; texto
    still reads `Diurno`).

The asymmetry is not a mutator bug. `layer_l1._replace_value` writes to
`parameters[axis].values[i].value` and does not touch `text_variables`;
`layer_l2._replace_fragment` writes to `text_variables[var]` and does not touch
parameter values. Given the template structure, that is exactly what one
should expect.

### 3.3 The dual encoding predates any modification

The redundancy is visible in the original catalog itself. Rendered leaves show
`i >==5 horas` in resumen (from `$M`, with the source-catalog typo) but
`i >= 5 horas` in texto (from `$C`, without the typo). The two surfaces
already disagree on the surface form of the same axis value before the
synthetic pipeline runs. This is a property of `OEB070` — not something the
synthetic harness introduced.

### 3.4 Implication for the benchmark premise

The proposal's premise is that a synthetic variant is a meaning-preserving
rewrite of the *pair* (resumen, texto) — that is, the query and the document
both carry the transformation. On axes B / C / D of `OEB070`, a single-layer
modification produces a variant where only one side of the pair has changed.
That still yields a valid document referring to the same catalog item, but it
is not what the proposal describes, and its interpretation for retrieval is
different: it is closer to *query drift against an unchanged document* (for L2
mods) or *document drift against an unchanged query* (for L1 mods on B/C/D).

Whether this is a design decision to embrace or a defect to fix is a research
question that belongs to a later sprint (see §6). What the pilot establishes
is that the current single-layer mutation strategy does not produce paired
query+doc variability on `OEB070`. A concept audit is required before
generalising.

**Caveat.** The dual-encoding pattern is confirmed only for `OEB070`. Other
OEB concepts may render both surfaces from the same variable, in which case
the asymmetry disappears. This must be audited across concept groups before
committing to any surface-mapping policy.

## 4. Plumbing defects surfaced by the review

Three code-level defects survived the Sprint 29 fixes and were exposed by
manual review of the digest. Locations are recorded here for a future sprint;
no code is changed by this note.

### 4.1 No per-axis applicability gate in target enumeration

`slot_extractor.enumerate_targets()` ([slot_extractor.py:62-90](../../src/synthetic/slot_extractor.py)) yields
every axis under the concept for L1 modification types:

```python
if modification_type in _L1_TYPES:
    yield from sorted(item.get("parameters", {}).keys())
```

Nothing filters axes for applicability. Consequences observed in the digest:

- `unit_expansion` / `abbrev_expansion` / `code_expansion` / `unit_conversion`
  applied to axis A (`Nº TUBOS`, a numeric count) produce **grammatically
  broken duplications** because the template already supplies "tubo(s) de
  polietileno…" after `$A`. Digest #4 renders `de Un tubo tubo(s) de
  polietileno`; #10 renders `de 1 tubo(s) tubo(s) de polietileno`; #12
  renders `de 1 tubo(s) de polietileno 110 milímetros … tubo(s) de polietileno
  110 mm …`.
- The same L1 expansion/conversion types applied to time-band axes with no
  abbreviation to expand produce **no-op identities** (digest #2, #13, #22,
  parts of #43). A benchmark item identical to the original does not measure
  robustness.

Recommendation for a future sprint: gate `enumerate_targets()` on axis
properties (numeric vs. categorical; has abbreviations / codes / units) so
that inapplicable L1 types are not enumerated. This saves LLM calls, avoids
the broken duplications, and eliminates the no-op identities.

### 4.2 L2 content is not guarded against re-embedding template placeholders

`variant_proposer._validate_payload()` ([variant_proposer.py:167-196](../../src/synthetic/variant_proposer.py))
guards placeholders only for `REORDER` and `OMISSION`. `EXPANSION`,
`PARAPHRASE`, `COMPRESSION` are validated for structure only via
`_validate_original_new_preserves`. Consequences in the digest:

- Digest #23 (`expansion[N %D=a]`) rewrites the fragment to
  `Volumen de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo
  bajo vías ($L(%B)/$M(%C)/$N(%D))`. The rendered resumen leaks
  `($L(%B)/$M(%C)/$N(%D))(%D)))` verbatim.
- Digest #31 and #42 exhibit the same leakage.
- Digest #24, #25, #f67cf6a1ec carry latent leaks: the placeholder tokens are
  in the `new` fragment but the representative leaf is not the one where they
  render — leaves that *do* match the modified condition will emit garbage.

The helpers to catch this already exist in the same file:
`_placeholders()` and `_PLACEHOLDER_RE` ([variant_proposer.py:277-282](../../src/synthetic/variant_proposer.py)).

Recommendation for a future sprint: add
`_require_no_placeholders_in_new_fragment(payload["new"])` and call it for the
three L2 types, symmetrical to `_require_placeholders_preserved` for reorder.

### 4.3 The review digest is hand/notebook-built and its representative leaf is misleading

`docs/synthetic/F1_PILOT_REVIEW_DIGEST.md` was produced ad hoc; no committed
generator exists in `src/synthetic/`. Its representative-leaf strategy —
always the minimal leaf (`OEB070aaaa` or the closest equivalent) — is the
main defect of the gate itself: in a large fraction of entries the modified
parameter value is *not the one selected in the representative leaf*, so the
digest reader cannot see what changed. Examples:

- #6 modifies `%C ∈ {b, c, d}`; the shown leaf is `%C = a` (`i >= 5 horas`).
- #14 modifies `%D = c`; the shown leaf is `%D = a`.
- #16 modifies `%B = c`; the shown leaf is `%B = b`.
- Many #single_L2_expansion_* entries are similarly invisible.

`review.sample_review_queue()` ([review.py:169-246](../../src/synthetic/review.py))
does deterministic sampling but is not what produced the digest. A future
sprint should build a small digest generator whose selection rule is "pick a
leaf whose parameter assignment binds to the modified condition" — that is,
for a mod on `%B=b`, pick a leaf with `%B=b`, not `%B=a`. Without this the
manual review gate is not tractable.

## 5. Content-quality findings (the F1-review verdict on `llama3.1:8b`)

The mechanical scorecard counted 48 placeholder-clean variants and marked L2
as "solid" (28 of 37 generated in the pre-fix run). Reading the actual
rendered text shows this count is misleading. The findings below use digest
entry numbers.

### 5.1 Meaning loss on L2 (violates Stage-D criterion ii)

- **`Excepcional` dropped systematically.**
  - #1 `paraphrase[L %B=c] "Diurno Excepcional" → "Día normal"` — the
    qualifier `Excepcional` is discarded and `normal` is added.
  - #16 `compression[L %B=c] "Diurno Excepcional" → "Diurno"`.
  - #20 `compression[L %B=d] "Nocturno Excepcional" → "Noche"`.
  - #32 `paraphrase[L %B=d] "Nocturno Excepcional" → "Noche"`.
  - #33 same as #1.
  These are not compressions of surface form; they collapse a distinct
  parameter value onto another parameter value.

- **Semantic drift on volumes.**
  - #36 `paraphrase[N %D=a] "Volumen relevante" → "Volumen de excavación"`.
    The qualifier changes from magnitude ("relevant volume") to type
    ("excavation volume"). Not equivalent.
  - #37 `paraphrase[N %D=b] "Volumen escaso" → "Volumen insuficiente"`. Subtle
    but present ("scarce" vs. "insufficient" carries an adequacy connotation).

- **Register breaks unacceptable for a construction catalog.**
  - #38 `paraphrase[L %B=b] "Nocturno" → "Bajo la luz de la luna"`.

- **Introduced errors from a preexisting typo.**
  - #35 `paraphrase[L %B=e] "Cualquier frana horaria" → "Cualquier frana en la
    zona horaria"`. The source typo (`frana` for `franja`) is retained and the
    modifier changes from time slot to time zone.

### 5.2 Ungrammatical L1 on axis A (violates Stage-D criterion i)

- #4 `code_expansion[A] "1" → "Un tubo"` → renders `de Un tubo tubo(s) de
  polietileno`.
- #5 `num_to_text[A] "1" → "uno"` → renders `de uno tubo(s) de polietileno`
  (should apocopate to *un*).
- #10 `unit_conversion[A]` → `de 1 tubo(s) tubo(s) de polietileno`.
- #12 `unit_expansion[A]` → `de 1 tubo(s) de polietileno 110 milímetros … 5
  At. con topo bajo vías tubo(s) de polietileno 110 mm 5 At. con topo bajo
  vías`.

These are all consequences of §4.1 (no per-axis targeting gate). Fixing the
gate removes them.

### 5.3 Placeholder leakage in L2 expansions

Documented in §4.2. #23, #31, #42 emit `($L(%B)/$M(%C)/$N(%D))` literally in
the rendered surface.

### 5.4 No-op identity transforms

Digest #2, #13, #22, and identity portions of #43 emit modifications where the
`new` value equals the `original`. Same root cause as §4.1: L1
expansion/conversion types being enumerated on axes with nothing to expand.

### 5.5 Roll-up

Of 43 distinct modifications shown in the digest, roughly **6 to 8 clear the
Stage-D bar unconditionally**. Another handful are usable subject to the
surface-mapping caveat in §3.4. The remainder fail one or more of grammar,
meaning preservation, or render fidelity. The dominant failure sources are
llama3.1:8b's semantic drift on L2 rewrites and the two missing plumbing
gates (§4.1, §4.2).

**Verdict on `llama3.1:8b`:** inadequate for L1 keyed-list tasks and too
error-prone in L2 semantics for this domain. It was the right choice for
de-risking the process (Sprints 28–29 succeeded at that) but should not be
the model driving F3.

## 6. Recommendations for the next sprint

None of this is executed by this note. The recommendations are ranked by
impact on the benchmark's validity.

### 6.1 Model — try `phi4:latest`, fall back to Claude if it is insufficient

**Decision (2026-07-05, César).** Sequence is fixed: try `phi4:latest` first;
if quality is insufficient, fall back to Claude (Anthropic, native
Messages API).

- **Try `phi4:latest`** (14B, already installed via Ollama). No code changes
  required — set `BC3CAT_LLM_MODEL=phi4:latest` in the environment. Re-run F1
  on `OEB070$` and compare offline via the `spike.py` scorecard against the
  recorded llama3.1:8b transcripts.
- **Frontier fallback: Claude.** The current `HttpLLMClient` in
  [`src/synthetic/llm_client.py`](../../src/synthetic/llm_client.py) targets
  OpenAI-compatible endpoints. Anthropic's native Messages API is not
  OpenAI-compatible, so a small adapter (a second `LLMClient` implementation
  targeting `/v1/messages`) will be needed. Keep temperature 0, keep the
  `RecordingClient` wrap for reproducibility. This adapter is the only new
  transport code the surface-mapping + plumbing sprint should introduce.
- OpenAI / OpenRouter are explicitly out of scope as fallbacks.

### 6.2 Surface-mapping policy — paired L1+L2 modifications, applied catalog-wide

**Decision (2026-07-05, César).** The mutator will be extended so that any
modification targeting an axis with a dual representation applies to both
the parameter value and its twin text variable, so that both `resumen` and
`texto` carry the change consistently. This is the closest option to the
proposal's original "meaning-preserving rewrite of the item" framing.

**Assumption (2026-07-05, César).** We assume the dual-encoding pattern is
general across BC3 concepts, not specific to `OEB070`. The fix is therefore
designed once, catalog-wide, without gating on a separate concept-audit
sprint. If a later concept turns out to have a single shared variable per
axis (no twin), the paired-modification logic degenerates to a single-layer
mutation on that axis with no extra work.

Concretely, the mutator sprint that follows will need to:

- Detect, per concept and per axis, whether the axis has a twin representation
  (parameter value on one side, text variable on the other) or a single
  shared variable on both sides.
- For axes with twins, coordinate an L1 rewrite of the parameter value with
  a matching L2 rewrite of the corresponding text-variable fragment,
  emitting a single logical modification with both edits recorded in the
  `modifications` metadata list.
- For axes without twins (e.g. axis A in `OEB070`), keep the current
  single-layer behaviour.

Metadata implication: the per-item `modifications` field will now sometimes
carry a pair of edits (one L1 + one L2) tied to the same conceptual
modification. The `modification_types` roll-up should stay flat and use the
primary modification type; the paired edit is an implementation detail of
the mutator, not a new taxonomy entry.

### 6.2.1 Refinement (2026-07-05, Sprint 35 review) — bare-referenced text-vars are single-surface by design

The Sprint 31 pairing implementation discovers twins by scanning the
`resumen` / `texto` templates for **indexed** references of the form
`$VAR(%AXIS)` (via `l2_repr.derive_var_axis_map`). This catches the
`OEB070` shape cleanly: `$L(%B)` in `resumen` pairs with parameter `$B` in
`texto`, and `paired_l1_into_text_var` / `paired_l2_into_param` propagate
edits between them.

The Sprint 35 sanity check on `OEB020` surfaced a second shape the
discovery does **not** catch: two *bare-referenced* text-variables whose
formulas both dispatch on the same axis. On `OEB020`, `$K` (bare in
`resumen`) and `$I` (bare in `texto`) both dispatch on axis B (TIPO DE
TERRENO). Their fragments are independent authored wordings of the same
axis (`$K %B=a → "normal"`, `$I %B=a → "en cualquier clase de terreno,
excepto roca"`). Modifying `$I` only touches `texto`; modifying `$K` only
touches `resumen`.

**Decision (2026-07-05, César, Sprint 35 review):** accept this as
single-surface (document-side or query-side) variability by design, not a
gap to fix. Rationale:

- **The two independent wordings are a catalog-authoring choice**, not a
  redundancy the tool should paper over. Coupling them retroactively risks
  overwriting distinctions the author intentionally introduced (e.g. `$K`
  wants the short label, `$I` wants the long descriptive phrase).
- **Retrieval-benchmark validity is preserved.** A variant that modifies
  only `texto`'s bare `$I` produces a legitimate query-stable /
  document-varying pair — the retrieval task's gold pairing (same
  concept, same parametric assignment) is intact. If anything, this is
  closer to real-world deployment where query wording is stable and
  catalog wording is the variable surface.
- **The paired-mutation logic still fires on all *indexed* twins** in
  every concept (Sprint 35 confirmed this on `OEB020`'s `$G(%C)`,
  `$H(%D)`, `$J(%F)`), so meaning-preserving-on-both-surfaces coverage
  remains where the catalog structure supports it.

Operational consequence: some fraction of L2 modifications will produce
single-surface variants. This is expected and does not disqualify them
from `Full BC3CAT-Syn` (§4.3 of the proposal); it only means those
variants belong to the "query-side variability" evaluation slice
described in §6 Future Work of the proposal. No metadata change is
needed — the `modifications` list already records which variable and
which condition was touched, and downstream analysis can slice on
`layer=text_variable` + `paired` presence to distinguish paired
(both-surface) from single-layer (one-surface) variants.

Rejected alternatives (recorded for the archive):

- **Extend twin discovery to bare-referenced same-axis pairs.** Would
  make the mutator link `$K` and `$I` via their shared axis and modify
  them together. Rejected — would flatten the catalog author's
  distinction between short-label and long-descriptive representations.
- **Opt-in per concept.** Rejected as unnecessary machinery given the
  accept-as-is choice above.

### 6.3 Plumbing fixes to land before F3 (order matters)

1. **Per-axis targeting gate** in `slot_extractor.enumerate_targets()`.
   Removes §5.2 (ungrammatical axis-A duplications) and §5.4 (no-op
   identities). Highest impact per line of code.
2. **L2-content placeholder guard** in `variant_proposer._validate_payload()`.
   Removes §5.3 (rendered `($L(%B)/…)` leaks). Trivial addition using the
   existing `_placeholders()` helper.
3. **Digest generator** (a new script) whose representative-leaf rule is
   "pick a leaf whose parameter assignment binds to the modified condition".
   Without this the manual review gate is not tractable; the current digest
   hides most modifications.

### 6.4 Re-run and re-review

After the fixes above and the model swap, rerun F1 on `OEB070$` from the
recorded transcript store where possible, regenerate the digest with the new
selector, and record the model verdict. That closes F1 for real and unblocks
F3 (full-scale generation) with a defensible model + surface-mapping choice.

## 7. Decisions locked in (2026-07-05)

The four open questions after the F1-review have been resolved.

1. **Surface-mapping policy — paired L1+L2 modifications.** The mutator will
   be extended to co-modify the parameter value and its twin text variable
   whenever an axis has a dual representation, so `resumen` and `texto`
   change together. See §6.2 for the operational shape.
2. **Scope of the surface-mapping fix — catalog-wide, no separate audit.**
   We assume the twin-copy pattern is general across BC3 concepts and
   implement the fix once across the mutator. No dedicated F1.5 audit
   sprint; concept-specific edge cases will be handled if and when they
   surface during the next generation pass.
3. **Model sequence — `phi4:latest` first, Claude (native Messages API) as
   fallback.** OpenAI / OpenRouter are out of scope. Building a small
   Anthropic adapter is accepted work if `phi4` proves insufficient.
4. **Record — this note plus a `RESEARCH_LOG.md` entry.** The findings note
   is the reference document; a short sprint entry in the research log
   points to it and records the decisions above with rationale.

These four decisions define the shape of the next sprint (whose task ID
will be assigned in the research log entry): paired-mutation refactor +
per-axis targeting gate + L2 placeholder guard + digest generator +
`phi4:latest` re-run of F1, with Claude adapter held in reserve.
