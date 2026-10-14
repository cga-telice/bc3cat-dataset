# Piloto de BT sobre STACKED-P (OE)

Pivote EN, MarianMT (`Helsinki-NLP/opus-mt-es-en@c96e2c5`, `Helsinki-NLP/opus-mt-en-es@5bc4493`), beam 4 sin muestreo, máscara `bracket`. Valores de eje y fragmentos L2 enmascarados; verificación estructural sin LLM. Commit `8bedcd6`.

| Métrica | Valor | Umbral |
|---|---:|---|
| Aceptación `stacked_bt_en` | 294/300 (98.0 %) | ≥ 80 % → cumple |
| Aceptación `bt_orig_en` | 296/300 (98.7 %) | se reporta |
| No-ops `stacked_bt_en` | 0 (0.0 %) | ≤ 10 % → cumple |
| Máscara perdida `stacked_bt_en` / `bt_orig_en` | 4 / 3 | se reporta |
| Valores cambiados de orden `stacked_bt_en` / `bt_orig_en` | 0 / 0 | se reporta |
| Mediana de distancia en tokens al gold, antes → después (`stacked_bt`) | 34.0 → 42.0 | se reporta |
| Mediana de distancia en tokens al gold, antes → después (`bt_orig`) | 0 → 19.0 | se reporta |
| BM25 Acc@1 de STACKED: aceptadas / muestra / todo STACKED-P | 24.1 / 23.7 / 23.6 % | diferencia ≤ 2 pp → +0.5 pp, cumple |
| BM25 Acc@1 de las consultas BT aceptadas | 28.9 % | se reporta |

## Rechazos por puerta

| Puerta | `stacked_bt_en` | `bt_orig_en` |
|---|---:|---:|
| BT | 4 | 3 |
| G1 | 2 | 1 |

## Rechazos por puerta, concepto, eje y motivo (`stacked_bt_en`, 25 primeros)

| Clave | Consultas |
|---|---:|
| BT OEC030$  mask_lost | 2 |
| G1 OEA070$  missing | 1 |
| BT OEB020$  mask_lost | 1 |
| G1 OEC120$  missing | 1 |
| BT OEC120$  mask_lost | 1 |

## Supervivencia de las modificaciones (G5, aceptadas `stacked_bt_en`)

| Tipo | Sobrevive | Revertido |
|---|---:|---:|
| compression | 82 | 1 |
| expansion | 93 | 0 |
| num_to_text | 35 | 0 |
| paraphrase | 100 | 0 |
| synonym_label | 285 | 0 |
| template_paraphrase | 290 | 4 |
| unit_conversion | 18 | 0 |
| unit_expansion | 26 | 0 |

## Aceptación por concepto (`stacked_bt_en`)

| Concepto | Aceptadas | Total |
|---|---:|---:|
| OEA040$ | 1 | 1 |
| OEA050$ | 3 | 3 |
| OEA070$ | 0 | 1 |
| OEA080$ | 4 | 4 |
| OEA090$ | 1 | 1 |
| OEA150$ | 1 | 1 |
| OEB020$ | 17 | 18 |
| OEB030$ | 26 | 26 |
| OEB040$ | 27 | 27 |
| OEB070$ | 1 | 1 |
| OEB090$ | 1 | 1 |
| OEB120$ | 1 | 1 |
| OEB170$ | 12 | 12 |
| OEB190$ | 3 | 3 |
| OEB200$ | 2 | 2 |
| OEB230$ | 26 | 26 |
| OEB250$ | 1 | 1 |
| OEB280$ | 26 | 26 |
| OEB290$ | 26 | 26 |
| OEB300$ | 26 | 26 |
| OEC010$ | 4 | 4 |
| OEC020$ | 4 | 4 |
| OEC030$ | 2 | 4 |
| OEC040$ | 3 | 3 |
| OEC070$ | 1 | 1 |
| OEC090$ | 1 | 1 |
| OEC100$ | 1 | 1 |
| OEC120$ | 1 | 3 |
| OED010$ | 10 | 10 |
| OED020$ | 10 | 10 |
| OED030$ | 4 | 4 |
| OED040$ | 5 | 5 |
| OED050$ | 3 | 3 |
| OED060$ | 3 | 3 |
| OED070$ | 2 | 2 |
| OED080$ | 5 | 5 |
| OED090$ | 4 | 4 |
| OED100$ | 4 | 4 |
| OED110$ | 1 | 1 |
| OED120$ | 1 | 1 |
| OED140$ | 3 | 3 |
| OED150$ | 1 | 1 |
| OED160$ | 10 | 10 |
| OED180$ | 2 | 2 |
| OEE010$ | 1 | 1 |
| OEG010$ | 1 | 1 |
| OEG020$ | 1 | 1 |
| OEG050$ | 1 | 1 |

## Ejemplos de rechazo (`stacked_bt_en`)

- **G1** `OEA070becb_syn_cdcff4e9449f` eje None · missing: missing=['PTR'] extra=[]
  - origen: Se procederá al suministro y montaje de Curvatura Direccional para canaleta composite-PTR, incluyendo los componentes para el cosido entre las mismas, de acuerdo con el ET 03.365.064.9.. Se establecerán el trabajo: Cualquier franja horaria, la banda de mantenimiento: Mantenimiento cada menos de tres horas y las condiciones de ejecución: Volumen escaso.
  - BT: El suministro y el montaje de Curvatura Direccional para canaletas compuestasPTR, incluidos los componentes para coser entre ellas, se llevarán a cabo de conformidad con ET 03.365.064.9. El trabajo se establecerá: Cualquier franja horaria, la banda de mantenimiento: Mantenimiento cada menos de tres horas y las condiciones de ejecución: Volumen escaso.
- **BT** `OEB020cafab_syn_a896ed307780` eje None · mask_lost
  - origen: Conducción enterrada de Número seis conductos de PVC de 110 mm de diámetro nominal en cualquier tipo de terreno, a excepción de roca, junto con el relleno y compactado de la zanja y el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos y el transporte y retirada de los productos al lugar de empleo. Trabajo: Cualquier franja horaria excepcional Banda de m
  - BT: Buried conduction of [1] nominal diameter [3] [2] ducts, together with the filling and compacting of the ditch and the supply and assembly of non-vibrating tubes and concrete [5], duct testing and the transport and removal of products to the place of use. Work: [6] Maintenance band: [7] Conditions of execution: [8]
- **BT** `OEC030debb_syn_778f53a9d453` eje None · mask_lost
  - origen: Se ofrece la arqueta de registro compuesta-PRFV modelo AFC-4, correspondiente a 90x81x100 centímetros de medidas interiores, con fondo y cama de arena, así como los taladros necesarios para la acometida de los tubos. Incluidas dos tapas de seguridad de chapa galvanizada adaptada para el cierre de seguridad (candado normalizado).. El trabajo que abarca: Horario Integral. La banda de mantenimiento s
  - BT: The model [2]-[3] composite record rack is offered for [4] [5]. The work covered: [6]. The maintenance band is defined as: [7]. The conditions for execution are expressed in: [8].
- **BT** `OEC030ebac_syn_96e4bc99dc24` eje None · mask_lost
  - origen: Arqueta de registro de composite-PRFV tipo AFC-5 para 130x90x100 centímetros de medidas interiores, con fondo y cama de arena, así como los taladros necesarios para la acometida de los tubos. Incluidas dos tapas de seguridad de chapa galvanizada adaptada para el cierre de seguridad (candado normalizado). Ejecución: Horario de Oscuridad Mantenimiento: i >= 5 horas Condiciones de aplicación: Cualqui
  - BT: Type [2]-[3] composite record rack for [4] [5] Execution: [6] Maintenance: [7] Conditions of application: [8]
- **G1** `OEC120dbdb_syn_38af00636a38` eje None · missing: missing=['PRFV'] extra=[]
  - origen: Trabajo: Horario de Oscuridad - Suministro y montaje de suplemento de arqueta de registro de composite-PRFV tipo SFC-7 de 170x81x70 centímetros existente, con condiciones de ejecución: Volumen escaso, y dentro de la banda de mantenimiento: No necesita intervalo
  - BT: Trabajo: Horario de Oscuridad - Suministro y montaje del tipo de registro compuesto existentePRFV SFC-7 de 170x81x70 centímetros, con condiciones de rendimiento: Volumen escaso, y dentro de la banda de mantenimiento: No necesita intervalo
