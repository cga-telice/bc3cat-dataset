"""BT de valores de eje y fragmentos L2 (opción A, vuelta tras CP4).

Los valores y fragmentos que la BT de prosa enmascara son un conjunto cerrado
(OE: 346 pares etiqueta/valor y 78 fragmentos L2, más las reescrituras de
STACKED). Se traducen una vez, fuera de la consulta:

1. entrada «ETIQUETA: valor» (la etiqueta da contexto al MT); los fragmentos L2
   van solos;
2. cadena ES→EN→X→ES, X ∈ {FR, IT, DE};
3. filtro automático contra las hermanas del mismo hueco (:func:`filter_candidates`);
4. César aprueba la tabla (:func:`menu_markdown` / :func:`parse_menu`).

Al montar la consulta, cada marcador de valor se rellena con una variante
aprobada elegida con semilla, o con el original (:func:`fill_values`); a veces
con la etiqueta traducida delante, salvo que la prosa ya la diga
(:func:`label_present`). Funciones puras, solo stdlib.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, replace
from typing import Mapping, Optional, Sequence

from .bt_masking import MARKER_RE

_STOP = frozenset({"de", "del", "la", "el", "los", "las", "y", "o", "en", "a", "al",
                   "con", "por", "para", "un", "una", "se"})


def _fold(text: str) -> str:
    t = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in t if not unicodedata.combining(c))


def _norm(text: str) -> str:
    return " ".join(re.findall(r"\w+", _fold(text)))


def source_text(surface: str, label: Optional[str]) -> str:
    """Lo que entra en la cadena de traducción."""
    if not label:
        return surface
    # en mayúsculas («TRABAJO») bt_masking la tomaría por sigla y la ocultaría
    label = " ".join(label.split())
    return f"{label[:1].upper()}{label[1:].lower()}: {surface}"


def split_label(translated: str) -> Optional[tuple[str, str]]:
    """(etiqueta traducida, valor traducido); ``None`` si la traducción perdió
    los dos puntos y no se pueden separar."""
    if ":" not in translated:
        return None
    label, value = translated.split(":", 1)
    label, value = " ".join(label.split()), " ".join(value.split())
    if not label or not value:
        return None
    return label[:1].upper() + label[1:].lower(), value


@dataclass(frozen=True)
class Candidate:
    concept: str
    placeholder: str
    surface: str          # superficie de origen (gold o reescritura STACKED)
    option: str           # opción a la que pertenece (letra L1 o fragmento gold L2)
    pivot: str            # idioma intermedio X
    variant: str          # valor traducido
    label_variant: Optional[str] = None  # etiqueta traducida (solo L1)
    status: str = "pending"
    reason: Optional[str] = None
    label: Optional[str] = None  # etiqueta original del parámetro (solo L1)

    @property
    def uid(self) -> str:
        """Identidad de revisión: etiqueta, superficie y variante, sin concepto.
        «Trabajo: Diurno → De día» se aprueba una vez para todos los conceptos;
        el filtro de colisiones sigue siendo por concepto."""
        raw = "|".join([_norm(self.label or ""), _norm(self.surface), _norm(self.variant)])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def filter_candidates(group: Mapping[str, str], candidates: Sequence[Candidate]) -> list[Candidate]:
    """Filtro automático para un hueco ``(concepto, placeholder)``.

    ``group`` va de superficie a opción. Una variante se rechaza si está vacía,
    si es el propio original (sin mayúsculas ni puntuación), si coincide con la
    superficie o con una variante de **otra** opción, o si repite una variante
    ya vista para la misma superficie."""
    by_norm: dict[str, set] = {}
    for surface, option in group.items():
        by_norm.setdefault(_norm(surface), set()).add(option)
    for c in candidates:
        if c.variant.strip():
            by_norm.setdefault(_norm(c.variant), set()).add(c.option)

    out, seen = [], set()
    for c in candidates:
        n = _norm(c.variant)
        if not n:
            out.append(replace(c, status="rejected", reason="empty"))
        elif n == _norm(c.surface):
            out.append(replace(c, status="rejected", reason="same_as_original"))
        elif by_norm.get(n, set()) - {c.option}:
            out.append(replace(c, status="rejected", reason="collides_with_sibling"))
        elif (c.surface, n) in seen:
            out.append(replace(c, status="rejected", reason="duplicate"))
        else:
            seen.add((c.surface, n))
            out.append(replace(c, status="ok"))
    return out


# ---------------------------------------------------------------------------
# Menú para César
# ---------------------------------------------------------------------------

_BOX_RE = re.compile(r"^- \[(?P<mark>[ xX])\] `(?P<uid>[0-9a-f]{12})`", re.M)


def menu_markdown(candidates: Sequence[Candidate], title: str = "Variantes de valores") -> str:
    """Una casilla por variante distinta que pasa el filtro, sin repetir entre
    conceptos (:attr:`Candidate.uid`). Agrupado por etiqueta del parámetro (L1)
    o como fragmento L2, y por superficie. Marca ``[x]`` para aprobar."""
    lines = [f"# {title}", "",
             "Marca `[x]` en cada variante que describa **exactamente el mismo valor** que el "
             "original, en el contexto del parámetro. Lo que quede sin marcar no se usa. "
             "Cada casilla vale para todos los conceptos indicados.", ""]
    by_uid: dict[str, list[Candidate]] = {}
    for c in candidates:
        if c.status == "ok":
            by_uid.setdefault(c.uid, []).append(c)
    rows = []
    for uid, cs in by_uid.items():
        c = min(cs, key=lambda x: (x.pivot, x.concept))
        group = f"Parámetro «{' '.join((c.label or '').split())}»" if c.label else "Fragmentos de texto (L2)"
        rows.append((group, " ".join(c.surface.split()), _norm(c.variant), uid, c, cs))
    current_group = current_surface = None
    for group, surface, _, uid, c, cs in sorted(rows, key=lambda r: r[:3]):
        if group != current_group:
            lines += ["", f"## {group}", ""]
            current_group, current_surface = group, None
        if surface != current_surface:
            lines.append(f"**{surface}**")
            current_surface = surface
        n = len({x.concept for x in cs})
        pivots = ", ".join(sorted({x.pivot for x in cs}))
        label = f" · etiqueta «{c.label_variant}»" if c.label_variant else ""
        lines.append(f"- [ ] `{uid}` {c.variant}  _(vía {pivots}{label}; {n} concepto{'s' if n != 1 else ''})_")
    return "\n".join(lines) + "\n"


def parse_menu(md: str) -> set[str]:
    return {m.group("uid") for m in _BOX_RE.finditer(md) if m.group("mark") in "xX"}


# ---------------------------------------------------------------------------
# Montaje
# ---------------------------------------------------------------------------

def fill_values(back_masked: str, mapping: Mapping[str, str], values: Sequence[str],
                choices: Mapping[str, str]) -> str:
    """Rellena los marcadores: los de valor con ``choices`` (si hay) y el resto,
    y los de valor sin elección, con su literal original."""
    wanted = set(values)

    def sub(m: re.Match) -> str:
        marker = m.group(0)
        if marker in wanted and marker in choices:
            return choices[marker]
        return mapping.get(marker, marker)

    return MARKER_RE.sub(sub, back_masked)


def label_present(prefix: str, label: str, window: int = 6) -> bool:
    """¿La prosa justo antes del hueco ya nombra el parámetro? Entonces no se
    añade la etiqueta (evita «Trabajo: trabajo nocturno»)."""
    words = re.findall(r"\w+", _fold(prefix))[-window:]
    label_words = [w for w in re.findall(r"\w+", _fold(label)) if w not in _STOP and len(w) > 2]
    return bool(label_words) and any(w in words for w in label_words)


# ---------------------------------------------------------------------------
# Inventario de huecos
# ---------------------------------------------------------------------------

def value_groups(stage: Mapping, corpus: Sequence[Mapping], stacked: Sequence[Mapping],
                 sidecar: Mapping[str, Sequence[Mapping]]):
    """Para cada hueco ``(concepto, placeholder)`` de los conceptos de
    ``stacked``: superficie → opción. Las hojas gold dan todas las opciones (la
    letra del eje en L1, el fragmento gold en L2); las consultas STACKED añaden
    sus reescrituras, con la opción de su hoja gold. Devuelve también la
    etiqueta de cada hueco (``None`` en L2: el fragmento ya lleva su contexto)."""
    from .bt_alignment import gold_slots, stacked_slots

    concepts = {q["parent_key"] for q in stacked}
    gold_by_key = {r["item_key"]: r for r in corpus}
    groups: dict[tuple, dict[str, str]] = {}
    labels: dict[tuple, Optional[str]] = {}
    gold_option: dict[tuple, str] = {}  # (hoja, placeholder) -> opción

    for r in corpus:
        if r["parent_key"] not in concepts:
            continue
        concept = stage[r["parent_key"]]
        params = concept.get("parameters") or {}
        suffix = r["item_key"][-len(params):] if params else ""
        letters = dict(zip(params, suffix))
        for s in gold_slots(concept, r["item_key"], r["text"]):
            if not s.text:
                continue
            axis = s.placeholder[1:]
            key = (r["parent_key"], s.placeholder)
            if axis in params:
                option = letters[axis]
                labels[key] = " ".join(params[axis]["label"].split())
            else:
                option = s.text
                labels.setdefault(key, None)
            groups.setdefault(key, {})[s.text] = option
            gold_option[(r["item_key"], s.placeholder)] = option

    for q in stacked:
        gold = gold_by_key[q["gold_item_key"]]
        concept = stage[q["parent_key"]]
        for s in stacked_slots(concept, gold["item_key"], gold["text"], q["text"],
                               sidecar[q["item_key"]]):
            option = gold_option.get((gold["item_key"], s.placeholder))
            if s.text and option is not None:
                groups[(q["parent_key"], s.placeholder)].setdefault(s.text, option)
    return groups, labels


# ---------------------------------------------------------------------------
# Términos de dominio (descarte automático de variantes L2, decisión de César)
# ---------------------------------------------------------------------------

def _content_words(text: str) -> list[str]:
    return [w for w in re.findall(r"[^\W\d_]+", _fold(text)) if len(w) >= 4 and w not in _STOP]


def domain_terms(docs: Mapping[str, str], max_df: float) -> frozenset:
    """Palabras con contenido que aparecen en una fracción de conceptos
    ``<= max_df``: el léxico técnico (entibación, balasto, topo…). Las que
    salen en muchos conceptos (suministro, montaje…) se consideran genéricas."""
    df: dict[str, int] = {}
    for text in docs.values():
        for w in set(_content_words(text)):
            df[w] = df.get(w, 0) + 1
    n = max(len(docs), 1)
    return frozenset(w for w, c in df.items() if c / n <= max_df)


def _stem(word: str) -> str:
    return word[:max(4, len(word) - 2)]


def lost_domain_terms(surface: str, variant: str, terms: frozenset) -> list[str]:
    """Términos de dominio del original cuya raíz no aparece en la variante
    (sin acentos; «pozo» → «pozos» o «topo» → «topos» no cuentan como pérdida)."""
    have = _content_words(variant)
    out = []
    for t in dict.fromkeys(_content_words(surface)):
        if t in terms and not any(w.startswith(_stem(t)) for w in have):
            out.append(t)
    return out


def concept_docs(stage: Mapping) -> dict[str, str]:
    """Texto de cada concepto para :func:`domain_terms`: plantillas TEXTO y
    RESUMEN, variables de texto y valores de los parámetros."""
    def flat(v):
        return v if isinstance(v, str) else " ".join(map(str, v or ()))

    out = {}
    for key, c in stage.items():
        if not key.endswith("$"):
            continue
        parts = [flat(c.get("texto")), flat(c.get("resumen"))]
        parts += [flat(v) for v in (c.get("text_variables") or {}).values()]
        parts += [v["value"] for b in (c.get("parameters") or {}).values() for v in b["values"]]
        out[key] = " ".join(parts)
    return out
