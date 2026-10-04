# Auditoría de STACKED → STACKED-P (OE)

Entrada: `OE_stacked_texto.json` (sha256 `c34a222ae2af05a0b5335b774cb7fb45f14064cc17234d9d885e809fb29b6f45`) y su sidecar. Determinista, sin LLM (CP2). Filtros en orden: alineación de la plantilla, lista de derivas conocidas, verificador estructural (G0, G1 contra el gold con las conversiones registradas, G3, G6) y duplicados dentro de STACKED.

- Consultas: 4998.
- **STACKED-P (aceptadas): 4674 (93.5 %).**
- Excluidas: 324 (6.5 %).
- Derivas conocidas: 14 reescrituras distintas en 321 consultas. La cota inferior del análisis previo era 323.

## Exclusiones por filtro

| Filtro | Consultas |
|---|---:|
| DRIFT | 321 |
| G6 | 2 |
| G1 | 1 |

## Por filtro y motivo

| Filtro · motivo | Consultas |
|---|---:|
| DRIFT · known_drift | 321 |
| G6 · duplicate_of_delivered | 2 |
| G1 · extra | 1 |

## Por reescritura de origen

| Tipo | Consultas |
|---|---:|
| paraphrase | 198 |
| expansion | 123 |
| template_paraphrase | 3 |
| num_to_text | 1 |
| synonym_label | 1 |

## Lista de derivas conocidas (exclusión)

| Tipo | Original | Nuevo | Consultas |
|---|---|---|---:|
| expansion | en cruce bajo vías ejecutado con topo | en cruce bajo vías ejecutado con topografía detallada para asegurar la compatibilidad con las especificaciones técnicas | 20 |
| expansion | en cruce bajo vías ejecutado con topo | en cruce bajo vías ejecutado con topografía detallada para garantizar la correcta integración estructural | 21 |
| expansion | en cruce bajo vías ejecutado con topo | en cruce bajo vías ejecutado con topografía exacta para facilitar la instalación sin afectar el tráfico ferroviario | 20 |
| expansion | en cruce bajo vías ejecutado con topo | en cruce bajo vías ejecutado con topografía meticulosa para minimizar interferencias con la infraestructura ferroviaria | 21 |
| expansion | en cruce bajo vías ejecutado con topo | en cruce bajo vías ejecutado con topografía precisa para asegurar alineación y nivelación adecuadas | 21 |
| expansion | en cruce bajo vías ejecutado con topo | en cruce bajo vías ejecutado con topografía precisa para optimizar el uso del espacio disponible | 20 |
| paraphrase | adosada o superficial | empotrada o a nivel | 24 |
| paraphrase | adosada o superficial | empotrada o a ras | 25 |
| paraphrase | adosada o superficial | incrustada o a nivel | 25 |
| paraphrase | adosada o superficial | incrustada o a nivel del suelo | 25 |
| paraphrase | adosada o superficial | integrada o a ras | 25 |
| paraphrase | adosada o superficial | integrada o a ras del suelo | 24 |
| paraphrase | en cruce bajo vías ejecutado con topo | en intersección subterránea de vías con topografía | 25 |
| paraphrase | en cruce bajo vías ejecutado con topo | en intersección subvial de vías con topografía | 25 |

## Por concepto

| Concepto | Excluidas | Total | % |
|---|---:|---:|---:|
| OEB280$ | 54 | 451 | 12.0 % |
| OEB230$ | 52 | 451 | 11.5 % |
| OEB030$ | 50 | 451 | 11.1 % |
| OEB290$ | 44 | 451 | 9.8 % |
| OEB300$ | 43 | 451 | 9.5 % |
| OEB020$ | 42 | 328 | 12.8 % |
| OEB040$ | 36 | 451 | 8.0 % |
| OEB310$ | 1 | 1 | 100.0 % |
| OEG010$ | 1 | 19 | 5.3 % |
| OEG030$ | 1 | 2 | 50.0 % |

## Ficheros

| Fichero | sha256 |
|---|---|
| `OE_stacked_characterization.jsonl` | `72d86a27776332988983cfdd8d0282f82cd03474dd58f20e018690b072f14ee9` |
| `OE_stacked_P_keys.json` | `e7b894bc93881a80b1eedd9ed70faa11676e6cff790d07e4e0906ff3481a1118` |
| `OE_stacked_P_exclusion.json` | `bbe36522fdccb4fabb526a8ee029ccd5494c2f60c4b5dd87d036ab3e3f9c69c1` |
| `OE_known_drift_rewrites.json` | `1431f19dfb4791f22ac4a1b8be6779ff6f6d0fe89c12362932474d6cae0dc759` |
