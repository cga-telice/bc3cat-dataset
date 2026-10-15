# QA de la BT de prosa + valores sobre STACKED-P (OE)

Pivote EN, MarianMT (`Helsinki-NLP/opus-mt-es-en@c96e2c5`, `Helsinki-NLP/opus-mt-en-es@5bc4493`), beam 4 sin muestreo, máscara `bracket`. Valores de eje y fragmentos L2 enmascarados; verificación estructural sin LLM. Commit `0502b2f`.

| Métrica | Valor | Umbral |
|---|---:|---|
| Aceptación `stacked_btv_en` | 4566/4674 (97.7 %) | ≥ 80 % → cumple |
| Aceptación `bt_origv_en` | 4613/4674 (98.7 %) | se reporta |
| No-ops `stacked_btv_en` | 0 (0.0 %) | ≤ 10 % → cumple |
| Máscara perdida `stacked_btv_en` / `bt_origv_en` | 74 / 44 | se reporta |
| Valores cambiados de orden `stacked_btv_en` / `bt_origv_en` | 4 / 0 | se reporta |
| Mediana de distancia en tokens al gold, antes → después (`stacked_btv`) | 34.0 → 43.0 | se reporta |
| Mediana de distancia en tokens al gold, antes → después (`bt_origv`) | 0 → 22 | se reporta |
| BM25 Acc@1 de STACKED: aceptadas / muestra / todo STACKED-P | 23.7 / 23.6 / 23.6 % | diferencia ≤ 2 pp → +0.1 pp, cumple |
| BM25 Acc@1 de las consultas BT aceptadas | 20.4 % | se reporta |

## Rechazos por puerta

| Puerta | `stacked_btv_en` | `bt_origv_en` |
|---|---:|---:|
| BT | 78 | 44 |
| G1 | 30 | 15 |
| G6 | 0 | 2 |

## Rechazos por puerta, concepto, eje y motivo (`stacked_btv_en`, 25 primeros)

| Clave | Consultas |
|---|---:|
| BT OEB020$  mask_lost | 19 |
| BT OEC030$  mask_lost | 18 |
| BT OEC120$  mask_lost | 15 |
| G1 OEA070$  missing | 14 |
| BT OED020$  mask_lost | 11 |
| G1 OEC120$  missing | 8 |
| G1 OEC030$  missing | 5 |
| BT OED040$  value_order_changed | 4 |
| BT OEB300$  mask_lost | 3 |
| BT OED030$  mask_lost | 3 |
| G1 OEA040$  missing | 2 |
| BT OEB180$  mask_lost | 2 |
| BT OEB010$  mask_lost | 1 |
| G1 OEB070$  missing | 1 |
| BT OEB250$  mask_lost | 1 |
| BT OEC050$  mask_lost | 1 |

## Supervivencia de las modificaciones (G5, aceptadas `stacked_btv_en`)

| Tipo | Sobrevive | Revertido |
|---|---:|---:|
| compression | 1184 | 43 |
| expansion | 1447 | 0 |
| num_to_text | 596 | 0 |
| paraphrase | 1433 | 50 |
| synonym_label | 3991 | 66 |
| template_paraphrase | 4489 | 48 |
| unit_conversion | 210 | 0 |
| unit_expansion | 408 | 16 |

## Aceptación por concepto (`stacked_btv_en`)

| Concepto | Aceptadas | Total |
|---|---:|---:|
| OEA010$ | 5 | 5 |
| OEA020$ | 5 | 5 |
| OEA030$ | 5 | 5 |
| OEA040$ | 19 | 21 |
| OEA050$ | 41 | 41 |
| OEA060$ | 3 | 3 |
| OEA070$ | 1 | 15 |
| OEA080$ | 62 | 62 |
| OEA090$ | 10 | 10 |
| OEA100$ | 1 | 1 |
| OEA110$ | 1 | 1 |
| OEA120$ | 5 | 5 |
| OEA130$ | 5 | 5 |
| OEA140$ | 1 | 1 |
| OEA150$ | 21 | 21 |
| OEA160$ | 2 | 2 |
| OEA170$ | 5 | 5 |
| OEA180$ | 1 | 1 |
| OEB010$ | 0 | 1 |
| OEB020$ | 267 | 286 |
| OEB030$ | 401 | 401 |
| OEB040$ | 415 | 415 |
| OEB050$ | 1 | 1 |
| OEB070$ | 9 | 10 |
| OEB080$ | 1 | 1 |
| OEB090$ | 10 | 10 |
| OEB100$ | 5 | 5 |
| OEB110$ | 5 | 5 |
| OEB120$ | 15 | 15 |
| OEB130$ | 5 | 5 |
| OEB140$ | 5 | 5 |
| OEB150$ | 5 | 5 |
| OEB160$ | 1 | 1 |
| OEB170$ | 179 | 179 |
| OEB180$ | 3 | 5 |
| OEB190$ | 46 | 46 |
| OEB200$ | 31 | 31 |
| OEB230$ | 399 | 399 |
| OEB240$ | 2 | 2 |
| OEB250$ | 18 | 19 |
| OEB280$ | 397 | 397 |
| OEB290$ | 407 | 407 |
| OEB300$ | 405 | 408 |
| OEC010$ | 62 | 62 |
| OEC020$ | 56 | 56 |
| OEC030$ | 33 | 56 |
| OEC040$ | 51 | 51 |
| OEC050$ | 1 | 2 |
| OEC070$ | 10 | 10 |
| OEC080$ | 5 | 5 |
| OEC090$ | 10 | 10 |
| OEC100$ | 15 | 15 |
| OEC110$ | 5 | 5 |
| OEC120$ | 18 | 41 |
| OED010$ | 154 | 154 |
| OED020$ | 150 | 161 |
| OED030$ | 59 | 62 |
| OED040$ | 65 | 69 |
| OED050$ | 38 | 38 |
| OED060$ | 38 | 38 |
| OED070$ | 31 | 31 |
| OED080$ | 69 | 69 |
| OED090$ | 69 | 69 |
| OED100$ | 62 | 62 |
| OED110$ | 20 | 20 |
| OED120$ | 10 | 10 |
| OED130$ | 5 | 5 |
| OED140$ | 38 | 38 |
| OED150$ | 15 | 15 |
| OED160$ | 154 | 154 |
| OED180$ | 23 | 23 |
| OEE010$ | 8 | 8 |
| OEE020$ | 3 | 3 |
| OEE030$ | 3 | 3 |
| OEE040$ | 3 | 3 |
| OEF010$ | 3 | 3 |
| OEG010$ | 18 | 18 |
| OEG020$ | 20 | 20 |
| OEG030$ | 1 | 1 |
| OEG040$ | 2 | 2 |
| OEG050$ | 14 | 14 |

## Ejemplos de rechazo (`stacked_btv_en`)

- **G1** `OEA040aabab_syn_e111a0f6c17e` eje None · missing: missing=['PTR'] extra=[]
  - origen: Provisión e instalación de conducto enterrada con uno alveolo celdas de composite-PTR 1000x264x266 mm, incluyendo la nivelación de la solera, la cama de arena de río de 5 cm y el relleno del sellado de los laterales de la canaleta de hormigón pobre, conforme a la ET 03.365.064.9. Actividad: Horario de Noche Línea de servicio: Mantenimiento cada cinco horas o más Requisitos de ejecución: Volumen es
  - BT: Suministro e instalación de conducto Tipo: enterrada con Alveolos: un alveolo células compuestasPTR 1000x264x266 mm, incluyendo la nivelación de la solera, la cama de arena de río de 5 cm y el relleno del sellado de los laterales de la canaleta de hormigón pobre, de conformidad con ET 03.365.064.9. Actividad: Trabajo: Horario de Noche Línea de servicio: Banda de mantenimiento: Mantenimiento cada c
- **G1** `OEA040abfdb_syn_174f0afc6431` eje None · missing: missing=['PTR'] extra=[]
  - origen: Provisión e instalación de conducto enterrada con dos alveolos celdas de composite-PTR 1000x264x266 mm, incluyendo la nivelación de la solera, la cama de arena de río de 5 cm y el relleno del sellado de los laterales de la canaleta de hormigón pobre, conforme a la ET 03.365.064.9. Actividad: Cualquier franja horaria excepcional Línea de servicio: Mantenimiento Sin Paradas Requisitos de ejecución: 
  - BT: Suministro e instalación de conducto enterrada con dos alveolos células compuestasPTR 1000x264x266 mm, incluyendo la nivelación de la solera, la cama de arena de río de 5 cm y el relleno del sellado de los laterales de la canaleta de hormigón pobre, de conformidad con ET 03.365.064.9. Actividad: Cualquier intervalo de tiempo excepcional Línea de servicio: Banda de mantenimiento: Mantenimiento cont
- **G1** `OEA070abbb_syn_4303ec0ea2e9` eje None · missing: missing=['PTR'] extra=[]
  - origen: Suministro e instalación de Unión de Módulo, con canaleta composite-PTR, que incluye piezas para la unión entre ellas, y de acuerdo al ET 03.365.064.9.. Trabajo: Nocturno, banda de mantenimiento: Intervalo entre tres y cinco horas. Condiciones de ejecución: Volumen escaso.
  - BT: Suministro e instalación de Equipo: Unión de módulos con canal compuestoPTR, incluidas las partes para unirlas entre sí, y según ET 03.365.064.9. Trabajo: Nocturno, banda de mantenimiento: De tres a cinco horas. Condiciones de ejecución: Volumen bajo.
- **BT** `OEB010cbb_syn_bfd8a15b19d5` eje None · mask_lost
  - origen: Instalación de conducción subterránea para línea de doble circuito de 220 o 400 kV con cables encapsulados y conductos inyectados en hormigón HM-20, de dimensiones totales 2 m de ancho por 1,60 m de alto, con concreto extendido hasta profundidad 760 mm, seguido de relleno a compresión 95% P.M. Incluidos 2 ternas de conductos de polietileno (PE) de alta densidad de 250 mm de diámetro exterior para 
  - BT: Underground conduction installation for a double-circuit line of [1] or [2] with encapsulated cables and ducts injected into concrete [3], of total dimensions [4] wide by [5] high, with concrete extended to depth [6], followed by compression filling [7] [8] Including [9] high density [11] outer diameter polyethylene ducts for power cables; [12] double-layer [13] outer diameter polyethylene ducts f
- **BT** `OEB020bdbac_syn_77ed6f038574` eje None · mask_lost
  - origen: Conducción enterrada de Número cuatro conductos de PVC de 110 mm de diámetro nominal en cruce de carretera, manteniendo la integridad de la canalización en intersecciones viales, junto con la destrucción y la reinstalación del firme y del pavimento, el relleno y compactado de la zanja y el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos y el transport
  - BT: Buried conduction of [1] nominal diameter [3] [2] ducts, together with [5] filling and compacting of the ditch and supply and assembly of non-vibrating tubes and concrete [6], duct testing and transport and removal of products to the place of use. Work: [7] Maintenance band: [8] Conditions of execution: [9]
- **BT** `OEB020bebda_syn_d47c092ee538` eje None · mask_lost
  - origen: Conducción enterrada de Cuatro tubos conductos de PVC de 110 mm de diámetro nominal en área de andén, junto con la demolición y la reposición del pavimento y la solera, asegurando la compatibilidad de los materiales con las condiciones ambientales previstas, el relleno y compactado de la zanja y el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos y el 
  - BT: Buried conduction of [1] nominal diameter [3] [2] ducts, together with [5] filling and compacting of the ditch and supply and assembly of non-vibrating tubes and concrete [6], duct testing and transport and removal of products to the place of use. Work: [7] Maintenance band: [8] Conditions of execution: [9]
