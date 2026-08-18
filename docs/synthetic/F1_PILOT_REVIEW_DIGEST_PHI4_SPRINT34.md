# Review Digest — OEB070$ (phi4:latest, Sprint 34: collision guard + no-collision prompts + sibling slots, seed 7)

45 distinct variants (representative leaf per variant chosen to exhibit each modification's condition).

## 1. full_random_mix_bf2ef4b9a9
- **item_key:** `OEB070adac`  (modifications: 5)
- synonym_label[D]: 'Volumen relevante' → 'Alto volumen'
- synonym_label[D]: 'Volumen escaso' → 'Bajo volumen'
- synonym_label[D]: 'Cualquier condición de ejecución' → 'Sin restricciones'
- expansion[L %B=a]: 'Diurno' → 'Diurno, es decir, durante las horas de luz natural, excluyendo las horas nocturnas, para minimizar el impacto en el tráfico ferroviario y garantizar la seguridad en la ejecución de la obra.'
- compression[L %B=d]: 'Nocturno Excepcional' → 'Nocturno Especial'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Nocturno Especial/i >==5 horas/Sin restricciones)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Nocturno Especial Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Sin restricciones

## 2. new_param_only_76cedfeb04
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- new_param: '?' → 'MATERIAL DE AISLAMIENTO'

## 3. single_L1_num_to_text_01eae26f80
- **item_key:** `OEB070baaa`  (modifications: 2)
- num_to_text[A]: '1' → 'un tubo'
- num_to_text[A]: '2' → 'dos tubos'
- **resumen:** Suministro y ejecución de canalización de dos tubos tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de dos tubos tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 4. single_L1_synonym_label_0160e36e6d
- **item_key:** `OEB070aaac`  (modifications: 3)
- synonym_label[D]: 'Volumen relevante' → 'Alto volumen'
- synonym_label[D]: 'Volumen escaso' → 'Bajo volumen'
- synonym_label[D]: 'Cualquier condición de ejecución' → 'Sin restricciones'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Sin restricciones)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Sin restricciones

## 5. single_L1_synonym_label_7b10f32b46
- **item_key:** `OEB070afaa`  (modifications: 6)
- synonym_label[B]: 'Diurno' → 'Horario Diurno'
- synonym_label[B]: 'Nocturno' → 'Horario Nocturno'
- synonym_label[B]: 'Diurno Excepcional' → 'Horario Diurno Especial'
- synonym_label[B]: 'Nocturno Excepcional' → 'Horario Nocturno Especial'
- synonym_label[B]: 'Cualquier franja horaria' → 'Horario Flexible'
- synonym_label[B]: 'Cualquier franja horaria excepcional' → 'Horario Flexible Especial'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Horario Flexible Especial/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Horario Flexible Especial Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 6. single_L1_synonym_label_96cf99013c
- **item_key:** `OEB070aada`  (modifications: 1)
- synonym_label[C]: 'No necesita intervalo' → 'Sin Mantenimiento'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/No necesita intervalo/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento: Sin Mantenimiento Condiciones de ejecución: Volumen relevante

## 7. single_L1_unit_conversion_bb6a562c03
- **item_key:** `OEB070aada`  (modifications: 3)
- unit_conversion[C]: '3 <= i < 5 horas' → '3 a 5 horas'
- unit_conversion[C]: 'i < 3 horas' → 'menos de 3 horas'
- unit_conversion[C]: 'No necesita intervalo' → 'sin intervalo'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/No necesita intervalo/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento: sin intervalo Condiciones de ejecución: Volumen relevante

## 8. single_L1_unit_expansion_b84c4983f7
- **item_key:** `OEB070aada`  (modifications: 3)
- unit_expansion[C]: '3 <= i < 5 horas' → 'Intervalo entre tres y cinco horas'
- unit_expansion[C]: 'i < 3 horas' → 'Intervalo menor a tres horas'
- unit_expansion[C]: 'No necesita intervalo' → 'Sin intervalo requerido'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/No necesita intervalo/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento: Sin intervalo requerido Condiciones de ejecución: Volumen relevante

## 9. single_L2_compression_05fd9aee20
- **item_key:** `OEB070aeaa`  (modifications: 1)
- compression[L %B=e]: 'Cualquier frana horaria' → 'Horario flexible'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Horario flexible/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 10. single_L2_compression_1453ea1795
- **item_key:** `OEB070aaab`  (modifications: 1)
- compression[N %D=b]: 'Volumen escaso' → 'Volumen bajo'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen bajo)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen bajo

## 11. single_L2_compression_150aa484c5
- **item_key:** `OEB070acaa`  (modifications: 1)
- compression[L %B=c]: 'Diurno Excepcional' → 'Diurno Especial'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno Especial/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Especial Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 12. single_L2_compression_2632e273eb
- **item_key:** `OEB070aaaa`  (modifications: 1)
- compression[N %D=a]: 'Volumen relevante' → 'Volumen alto'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen alto)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen alto

## 13. single_L2_compression_5a596d6b99
- **item_key:** `OEB070abaa`  (modifications: 1)
- compression[L %B=b]: 'Nocturno' → 'Noche'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Noche/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Noche Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 14. single_L2_compression_5bae339efa
- **item_key:** `OEB070afaa`  (modifications: 1)
- compression[L %B=f]: 'Cualquier franja horaria excepcional' → 'Horario Excepcional'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Horario Excepcional/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Horario Excepcional Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 15. single_L2_compression_8a3e8894a8
- **item_key:** `OEB070aaac`  (modifications: 1)
- compression[N %D=c]: 'Cualquier condición de ejecución' → 'Ejecución variable'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Ejecución variable)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Ejecución variable

## 16. single_L2_compression_cf52287033
- **item_key:** `OEB070aaaa`  (modifications: 1)
- compression[L %B=a]: 'Diurno' → 'Horario Diurno'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Horario Diurno/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Horario Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 17. single_L2_compression_d840b02805
- **item_key:** `OEB070adaa`  (modifications: 1)
- compression[L %B=d]: 'Nocturno Excepcional' → 'Nocturno Especial'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Nocturno Especial/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Nocturno Especial Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 18. single_L2_expansion_2489c746e8
- **item_key:** `OEB070adaa`  (modifications: 1)
- expansion[L %B=d]: 'Nocturno Excepcional' → 'Ejecución programada durante horas nocturnas, con condiciones excepcionales para minimizar el impacto en el tráfico ferroviario y garantizar la seguridad.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Ejecución programada durante horas nocturnas, con condiciones excepcionales para minimizar el impacto en el tráfico ferroviario y garantizar la seguridad./i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Ejecución programada durante horas nocturnas, con condiciones excepcionales para minimizar el impacto en el tráfico ferroviario y garantizar la seguridad. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 19. single_L2_expansion_291cf29e6b
- **item_key:** `OEB070aaab`  (modifications: 1)
- expansion[N %D=b]: 'Volumen escaso' → 'Volumen escaso, indicando una cantidad mínima de tubos necesarios para la ejecución del proyecto bajo las condiciones especificadas.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen escaso, indicando una cantidad mínima de tubos necesarios para la ejecución del proyecto bajo las condiciones especificadas.)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen escaso, indicando una cantidad mínima de tubos necesarios para la ejecución del proyecto bajo las condiciones especificadas.

## 20. single_L2_expansion_29ba3f00e1
- **item_key:** `OEB070aaaa`  (modifications: 1)
- expansion[N %D=a]: 'Volumen relevante' → 'Volumen relevante, indicando una cantidad significativa que requiere una planificación y ejecución cuidadosa para asegurar la eficiencia y cumplimiento de los estándares de construcción.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen relevante, indicando una cantidad significativa que requiere una planificación y ejecución cuidadosa para asegurar la eficiencia y cumplimiento de los estándares de construcción.)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante, indicando una cantidad significativa que requiere una planificación y ejecución cuidadosa para asegurar la eficiencia y cumplimiento de los estándares de construcción.

## 21. single_L2_expansion_4792eb2d1d
- **item_key:** `OEB070abaa`  (modifications: 1)
- expansion[L %B=b]: 'Nocturno' → 'Ejecución durante la noche, evitando interrupciones en el tráfico ferroviario y minimizando el impacto en la operación diaria.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Ejecución durante la noche, evitando interrupciones en el tráfico ferroviario y minimizando el impacto en la operación diaria./i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Ejecución durante la noche, evitando interrupciones en el tráfico ferroviario y minimizando el impacto en la operación diaria. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 22. single_L2_expansion_4c812ec89a
- **item_key:** `OEB070aaaa`  (modifications: 1)
- expansion[L %B=a]: 'Diurno' → 'Durante las horas de luz natural, excluyendo las horas nocturnas, para minimizar el impacto en el tráfico ferroviario y garantizar condiciones de seguridad óptimas.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Durante las horas de luz natural, excluyendo las horas nocturnas, para minimizar el impacto en el tráfico ferroviario y garantizar condiciones de seguridad óptimas./i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Durante las horas de luz natural, excluyendo las horas nocturnas, para minimizar el impacto en el tráfico ferroviario y garantizar condiciones de seguridad óptimas. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 23. single_L2_expansion_803422de0c
- **item_key:** `OEB070acaa`  (modifications: 1)
- expansion[L %B=c]: 'Diurno Excepcional' → 'Diurno Excepcional, que implica trabajos realizados durante el horario diurno pero con condiciones especiales que permiten excepciones a las normas habituales de operación.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno Excepcional, que implica trabajos realizados durante el horario diurno pero con condiciones especiales que permiten excepciones a las normas habituales de operación./i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Excepcional, que implica trabajos realizados durante el horario diurno pero con condiciones especiales que permiten excepciones a las normas habituales de operación. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 24. single_L2_expansion_976a3487ab
- **item_key:** `OEB070aeaa`  (modifications: 1)
- expansion[L %B=e]: 'Cualquier frana horaria' → 'Cualquier franja horaria, permitiendo flexibilidad en la programación de trabajos para adaptarse a las necesidades operativas y logísticas del proyecto.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Cualquier franja horaria, permitiendo flexibilidad en la programación de trabajos para adaptarse a las necesidades operativas y logísticas del proyecto./i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 25. single_L2_expansion_ebf056d4ac
- **item_key:** `OEB070afaa`  (modifications: 1)
- expansion[L %B=f]: 'Cualquier franja horaria excepcional' → 'Cualquier franja horaria excepcional, incluyendo aquellas que no se ajustan a los horarios estándar de trabajo diurno o nocturno, permitiendo flexibilidad en la programación de actividades.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Cualquier franja horaria excepcional, incluyendo aquellas que no se ajustan a los horarios estándar de trabajo diurno o nocturno, permitiendo flexibilidad en la programación de actividades./i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria excepcional, incluyendo aquellas que no se ajustan a los horarios estándar de trabajo diurno o nocturno, permitiendo flexibilidad en la programación de actividades. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 26. single_L2_expansion_f23a67cfc9
- **item_key:** `OEB070aaac`  (modifications: 1)
- expansion[N %D=c]: 'Cualquier condición de ejecución' → 'Cualquier condición de ejecución, incluyendo variaciones en el terreno o condiciones climáticas adversas, que puedan afectar la instalación.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Cualquier condición de ejecución, incluyendo variaciones en el terreno o condiciones climáticas adversas, que puedan afectar la instalación.)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Cualquier condición de ejecución, incluyendo variaciones en el terreno o condiciones climáticas adversas, que puedan afectar la instalación.

## 27. single_L2_paraphrase_0afab6ef1a
- **item_key:** `OEB070aaab`  (modifications: 1)
- paraphrase[N %D=b]: 'Volumen escaso' → 'Cantidad reducida'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Cantidad reducida)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Cantidad reducida

## 28. single_L2_paraphrase_1f8eaf2ffb
- **item_key:** `OEB070aaaa`  (modifications: 1)
- paraphrase[L %B=a]: 'Diurno' → 'Horario de día'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Horario de día/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Horario de día Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 29. single_L2_paraphrase_286094f47a
- **item_key:** `OEB070aeaa`  (modifications: 1)
- paraphrase[L %B=e]: 'Cualquier frana horaria' → 'En cualquier franja horaria'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (En cualquier franja horaria/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 30. single_L2_paraphrase_2afad3cd87
- **item_key:** `OEB070afaa`  (modifications: 1)
- paraphrase[L %B=f]: 'Cualquier franja horaria excepcional' → 'Horario extraordinario'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Horario extraordinario/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Horario extraordinario Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 31. single_L2_paraphrase_352cc035b0
- **item_key:** `OEB070acaa`  (modifications: 1)
- paraphrase[L %B=c]: 'Diurno Excepcional' → 'Horario Diurno Especial'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Horario Diurno Especial/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Horario Diurno Especial Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 32. single_L2_paraphrase_6fc9dbcf74
- **item_key:** `OEB070abaa`  (modifications: 1)
- paraphrase[L %B=b]: 'Nocturno' → 'Horario nocturno'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Horario nocturno/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Horario nocturno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 33. single_L2_paraphrase_bbc6c318ac
- **item_key:** `OEB070aaac`  (modifications: 1)
- paraphrase[N %D=c]: 'Cualquier condición de ejecución' → 'Condiciones diversas de ejecución'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Condiciones diversas de ejecución)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Condiciones diversas de ejecución

## 34. single_L2_paraphrase_c413944575
- **item_key:** `OEB070adaa`  (modifications: 1)
- paraphrase[L %B=d]: 'Nocturno Excepcional' → 'Nocturno Especial'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Nocturno Especial/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Nocturno Especial Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 35. single_L2_paraphrase_fda48a9360
- **item_key:** `OEB070aaaa`  (modifications: 1)
- paraphrase[N %D=a]: 'Volumen relevante' → 'Volumen considerable'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen considerable)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen considerable

## 36. single_L3_omission_a516ff61df
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- omission[RESUMEN]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))' → 'Suministro y ejecución de canalización de tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))'

## 37. single_L3_omission_cacf7915c2
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- omission[RESUMEN]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))' → 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$N(%D))'

## 38. single_L3_omission_e7670ffcba
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- omission[RESUMEN]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))' → 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C))'

## 39. single_L3_omission_f5aac4cea1
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- omission[RESUMEN]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))' → 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($M(%C)/$N(%D))'

## 40. single_L3_reorder_878b0fc215
- **item_key:** `OEB070aaaa`  (modifications: 1)
- reorder[TEXTO]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: $B Banda de mantenimiento: $C Condiciones de ejecución: $D' → 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Condiciones de ejecución: $D Banda de mantenimiento: $C Trabajo: $B'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Condiciones de ejecución: Volumen relevante Banda de mantenimiento:  i >= 5 horas Trabajo: Diurno

## 41. single_L3_reorder_91fe70d624
- **item_key:** `OEB070aaaa`  (modifications: 1)
- reorder[RESUMEN]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))' → 'Suministro y ejecución de canalización de ($L(%B)/$M(%C)/$N(%D)) $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías'
- **resumen:** Suministro y ejecución de canalización de (Diurno/i >==5 horas/Volumen relevante) 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 42. stacked_2_bccade917c
- **item_key:** `OEB070aeaa`  (modifications: 2)
- compression[L %B=e]: 'Cualquier frana horaria' → 'Horario flexible'
- paraphrase[N %D=a]: 'Volumen relevante' → 'Volumen considerable'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Horario flexible/i >==5 horas/Volumen considerable)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen considerable

## 43. stacked_3_b9ac001967
- **item_key:** _(no materialized leaves)_  (modifications: 2)
- compression[N %D=a]: 'Volumen relevante' → 'Volumen alto'
- omission[RESUMEN]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))' → 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C))'

## 44. stacked_4_e348696140
- **item_key:** `OEB070acaa`  (modifications: 3)
- compression[L %B=d]: 'Nocturno Excepcional' → 'Nocturno Especial'
- paraphrase[L %B=e]: 'Cualquier frana horaria' → 'En cualquier franja horaria'
- compression[L %B=c]: 'Diurno Excepcional' → 'Diurno Especial'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno Especial/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Especial Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 45. stacked_5plus_ce5742d4f2
- **item_key:** `OEB070aeaa`  (modifications: 3)
- compression[L %B=f]: 'Cualquier franja horaria excepcional' → 'Horario Excepcional'
- compression[L %B=e]: 'Cualquier frana horaria' → 'Horario flexible'
- expansion[N %D=a]: 'Volumen relevante' → 'Volumen relevante, indicando una cantidad significativa que requiere una planificación y ejecución cuidadosa para asegurar la eficiencia y cumplimiento de los estándares de construcción.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Horario flexible/i >==5 horas/Volumen relevante, indicando una cantidad significativa que requiere una planificación y ejecución cuidadosa para asegurar la eficiencia y cumplimiento de los estándares de construcción.)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante, indicando una cantidad significativa que requiere una planificación y ejecución cuidadosa para asegurar la eficiencia y cumplimiento de los estándares de construcción.
