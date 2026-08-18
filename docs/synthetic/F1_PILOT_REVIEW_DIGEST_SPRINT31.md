# Review Digest — OEB070$ (Sprint 31 replay, llama3.1:8b transcripts + new plumbing)

38 distinct variants (representative leaf per variant chosen to exhibit each modification's condition).

## 1. full_random_mix_59b36b9a82
- **item_key:** `OEB070adac`  (modifications: 5)
- synonym_label[D]: 'Volumen relevante' → 'Volumen significativo'
- synonym_label[D]: 'Volumen escaso' → 'Volumen limitado'
- synonym_label[D]: 'Cualquier condición de ejecución' → 'Condiciones de trabajo variables'
- expansion[L %B=a]: 'Diurno' → 'Realizado durante la jornada diurna, es decir, entre las 7:00 y las 19:00 horas, con el fin de evitar interferencias con el tráfico ferroviario nocturno.'
- compression[L %B=d]: 'Nocturno Excepcional' → 'Noche'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Noche/i >==5 horas/Condiciones de trabajo variables)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Noche Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Condiciones de trabajo variables

## 2. new_param_only_49fe3d7598
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- new_param: '?' → 'TIPO DE CONEXIÓN'

## 3. single_L1_num_to_text_2d7b482a2a
- **item_key:** `OEB070baaa`  (modifications: 2)
- num_to_text[A]: '1' → 'uno'
- num_to_text[A]: '2' → 'dos'
- **resumen:** Suministro y ejecución de canalización de dos tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de dos tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 4. single_L1_synonym_label_314e7dfdb3
- **item_key:** `OEB070aada`  (modifications: 3)
- synonym_label[C]: '3 <= i < 5 horas' → 'Mantenimiento diurno'
- synonym_label[C]: 'i < 3 horas' → 'Mantenimiento nocturno'
- synonym_label[C]: 'No necesita intervalo' → 'Sin mantenimiento programado'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/No necesita intervalo/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento: Sin mantenimiento programado Condiciones de ejecución: Volumen relevante

## 5. single_L1_synonym_label_333a950e94
- **item_key:** `OEB070aaac`  (modifications: 3)
- synonym_label[D]: 'Volumen relevante' → 'Volumen significativo'
- synonym_label[D]: 'Volumen escaso' → 'Volumen limitado'
- synonym_label[D]: 'Cualquier condición de ejecución' → 'Condiciones de trabajo variables'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Condiciones de trabajo variables)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Condiciones de trabajo variables

## 6. single_L1_synonym_label_9468265cff
- **item_key:** `OEB070afaa`  (modifications: 6)
- synonym_label[B]: 'Diurno' → 'Horario de luz solar'
- synonym_label[B]: 'Nocturno' → 'Horario de oscuridad'
- synonym_label[B]: 'Diurno Excepcional' → 'Horario de luz solar con restricciones'
- synonym_label[B]: 'Nocturno Excepcional' → 'Horario de oscuridad con restricciones'
- synonym_label[B]: 'Cualquier franja horaria' → 'Horario flexible'
- synonym_label[B]: 'Cualquier franja horaria excepcional' → 'Horario flexible con restricciones'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Horario flexible con restricciones/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Horario flexible con restricciones Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 7. single_L1_unit_conversion_5e0a6c028e
- **item_key:** `OEB070aada`  (modifications: 3)
- unit_conversion[C]: '3 <= i < 5 horas' → '180 <= i < 300 minutos'
- unit_conversion[C]: 'i < 3 horas' → 'i < 180 minutos'
- unit_conversion[C]: 'No necesita intervalo' → 'No necesita intervalo'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/No necesita intervalo/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento: No necesita intervalo Condiciones de ejecución: Volumen relevante

## 8. single_L1_unit_expansion_f20e0423ca
- **item_key:** `OEB070aada`  (modifications: 3)
- unit_expansion[C]: '3 <= i < 5 horas' → '3 <= i < 5 horas'
- unit_expansion[C]: 'i < 3 horas' → 'i < 3 horas'
- unit_expansion[C]: 'No necesita intervalo' → 'No necesita intervalo'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/No necesita intervalo/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento: No necesita intervalo Condiciones de ejecución: Volumen relevante

## 9. single_L2_compression_05659b80f6
- **item_key:** `OEB070aaac`  (modifications: 1)
- compression[N %D=c]: 'Cualquier condición de ejecución' → 'Condición de ejecución cualquiera'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Condición de ejecución cualquiera)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Condición de ejecución cualquiera

## 10. single_L2_compression_089b050153
- **item_key:** `OEB070aaaa`  (modifications: 1)
- compression[N %D=a]: 'Volumen relevante' → 'Volumen'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen

## 11. single_L2_compression_337e6fdb64
- **item_key:** `OEB070abaa`  (modifications: 1)
- compression[L %B=c]: 'Diurno Excepcional' → 'Diurno'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Nocturno/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Nocturno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 12. single_L2_compression_5a596d6b99
- **item_key:** `OEB070abaa`  (modifications: 1)
- compression[L %B=b]: 'Nocturno' → 'Noche'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Noche/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Noche Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 13. single_L2_compression_5c0d5650ac
- **item_key:** `OEB070afaa`  (modifications: 1)
- compression[L %B=f]: 'Cualquier franja horaria excepcional' → 'Franja horaria excepcional'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Franja horaria excepcional/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Franja horaria excepcional Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 14. single_L2_compression_8fada2a686
- **item_key:** `OEB070aaab`  (modifications: 1)
- compression[N %D=b]: 'Volumen escaso' → 'Volumen limitado'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen limitado)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen limitado

## 15. single_L2_compression_95e182db65
- **item_key:** `OEB070adaa`  (modifications: 1)
- compression[L %B=d]: 'Nocturno Excepcional' → 'Noche'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Noche/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Noche Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 16. single_L2_compression_a67ec5bae5
- **item_key:** `OEB070aeaa`  (modifications: 1)
- compression[L %B=e]: 'Cualquier frana horaria' → 'Frana horaria'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Frana horaria/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 17. single_L2_compression_c9ea0962ce
- **item_key:** `OEB070aaaa`  (modifications: 1)
- compression[L %B=a]: 'Diurno' → 'Diurno'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 18. single_L2_expansion_cc0082f1ab
- **item_key:** `OEB070aeaa`  (modifications: 1)
- expansion[L %B=e]: 'Cualquier frana horaria' → 'Cualquier frana horaria que se produzca durante la ejecución de la obra'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Cualquier frana horaria que se produzca durante la ejecución de la obra/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 19. single_L2_expansion_d4540f468d
- **item_key:** `OEB070aaac`  (modifications: 1)
- expansion[N %D=c]: 'Cualquier condición de ejecución' → 'Cualquier condición de ejecución, incluyendo cambios en el terreno, presencia de obstáculos subterráneos o necesidades de adaptación de la canalización'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Cualquier condición de ejecución, incluyendo cambios en el terreno, presencia de obstáculos subterráneos o necesidades de adaptación de la canalización)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Cualquier condición de ejecución, incluyendo cambios en el terreno, presencia de obstáculos subterráneos o necesidades de adaptación de la canalización

## 20. single_L2_expansion_e8c70cccbe
- **item_key:** `OEB070afaa`  (modifications: 1)
- expansion[L %B=f]: 'Cualquier franja horaria excepcional' → 'Cualquier franja horaria excepcional que se produzca fuera de la franja horaria normal de trabajo, definida como la franja horaria comprendida entre las 8:00 y las 18:00 horas, de lunes a viernes, excluyendo festivos y días de descanso'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Cualquier franja horaria excepcional que se produzca fuera de la franja horaria normal de trabajo, definida como la franja horaria comprendida entre las 8:00 y las 18:00 horas, de lunes a viernes, excluyendo festivos y días de descanso/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria excepcional que se produzca fuera de la franja horaria normal de trabajo, definida como la franja horaria comprendida entre las 8:00 y las 18:00 horas, de lunes a viernes, excluyendo festivos y días de descanso Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 21. single_L2_expansion_ebbd47217e
- **item_key:** `OEB070abaa`  (modifications: 1)
- expansion[L %B=b]: 'Nocturno' → 'Nocturno, con ejecución bajo condiciones de iluminación reducida y sin interrupción del tráfico ferroviario'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Nocturno, con ejecución bajo condiciones de iluminación reducida y sin interrupción del tráfico ferroviario/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Nocturno, con ejecución bajo condiciones de iluminación reducida y sin interrupción del tráfico ferroviario Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 22. single_L2_expansion_ed4d99d62f
- **item_key:** `OEB070aaaa`  (modifications: 1)
- expansion[L %B=a]: 'Diurno' → 'Realizado durante la jornada diurna, es decir, entre las 7:00 y las 19:00 horas, con el fin de evitar interferencias con el tráfico ferroviario nocturno.'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Realizado durante la jornada diurna, es decir, entre las 7:00 y las 19:00 horas, con el fin de evitar interferencias con el tráfico ferroviario nocturno./i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Realizado durante la jornada diurna, es decir, entre las 7:00 y las 19:00 horas, con el fin de evitar interferencias con el tráfico ferroviario nocturno. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 23. single_L2_paraphrase_1dbbcafa03
- **item_key:** `OEB070adaa`  (modifications: 1)
- paraphrase[L %B=d]: 'Nocturno Excepcional' → 'Noche'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Noche/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Noche Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 24. single_L2_paraphrase_33354d49d5
- **item_key:** `OEB070acaa`  (modifications: 1)
- paraphrase[L %B=c]: 'Diurno Excepcional' → 'Día normal'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Día normal/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Día normal Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 25. single_L2_paraphrase_8345d65fa1
- **item_key:** `OEB070afaa`  (modifications: 1)
- paraphrase[L %B=f]: 'Cualquier franja horaria excepcional' → 'Horarios fuera del horario normal'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Horarios fuera del horario normal/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Horarios fuera del horario normal Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 26. single_L2_paraphrase_97fcbf4e22
- **item_key:** `OEB070aeaa`  (modifications: 1)
- paraphrase[L %B=e]: 'Cualquier frana horaria' → 'Cualquier frana en la zona horaria'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Cualquier frana en la zona horaria/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 27. single_L2_paraphrase_a2a21087b5
- **item_key:** `OEB070aaaa`  (modifications: 1)
- paraphrase[N %D=a]: 'Volumen relevante' → 'Volumen de excavación'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen de excavación)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen de excavación

## 28. single_L2_paraphrase_b7d7a012ac
- **item_key:** `OEB070aaab`  (modifications: 1)
- paraphrase[N %D=b]: 'Volumen escaso' → 'Volumen insuficiente'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen insuficiente)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen insuficiente

## 29. single_L2_paraphrase_bb2be41ed3
- **item_key:** `OEB070abaa`  (modifications: 1)
- paraphrase[L %B=b]: 'Nocturno' → 'Bajo la luz de la luna'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Bajo la luz de la luna/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Bajo la luz de la luna Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 30. single_L2_paraphrase_d9afcba08d
- **item_key:** `OEB070aaaa`  (modifications: 1)
- paraphrase[L %B=a]: 'Diurno' → 'Día'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Día/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Día Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 31. single_L2_paraphrase_fa62fcad9d
- **item_key:** `OEB070aaac`  (modifications: 1)
- paraphrase[N %D=c]: 'Cualquier condición de ejecución' → 'Ejecución bajo cualquier condición'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Ejecución bajo cualquier condición)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Ejecución bajo cualquier condición

## 32. single_L3_omission_a516ff61df
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- omission[RESUMEN]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))' → 'Suministro y ejecución de canalización de tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))'

## 33. single_L3_omission_cacf7915c2
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- omission[RESUMEN]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))' → 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$N(%D))'

## 34. single_L3_omission_e7670ffcba
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- omission[RESUMEN]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))' → 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C))'

## 35. stacked_2_e605322e03
- **item_key:** `OEB070aeaa`  (modifications: 2)
- compression[L %B=e]: 'Cualquier frana horaria' → 'Frana horaria'
- paraphrase[N %D=a]: 'Volumen relevante' → 'Volumen de excavación'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Frana horaria/i >==5 horas/Volumen de excavación)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen de excavación

## 36. stacked_3_75c8d5e7be
- **item_key:** _(no materialized leaves)_  (modifications: 2)
- compression[N %D=a]: 'Volumen relevante' → 'Volumen'
- omission[RESUMEN]: 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))' → 'Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C))'

## 37. stacked_4_9afdfde661
- **item_key:** `OEB070abaa`  (modifications: 3)
- compression[L %B=d]: 'Nocturno Excepcional' → 'Noche'
- paraphrase[L %B=e]: 'Cualquier frana horaria' → 'Cualquier frana en la zona horaria'
- compression[L %B=c]: 'Diurno Excepcional' → 'Diurno'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Nocturno/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Nocturno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 38. stacked_5plus_2810585673
- **item_key:** `OEB070aeaa`  (modifications: 2)
- compression[L %B=f]: 'Cualquier franja horaria excepcional' → 'Franja horaria excepcional'
- compression[L %B=e]: 'Cualquier frana horaria' → 'Frana horaria'
- **resumen:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías (Frana horaria/i >==5 horas/Volumen relevante)
- **texto:** Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante
