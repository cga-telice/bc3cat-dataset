# Review Digest — OEB070$ (phi4:latest, Sprint 32 tuned prompts, seed 7)

44 distinct variants (representative leaf per variant chosen to exhibit each modification's condition).

## 1. full_random_mix_84c4cd6aa1
- **item_key:** `OEB070adac`  (modifications: 5)
- synonym_label[D]: 'Volumen relevante' → 'Alto volumen'
- synonym_label[D]: 'Volumen escaso' → 'Bajo volumen'
- synonym_label[D]: 'Cualquier condición de ejecución' → 'Sin restricción'
- expansion[L %B=a]: 'Diurno' → 'Diurno, es decir, durante las horas de luz natural, excluyendo las horas nocturnas, para garantizar la visibilidad y seguridad durante la ejecución de la canalización.'
- compression[L %B=d]: 'Nocturno Excepcional' → 'Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Nocturno Excepcional/%B/%C/%D)'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Nocturno Excepcional/"Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Nocturno Excepcional/%B/" i >= 5 horas"/"Sin restricción")"/" i >= 5 horas"/"Sin restricción")/i >==5 horas/Sin restricción)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Nocturno Excepcional/%B/%C/%D) Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Sin restricción

## 2. new_param_only_76cedfeb04
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- new_param: '?' → 'MATERIAL DE AISLAMIENTO'

## 3. single_L1_num_to_text_2d7b482a2a
- **item_key:** `OEB070baaa`  (modifications: 2)
- num_to_text[A]: '1' → 'uno'
- num_to_text[A]: '2' → 'dos'
- **resumen:** Suministro y ejecución de canalización de dos tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de dos tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 4. single_L1_synonym_label_bf725471fe
- **item_key:** `OEB070aaac`  (modifications: 3)
- synonym_label[D]: 'Volumen relevante' → 'Alto volumen'
- synonym_label[D]: 'Volumen escaso' → 'Bajo volumen'
- synonym_label[D]: 'Cualquier condición de ejecución' → 'Sin restricción'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Sin restricción)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Sin restricción

## 5. single_L1_synonym_label_df18b64ad0
- **item_key:** `OEB070afaa`  (modifications: 6)
- synonym_label[B]: 'Diurno' → 'Horario Diurno'
- synonym_label[B]: 'Nocturno' → 'Horario Nocturno'
- synonym_label[B]: 'Diurno Excepcional' → 'Horario Diurno Excepcional'
- synonym_label[B]: 'Nocturno Excepcional' → 'Horario Nocturno Excepcional'
- synonym_label[B]: 'Cualquier franja horaria' → 'Horario Flexible'
- synonym_label[B]: 'Cualquier franja horaria excepcional' → 'Horario Flexible Excepcional'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Horario Flexible Excepcional/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Horario Flexible Excepcional Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 6. single_L1_synonym_label_ee0ceee966
- **item_key:** `OEB070aada`  (modifications: 1)
- synonym_label[C]: 'No necesita intervalo' → 'Sin intervalo'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/No necesita intervalo/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento: Sin intervalo Condiciones de ejecución: Volumen relevante

## 7. single_L1_unit_conversion_732490729c
- **item_key:** `OEB070aada`  (modifications: 3)
- unit_conversion[C]: '3 <= i < 5 horas' → '3-5 h'
- unit_conversion[C]: 'i < 3 horas' → '<3 h'
- unit_conversion[C]: 'No necesita intervalo' → 'N/A'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/No necesita intervalo/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento: N/A Condiciones de ejecución: Volumen relevante

## 8. single_L1_unit_expansion_746dc5e6fc
- **item_key:** `OEB070aada`  (modifications: 3)
- unit_expansion[C]: '3 <= i < 5 horas' → 'intervalo entre 3 y 5 horas'
- unit_expansion[C]: 'i < 3 horas' → 'intervalo menor a 3 horas'
- unit_expansion[C]: 'No necesita intervalo' → 'sin intervalo necesario'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/No necesita intervalo/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento: sin intervalo necesario Condiciones de ejecución: Volumen relevante

## 9. single_L2_compression_1453ea1795
- **item_key:** `OEB070aaab`  (modifications: 1)
- compression[N %D=b]: 'Volumen escaso' → 'Volumen bajo'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen bajo)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen bajo

## 10. single_L2_compression_3089250cf7
- **item_key:** `OEB070adaa`  (modifications: 1)
- compression[L %B=d]: 'Nocturno Excepcional' → 'Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Nocturno Excepcional/%C/%D)'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Nocturno Excepcional/" i >= 5 horas"/"Volumen relevante")/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Nocturno Excepcional/%C/%D) Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 11. single_L2_compression_5c0d5650ac
- **item_key:** `OEB070afaa`  (modifications: 1)
- compression[L %B=f]: 'Cualquier franja horaria excepcional' → 'Franja horaria excepcional'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Franja horaria excepcional/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Franja horaria excepcional Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 12. single_L2_compression_5d0b270b34
- **item_key:** `OEB070abaa`  (modifications: 1)
- compression[L %B=b]: 'Nocturno' → 'Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Nocturno/%B/%C/%D)'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Nocturno/"Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Nocturno/%B/" i >= 5 horas"/"Volumen relevante")"/" i >= 5 horas"/"Volumen relevante")/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Nocturno/%B/%C/%D) Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 13. single_L2_compression_913c5ffe3d
- **item_key:** `OEB070aaaa`  (modifications: 1)
- compression[N %D=a]: 'Volumen relevante' → '%D=a'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/%D=a"=a)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: %D=a

## 14. single_L2_compression_a67ec5bae5
- **item_key:** `OEB070aeaa`  (modifications: 1)
- compression[L %B=e]: 'Cualquier frana horaria' → 'Frana horaria'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Frana horaria/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 15. single_L2_compression_bf1aed6b37
- **item_key:** `OEB070acaa`  (modifications: 1)
- compression[L %B=c]: 'Diurno Excepcional' → 'Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Diurno Excepcional/%B/%C/%D)'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Diurno Excepcional/"Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Diurno Excepcional/%B/" i >= 5 horas"/"Volumen relevante")"/" i >= 5 horas"/"Volumen relevante")/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Diurno Excepcional/%B/%C/%D) Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 16. single_L2_compression_c3f4d44c43
- **item_key:** `OEB070aaaa`  (modifications: 1)
- compression[L %B=a]: 'Diurno' → 'Suministro y ejecución de canalización de 5 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (L/%B/%C/%D)'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Suministro y ejecución de canalización de 5 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (L/"Suministro y ejecución de canalización de 5 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (L/%B/" i >= 5 horas"/"Volumen relevante")"/" i >= 5 horas"/"Volumen relevante")/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Suministro y ejecución de canalización de 5 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (L/%B/%C/%D) Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 17. single_L2_expansion_090236089c
- **item_key:** `OEB070aeaa`  (modifications: 1)
- expansion[L %B=e]: 'Cualquier frana horaria' → 'Cualquier fractura o desprendimiento de tierra que ocurra en el horario de ejecución de la obra, que pueda afectar la estabilidad del terreno en el área de instalación de la canalización.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Cualquier fractura o desprendimiento de tierra que ocurra en el horario de ejecución de la obra, que pueda afectar la estabilidad del terreno en el área de instalación de la canalización./i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 18. single_L2_expansion_1661f4472d
- **item_key:** `OEB070aaab`  (modifications: 1)
- expansion[N %D=b]: 'Volumen escaso' → 'Volumen escaso, indicando que la cantidad de tubos de polietileno de 110 mm 5 At. con topo bajo vías es limitada, adecuada para proyectos de pequeña escala o específicos donde se requiere una instalación mínima.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen escaso, indicando que la cantidad de tubos de polietileno de 110 mm 5 At. con topo bajo vías es limitada, adecuada para proyectos de pequeña escala o específicos donde se requiere una instalación mínima.)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen escaso, indicando que la cantidad de tubos de polietileno de 110 mm 5 At. con topo bajo vías es limitada, adecuada para proyectos de pequeña escala o específicos donde se requiere una instalación mínima.

## 19. single_L2_expansion_2f7c17c520
- **item_key:** `OEB070aaac`  (modifications: 1)
- expansion[N %D=c]: 'Cualquier condición de ejecución' → 'Cualquier condición de ejecución que pueda surgir durante el proceso de instalación, incluyendo pero no limitándose a variaciones en el terreno, condiciones climáticas adversas o dificultades técnicas imprevistas, siempre que estas no afecten la funcionalidad y seguridad del sistema de canalización.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Cualquier condición de ejecución que pueda surgir durante el proceso de instalación, incluyendo pero no limitándose a variaciones en el terreno, condiciones climáticas adversas o dificultades técnicas imprevistas, siempre que estas no afecten la funcionalidad y seguridad del sistema de canalización.)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Cualquier condición de ejecución que pueda surgir durante el proceso de instalación, incluyendo pero no limitándose a variaciones en el terreno, condiciones climáticas adversas o dificultades técnicas imprevistas, siempre que estas no afecten la funcionalidad y seguridad del sistema de canalización.

## 20. single_L2_expansion_3bc3ee152c
- **item_key:** `OEB070adaa`  (modifications: 1)
- expansion[L %B=d]: 'Nocturno Excepcional' → 'Ejecución Nocturna Excepcional, programada específicamente para minimizar las interrupciones en el tráfico ferroviario, permitiendo la instalación de los tubos de polietileno de 110 mm de diámetro y 5 at. de longitud bajo las vías durante las horas de menor actividad, garantizando así la seguridad y eficiencia del proceso.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Ejecución Nocturna Excepcional, programada específicamente para minimizar las interrupciones en el tráfico ferroviario, permitiendo la instalación de los tubos de polietileno de 110 mm de diámetro y 5 at. de longitud bajo las vías durante las horas de menor actividad, garantizando así la seguridad y eficiencia del proceso./i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Ejecución Nocturna Excepcional, programada específicamente para minimizar las interrupciones en el tráfico ferroviario, permitiendo la instalación de los tubos de polietileno de 110 mm de diámetro y 5 at. de longitud bajo las vías durante las horas de menor actividad, garantizando así la seguridad y eficiencia del proceso. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 21. single_L2_expansion_54271f7444
- **item_key:** `OEB070abaa`  (modifications: 1)
- expansion[L %B=b]: 'Nocturno' → 'Ejecución nocturna para minimizar las interrupciones en el tráfico ferroviario y garantizar la seguridad de los trabajadores y el público.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Ejecución nocturna para minimizar las interrupciones en el tráfico ferroviario y garantizar la seguridad de los trabajadores y el público./i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Ejecución nocturna para minimizar las interrupciones en el tráfico ferroviario y garantizar la seguridad de los trabajadores y el público. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 22. single_L2_expansion_847c4a3086
- **item_key:** `OEB070acaa`  (modifications: 1)
- expansion[L %B=c]: 'Diurno Excepcional' → 'Diurno Excepcional, que implica la realización de las actividades de suministro y ejecución de canalización durante el horario diurno, con condiciones especiales que permiten la ejecución de las obras en horario de día, a pesar de las restricciones habituales que podrían requerir trabajos nocturnos o en horarios restringidos, para minimizar el impacto en el tráfico ferroviario y garantizar la seguridad en la zona de trabajo.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno Excepcional, que implica la realización de las actividades de suministro y ejecución de canalización durante el horario diurno, con condiciones especiales que permiten la ejecución de las obras en horario de día, a pesar de las restricciones habituales que podrían requerir trabajos nocturnos o en horarios restringidos, para minimizar el impacto en el tráfico ferroviario y garantizar la seguridad en la zona de trabajo./i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Excepcional, que implica la realización de las actividades de suministro y ejecución de canalización durante el horario diurno, con condiciones especiales que permiten la ejecución de las obras en horario de día, a pesar de las restricciones habituales que podrían requerir trabajos nocturnos o en horarios restringidos, para minimizar el impacto en el tráfico ferroviario y garantizar la seguridad en la zona de trabajo. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 23. single_L2_expansion_9e120e647d
- **item_key:** `OEB070afaa`  (modifications: 1)
- expansion[L %B=f]: 'Cualquier franja horaria excepcional' → 'Cualquier franja horaria excepcional que pueda surgir debido a circunstancias imprevistas o condiciones operativas específicas que requieran ajustes en el cronograma de trabajo.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Cualquier franja horaria excepcional que pueda surgir debido a circunstancias imprevistas o condiciones operativas específicas que requieran ajustes en el cronograma de trabajo./i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria excepcional que pueda surgir debido a circunstancias imprevistas o condiciones operativas específicas que requieran ajustes en el cronograma de trabajo. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 24. single_L2_expansion_dc1f593ae6
- **item_key:** `OEB070aaaa`  (modifications: 1)
- expansion[N %D=a]: 'Volumen relevante' → "Volumen relevante, considerando la condición asociada donde %D es igual a 'a', lo que implica que el suministro y ejecución de la canalización de tubos de polietileno de 110 mm y 5 At. con topo bajo vías se realiza bajo parámetros específicos que garantizan la adecuada integración y funcionalidad en el entorno ferroviario."
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen relevante, considerando la condición asociada donde Volumen relevante, considerando la condición asociada donde %D es igual a 'a', lo que implica que el suministro y ejecución de la canalización de tubos de polietileno de 110 mm y 5 At. con topo bajo vías se realiza bajo parámetros específicos que garantizan la adecuada integración y funcionalidad en el entorno ferroviario. es igual a 'a', lo que implica que el suministro y ejecución de la canalización de tubos de polietileno de 110 mm y 5 At. con topo bajo vías se realiza bajo parámetros específicos que garantizan la adecuada integración y funcionalidad en el entorno ferroviario.)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante, considerando la condición asociada donde %D es igual a 'a', lo que implica que el suministro y ejecución de la canalización de tubos de polietileno de 110 mm y 5 At. con topo bajo vías se realiza bajo parámetros específicos que garantizan la adecuada integración y funcionalidad en el entorno ferroviario.

## 25. single_L2_expansion_fd36419090
- **item_key:** `OEB070aaaa`  (modifications: 1)
- expansion[L %B=a]: 'Diurno' → 'Diurno, es decir, durante las horas de luz natural, excluyendo las horas nocturnas, para garantizar la visibilidad y seguridad durante la ejecución de la canalización.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno, es decir, durante las horas de luz natural, excluyendo las horas nocturnas, para garantizar la visibilidad y seguridad durante la ejecución de la canalización./i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno, es decir, durante las horas de luz natural, excluyendo las horas nocturnas, para garantizar la visibilidad y seguridad durante la ejecución de la canalización. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 26. single_L2_paraphrase_0395d36106
- **item_key:** `OEB070aaac`  (modifications: 1)
- paraphrase[N %D=c]: 'Cualquier condición de ejecución' → 'En cualquier circunstancia de instalación'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/En cualquier circunstancia de instalación)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: En cualquier circunstancia de instalación

## 27. single_L2_paraphrase_0afab6ef1a
- **item_key:** `OEB070aaab`  (modifications: 1)
- paraphrase[N %D=b]: 'Volumen escaso' → 'Cantidad reducida'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Cantidad reducida)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Cantidad reducida

## 28. single_L2_paraphrase_0f0bafa249
- **item_key:** `OEB070aeaa`  (modifications: 1)
- paraphrase[L %B=e]: 'Cualquier frana horaria' → 'Cualquier franja horaria'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Cualquier franja horaria/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 29. single_L2_paraphrase_51b577ecad
- **item_key:** `OEB070afaa`  (modifications: 1)
- paraphrase[L %B=f]: 'Cualquier franja horaria excepcional' → 'Cualquier horario fuera del estándar'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Cualquier horario fuera del estándar/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier horario fuera del estándar Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 30. single_L2_paraphrase_9275daf1aa
- **item_key:** `OEB070acaa`  (modifications: 1)
- paraphrase[L %B=c]: 'Diurno Excepcional' → 'Ejecución Diurna Especial'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Ejecución Diurna Especial/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Ejecución Diurna Especial Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 31. single_L2_paraphrase_95dc471c8f
- **item_key:** `OEB070adaa`  (modifications: 1)
- paraphrase[L %B=d]: 'Nocturno Excepcional' → 'Ejecución Nocturna Especial'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Ejecución Nocturna Especial/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Ejecución Nocturna Especial Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 32. single_L2_paraphrase_ac4d112142
- **item_key:** `OEB070aaaa`  (modifications: 1)
- paraphrase[L %B=a]: 'Diurno' → 'Durante el día'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Durante el día/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Durante el día Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 33. single_L2_paraphrase_c5cb42657b
- **item_key:** `OEB070aaaa`  (modifications: 1)
- paraphrase[N %D=a]: 'Volumen relevante' → 'Cantidad significativa'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Cantidad significativa)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Cantidad significativa

## 34. single_L2_paraphrase_dc14e881ee
- **item_key:** `OEB070abaa`  (modifications: 1)
- paraphrase[L %B=b]: 'Nocturno' → 'Durante la noche'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Durante la noche/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Durante la noche Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 35. single_L3_omission_a516ff61df
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- omission[RESUMEN]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))' → 'Suministro y ejecución de canalización de tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))'

## 36. single_L3_omission_cacf7915c2
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- omission[RESUMEN]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))' → 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$N(%D))'

## 37. single_L3_omission_e7670ffcba
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- omission[RESUMEN]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))' → 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C))'

## 38. single_L3_omission_f5aac4cea1
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- omission[RESUMEN]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))' → 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($M(%C)/$N(%D))'

## 39. single_L3_reorder_878b0fc215
- **item_key:** `OEB070aaaa`  (modifications: 1)
- reorder[TEXTO]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: $B Banda de mantenimiento: $C Condiciones de ejecución: $D' → 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Condiciones de ejecución: $D Banda de mantenimiento: $C Trabajo: $B'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Condiciones de ejecución: Volumen relevante Banda de mantenimiento:  i >= 5 horas Trabajo: Diurno

## 40. single_L3_reorder_fb874aa6e4
- **item_key:** `OEB070aaaa`  (modifications: 1)
- reorder[RESUMEN]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))' → 'Suministro y ejecución de canalización de $L(%B)/$M(%C)/$N(%D) tubo(s) de polietileno 110 mm 5 At. con topo bajo vías de $A'
- **resumen:** Suministro y ejecución de canalización de Diurno/i >==5 horas/Volumen relevante tubo(s) de polietileno 110 mm 5 At. con topo bajo vías de 1
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 41. stacked_2_b69b4cacd1
- **item_key:** `OEB070aeaa`  (modifications: 2)
- compression[L %B=e]: 'Cualquier frana horaria' → 'Frana horaria'
- paraphrase[N %D=a]: 'Volumen relevante' → 'Cantidad significativa'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Frana horaria/i >==5 horas/Cantidad significativa)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Cantidad significativa

## 42. stacked_3_56458ed691
- **item_key:** _(no materialized leaves)_  (modifications: 2)
- compression[N %D=a]: 'Volumen relevante' → '%D=a'
- omission[RESUMEN]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))' → 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C))'

## 43. stacked_4_91f4c50649
- **item_key:** `OEB070acaa`  (modifications: 3)
- compression[L %B=d]: 'Nocturno Excepcional' → 'Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Nocturno Excepcional/%C/%D)'
- paraphrase[L %B=e]: 'Cualquier frana horaria' → 'Cualquier franja horaria'
- compression[L %B=c]: 'Diurno Excepcional' → 'Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Diurno Excepcional/%B/%C/%D)'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Diurno Excepcional/"Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Diurno Excepcional/%B/" i >= 5 horas"/"Volumen relevante")"/" i >= 5 horas"/"Volumen relevante")/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Diurno Excepcional/%B/%C/%D) Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 44. stacked_5plus_063543e9f7
- **item_key:** `OEB070aeaa`  (modifications: 3)
- compression[L %B=f]: 'Cualquier franja horaria excepcional' → 'Franja horaria excepcional'
- compression[L %B=e]: 'Cualquier frana horaria' → 'Frana horaria'
- expansion[N %D=a]: 'Volumen relevante' → "Volumen relevante, considerando la condición asociada donde %D es igual a 'a', lo que implica que el suministro y ejecución de la canalización de tubos de polietileno de 110 mm y 5 At. con topo bajo vías se realiza bajo parámetros específicos que garantizan la adecuada integración y funcionalidad en el entorno ferroviario."
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Frana horaria/i >==5 horas/Volumen relevante, considerando la condición asociada donde Volumen relevante, considerando la condición asociada donde %D es igual a 'a', lo que implica que el suministro y ejecución de la canalización de tubos de polietileno de 110 mm y 5 At. con topo bajo vías se realiza bajo parámetros específicos que garantizan la adecuada integración y funcionalidad en el entorno ferroviario. es igual a 'a', lo que implica que el suministro y ejecución de la canalización de tubos de polietileno de 110 mm y 5 At. con topo bajo vías se realiza bajo parámetros específicos que garantizan la adecuada integración y funcionalidad en el entorno ferroviario.)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante, considerando la condición asociada donde %D es igual a 'a', lo que implica que el suministro y ejecución de la canalización de tubos de polietileno de 110 mm y 5 At. con topo bajo vías se realiza bajo parámetros específicos que garantizan la adecuada integración y funcionalidad en el entorno ferroviario.
