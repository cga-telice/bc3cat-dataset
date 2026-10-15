"""Motor de back-translation (BT, opción A, T4).

``back_translate`` = enmascarar → segmentar → ES → pivote → ES →
reensamblar → comprobar máscaras → desenmascarar. Se enmascara *antes* de
segmentar: así una sigla con puntos (``E.T.``) o un decimal nunca parten
una frase (los marcadores no llevan puntos). Si una máscara se pierde, el
resultado es ``ok=False, reason="mask_lost"``; nunca se repara a mano.

``CachedEngine`` es la fuente de verdad de la reproducibilidad: clave
``sha256(firma del motor | src | tgt | segmento)``, un JSONL por dirección,
y modo ``replay`` que falla si falta una entrada. ``MarianEngine`` (OPUS-MT
vía ``transformers``) se importa solo al usarlo.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Protocol, Sequence

from .bt_masking import (
    MaskError,
    check_masks,
    check_value_order,
    glossary_spans,
    mask_with_values,
    unmask_surface,
)


class BTEngine(Protocol):
    signature: Mapping

    def translate(self, segments: Sequence[str], src: str, tgt: str) -> list[str]: ...


# ---------------------------------------------------------------------------
# Segmentación
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Piece:
    text: str
    translate: bool


_LINE_RE = re.compile(r"(\r?\n)")
_SENT_RE = re.compile(r"(?<=[.!?])(\s+)")


def segment(text: str) -> list[Piece]:
    """Corta por saltos de línea y luego por frase, conservando los
    separadores como piezas no traducibles (reensamblado exacto)."""
    pieces: list[Piece] = []
    for line in _LINE_RE.split(text):
        if not line:
            continue
        if _LINE_RE.fullmatch(line):
            pieces.append(Piece(line, False))
            continue
        for part in _SENT_RE.split(line):
            if not part:
                continue
            if not part.strip():
                pieces.append(Piece(part, False))
                continue
            lead = part[: len(part) - len(part.lstrip())]
            trail = part[len(part.rstrip()):]
            if lead:
                pieces.append(Piece(lead, False))
            pieces.append(Piece(part.strip(), True))
            if trail:
                pieces.append(Piece(trail, False))
    return pieces


def reassemble(pieces: Sequence[Piece], translated: Sequence[str]) -> str:
    it = iter(translated)
    return "".join(next(it) if p.translate else p.text for p in pieces)


# ---------------------------------------------------------------------------
# Back-translation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BTResult:
    text: Optional[str]
    ok: bool
    reason: Optional[str]
    mapping: dict
    masked: str
    pivot_text: str
    back_masked: str
    segments: int
    values: list = field(default_factory=list)  # marcadores de valor de eje, en orden de origen


def back_translate_many(texts: Sequence[str], pivot: str, engine: BTEngine,
                        mask_strategy: str, src: str = "es",
                        spans: Optional[Sequence[Optional[Sequence[tuple[int, int]]]]] = None,
                        glossary_terms: Sequence[str] = (),
                        ) -> list[BTResult]:
    """Una llamada al motor por dirección para todos los segmentos.

    ``spans`` (uno por texto, o ``None``) son los tramos de valores de eje y
    fragmentos L2 (:mod:`bt_alignment`): se enmascaran enteros y, además de
    preservarse, tienen que volver en el mismo orden (``value_order_changed``)."""
    spans = list(spans) if spans is not None else [None] * len(texts)
    prepared = []
    flat: list[str] = []
    for text, sp in zip(texts, spans):
        gloss = glossary_spans(text, glossary_terms, exclude=sp or ()) if glossary_terms else ()
        masked, mapping, values = mask_with_values(text, mask_strategy, sp or (), glossary=gloss)
        pieces = segment(masked)
        segs = [p.text for p in pieces if p.translate]
        prepared.append((masked, mapping, list(values), pieces, len(flat), len(segs)))
        flat.extend(segs)
    there = engine.translate(flat, src, pivot)
    back = engine.translate(there, pivot, src)

    out = []
    for masked, mapping, values, pieces, start, n in prepared:
        pivot_text = reassemble(pieces, there[start:start + n])
        back_masked = reassemble(pieces, back[start:start + n])
        reason = None
        try:
            check_masks(back_masked, mapping)
            check_value_order(back_masked, values)
        except MaskError as err:
            reason = "value_order_changed" if str(err).startswith("value_order") else "mask_lost"
        text = None if reason else unmask_surface(back_masked, mapping)
        out.append(BTResult(text, reason is None, reason, mapping, masked,
                            pivot_text, back_masked, n, values))
    return out


def back_translate(text: str, pivot: str, engine: BTEngine, mask_strategy: str) -> BTResult:
    return back_translate_many([text], pivot, engine, mask_strategy)[0]


# ---------------------------------------------------------------------------
# Caché
# ---------------------------------------------------------------------------

class CacheMiss(KeyError):
    """Modo replay y el segmento no está en caché."""


class CachedEngine:
    MODES = ("record", "replay")

    def __init__(self, inner: BTEngine, cache_dir: Path, mode: str = "record"):
        if mode not in self.MODES:
            raise ValueError(f"modo de caché desconocido: {mode!r}")
        self.inner = inner
        self.mode = mode
        self.signature = dict(inner.signature)
        self._dir = Path(cache_dir)
        self._store: dict[tuple, dict[str, str]] = {}

    def _sig(self) -> str:
        return json.dumps(self.signature, sort_keys=True, ensure_ascii=False)

    def key(self, segment_: str, src: str, tgt: str) -> str:
        raw = "|".join([self._sig(), src, tgt, segment_])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _path(self, src: str, tgt: str) -> Path:
        return self._dir / f"{src}-{tgt}.jsonl"

    def _load(self, src: str, tgt: str) -> dict[str, str]:
        if (src, tgt) not in self._store:
            store: dict[str, str] = {}
            path = self._path(src, tgt)
            if path.exists():
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        r = json.loads(line)
                        store[r["key"]] = r["out"]
            self._store[(src, tgt)] = store
        return self._store[(src, tgt)]

    def translate(self, segments: Sequence[str], src: str, tgt: str) -> list[str]:
        store = self._load(src, tgt)
        keys = [self.key(s, src, tgt) for s in segments]
        missing = list(dict.fromkeys(s for s, k in zip(segments, keys) if k not in store))
        if missing:
            if self.mode == "replay":
                raise CacheMiss(f"{len(missing)} segmentos sin caché ({src}->{tgt}): {missing[0]!r}")
            outs = self.inner.translate(missing, src, tgt)
            self._dir.mkdir(parents=True, exist_ok=True)
            with self._path(src, tgt).open("a", encoding="utf-8") as fh:
                for s, o in zip(missing, outs):
                    k = self.key(s, src, tgt)
                    store[k] = o
                    fh.write(json.dumps({"key": k, "src": s, "out": o}, ensure_ascii=False) + "\n")
        return [store[k] for k in keys]


# ---------------------------------------------------------------------------
# OPUS-MT (MarianMT)
# ---------------------------------------------------------------------------

def max_new_tokens(input_lens: Sequence[int], cap: int, ratio: Optional[float]) -> int:
    """Tope de generación de un lote. Con ``ratio``, proporcional a la entrada
    más larga (+16): una salida degenerada que se repite hasta el tope del
    modelo (512) tarda minutos por lote; los valores son cortos."""
    if ratio is None:
        return cap
    return min(cap, int(ratio * max(input_lens, default=0)) + 16)


class MarianEngine:
    """OPUS-MT con modelo y revisión fijados, beam fijo, sin muestreo y lotes
    de tamaño fijo en el orden de entrada."""

    def __init__(self, models: Mapping[tuple, tuple[str, str]], *, num_beams: int = 4,
                 max_new_tokens: int = 512, batch_size: int = 16,
                 device: Optional[str] = None, license: str = "apache-2.0",
                 length_ratio: Optional[float] = None):
        self.models = dict(models)  # (src, tgt) -> (model_id, revision)
        self.num_beams = num_beams
        self.max_new_tokens = max_new_tokens
        self.batch_size = batch_size
        self.device = device
        self.length_ratio = length_ratio
        self._loaded: dict[tuple, tuple] = {}
        self.signature = {
            "engine": "marian",
            "models": {f"{s}-{t}": f"{m}@{r}" for (s, t), (m, r) in sorted(self.models.items())},
            "num_beams": num_beams, "do_sample": False, "max_new_tokens": max_new_tokens,
            "license": license,
        }
        if length_ratio is not None:  # solo entra en la firma si se usa (caché de la prosa intacta)
            self.signature["length_ratio"] = length_ratio

    def _get(self, src: str, tgt: str):
        if (src, tgt) not in self._loaded:
            import torch
            from transformers import MarianMTModel, MarianTokenizer

            torch.use_deterministic_algorithms(True, warn_only=True)
            model_id, rev = self.models[(src, tgt)]
            device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
            tok = MarianTokenizer.from_pretrained(model_id, revision=rev)
            model = MarianMTModel.from_pretrained(model_id, revision=rev).to(device).eval()
            self._loaded[(src, tgt)] = (tok, model, device)
        return self._loaded[(src, tgt)]

    def translate(self, segments: Sequence[str], src: str, tgt: str) -> list[str]:
        import torch

        tok, model, device = self._get(src, tgt)
        out: list[str] = []
        for i in range(0, len(segments), self.batch_size):
            batch = list(segments[i:i + self.batch_size])
            enc = tok(batch, return_tensors="pt", padding=True, truncation=True).to(device)
            with torch.no_grad():
                limit = max_new_tokens([int(x) for x in enc["attention_mask"].sum(dim=1)],
                                       self.max_new_tokens, self.length_ratio)
                gen = model.generate(**enc, num_beams=self.num_beams, do_sample=False,
                                     max_new_tokens=limit)
            out.extend(tok.batch_decode(gen, skip_special_tokens=True))
        return out
