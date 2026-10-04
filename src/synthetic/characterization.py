"""Verificador de la caracterización paramétrica (BT, opción A, T2).

Una consulta *q* con gold *g* del concepto *C* preserva su caracterización
si, para cada eje *a* de R(C) (los ejes que la plantilla TEXTO de *C*
renderiza), *q* determina *g[a]* dentro del conjunto cerrado V(C, a), no
determina ningún otro valor y no añade información paramétrica que *g* no
tiene.

Puertas, en orden; la primera que falla rechaza con ``gate``/``axis``/
``reason`` (nunca en silencio):

* **G0** elegibilidad — el gold existe y la consulta no está en P7/P8;
* **G1** invariantes — multiconjunto normalizado de bandas, cantidades,
  códigos y siglas (:mod:`bt_masking`), en el espacio de valores
  originales: antes de comparar se deshacen en el texto las sustituciones
  L1/L2 visibles del sidecar (:func:`undo_records`), así las conversiones
  aprobadas no cuentan como cambio y una reversión de la BT tampoco (G5 la
  cuenta). Sin ``source_text`` se compara con el TEXTO gold más los
  cambios de la plantilla TEXTO parafraseada; con ``source_text``, con el
  origen;
* **G2** extracción cerrada — cada extractor elige, por eje, una opción
  numerada o 0 (``no_determinable``) sin ver el gold. Se acepta si los dos
  dan un valor admitido en todo eje de R(C). Valores admitidos: los de las
  hojas del grupo D-031 del gold (más 0 si difieren entre sí);
* **G3** no confundibilidad — la consulta no es el TEXTO de ninguna hoja
  fuera del grupo del gold (sin mayúsculas ni espacios), y Guard #1
  (:func:`cross_concept_guard.classify`) no da colisión introducida;
* **G4** sin añadidos — en los ejes fuera de R(C), ``no_determinable`` o un
  valor del grupo D-031 del gold (iteración 2: un valor que el gold comparte
  con sus hermanas de TEXTO idéntico no es información nueva; en OEG010 el
  eje F repite lo que ya dice el eje C). La señal
  ``meaning_drift_flag.analyze`` se guarda para ordenar la auditoría;
* **G5** supervivencia — solo informa: tipos cuyos registros visibles
  sobreviven o se revierten;
* **G6** no trivialidad — distinta del origen, del TEXTO gold y de los
  textos ya entregados (``forbidden``).

R(C) se calcula desde la fuente: un eje está en R(C) si su placeholder es
token de la plantilla TEXTO o si lo indexa una variable de texto que es
token (argumento ``%X`` de la llamada o condición ``%X`` de la fórmula).
La visibilidad de los registros la decide
:meth:`dose_ladder.TextoSurface.shows_record`.
"""

from __future__ import annotations

import importlib.util
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Optional, Protocol, Sequence

from . import cross_concept_guard
from .bt_masking import mask_surface
from .dose_ladder import TextoSurface

NO_DET = 0
PROTOCOL_VERSION = "3"  # v3: opción con cita literal comprobada; v2: letras, null, G4 por grupo

_PROMPT_PATH = Path(__file__).parent / "prompts_bt" / "characterization_extract.txt"
_CALL_RE = re.compile(r"\$([A-Za-z]\w*)(?:\(([^)]*)\))?")
_AXIS_REF_RE = re.compile(r"%([A-Z])")
_TOKEN_RE = re.compile(r"\$([A-Za-z]\w*)")


def _ws(text: object) -> str:
    return " ".join(str(text).split())


def norm_text(text: str) -> str:
    """Igualdad de textos para G3/G6: sin mayúsculas ni espacios extra."""
    return " ".join(text.casefold().split())


# ---------------------------------------------------------------------------
# Conceptos y hojas
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AxisInfo:
    letter: str
    label: str
    values: tuple[str, ...]
    rendered: bool


@dataclass(frozen=True)
class ConceptInfo:
    key: str
    name: str
    texto_template: str
    axes: tuple[AxisInfo, ...]

    @property
    def rendered(self) -> tuple[str, ...]:
        return tuple(a.letter for a in self.axes if a.rendered)

    @property
    def not_rendered(self) -> tuple[str, ...]:
        return tuple(a.letter for a in self.axes if not a.rendered)

    def axis(self, letter: str) -> AxisInfo:
        for a in self.axes:
            if a.letter == letter:
                return a
        raise KeyError(letter)


@dataclass(frozen=True)
class Leaf:
    key: str
    concept: str
    options: Mapping[str, str]  # eje -> letra de opción
    text: str


def _flat(value: object) -> str:
    if isinstance(value, str):
        return value
    return " ".join(map(str, value or ()))


def rendered_axes(concept: Mapping) -> frozenset:
    """R(C) desde la plantilla TEXTO de la fuente."""
    texto = _flat(concept.get("texto") or "")
    axes = set(concept.get("parameters") or {})
    tv = concept.get("text_variables") or {}
    out: set[str] = set()
    for name, args in _CALL_RE.findall(texto):
        if name in axes:
            out.add(name)
        if args:
            out |= set(_AXIS_REF_RE.findall(args))
        if name in tv:
            out |= set(_AXIS_REF_RE.findall(_flat(tv[name])))
    return frozenset(out & axes)


def _concept_info(key: str, concept: Mapping) -> ConceptInfo:
    r = rendered_axes(concept)
    axes = []
    for letter, block in (concept.get("parameters") or {}).items():
        axes.append(AxisInfo(
            letter=letter,
            label=_ws(block["label"]),
            values=tuple(_ws(v["value"]) for v in block["values"]),
            rendered=letter in r,
        ))
    return ConceptInfo(
        key=key, name=_ws(concept.get("concept", "")),
        texto_template=_flat(concept.get("texto") or "").lstrip("\\"),
        axes=tuple(axes),
    )


# ---------------------------------------------------------------------------
# G1 — invariantes
# ---------------------------------------------------------------------------

_AXB_RE = re.compile(r"(\d)\s*[x×]\s*(\d)")


def _norm_invariant(literal: str) -> str:
    s = literal.replace("≥", ">=").replace("≤", "<=")
    s = "".join(s.split())
    s = re.sub(r"(\d),(\d)", r"\1.\2", s)
    return s.lower()


def invariants(text: str) -> Counter:
    """Multiconjunto normalizado de bandas, cantidades, códigos y siglas
    (coma o punto decimal, espacios en ``AxB``, ``>=`` ≡ ``≥``). Las
    siglas conservan sus mayúsculas; el resto va en minúsculas."""
    text = _AXB_RE.sub(r"\1x\2", text)
    _, mapping = mask_surface(text, "sentinel")
    out: Counter = Counter()
    for marker, literal in mapping.items():
        if marker.startswith("[[S"):
            out["".join(literal.split())] += 1
        else:
            out[_norm_invariant(literal)] += 1
    return out


def _signed(c: Counter) -> dict[str, int]:
    return {k: v for k, v in c.items() if v}


def _add(acc: dict[str, int], delta: Mapping[str, int], k: int = 1) -> None:
    for key, v in delta.items():
        acc[key] = acc.get(key, 0) + k * v
        if acc[key] == 0:
            del acc[key]


def _delta(original: str, new: str) -> dict[str, int]:
    d: dict[str, int] = dict(invariants(new))
    _add(d, invariants(original), -1)
    return d


def undo_records(text: str, records: Sequence[Mapping]) -> str:
    """Deshace en ``text`` las sustituciones de los registros no-plantilla
    (``new`` → ``original``, palabras completas, las más largas primero).
    Lleva el texto al espacio de valores originales, donde la unidad que
    aporta la plantilla (``$B m``) vuelve a quedar pegada a su número. Si
    ``new`` no aparece (porque se tradujo o se revirtió), no se toca."""
    subs = [(r["new"].strip(), r["original"].strip()) for r in records
            if r.get("layer") != "template" and r["new"].strip()]
    for new, original in sorted(subs, key=lambda s: len(s[0]), reverse=True):
        text = re.sub(rf"(?<!\w){re.escape(new)}(?!\w)", lambda _m: original, text)
    return text


def _diff_reason(got: Counter, expected: Mapping[str, int]) -> str:
    got_d = dict(got)
    missing = sorted(k for k, v in expected.items() if v > got_d.get(k, 0))
    extra = sorted(k for k, v in got_d.items() if v > expected.get(k, 0))
    if any(v < 0 for v in expected.values()):
        missing.append("<negativo>")
    head = "missing" if missing else "extra"
    return f"{head}: missing={missing} extra={extra}"


# ---------------------------------------------------------------------------
# G2 — extracción cerrada
# ---------------------------------------------------------------------------

class ExtractionError(ValueError):
    """La salida del extractor no es el JSON esperado."""


class Extractor(Protocol):
    name: str

    def extract(self, text: str, concept: ConceptInfo) -> dict[str, int]: ...


def _load_prompt_template() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def build_extraction_prompt(text: str, concept: ConceptInfo,
                            template: Optional[str] = None) -> str:
    """Prompt del extractor (v2): la descripción y, por eje, los valores
    originales con letras, uno por línea (con números, «d4» o «Nº tubos: 2»
    se confundían con el número de opción). No recibe el gold ni la clave."""
    template = template if template is not None else _load_prompt_template()
    lines = []
    for axis in concept.axes:
        lines.append(f"{axis.letter} — {axis.label}")
        lines.extend(f"  {chr(96 + i)}) {v}" for i, v in enumerate(axis.values, 1))
    return (template.replace("{description}", text)
                    .replace("{parameters}", "\n".join(lines)))


_NULLS = (None, "", "0", 0, "null", "none", "ninguna")


def _first_json_object(raw: str) -> dict:
    dec = json.JSONDecoder()
    for i, ch in enumerate(raw or ""):
        if ch == "{":
            try:
                obj, _ = dec.raw_decode(raw, i)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                return obj
    raise ExtractionError("no_json")


def _is_null(v) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, str):
        return v.strip().lower() in _NULLS
    return any(v == n and type(v) is type(n) for n in _NULLS)


def _letter(axis: AxisInfo, v) -> int:
    letter = v.strip().rstrip(").").strip().lower() if isinstance(v, str) else None
    if not letter or len(letter) != 1 or not "a" <= letter <= "z":
        raise ExtractionError(f"not_letter: {axis.letter}={v!r}")
    idx = ord(letter) - 96
    if idx > len(axis.values):
        raise ExtractionError(f"out_of_range: {axis.letter}={v!r}")
    return idx


def evidence_ok(cita: object, text: str, axis: AxisInfo) -> bool:
    """La cita está en la descripción (todas sus palabras, sin mayúsculas ni
    acentos) y aporta alguna palabra que no sea la etiqueta del parámetro."""
    if not isinstance(cita, str):
        return False
    words = _words(cita)
    if not words or not set(words) <= set(_words(text)):
        return False
    return bool(set(words) - set(_words(axis.label)) - _STOP)


def parse_extraction(raw: str, concept: ConceptInfo, text: str) -> dict[str, int]:
    """Prompt v3. Primer objeto JSON de la respuesta; por eje,
    ``{"opcion": <letra>, "cita": <fragmento de la descripción>}`` o ``null``.

    * ``null``, ``"null"`` o un eje omitido → :data:`NO_DET`;
    * una opción sin cita válida (:func:`evidence_ok`) → :data:`NO_DET`: elegir
      sin poder señalar el texto que lo dice es elegir por descarte;
    * una letra fuera de rango, un número o el valor en vez de la letra →
      :class:`ExtractionError` (el extractor no ha entendido el formato).
    """
    obj = _first_json_object(raw)
    out: dict[str, int] = {}
    for axis in concept.axes:
        v = obj.get(axis.letter)
        if _is_null(v):
            out[axis.letter] = NO_DET
            continue
        if isinstance(v, dict):
            if _is_null(v.get("opcion")):
                out[axis.letter] = NO_DET
                continue
            idx = _letter(axis, v.get("opcion"))
            out[axis.letter] = idx if evidence_ok(v.get("cita"), text, axis) else NO_DET
            continue
        _letter(axis, v)  # valida el formato; sin cita no cuenta
        out[axis.letter] = NO_DET
    return out


def _json_mode_client_cls():
    from .llm_client import HttpLLMClient

    class _JsonModeClient(HttpLLMClient):
        """``HttpLLMClient`` que pide JSON estricto (``response_format``
        json_object, soportado por Ollama) y corta en ``max_tokens``: el
        extractor no escribe explicaciones. Subclase por encima de la
        costura; ``llm_client`` no se modifica."""

        def __init__(self, config_, *, max_tokens: int = 128, sender=None):
            super().__init__(config_, sender=sender)
            self.max_tokens = max_tokens

        def _build_body(self, prompt: str) -> bytes:
            payload = json.loads(super()._build_body(prompt))
            payload["response_format"] = {"type": "json_object"}
            payload["max_tokens"] = self.max_tokens
            return json.dumps(payload).encode("utf-8")

    return _JsonModeClient


def JsonModeClient(config_, *, max_tokens: int = 128, sender=None):  # noqa: N802
    return _json_mode_client_cls()(config_, max_tokens=max_tokens, sender=sender)


class LLMExtractor:
    """Extractor sobre cualquier cliente con ``complete(prompt) -> str``
    (``RecordingClient``/``ReplayClient`` de :mod:`llm_client`)."""

    def __init__(self, name: str, client, template: Optional[str] = None):
        self.name = name
        self._client = client
        self._template = template if template is not None else _load_prompt_template()

    def prompt(self, text: str, concept: ConceptInfo) -> str:
        return build_extraction_prompt(text, concept, self._template)

    def extract(self, text: str, concept: ConceptInfo) -> dict[str, int]:
        return parse_extraction(self._client.complete(self.prompt(text, concept)), concept, text)


# ---------------------------------------------------------------------------
# Decodificador léxico (tercera señal; no decide) y supervivencia (G5)
# ---------------------------------------------------------------------------

_STOP = frozenset({
    "de", "del", "al", "la", "el", "los", "las", "un", "una", "en", "para",
    "con", "y", "o", "u", "e", "a", "por", "su", "sus", "se", "que", "es",
})


def _fold(text: str) -> str:
    t = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in t if not unicodedata.combining(c))


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", _fold(text))


def _contains(haystack_words: Sequence[str], needle: str) -> bool:
    n = _words(needle)
    if not n:
        return False
    k = len(n)
    return any(list(haystack_words[i:i + k]) == n for i in range(len(haystack_words) - k + 1))


def lexical_decode(text: str, concept: ConceptInfo,
                   extra_surfaces: Optional[Mapping[tuple, Sequence[str]]] = None,
                   ) -> dict[str, tuple[int, ...]]:
    """Por eje, las opciones (1-based) cuya superficie (valor original o una
    reescritura L1 aprobada) aparece como secuencia de palabras completa."""
    extra = extra_surfaces or {}
    words = _words(text)
    out: dict[str, tuple[int, ...]] = {}
    for axis in concept.axes:
        hits = []
        for i, value in enumerate(axis.values, 1):
            surfaces = (value, *extra.get((concept.key, axis.letter, i), ()))
            if any(_contains(words, s) for s in surfaces):
                hits.append(i)
        out[axis.letter] = tuple(hits)
    return out


def pantry_surfaces(pantry, contexts: Mapping[str, ConceptInfo]) -> dict[tuple, tuple[str, ...]]:
    """Superficies L1 aprobadas por ``(concepto, eje, opción)`` desde
    :func:`pantry.load_pantry` (``dedup_key = (etiqueta del eje, valor)``)."""
    from .dose_ladder import L1_VALUE_TYPES

    out: dict[tuple, list[str]] = {}
    for mtype, rewrites in pantry.by_type.items():
        if mtype not in L1_VALUE_TYPES:
            continue
        for rw in rewrites:
            if len(rw.dedup_key) < 2:
                continue
            label, value = _ws(rw.dedup_key[0]), _ws(rw.dedup_key[1])
            for usage in rw.usages:
                concept = contexts.get(usage.concept_key)
                if concept is None:
                    continue
                for axis in concept.axes:
                    if axis.label != label:
                        continue
                    for i, v in enumerate(axis.values, 1):
                        if v == value:
                            out.setdefault((concept.key, axis.letter, i), []).append(
                                rw.payload["new"])
    return {k: tuple(dict.fromkeys(v)) for k, v in out.items()}


_PH_RE = re.compile(r"\$[A-Za-z]\w*(?:\([^)]*\))?")


def survival(original: str, new: str, query: str) -> str:
    """``survived`` si en ``query`` pesan más las palabras propias de ``new``
    que las propias de ``original``; ``reverted`` si al revés;
    ``transformed`` si empatan (ni una ni otra)."""
    o = set(_words(_PH_RE.sub(" ", original))) - _STOP
    n = set(_words(_PH_RE.sub(" ", new))) - _STOP
    q = set(_words(query))
    only_o, only_n = o - n, n - o
    s_o = len(only_o & q) / len(only_o) if only_o else None
    s_n = len(only_n & q) / len(only_n) if only_n else None
    if s_o is None and s_n is None:
        return "transformed"
    if s_n is None:
        s_n = 1 - s_o
    if s_o is None:
        s_o = 1 - s_n
    if s_n > s_o:
        return "survived"
    if s_o > s_n:
        return "reverted"
    return "transformed"


# ---------------------------------------------------------------------------
# meaning_drift_flag (script, no paquete)
# ---------------------------------------------------------------------------

_DRIFT = None


def _drift(original: str, new: str) -> dict:
    global _DRIFT
    if _DRIFT is None:
        path = Path(__file__).resolve().parents[2] / "scripts" / "meaning_drift_flag.py"
        spec = importlib.util.spec_from_file_location("_bt_meaning_drift_flag", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _DRIFT = mod.analyze
    return _DRIFT(original, new)


# ---------------------------------------------------------------------------
# Resultado y contexto
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    ok: bool
    gate: Optional[str] = None
    axis: Optional[str] = None
    reason: Optional[str] = None
    axes: dict = field(default_factory=dict)
    not_rendered: list = field(default_factory=list)
    extractions: dict = field(default_factory=dict)
    decoder: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    surviving_types: list = field(default_factory=list)
    reverted_types: list = field(default_factory=list)
    drift: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        d = dict(self.__dict__)
        d["decoder"] = {k: list(v) for k, v in self.decoder.items()}
        return d


class CharacterizationContext:
    def __init__(self, concepts, leaves, groups, excluded, surface, owners, guard_index,
                 extra_surfaces=None):
        self.concepts: dict[str, ConceptInfo] = concepts
        self.leaves: dict[str, Leaf] = leaves
        self.groups: dict[str, frozenset] = groups
        self.excluded: frozenset = excluded
        self.surface: TextoSurface = surface
        self._owners: dict[str, frozenset] = owners
        self._guard = guard_index
        self.extra_surfaces = extra_surfaces or {}

    # -- carga ---------------------------------------------------------------

    @classmethod
    def load(cls, stage_json: Mapping[str, dict], texto_corpus: Iterable[Mapping], *,
             d031_groups: Optional[Mapping] = None,
             exclusions: Iterable[Mapping] = (),
             concept_schema: Optional[Mapping] = None,
             extra_surfaces: Optional[Mapping] = None) -> "CharacterizationContext":
        concepts = {k: _concept_info(k, c) for k, c in stage_json.items() if k.endswith("$")}
        if concept_schema is not None:
            for key, entry in concept_schema.items():
                info = concepts.get(key)
                schema_axes = {_ws(l): tuple(_ws(v) for v in vals)
                               for l, vals in entry.get("axes", {}).items()}
                stage_axes = {a.label: a.values for a in info.axes} if info else None
                if stage_axes != schema_axes:
                    raise ValueError(f"concept_schema: {key} no coincide con el stage")

        leaves: dict[str, Leaf] = {}
        owners: dict[str, set] = {}
        long_cols = {"item_key": [], "parent_key": [], "text": []}
        for row in texto_corpus:
            key, parent = row["item_key"], row["parent_key"]
            info = concepts.get(parent)
            if info is None:
                continue
            suffix = key[len(parent) - 1:]
            options = dict(zip((a.letter for a in info.axes), suffix))
            leaves[key] = Leaf(key, parent, options, row["text"])
            owners.setdefault(norm_text(row["text"]), set()).add(key)
            long_cols["item_key"].append(key)
            long_cols["parent_key"].append(parent)
            long_cols["text"].append(row["text"])

        groups: dict[str, frozenset] = {}
        for members in ((d031_groups or {}).get("groups") or {}).values():
            g = frozenset(members)
            for m in members:
                groups[m] = g

        excluded = frozenset(k for e in exclusions for k in e.get("item_keys", ()))
        guard = cross_concept_guard.build_base_index(long_cols, {"item_key": [], "text": []})
        return cls(concepts, leaves, groups, excluded, TextoSurface.from_stage(stage_json),
                   {k: frozenset(v) for k, v in owners.items()}, guard, extra_surfaces)

    # -- valores admitidos ---------------------------------------------------

    def group(self, gold: str) -> frozenset:
        return self.groups.get(gold, frozenset({gold}))

    def allowed(self, gold: str, axis: str) -> frozenset:
        leaf = self.leaves[gold]
        concept = self.concepts[leaf.concept]
        values = concept.axis(axis).values
        letters = {self.leaves[m].options[axis] for m in self.group(gold) if m in self.leaves}
        idx = {ord(l) - 96 for l in letters}
        # opciones con la misma etiqueta tampoco se distinguen
        labels = {values[i - 1] for i in idx}
        idx |= {i for i, v in enumerate(values, 1) if v in labels}
        if len(idx) > 1:
            idx.add(NO_DET)
        return frozenset(idx)

    # -- registros visibles --------------------------------------------------

    def _visible(self, records: Sequence[Mapping], leaf: Leaf) -> list[Mapping]:
        return [r for r in records or ()
                if self.surface.shows_record(r, leaf.concept, leaf.key)]

    # -- comprobación ---------------------------------------------------------

    def check(self, query_text: str, gold_item_key: str, *,
              extractors: Sequence[Extractor],
              source_text: Optional[str] = None,
              records: Optional[Sequence[Mapping]] = None,
              query_key: Optional[str] = None,
              forbidden: frozenset = frozenset()) -> CheckResult:
        res = CheckResult(ok=False)

        # G0
        leaf = self.leaves.get(gold_item_key)
        if leaf is None:
            return self._fail(res, "G0", None, "unknown_gold")
        if query_key is not None and query_key in self.excluded:
            return self._fail(res, "G0", None, "excluded_p7_p8")
        concept = self.concepts[leaf.concept]
        res.not_rendered = list(concept.not_rendered)
        visible = self._visible(records, leaf)

        # G1 — en el espacio de valores originales
        got = invariants(undo_records(query_text, visible))
        if source_text is None:
            expected = self._expected_from_gold(leaf, concept, visible)
        else:
            expected = _signed(invariants(undo_records(source_text, visible)))
        if dict(got) != expected:
            return self._fail(res, "G1", None, _diff_reason(got, expected))

        # G2
        extractions: dict[str, dict[str, int]] = {}
        for ex in extractors:
            try:
                extractions[ex.name] = ex.extract(query_text, concept)
            except ExtractionError:
                res.extractions = extractions
                return self._fail(res, "G2", None, f"extractor_output_invalid:{ex.name}")
        res.extractions = extractions
        res.decoder = lexical_decode(query_text, concept, self.extra_surfaces)
        gold_idx = {a: ord(leaf.options[a]) - 96 for a in concept.rendered}
        first_fail = None
        # Sin extractores (modo estructural, rediseño tras CP2): los valores de
        # eje van enmascarados en la BT y salen literalmente iguales; G2 no aplica.
        for a in (concept.rendered if extractors else ()):
            allowed = self.allowed(gold_item_key, a)
            answers = [e[a] for e in extractions.values()]
            if all(v in allowed for v in answers):
                res.axes[a] = "ok" if all(v == gold_idx[a] for v in answers) else "ok_group"
                continue
            if len(set(answers)) > 1:
                status = "extractor_disagree"
            elif answers[0] == NO_DET:
                status = "not_determinable"
            else:
                status = "wrong_value"
            res.axes[a] = status
            first_fail = first_fail or (a, status)
        if first_fail:
            return self._fail(res, "G2", *first_fail)

        # G3
        owners = self._owners.get(norm_text(query_text), frozenset())
        if owners - self.group(gold_item_key):
            return self._fail(res, "G3", None, "confusable_with_leaf")
        coll = cross_concept_guard.classify(self._guard, query_key or "query",
                                            gold_item_key, leaf.concept, "texto", query_text)
        if coll is not None and coll.kind == "introduced":
            return self._fail(res, "G3", None, "cross_concept_collision")

        # G4
        res.drift = _drift(source_text if source_text is not None else leaf.text, query_text)
        for a in concept.not_rendered:
            allowed = self.allowed(gold_item_key, a) | {NO_DET}
            if any(e[a] not in allowed for e in extractions.values()):
                return self._fail(res, "G4", a, "added_axis_value")

        # G5 (solo informa)
        if source_text is not None and records:
            by_type: dict[str, set] = {}
            for r in visible:
                by_type.setdefault(r["type"], set()).add(
                    survival(r["original"], r["new"], query_text))
            res.surviving_types = sorted(t for t, s in by_type.items() if "survived" in s)
            res.reverted_types = sorted(t for t, s in by_type.items()
                                        if "survived" not in s and "reverted" in s)

        # G6
        q = norm_text(query_text)
        if source_text is not None and q == norm_text(source_text):
            return self._fail(res, "G6", None, "no_op")
        if q == norm_text(leaf.text):
            return self._fail(res, "G6", None, "equals_gold")
        if q in forbidden:
            return self._fail(res, "G6", None, "duplicate_of_delivered")

        res.ok = True
        return res

    def _expected_from_gold(self, leaf: Leaf, concept: ConceptInfo,
                            visible: Sequence[Mapping]) -> dict[str, int]:
        """Invariantes del TEXTO gold más lo que cambia la plantilla TEXTO
        parafraseada: sus literales y las repeticiones de placeholders de
        eje (repetir un valor no añade información)."""
        expected = _signed(invariants(leaf.text))
        for r in visible:
            if r.get("layer") != "template":
                continue
            _add(expected, _delta(r["original"], r["new"]))
            before = Counter(_TOKEN_RE.findall(r["original"]))
            after = Counter(_TOKEN_RE.findall(r["new"]))
            for a in concept.axes:
                extra = after[a.letter] - before[a.letter]
                if extra:
                    value = a.values[ord(leaf.options[a.letter]) - 97]
                    _add(expected, invariants(value), extra)
        return expected

    @staticmethod
    def _fail(res: CheckResult, gate: str, axis: Optional[str], reason: str) -> CheckResult:
        res.ok, res.gate, res.axis, res.reason = False, gate, axis, reason
        return res
