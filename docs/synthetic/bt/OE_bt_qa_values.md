# QA de la BT de prosa + valores sobre STACKED-P (OE)

Pivote EN, MarianMT (`Helsinki-NLP/opus-mt-es-en@c96e2c5`, `Helsinki-NLP/opus-mt-en-es@5bc4493`), beam 4 sin muestreo, máscara `bracket`. Valores de eje y fragmentos L2 enmascarados; verificación estructural sin LLM. Commit `5ce7a17`.

| Métrica | Valor | Umbral |
|---|---:|---|
| Aceptación `stacked_btv_en` | 4577/4674 (97.9 %) | ≥ 80 % → cumple |
| Aceptación `bt_origv_en` | 4613/4674 (98.7 %) | se reporta |
| No-ops `stacked_btv_en` | 0 (0.0 %) | ≤ 10 % → cumple |
| Máscara perdida `stacked_btv_en` / `bt_origv_en` | 77 / 57 | se reporta |
| Valores cambiados de orden `stacked_btv_en` / `bt_origv_en` | 1 / 0 | se reporta |
| Mediana de distancia en tokens al gold, antes → después (`stacked_btv`) | 34 → 44 | se reporta |
| Mediana de distancia en tokens al gold, antes → después (`bt_origv`) | 0 → 24 | se reporta |

## Rechazos por puerta

| Puerta | `stacked_btv_en` | `bt_origv_en` |
|---|---:|---:|
| BT | 78 | 57 |
| G1 | 19 | 0 |
| G6 | 0 | 4 |

## Rechazos por puerta, concepto, eje y motivo (`stacked_btv_en`, 25 primeros)

| Clave | Consultas |
|---|---:|
| BT OEB020$  mask_lost | 24 |
| BT OEC030$  mask_lost | 18 |
| BT OED020$  mask_lost | 11 |
| BT OEC120$  mask_lost | 9 |
| G1 OEC030$  missing | 8 |
| G1 OEA070$  missing | 6 |
| BT OEB300$  mask_lost | 3 |
| G1 OEA040$  missing | 2 |
| BT OEB180$  mask_lost | 2 |
| G1 OEC120$  missing | 2 |
| BT OED070$  mask_lost | 2 |
| BT OEA090$  mask_lost | 1 |
| BT OEA150$  value_order_changed | 1 |
| BT OEB010$  mask_lost | 1 |
| G1 OEB070$  missing | 1 |
| BT OEB110$  mask_lost | 1 |
| BT OEB250$  mask_lost | 1 |
| BT OEC090$  mask_lost | 1 |
| BT OEC100$  mask_lost | 1 |
| BT OED120$  mask_lost | 1 |
| BT OED150$  mask_lost | 1 |

## Supervivencia de las modificaciones (G5, aceptadas `stacked_btv_en`)

| Tipo | Sobrevive | Revertido |
|---|---:|---:|
| compression | 1183 | 43 |
| expansion | 1441 | 0 |
| num_to_text | 590 | 0 |
| paraphrase | 1429 | 51 |
| synonym_label | 4001 | 66 |
| template_paraphrase | 4505 | 26 |
| unit_conversion | 209 | 0 |
| unit_expansion | 416 | 19 |

## Aceptación por concepto (`stacked_btv_en`)

| Concepto | Aceptadas | Total |
|---|---:|---:|
| OEA010$ | 5 | 5 |
| OEA020$ | 5 | 5 |
| OEA030$ | 5 | 5 |
| OEA040$ | 19 | 21 |
| OEA050$ | 41 | 41 |
| OEA060$ | 3 | 3 |
| OEA070$ | 9 | 15 |
| OEA080$ | 62 | 62 |
| OEA090$ | 9 | 10 |
| OEA100$ | 1 | 1 |
| OEA110$ | 1 | 1 |
| OEA120$ | 5 | 5 |
| OEA130$ | 5 | 5 |
| OEA140$ | 1 | 1 |
| OEA150$ | 20 | 21 |
| OEA160$ | 2 | 2 |
| OEA170$ | 5 | 5 |
| OEA180$ | 1 | 1 |
| OEB010$ | 0 | 1 |
| OEB020$ | 262 | 286 |
| OEB030$ | 401 | 401 |
| OEB040$ | 415 | 415 |
| OEB050$ | 1 | 1 |
| OEB070$ | 9 | 10 |
| OEB080$ | 1 | 1 |
| OEB090$ | 10 | 10 |
| OEB100$ | 5 | 5 |
| OEB110$ | 4 | 5 |
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
| OEC030$ | 30 | 56 |
| OEC040$ | 51 | 51 |
| OEC050$ | 2 | 2 |
| OEC070$ | 10 | 10 |
| OEC080$ | 5 | 5 |
| OEC090$ | 9 | 10 |
| OEC100$ | 14 | 15 |
| OEC110$ | 5 | 5 |
| OEC120$ | 30 | 41 |
| OED010$ | 154 | 154 |
| OED020$ | 150 | 161 |
| OED030$ | 62 | 62 |
| OED040$ | 69 | 69 |
| OED050$ | 38 | 38 |
| OED060$ | 38 | 38 |
| OED070$ | 29 | 31 |
| OED080$ | 69 | 69 |
| OED090$ | 69 | 69 |
| OED100$ | 62 | 62 |
| OED110$ | 20 | 20 |
| OED120$ | 9 | 10 |
| OED130$ | 5 | 5 |
| OED140$ | 38 | 38 |
| OED150$ | 14 | 15 |
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
- **G1** `OEA070aeca_syn_2e51fe11a81d` eje None · missing: missing=['PTR'] extra=[]
  - origen: Para la canaleta composite-PTR, se llevará a cabo el suministro y el montaje de módulo de empalme, que incluye piezas para el cosido entre las mismas, de acuerdo con la ET 03.365.064.9.. Las tareas a realizar son Horario Completo, con una banda de mantenimiento de Intervalo menor a tres horas, y las condiciones de ejecución Volumen relevante serán aplicables.
  - BT: En el caso de canaleta compuestoPTR, el suministro y el montaje de módulo de empalme, incluidas las partes para coser entre ellas, se efectuarán de conformidad con ET 03.365.064.9. Las tareas que deben realizarse son Trabajo: Horario Completo, con una banda de mantenimiento de Intervalo inferior a tres horas, y se aplicarán las condiciones de ejecución Volumen importante.
- **BT** `OEA090aaca_syn_f463f0847dd9` eje None · mask_lost
  - origen: Se realiza el destape de la canaleta existente de tipo a mano, con el objetivo de localizar o instalar nuevos cables. Trabajo: Día Laboral Banda de mantenimiento: Mantenimiento cada cinco horas o más Condiciones para la ejecución: Cualquier condición de ejecución
  - BT: Uncovering of the existing [1] type [2] is carried out with the aim of locating or installing new cables. Work: [3] Maintenance band: [4] Conditions for execution: [5]
- **BT** `OEA150bacbc_syn_e34bbd7e3480` eje None · value_order_changed
  - origen: Se realiza una apertura apertura automatizada en la canaleta mezcla de cemento existente destinada al tendido de cables, abarcando las tareas de excavación del suelo. Trabajo: Diurno Excepcional Banda de mantenimiento: 3 a 5 horas Condiciones de ejecución: Cualquier condición de ejecución
  - BT: An opening [1] is made in the [2] [3] existing one intended for cable laying, covering the excavation tasks of the ground. Work: [4] Maintenance band: [5] Conditions of execution: [6]
- **BT** `OEB010cbb_syn_bfd8a15b19d5` eje None · mask_lost
  - origen: Instalación de conducción subterránea para línea de doble circuito de 220 o 400 kV con cables encapsulados y conductos inyectados en hormigón HM-20, de dimensiones totales 2 m de ancho por 1,60 m de alto, con concreto extendido hasta profundidad 760 mm, seguido de relleno a compresión 95% P.M. Incluidos 2 ternas de conductos de polietileno (PE) de alta densidad de 250 mm de diámetro exterior para 
  - BT: Underground conduction installation for a double-circuit line of [1] or [2] with encapsulated cables and ducts injected into concrete [3], of total dimensions [4] wide by [5] high, with concrete extended to depth [6], followed by compression filling [7] [8] Including [9] high density [11] outer diameter polyethylene ducts for power cables; [12] double-layer [13] outer diameter polyethylene ducts f
