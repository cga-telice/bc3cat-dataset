"""Entrega aditiva de la BT a ``handoff_OE/`` (BT, opción A, T7; CP5).

Copia a ``data/synthetic/handoff_OE/`` (solo añade ficheros, no reescribe
ninguno de los ya entregados):

* ``OE_bt_texto.json`` — consultas BT sobre el TEXTO gold, por frases y con
  valores y términos del glosario sustituidos (4 670), auditadas;
* ``OE_bt_modifications.jsonl`` — su sidecar;
* ``OE_bt_provenance.json`` — procedencia (commit, modelos y revisiones,
  auditorías, sha256 de entradas y salidas);
* ``OE_stacked_P_exclusion.json`` y ``OE_known_drift_rewrites.json`` — las
  consultas STACKED con deriva conocida y la lista de esas reescrituras.

Antes y después comprueba los sha256 de los ficheros ya entregados.

  PYTHONPATH=src python scripts/package_bt_handoff.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import yaml  # noqa: E402

import audit_stacked_characterization as audit  # noqa: E402

HANDOFF = REPO / "data" / "synthetic" / "handoff_OE"
BT = REPO / "data" / "synthetic" / "bt_OE"

# Línea base de T0 (2026-10-04): los ficheros ya entregados no pueden cambiar.
BASELINE = {
    "MANIFEST.md": None,  # se le añaden filas; se comprueba aparte que no cambia ninguna línea previa
    "README.md": None,    # se le añade una sección; ídem
    "OE_P7_test_exclusion.json": "96fe3854f2b6d935720b23dad01b019d3903f5dd60ef586a4c272fe923d9a011",
    "OE_P8_test_exclusion.json": "6cda7fa05aa6e32ff76de1b459e1cb59164db69eb1e95ea2d7266edc93ea17ae",
    "OE_concept_schema.json": "2d3273ddb3e443a12553a6622704a3fc6462c57567abf24b2fc2dfba8a59416c",
    "OE_dose_texto.json": "555fab84d134886f85ece40115ffd485e796fd4e96291e6a9af3129004a80819",
    "OE_duplicate_texto_groups.json": "b3cfcad47c71c5ebaf86b0e77eaa741c8f6111efd4e8543262b4f1b8e4ced0df",
    "OE_isolated_texto.json": "054041ff05349fae79fd5b91ff111f4fe574b37f7f8ee9647cea044503c5e3ce",
    "OE_leaf_applicability.jsonl": "eda12d17c323add48a7d8deac0f93e767188824950357303b497a7ca8d3fbaa3",
    "OE_resumen.json": "4511eeac0135f594ecb9094e1831abe1cbb6ef2286c12de8a86e16381a9bafde",
    "OE_single_l2_modifications.jsonl": "e1e5adbb8824bd34abe08972c8ed9c66ad6fdf4cf8231c67182026efa7a7cc29",
    "OE_single_l2_provenance.json": "6885a7b2de28ae9c30376a7cff9a508bdb1f6a35c18207c46e224fb6de33d0af",
    "OE_single_l2_texto.json": "fff7dd3be023125bc5641ccd9632d2761675d7467eace9ab515ac1d299cd73ce",
    "OE_single_texto.json": "b6a43961295cc2ca374a326446512c4076442a21a970d3e256b01eed628d839a",
    "OE_stacked_texto.json": "c34a222ae2af05a0b5335b774cb7fb45f14064cc17234d9d885e809fb29b6f45",
    "OE_texto.json": "54c83faadd41bd86177006c5d7dc85e2145fa35f4bf98450870598bff70f23e9",
    "provenance.json": "c8101900bc76cf40952a93c68c904b0b5de62c2e79d2c9985250edc13bee1c33",
}

COPIES = {
    "OE_bt_texto.json": BT / "OE_bt_origv_sentences_en_texto.json",
    "OE_bt_modifications.jsonl": BT / "OE_bt_origv_sentences_modifications.jsonl",
    "OE_stacked_P_exclusion.json": BT / "OE_stacked_P_exclusion.json",
    "OE_known_drift_rewrites.json": BT / "OE_known_drift_rewrites.json",
}


def check_baseline() -> None:
    for name, sha in BASELINE.items():
        if sha and audit.sha256_file(HANDOFF / name) != sha:
            raise SystemExit(f"{name} cambió respecto a la línea base de T0")


def main() -> int:
    cfg = yaml.safe_load((REPO / "configs/synthetic/bt_OE.yaml").read_text(encoding="utf-8"))
    check_baseline()
    for dst in COPIES:
        if (HANDOFF / dst).exists() and audit.sha256_file(HANDOFF / dst) != audit.sha256_file(COPIES[dst]):
            raise SystemExit(f"{dst} ya existe en handoff_OE con otro contenido")
    for dst, src in COPIES.items():
        shutil.copyfile(src, HANDOFF / dst)

    recs = json.loads((HANDOFF / "OE_bt_texto.json").read_text(encoding="utf-8"))
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    b, v, s = cfg["bt"], cfg["bt_values"], cfg["bt_sentences"]
    provenance = {
        "request": "BT sobre STACKED, opción A (handoff 2026-10-04); rediseños tras CP2 y CP4 decididos por César",
        "script": "scripts/build_bt_sentences.py --assemble (empaquetado: scripts/package_bt_handoff.py)",
        "commit": commit,
        "packaged_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": cfg["seed"],
        "source": "TEXTO gold de las hojas de STACKED-P (OE_stacked_P_keys.json)",
        "unit": "frase; por frase, la primera traducción aprobada o la frase original",
        "chains": s["chains"],
        "models": {"es-en": f"{b['model_es_en']}@{b['revision_es_en']}",
                   "en-es": f"{b['model_en_es']}@{b['revision_en_es']}",
                   **{k: f"{m}@{r}" for k, (m, r) in v["models"].items() if k != "es-en"}},
        "licenses": v["licenses"],
        "decoding": b["decoding"],
        "masking": {"strategy": b["mask_strategy"],
                    "masked": "valores de eje, fragmentos L2, cantidades, bandas, siglas"},
        "glossary": {"restoration": "posterior (restore_terms)",
                     "terms": list(b["glossary"]) + list(s["extra_glossary"]),
                     "synonyms": s["glossary_alternatives"], "synonym_probability": s["glossary_probability"]},
        "values": {"approved": v["approved"], "label_probability": v["label_probability"],
                   "rule": "siempre que haya variante aprobada"},
        "audits": {
            "sentences": "agentes con contexto limpio, 281 pares frase/candidata, 107 aprobados",
            "values": "agentes, 218 variantes aprobadas (muestra de César pendiente)",
            "glossary": "agentes en tres rondas + decisiones de César, 122 alternativas",
        },
        "verification": "estructural sin LLM: máscaras y orden de valores, G0, G1, G3, G6",
        "counts": {"queries": len(recs), "concepts": len({r["parent_key"] for r in recs}),
                   "with_value_bt": sum("value_back_translation" in r["modification_types"] for r in recs),
                   "with_glossary_synonym": sum("glossary_synonym" in r["modification_types"] for r in recs)},
        "reproducibility": "doble ejecución en modo replay con sha256 idénticos; cachés en data/synthetic/bt_OE/cache*",
        "inputs_sha256": {
            "OE_texto.json": BASELINE["OE_texto.json"],
            "OE_stacked_texto.json": BASELINE["OE_stacked_texto.json"],
            "OE_stacked_P_keys.json": audit.sha256_file(BT / "OE_stacked_P_keys.json"),
            "OE_2026_stage.json": audit.sha256_file(REPO / cfg["stage_json"]),
            "OE_glossary_approved.json": audit.sha256_file(REPO / s["glossary_alternatives"]),
            "OE_bt_value_approved.json": audit.sha256_file(REPO / v["approved"]),
            "OE_bt_origv_sentence_verdicts.jsonl": audit.sha256_file(REPO / s["verdicts"]),
        },
        "files": {name: audit.sha256_file(HANDOFF / name) for name in COPIES},
    }
    audit.write_atomic(HANDOFF / "OE_bt_provenance.json",
                       json.dumps(provenance, ensure_ascii=False, indent=1) + "\n")
    check_baseline()
    for name in [*COPIES, "OE_bt_provenance.json"]:
        p = HANDOFF / name
        print(f"{name}\t{p.stat().st_size}\t{audit.sha256_file(p)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
