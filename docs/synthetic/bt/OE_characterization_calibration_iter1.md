# Calibración del verificador de caracterización (OE)

Extractores: phi4:latest, qwen2.5:14b, temperatura 0, JSON estricto. Semilla 42, 8 hojas por concepto. sha256 de los casos: `9d950dc3298d608d06f739a40f235505d0b9061549046bbfc867e4b3ae8823d3`.

| Prueba | Casos | Aciertos | Tasa | Umbral | Resultado |
|---|---:|---:|---:|---:|---|
| Positivos (ejes de R(C)) | 2508 | 2480 | 98.88 % | ≥ 99.5 % | **no cumple** |
| Discriminación (hermanas) | 648 | 633 | 97.69 % | ≥ 99 % | **no cumple** |
| Ablación (los dos dan 0) | 637 | 95 | 14.91 % | ≥ 99 % | **no cumple** |
| Derivas conocidas (rechazo) | 321 | 292 | 90.97 % | ≥ 100 % | **no cumple** |
| Estabilidad (reproducción) | 2254 | 2254 | 100 % | 100 % | cumple |

Señales secundarias:

- Ejes fuera de R(C) a 0 en los positivos (los dos extractores): 0/24 (0.00 %).
- Ablación: el par no acepta el valor gold en 532/637 (83.52 %).
- Discriminación por distancia en tokens: 1 token(s): 637, 2 token(s): 7, 3 token(s): 3, 4 token(s): 1.

Por extractor:

| Prueba | Extractor | Aciertos | Tasa |
|---|---|---:|---:|
| positive | phi4:latest | 2503/2508 | 99.80 % |
| positive | qwen2.5:14b | 2485/2508 | 99.08 % |
| ablation | phi4:latest | 168/637 | 26.37 % |
| ablation | qwen2.5:14b | 112/637 | 17.58 % |

Fallos por prueba (primeros 15; todos en el JSON):

- **positive**: 28
  - `["OEA030cac", "A", {"phi4:latest": {"A": 3, "B": 1, "C": 3}, "qwen2.5:14b": {"A": 6, "B": 1, "C": 3}}]`
  - `["OEA030ccc", "A", {"phi4:latest": {"A": 3, "B": 3, "C": 3}, "qwen2.5:14b": {"A": 6, "B": 3, "C": 3}}]`
  - `["OEA090cbca", "A", {"phi4:latest": {"A": 3, "B": 2, "C": 3, "D": 1}, "qwen2.5:14b": {"A": 4, "B": 2, "C": 3, "D": 1}}]`
  - `["OEA100aa", "A", {"phi4:latest": {"A": 1, "B": 1}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEA100aa", "B", {"phi4:latest": {"A": 1, "B": 1}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEA100ab", "A", {"phi4:latest": {"A": 1, "B": 2}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEA100ab", "B", {"phi4:latest": {"A": 1, "B": 2}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEA120cbc", "A", {"phi4:latest": {"A": 3, "B": 2, "C": 3}, "qwen2.5:14b": {"A": 4, "B": 2, "C": 3}}]`
  - `["OEB020cbecc", "B", {"phi4:latest": {"A": 3, "B": 2, "C": 5, "D": 3, "F": 3}, "qwen2.5:14b": {"A": 3, "B": 7, "C": 5, "D": 3, "F": 3}}]`
  - `["OEB040kbabb", "B", {"phi4:latest": {"A": 11, "B": 2, "C": 1, "D": 2, "F": 2}, "qwen2.5:14b": {"A": 11, "B": 7, "C": 1, "D": 2, "F": 2}}]`
  - `["OEB110cba", "A", {"phi4:latest": {"A": 3, "B": 2, "C": 1}, "qwen2.5:14b": {"A": 4, "B": 2, "C": 1}}]`
  - `["OEB150ccc", "A", {"phi4:latest": {"A": 3, "B": 3, "C": 3}, "qwen2.5:14b": {"A": 4, "B": 3, "C": 3}}]`
  - `["OEB180cda", "A", {"phi4:latest": {"A": 3, "B": 4, "C": 1}, "qwen2.5:14b": {"A": 6, "B": 4, "C": 1}}]`
  - `["OEB310b", "A", {"phi4:latest": {"A": 1}, "qwen2.5:14b": {"A": 2}}]`
  - `["OEC090baab", "A", {"phi4:latest": {"A": 2, "B": 1, "C": 1, "D": 2}, "qwen2.5:14b": {"A": 0, "B": 1, "C": 1, "D": 2}}]`
- **discrimination**: 15
  - `["OEA020cbc", "A", 1, {"phi4:latest": {"A": 3, "B": 2, "C": 3}, "qwen2.5:14b": {"A": 4, "B": 2, "C": 3}}]`
  - `["OEA030cac", "A", 1, {"phi4:latest": {"A": 3, "B": 1, "C": 3}, "qwen2.5:14b": {"A": 6, "B": 1, "C": 3}}]`
  - `["OEA100ab", "B", 1, {"phi4:latest": {"A": 1, "B": 2}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEA100ab", "A", 1, {"phi4:latest": {"A": 1, "B": 2}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEB020acbbc", "A", 1, {"phi4:latest": {"A": 2, "B": 3, "C": 2, "D": 2, "F": 3}, "qwen2.5:14b": {"A": 1, "B": 3, "C": 2, "D": 2, "F": 3}}]`
  - `["OEB100cdc", "A", 1, {"phi4:latest": {"A": 3, "B": 4, "C": 3}, "qwen2.5:14b": {"A": 6, "B": 4, "C": 3}}]`
  - `["OEB150cbc", "A", 1, {"phi4:latest": {"A": 3, "B": 2, "C": 3}, "qwen2.5:14b": {"A": 4, "B": 2, "C": 3}}]`
  - `["OEB310b", "A", 2, {"phi4:latest": {"A": 1}, "qwen2.5:14b": {"A": 2}}]`
  - `["OEB310b", "A", 1, {"phi4:latest": {"A": 1}, "qwen2.5:14b": {"A": 2}}]`
  - `["OEC090bfba", "A", 1, {"phi4:latest": {"A": 2, "B": 6, "C": 2, "D": 1}, "qwen2.5:14b": {"A": 0, "B": 6, "C": 2, "D": 1}}]`
  - `["OED010ccbac", "B", 1, {"phi4:latest": {"A": 3, "B": 3, "C": 2, "D": 1, "F": 3}, "qwen2.5:14b": {"A": 3, "B": 4, "C": 2, "D": 1, "F": 3}}]`
  - `["OED040cicbc", "B", 1, {"phi4:latest": {"A": 3, "B": 9, "C": 3, "D": 2, "F": 3}, "qwen2.5:14b": {"A": 3, "B": 8, "C": 3, "D": 2, "F": 3}}]`
  - `["OED040cibcc", "B", 1, {"phi4:latest": {"A": 3, "B": 9, "C": 2, "D": 3, "F": 3}, "qwen2.5:14b": {"A": 3, "B": 8, "C": 2, "D": 3, "F": 3}}]`
  - `["OED160accab", "B", 1, {"phi4:latest": {"A": 1, "B": 3, "C": 3, "D": 1, "F": 2}, "qwen2.5:14b": {"A": 1, "B": 4, "C": 3, "D": 1, "F": 2}}]`
  - `["OED160acadc", "B", 1, {"phi4:latest": {"A": 1, "B": 4, "C": 1, "D": 4, "F": 3}, "qwen2.5:14b": {"A": 1, "B": 3, "C": 1, "D": 4, "F": 3}}]`
- **ablation**: 542
  - `["OEA010aabc", "D", {"phi4:latest": {"A": 1, "B": 1, "C": 2, "D": 3}, "qwen2.5:14b": {"A": 1, "B": 1, "C": 2, "D": 3}}]`
  - `["OEA010abca", "D", {"phi4:latest": {"A": 1, "B": 2, "C": 3, "D": 0}, "qwen2.5:14b": {"A": 1, "B": 2, "C": 3, "D": 3}}]`
  - `["OEA010abcb", "B", {"phi4:latest": {"A": 1, "B": 3, "C": 3, "D": 2}, "qwen2.5:14b": {"A": 1, "B": 1, "C": 3, "D": 2}}]`
  - `["OEA010bacb", "C", {"phi4:latest": {"A": 2, "B": 1, "C": 4, "D": 2}, "qwen2.5:14b": {"A": 2, "B": 1, "C": 4, "D": 2}}]`
  - `["OEA010bbba", "B", {"phi4:latest": {"A": 2, "B": 3, "C": 2, "D": 1}, "qwen2.5:14b": {"A": 2, "B": 3, "C": 2, "D": 1}}]`
  - `["OEA010bcac", "C", {"phi4:latest": {"A": 2, "B": 3, "C": 4, "D": 3}, "qwen2.5:14b": {"A": 2, "B": 3, "C": 4, "D": 3}}]`
  - `["OEA010bcba", "D", {"phi4:latest": {"A": 2, "B": 3, "C": 2, "D": 3}, "qwen2.5:14b": {"A": 2, "B": 3, "C": 2, "D": 3}}]`
  - `["OEA010bcbb", "D", {"phi4:latest": {"A": 2, "B": 3, "C": 2, "D": 3}, "qwen2.5:14b": {"A": 2, "B": 3, "C": 2, "D": 3}}]`
  - `["OEA020baa", "B", {"phi4:latest": {"A": 2, "B": 4, "C": 1}, "qwen2.5:14b": {"A": 2, "B": 4, "C": 1}}]`
  - `["OEA020bab", "A", {"phi4:latest": {"A": 5, "B": 1, "C": 2}, "qwen2.5:14b": {"A": 5, "B": 1, "C": 2}}]`
  - `["OEA020dbc", "A", {"phi4:latest": {"A": 5, "B": 2, "C": 3}, "qwen2.5:14b": {"A": 5, "B": 2, "C": 3}}]`
  - `["OEA020dca", "A", {"phi4:latest": {"A": 5, "B": 3, "C": 1}, "qwen2.5:14b": {"A": 1, "B": 3, "C": 1}}]`
  - `["OEA020ddb", "A", {"phi4:latest": {"A": 5, "B": 4, "C": 2}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEA020eaa", "A", {"phi4:latest": {"A": 5, "B": 1, "C": 1}, "qwen2.5:14b": {"A": 5, "B": 1, "C": 1}}]`
  - `["OEA020eac", "A", {"phi4:latest": {"A": 5, "B": 1, "C": 3}, "qwen2.5:14b": {"A": 5, "B": 1, "C": 3}}]`
- **drift**: 29
  - `"OEB020dheac_syn_5bf7c0580f38"`
  - `"OEB020fhfaa_syn_fd5acdd9ca5e"`
  - `"OEB020hhabc_syn_10abac34922e"`
  - `"OEB020hhedb_syn_21436b5704d3"`
  - `"OEB030chddb_syn_c1e2478be99d"`
  - `"OEB030dhbba_syn_273f218857a7"`
  - `"OEB030fheda_syn_9cbb1dca89ee"`
  - `"OEB030ghcdb_syn_7d64b4c45eb2"`
  - `"OEB030ihdcc_syn_3493296d4c46"`
  - `"OEB030khbca_syn_3070e6be7874"`
  - `"OEB040bhdac_syn_c87f3671fc7c"`
  - `"OEB040dhaaa_syn_bc9a1fc1b518"`
  - `"OEB040fhbba_syn_5b00c2f8a27b"`
  - `"OEB040gheba_syn_0aee0c751d40"`
  - `"OEB230ahcdb_syn_b528725c8d25"`
