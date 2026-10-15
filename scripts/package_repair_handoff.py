"""Entrega aditiva de la v2 (paráfrasis rotas corregidas) a ``handoff_OE/``.

Copia los cuatro conjuntos v2 y el registro de cambios, escribe
``OE_v2_provenance.json`` y comprueba antes y después que ningún fichero ya
entregado cambia (línea base de T0 más la entrega BT del 2026-10-16).
MANIFEST.md y README.md se amplían a mano (solo se añaden líneas).

  PYTHONPATH=src python scripts/package_repair_handoff.py
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

import package_bt_handoff as bt  # noqa: E402

HANDOFF = bt.HANDOFF
SRC = REPO / "data" / "synthetic" / "broken_OE"
DELIVERED = {**bt.BASELINE,
             "OE_bt_texto.json": "421b3ca3a3d3f61f26d4653b3f84e4a614ff2dc6ade7acfb4a8f3da1da7d408c",
             "OE_bt_modifications.jsonl": "c1ffe3bfafa2736dcc7ab2444bfdedc046fc0a42a3ac9e7ffa14f715b109738a",
             "OE_bt_provenance.json": "d17653030a0b0cc320babffad9e0322a3259bc9ee07db608b97751516da01f33",
             "OE_stacked_P_exclusion.json": "bbe36522fdccb4fabb526a8ee029ccd5494c2f60c4b5dd87d036ab3e3f9c69c1",
             "OE_known_drift_rewrites.json": "1431f19dfb4791f22ac4a1b8be6779ff6f6d0fe89c12362932474d6cae0dc759"}
COPIES = {f"OE_{s}_texto_v2.json": SRC / f"OE_{s}_texto_v2.json"
          for s in ("stacked", "single", "dose", "isolated")}
COPIES["OE_v2_changes.jsonl"] = SRC / "OE_paraphrase_repair_changes.jsonl"


def check() -> None:
    for name, sha in DELIVERED.items():
        if sha and bt.audit.sha256_file(HANDOFF / name) != sha:
            raise SystemExit(f"{name} cambió")


def main() -> int:
    check()
    for dst, src in COPIES.items():
        if (HANDOFF / dst).exists() and bt.audit.sha256_file(HANDOFF / dst) != bt.audit.sha256_file(src):
            raise SystemExit(f"{dst} ya existe con otro contenido")
    for dst, src in COPIES.items():
        shutil.copyfile(src, HANDOFF / dst)
    changes = [json.loads(l) for l in (HANDOFF / "OE_v2_changes.jsonl").read_text(encoding="utf-8").splitlines()]
    verif = [json.loads(l) for l in (SRC / "OE_paraphrase_repair_verification.jsonl").read_text(encoding="utf-8").splitlines()]
    provenance = {
        "request": "César 2026-10-16: corregir paráfrasis de plantilla con hueco reasignado o valor "
                   "tratado como referencia; dejar unidades duplicadas, gramática y significado",
        "script": "scripts/repair_broken_paraphrases.py (empaquetado: scripts/package_repair_handoff.py)",
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "packaged_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "audit": "828 paráfrasis TEXTO usadas, 8 agentes con contexto limpio "
                 "(data/synthetic/broken_OE/OE_template_paraphrase_audit.jsonl)",
        "repaired": {"paraphrases": 163, "reasignacion": 134, "referencia": 29,
                     "file": "data/synthetic/broken_OE/OE_template_paraphrase_repairs.json"},
        "method": "alineación con la paráfrasis rota y nuevo renderizado con la corregida; "
                  "espacios normalizados en las consultas cambiadas; el resto byte a byte igual",
        "verification": {"repairs": len(verif), "resolved_hueco_o_referencia": len(verif),
                         "new_errors": sum(v["nuevo_error"] for v in verif),
                         "note": "11 conservan defectos de significado que se decidió dejar"},
        "changed_queries": {s: sum(c["set"] == s for c in changes)
                            for s in ("stacked", "single", "dose", "isolated")},
        "unchanged": "ids, item_key, gold_item_key y demás campos idénticos; STACKED-P sigue valiendo "
                     "para la v2 (mismos item_key)",
        "inputs_sha256": {f"OE_{s}_texto.json": DELIVERED[f"OE_{s}_texto.json"]
                          for s in ("stacked", "single", "dose", "isolated")},
        "files": {name: bt.audit.sha256_file(HANDOFF / name) for name in COPIES},
    }
    bt.audit.write_atomic(HANDOFF / "OE_v2_provenance.json",
                          json.dumps(provenance, ensure_ascii=False, indent=1) + "\n")
    check()
    for name in [*COPIES, "OE_v2_provenance.json"]:
        p = HANDOFF / name
        print(f"{name}\t{p.stat().st_size}\t{bt.audit.sha256_file(p)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
