# Calibración del verificador de caracterización (OE)

Extractores: phi4:latest, qwen2.5:14b, temperatura 0, JSON estricto. Semilla 42, 8 hojas por concepto. sha256 de los casos: `eb654d0af345fc044a121d1051086e0529e65e7ae21a06fa5927b056f039c475`.

| Prueba | Casos | Aciertos | Tasa | Umbral | Resultado |
|---|---:|---:|---:|---:|---|
| Positivos (ejes de R(C)) | 2508 | 2458 | 98.01 % | ≥ 99.5 % | **no cumple** |
| Discriminación (hermanas) | 648 | 631 | 97.38 % | ≥ 99 % | **no cumple** |
| Ablación (los dos dan 0) | 637 | 245 | 38.46 % | ≥ 99 % | **no cumple** |
| Derivas conocidas (rechazo) | 321 | 294 | 91.59 % | ≥ 100 % | **no cumple** |
| Estabilidad (reproducción) | 2254 | 2254 | 100 % | 100 % | cumple |

Señales secundarias:

- Ejes fuera de R(C) sin valor ajeno al grupo D-031 del gold, en los positivos (los dos extractores): 19/24 (79.17 %).
- Ablación: el par no acepta el valor gold en 629/637 (98.74 %).
- Discriminación por distancia en tokens: 1 token(s): 637, 2 token(s): 7, 3 token(s): 3, 4 token(s): 1.

Por extractor:

| Prueba | Extractor | Aciertos | Tasa |
|---|---|---:|---:|
| positive | phi4:latest | 2501/2508 | 99.72 % |
| positive | qwen2.5:14b | 2464/2508 | 98.25 % |
| ablation | phi4:latest | 552/637 | 86.66 % |
| ablation | qwen2.5:14b | 274/637 | 43.01 % |

Fallos por prueba (primeros 15; todos en el JSON):

- **positive**: 50
  - `["OEA100ab", "A", {"phi4:latest": {"A": 1, "B": 2}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEA100ab", "B", {"phi4:latest": {"A": 1, "B": 2}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEB030dbbdc", "B", {"phi4:latest": {"A": 4, "B": 2, "C": 2, "D": 4, "F": 3}, "qwen2.5:14b": {"A": 4, "B": 7, "C": 2, "D": 4, "F": 3}}]`
  - `["OEB040jfebc", "B", {"phi4:latest": {"A": 10, "B": 6, "C": 5, "D": 2, "F": 3}, "qwen2.5:14b": {"A": 10, "B": 0, "C": 5, "D": 2, "F": 3}}]`
  - `["OEB040kbabb", "B", {"phi4:latest": {"A": 11, "B": 2, "C": 1, "D": 2, "F": 2}, "qwen2.5:14b": {"A": 11, "B": 7, "C": 1, "D": 2, "F": 2}}]`
  - `["OEB230kffab", "A", {"phi4:latest": {"A": 11, "B": 6, "C": 6, "D": 1, "F": 2}, "qwen2.5:14b": {"error": "not_letter: B='null'"}}]`
  - `["OEB230kffab", "B", {"phi4:latest": {"A": 11, "B": 6, "C": 6, "D": 1, "F": 2}, "qwen2.5:14b": {"error": "not_letter: B='null'"}}]`
  - `["OEB230kffab", "C", {"phi4:latest": {"A": 11, "B": 6, "C": 6, "D": 1, "F": 2}, "qwen2.5:14b": {"error": "not_letter: B='null'"}}]`
  - `["OEB230kffab", "D", {"phi4:latest": {"A": 11, "B": 6, "C": 6, "D": 1, "F": 2}, "qwen2.5:14b": {"error": "not_letter: B='null'"}}]`
  - `["OEB230kffab", "F", {"phi4:latest": {"A": 11, "B": 6, "C": 6, "D": 1, "F": 2}, "qwen2.5:14b": {"error": "not_letter: B='null'"}}]`
  - `["OEB240abc", "A", {"phi4:latest": {"A": 1, "B": 2, "C": 3}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEB240abc", "B", {"phi4:latest": {"A": 1, "B": 2, "C": 3}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEB240abc", "C", {"phi4:latest": {"A": 1, "B": 2, "C": 3}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEB250bbbeb", "A", {"phi4:latest": {"A": 2, "B": 2, "C": 2, "D": 5, "F": 2}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEB250bbbeb", "B", {"phi4:latest": {"A": 2, "B": 2, "C": 2, "D": 5, "F": 2}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
- **discrimination**: 17
  - `["OEA070abaa", "B", 1, {"phi4:latest": {"A": 1, "B": 2, "C": 1, "D": 1}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEA100ab", "B", 1, {"phi4:latest": {"A": 1, "B": 2}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEA100ab", "A", 1, {"phi4:latest": {"A": 1, "B": 2}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEB120bcba", "B", 1, {"phi4:latest": {"A": 2, "B": 3, "C": 2, "D": 1}, "qwen2.5:14b": {"A": 2, "B": 6, "C": 2, "D": 1}}]`
  - `["OEB230gffab", "A", 1, {"phi4:latest": {"A": 7, "B": 6, "C": 6, "D": 1, "F": 2}, "qwen2.5:14b": {"error": "not_letter: B='null'"}}]`
  - `["OEB240abb", "B", 1, {"phi4:latest": {"A": 1, "B": 2, "C": 2}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEB250bcaaa", "C", 1, {"phi4:latest": {"A": 2, "B": 3, "C": 1, "D": 1, "F": 1}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEB280ifbca", "A", 1, {"phi4:latest": {"A": 9, "B": 6, "C": 2, "D": 3, "F": 1}, "qwen2.5:14b": {"error": "not_letter: B='null'"}}]`
  - `["OEB290ifbab", "C", 1, {"phi4:latest": {"A": 9, "B": 6, "C": 2, "D": 1, "F": 2}, "qwen2.5:14b": {"error": "not_letter: B='null'"}}]`
  - `["OEC040cbcba", "C", 1, {"phi4:latest": {"A": 3, "B": 2, "C": 3, "D": 2, "F": 1}, "qwen2.5:14b": {"A": 3, "B": 2, "C": 6, "D": 2, "F": 1}}]`
  - `["OEC100abcb", "D", 1, {"phi4:latest": {"A": 1, "B": 2, "C": 3, "D": 2}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OED010ccbac", "B", 1, {"phi4:latest": {"A": 3, "B": 10, "C": 2, "D": 1, "F": 3}, "qwen2.5:14b": {"error": "not_letter: B='d4'"}}]`
  - `["OED020aabaa", "B", 1, {"phi4:latest": {"A": 1, "B": 1, "C": 2, "D": 1, "F": 1}, "qwen2.5:14b": {"error": "not_letter: B='t1'"}}]`
  - `["OED020bccac", "B", 1, {"phi4:latest": {"error": "not_letter: B='t3'"}, "qwen2.5:14b": {"A": 2, "B": 3, "C": 3, "D": 1, "F": 3}}]`
  - `["OED160accab", "B", 1, {"phi4:latest": {"A": 1, "B": 10, "C": 3, "D": 1, "F": 2}, "qwen2.5:14b": {"A": 1, "B": 3, "C": 3, "D": 1, "F": 2}}]`
- **ablation**: 392
  - `["OEA010aabc", "D", {"phi4:latest": {"A": 1, "B": 1, "C": 2, "D": 0}, "qwen2.5:14b": {"A": 1, "B": 1, "C": 2, "D": 3}}]`
  - `["OEA010abca", "D", {"phi4:latest": {"A": 1, "B": 2, "C": 3, "D": 0}, "qwen2.5:14b": {"A": 1, "B": 2, "C": 3, "D": 3}}]`
  - `["OEA010abcb", "B", {"phi4:latest": {"A": 1, "B": 0, "C": 3, "D": 2}, "qwen2.5:14b": {"A": 1, "B": 3, "C": 3, "D": 2}}]`
  - `["OEA010bbba", "B", {"phi4:latest": {"A": 2, "B": 0, "C": 2, "D": 1}, "qwen2.5:14b": {"A": 2, "B": 3, "C": 2, "D": 1}}]`
  - `["OEA010bcba", "D", {"phi4:latest": {"A": 2, "B": 3, "C": 2, "D": 0}, "qwen2.5:14b": {"A": 2, "B": 3, "C": 2, "D": 3}}]`
  - `["OEA010bcbb", "D", {"phi4:latest": {"A": 2, "B": 3, "C": 2, "D": 0}, "qwen2.5:14b": {"A": 2, "B": 3, "C": 2, "D": 3}}]`
  - `["OEA020bab", "A", {"phi4:latest": {"A": 0, "B": 1, "C": 2}, "qwen2.5:14b": {"A": 5, "B": 1, "C": 2}}]`
  - `["OEA020dbc", "A", {"phi4:latest": {"A": 5, "B": 2, "C": 3}, "qwen2.5:14b": {"A": 5, "B": 2, "C": 3}}]`
  - `["OEA020dca", "A", {"phi4:latest": {"A": 0, "B": 3, "C": 1}, "qwen2.5:14b": {"A": 5, "B": 3, "C": 1}}]`
  - `["OEA020ddb", "A", {"phi4:latest": {"A": 0, "B": 4, "C": 2}, "qwen2.5:14b": {"error": "missing_axis: A"}}]`
  - `["OEA020eaa", "A", {"phi4:latest": {"A": 0, "B": 1, "C": 1}, "qwen2.5:14b": {"A": 5, "B": 1, "C": 1}}]`
  - `["OEA020eac", "A", {"phi4:latest": {"A": 5, "B": 1, "C": 3}, "qwen2.5:14b": {"A": 5, "B": 1, "C": 3}}]`
  - `["OEA030aab", "A", {"phi4:latest": {"A": 0, "B": 1, "C": 2}, "qwen2.5:14b": {"A": 5, "B": 1, "C": 2}}]`
  - `["OEA030bcc", "B", {"phi4:latest": {"A": 2, "B": 0, "C": 3}, "qwen2.5:14b": {"A": 2, "B": 4, "C": 3}}]`
  - `["OEA030bdb", "B", {"phi4:latest": {"A": 2, "B": 4, "C": 2}, "qwen2.5:14b": {"A": 2, "B": 4, "C": 2}}]`
- **drift**: 27
  - `"OEB030chddb_syn_c1e2478be99d"`
  - `"OEB030dhbba_syn_273f218857a7"`
  - `"OEB030ihdcc_syn_3493296d4c46"`
  - `"OEB030khbca_syn_3070e6be7874"`
  - `"OEB040bhdac_syn_c87f3671fc7c"`
  - `"OEB040dhaaa_syn_bc9a1fc1b518"`
  - `"OEB040fhbba_syn_5b00c2f8a27b"`
  - `"OEB040ghacb_syn_c7553359031d"`
  - `"OEB230aheac_syn_831194023060"`
  - `"OEB230bhebc_syn_9c079816c09f"`
  - `"OEB230dheba_syn_fea0c83c82ad"`
  - `"OEB230fhdda_syn_f796b2bb1e18"`
  - `"OEB280bhbcb_syn_95269b5138c4"`
  - `"OEB280bhfbc_syn_7bb1b60f913d"`
  - `"OEB280chcac_syn_c732ddc47ed3"`
