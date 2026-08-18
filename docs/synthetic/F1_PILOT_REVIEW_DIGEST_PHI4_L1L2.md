# Review Digest — OEB070$ (phi4:latest, Sprint 33 tuned L1+L2, seed 7)

45 distinct variants (representative leaf per variant chosen to exhibit each modification's condition).

## 1. full_random_mix_899e87bf05
- **item_key:** `OEB070aaaa`  (modifications: 5)
- synonym_label[D]: 'Volumen relevante' → 'Alto volumen'
- synonym_label[D]: 'Volumen escaso' → 'Bajo volumen'
- synonym_label[D]: 'Cualquier condición de ejecución' → 'Sin restricción'
- expansion[L %B=a]: 'Diurno' → 'Ejecución durante el horario diurno, en horas de luz natural, para facilitar la visibilidad y seguridad en la operación.'
- compression[L %B=d]: 'Nocturno Excepcional' → 'Nocturno'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Ejecución durante el horario diurno, en horas de luz natural, para facilitar la visibilidad y seguridad en la operación./i >==5 horas/Alto volumen)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Ejecución durante el horario diurno, en horas de luz natural, para facilitar la visibilidad y seguridad en la operación. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Alto volumen

## 2. new_param_only_69c1b3201f
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- new_param: '?' → 'MATERIAL DE AISLAMIENTO'

## 3. single_L1_num_to_text_2d7b482a2a
- **item_key:** `OEB070baaa`  (modifications: 2)
- num_to_text[A]: '1' → 'uno'
- num_to_text[A]: '2' → 'dos'
- **resumen:** Suministro y ejecución de canalización de dos tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de dos tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 4. single_L1_synonym_label_a5c25abf26
- **item_key:** `OEB070aada`  (modifications: 1)
- synonym_label[C]: 'No necesita intervalo' → 'Sin mantenimiento'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/No necesita intervalo/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento: Sin mantenimiento Condiciones de ejecución: Volumen relevante

## 5. single_L1_synonym_label_bf725471fe
- **item_key:** `OEB070aaac`  (modifications: 3)
- synonym_label[D]: 'Volumen relevante' → 'Alto volumen'
- synonym_label[D]: 'Volumen escaso' → 'Bajo volumen'
- synonym_label[D]: 'Cualquier condición de ejecución' → 'Sin restricción'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Sin restricción)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Sin restricción

## 6. single_L1_synonym_label_df18b64ad0
- **item_key:** `OEB070afaa`  (modifications: 6)
- synonym_label[B]: 'Diurno' → 'Horario Diurno'
- synonym_label[B]: 'Nocturno' → 'Horario Nocturno'
- synonym_label[B]: 'Diurno Excepcional' → 'Horario Diurno Excepcional'
- synonym_label[B]: 'Nocturno Excepcional' → 'Horario Nocturno Excepcional'
- synonym_label[B]: 'Cualquier franja horaria' → 'Horario Flexible'
- synonym_label[B]: 'Cualquier franja horaria excepcional' → 'Horario Flexible Excepcional'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Horario Flexible Excepcional/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Horario Flexible Excepcional Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

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

## 10. single_L2_compression_5f09a6683d
- **item_key:** `OEB070aaaa`  (modifications: 1)
- compression[L %B=a]: 'Diurno' → 'Día'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Día/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Día Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 11. single_L2_compression_727fc28e97
- **item_key:** `OEB070aaaa`  (modifications: 1)
- compression[L %B=d]: 'Nocturno Excepcional' → 'Nocturno'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 12. single_L2_compression_7881c59d0c
- **item_key:** `OEB070aaac`  (modifications: 1)
- compression[N %D=c]: 'Cualquier condición de ejecución' → 'Ejecución bajo cualquier condición'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Ejecución bajo cualquier condición)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Ejecución bajo cualquier condición

## 13. single_L2_compression_9c3fac9a1f
- **item_key:** `OEB070abaa`  (modifications: 1)
- compression[L %B=b]: 'Nocturno' → 'Nocturno'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Nocturno/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Nocturno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 14. single_L2_compression_a67ec5bae5
- **item_key:** `OEB070aeaa`  (modifications: 1)
- compression[L %B=e]: 'Cualquier frana horaria' → 'Frana horaria'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Frana horaria/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 15. single_L2_compression_abdd40a05a
- **item_key:** `OEB070acaa`  (modifications: 1)
- compression[L %B=c]: 'Diurno Excepcional' → 'Excepcional Diurno'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Excepcional Diurno/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Excepcional Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 16. single_L2_compression_bf25675606
- **item_key:** `OEB070aaaa`  (modifications: 1)
- compression[N %D=a]: 'Volumen relevante' → 'Volumen %D'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen Volumen %D)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen %D

## 17. single_L2_compression_cae6b64864
- **item_key:** `OEB070afaa`  (modifications: 1)
- compression[L %B=f]: 'Cualquier franja horaria excepcional' → 'Horario excepcional'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Horario excepcional/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Horario excepcional Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 18. single_L2_expansion_196bb5d4b3
- **item_key:** `OEB070aaac`  (modifications: 1)
- expansion[N %D=c]: 'Cualquier condición de ejecución' → 'Cualquier condición de ejecución, incluyendo variaciones en el terreno y condiciones climáticas adversas, siempre que no afecten la integridad estructural del proyecto.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Cualquier condición de ejecución, incluyendo variaciones en el terreno y condiciones climáticas adversas, siempre que no afecten la integridad estructural del proyecto.)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Cualquier condición de ejecución, incluyendo variaciones en el terreno y condiciones climáticas adversas, siempre que no afecten la integridad estructural del proyecto.

## 19. single_L2_expansion_2ed6ae0542
- **item_key:** `OEB070aaaa`  (modifications: 1)
- expansion[N %D=a]: 'Volumen relevante' → 'Volumen relevante para la instalación, asegurando la adecuada cobertura y protección de la infraestructura subterránea bajo las vías.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen relevante para la instalación, asegurando la adecuada cobertura y protección de la infraestructura subterránea bajo las vías.)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante para la instalación, asegurando la adecuada cobertura y protección de la infraestructura subterránea bajo las vías.

## 20. single_L2_expansion_360475cbde
- **item_key:** `OEB070afaa`  (modifications: 1)
- expansion[L %B=f]: 'Cualquier franja horaria excepcional' → 'Cualquier franja horaria excepcional, incluyendo aquellas que requieran coordinación adicional con el operador ferroviario para minimizar el impacto en el servicio.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Cualquier franja horaria excepcional, incluyendo aquellas que requieran coordinación adicional con el operador ferroviario para minimizar el impacto en el servicio./i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria excepcional, incluyendo aquellas que requieran coordinación adicional con el operador ferroviario para minimizar el impacto en el servicio. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 21. single_L2_expansion_39ab8632da
- **item_key:** `OEB070aeaa`  (modifications: 1)
- expansion[L %B=e]: 'Cualquier frana horaria' → 'Cualquier fractura o desplazamiento horizontal en la estructura del terreno que pueda afectar la instalación'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Cualquier fractura o desplazamiento horizontal en la estructura del terreno que pueda afectar la instalación/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 22. single_L2_expansion_54b9703a3f
- **item_key:** `OEB070adaa`  (modifications: 1)
- expansion[L %B=d]: 'Nocturno Excepcional' → 'Ejecución nocturna excepcional, programada fuera de los horarios habituales para minimizar el impacto en el tráfico ferroviario.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Ejecución nocturna excepcional, programada fuera de los horarios habituales para minimizar el impacto en el tráfico ferroviario./i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Ejecución nocturna excepcional, programada fuera de los horarios habituales para minimizar el impacto en el tráfico ferroviario. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 23. single_L2_expansion_96f2800a0d
- **item_key:** `OEB070aaab`  (modifications: 1)
- expansion[N %D=b]: 'Volumen escaso' → 'Volumen escaso, indicando una cantidad mínima requerida para la instalación específica bajo las vías.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen escaso, indicando una cantidad mínima requerida para la instalación específica bajo las vías.)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen escaso, indicando una cantidad mínima requerida para la instalación específica bajo las vías.

## 24. single_L2_expansion_96f4959920
- **item_key:** `OEB070acaa`  (modifications: 1)
- expansion[L %B=c]: 'Diurno Excepcional' → 'Ejecución durante el horario diurno, considerado como excepcional debido a las restricciones operativas normales en el entorno ferroviario.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Ejecución durante el horario diurno, considerado como excepcional debido a las restricciones operativas normales en el entorno ferroviario./i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Ejecución durante el horario diurno, considerado como excepcional debido a las restricciones operativas normales en el entorno ferroviario. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 25. single_L2_expansion_d210015d76
- **item_key:** `OEB070aaaa`  (modifications: 1)
- expansion[L %B=a]: 'Diurno' → 'Ejecución durante el horario diurno, en horas de luz natural, para facilitar la visibilidad y seguridad en la obra.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Ejecución durante el horario diurno, en horas de luz natural, para facilitar la visibilidad y seguridad en la obra./i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Ejecución durante el horario diurno, en horas de luz natural, para facilitar la visibilidad y seguridad en la obra. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 26. single_L2_expansion_e8678926a6
- **item_key:** `OEB070abaa`  (modifications: 1)
- expansion[L %B=b]: 'Nocturno' → 'Ejecución nocturna para minimizar interrupciones en el tráfico ferroviario'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Ejecución nocturna para minimizar interrupciones en el tráfico ferroviario/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Ejecución nocturna para minimizar interrupciones en el tráfico ferroviario Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 27. single_L2_paraphrase_0395d36106
- **item_key:** `OEB070aaac`  (modifications: 1)
- paraphrase[N %D=c]: 'Cualquier condición de ejecución' → 'En cualquier circunstancia de instalación'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/En cualquier circunstancia de instalación)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: En cualquier circunstancia de instalación

## 28. single_L2_paraphrase_0afab6ef1a
- **item_key:** `OEB070aaab`  (modifications: 1)
- paraphrase[N %D=b]: 'Volumen escaso' → 'Cantidad reducida'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Cantidad reducida)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Cantidad reducida

## 29. single_L2_paraphrase_12a414eb90
- **item_key:** `OEB070afaa`  (modifications: 1)
- paraphrase[L %B=f]: 'Cualquier franja horaria excepcional' → 'Horario extraordinario aplicable'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Horario extraordinario aplicable/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Horario extraordinario aplicable Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 30. single_L2_paraphrase_69669a5c45
- **item_key:** `OEB070acaa`  (modifications: 1)
- paraphrase[L %B=c]: 'Diurno Excepcional' → 'Horario Especial de Día'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Horario Especial de Día/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Horario Especial de Día Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 31. single_L2_paraphrase_973e276f97
- **item_key:** `OEB070aeaa`  (modifications: 1)
- paraphrase[L %B=e]: 'Cualquier frana horaria' → 'Cualquier deslizamiento lateral'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Cualquier deslizamiento lateral/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

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

## 35. single_L2_paraphrase_ed38f4f51c
- **item_key:** `OEB070adaa`  (modifications: 1)
- paraphrase[L %B=d]: 'Nocturno Excepcional' → 'Instalación Nocturna Especial'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Instalación Nocturna Especial/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Instalación Nocturna Especial Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

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

## 42. stacked_2_b69b4cacd1
- **item_key:** `OEB070aeaa`  (modifications: 2)
- compression[L %B=e]: 'Cualquier frana horaria' → 'Frana horaria'
- paraphrase[N %D=a]: 'Volumen relevante' → 'Cantidad significativa'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Frana horaria/i >==5 horas/Cantidad significativa)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Cantidad significativa

## 43. stacked_3_57830a3d2f
- **item_key:** _(no materialized leaves)_  (modifications: 2)
- compression[N %D=a]: 'Volumen relevante' → 'Volumen %D'
- omission[RESUMEN]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))' → 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C))'

## 44. stacked_4_de3be54965
- **item_key:** `OEB070acaa`  (modifications: 3)
- compression[L %B=d]: 'Nocturno Excepcional' → 'Nocturno'
- paraphrase[L %B=e]: 'Cualquier frana horaria' → 'Cualquier deslizamiento lateral'
- compression[L %B=c]: 'Diurno Excepcional' → 'Excepcional Diurno'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Excepcional Diurno/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Excepcional Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 45. stacked_5plus_f6b079f197
- **item_key:** `OEB070aeaa`  (modifications: 3)
- compression[L %B=f]: 'Cualquier franja horaria excepcional' → 'Horario excepcional'
- compression[L %B=e]: 'Cualquier frana horaria' → 'Frana horaria'
- expansion[N %D=a]: 'Volumen relevante' → 'Volumen relevante para la instalación de infraestructura subterránea bajo las vías, asegurando la adecuada distribución y funcionalidad del sistema.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Frana horaria/i >==5 horas/Volumen relevante para la instalación de infraestructura subterránea bajo las vías, asegurando la adecuada distribución y funcionalidad del sistema.)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante para la instalación de infraestructura subterránea bajo las vías, asegurando la adecuada distribución y funcionalidad del sistema.
