# Review Digest — OEB020$ (Sprint 35 sanity check, phi4:latest, seed 7)

112 distinct variants (representative leaf per variant chosen to exhibit each modification's condition).

## 1. full_random_mix_dbab3b1771
- **item_key:** `OEB020aaaaa`  (modifications: 2)
- compression[K %B=="c"]: 'rocoso' → 'rocoso'
- paraphrase[I %B=="a"]: 'en cualquier clase de terreno, excepto roca' → 'en cualquier tipo de suelo, salvo en roca'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier tipo de suelo, salvo en roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 2. new_param_only_972d7f6e76
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- new_param: '?' → 'MATERIAL DE AISLAMIENTO'

## 3. single_L1_synonym_label_666800912d
- **item_key:** `OEB020aaada`  (modifications: 3)
- synonym_label[D]: '3 <= i < 5 horas' → 'Mantenimiento Moderado'
- synonym_label[D]: 'i < 3 horas' → 'Mantenimiento Breve'
- synonym_label[D]: 'No necesita intervalo' → 'Sin Mantenimiento'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno/No necesita intervalo/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento: Sin Mantenimiento Condiciones de ejecución: Volumen relevante

## 4. single_L1_synonym_label_7279a01c30
- **item_key:** `OEB020aafaa`  (modifications: 6)
- synonym_label[C]: 'Diurno' → 'Horario Normal'
- synonym_label[C]: 'Nocturno' → 'Horario Nocturno'
- synonym_label[C]: 'Diurno Excepcional' → 'Horario Diurno Especial'
- synonym_label[C]: 'Nocturno Excepcional' → 'Horario Nocturno Especial'
- synonym_label[C]: 'Cualquier franja horaria' → 'Horario Flexible'
- synonym_label[C]: 'Cualquier franja horaria excepcional' → 'Horario Flexible Especial'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Horario Flexible Especial/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Horario Flexible Especial Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 5. single_L1_synonym_label_919149d9dd
- **item_key:** `OEB020aaaac`  (modifications: 3)
- synonym_label[F]: 'Volumen relevante' → 'Alto Volumen'
- synonym_label[F]: 'Volumen escaso' → 'Bajo Volumen'
- synonym_label[F]: 'Cualquier condición de ejecución' → 'Condiciones Generales'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno/i >==5 horas/Condiciones Generales)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Condiciones Generales

## 6. single_L1_synonym_label_c22857f617
- **item_key:** `OEB020ahaaa`  (modifications: 8)
- synonym_label[B]: 'Normal' → 'Terreno Estándar'
- synonym_label[B]: 'Bajo vías' → 'Subvías'
- synonym_label[B]: 'Rocoso' → 'Terreno Pedregoso'
- synonym_label[B]: 'Cruce de carretera' → 'Intersección Vial'
- synonym_label[B]: 'Andén' → 'Plataforma de Andén'
- synonym_label[B]: 'Adosada' → 'Contigua'
- synonym_label[B]: 'Balasto' → 'Subbalasto'
- synonym_label[B]: 'Con topo' → 'Con Topografía'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, con topo. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce bajo vías ejecutado con topo, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. Incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro. El suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 7. single_L1_unit_conversion_7342014358
- **item_key:** `OEB020aaada`  (modifications: 3)
- unit_conversion[D]: '3 <= i < 5 horas' → '3-5 h'
- unit_conversion[D]: 'i < 3 horas' → 'menos de 3 h'
- unit_conversion[D]: 'No necesita intervalo' → 'sin intervalo'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno/No necesita intervalo/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento: sin intervalo Condiciones de ejecución: Volumen relevante

## 8. single_L1_unit_expansion_fff0e23658
- **item_key:** `OEB020aaada`  (modifications: 3)
- unit_expansion[D]: '3 <= i < 5 horas' → 'Intervalo entre tres y cinco horas'
- unit_expansion[D]: 'i < 3 horas' → 'Intervalo menor a tres horas'
- unit_expansion[D]: 'No necesita intervalo' → 'Sin intervalo requerido'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno/No necesita intervalo/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento: Sin intervalo requerido Condiciones de ejecución: Volumen relevante

## 9. single_L2_compression_08b36def5f
- **item_key:** `OEB020aaaab`  (modifications: 1)
- compression[J %F=b]: 'Volumen escaso' → 'Volumen mínimo'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno/i >==5 horas/Volumen mínimo)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen mínimo

## 10. single_L2_compression_1572d618c4
- **item_key:** `OEB020aeaaa`  (modifications: 1)
- compression[K %B=="e"]: 'en andén' → 'en andén'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en andén. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en andén, incluso la demolición y la reposición del pavimento y la solera, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 11. single_L2_compression_15ce2fd3e5
- **item_key:** `OEB020ahaaa`  (modifications: 1)
- compression[K %B=="h"]: 'con topo' → 'topo'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, topo. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce bajo vías ejecutado con topo, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. Incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro. El suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 12. single_L2_compression_260a597abf
- **item_key:** `OEB020aaaaa`  (modifications: 1)
- compression[I %B=="a"]: 'en cualquier clase de terreno, excepto roca' → 'en cualquier terreno, no roca'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier terreno, no roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 13. single_L2_compression_27fceed447
- **item_key:** `OEB020acaaa`  (modifications: 1)
- compression[N %B=="c"]: 'la demolición de roca dura,' → 'demolición de roca,'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, rocoso. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en terreno rocoso, incluso demolición de roca, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 14. single_L2_compression_2e7c2c7e16
- **item_key:** `OEB020aaaaa`  (modifications: 1)
- compression[G %C=a]: 'Diurno' → 'Horario diurno'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Horario diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Horario diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 15. single_L2_compression_44e126e688
- **item_key:** `OEB020afaaa`  (modifications: 1)
- compression[I %B=="f"]: 'adosada o superficial' → 'en superficie'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, adosada. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en superficie, incluso  el relleno y el compactado de la zanja, la preparación y nivelación de la solera, suministro y montaje del encofrado, elementos de fijación, desencofrado, el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 16. single_L2_compression_50539ff501
- **item_key:** `OEB020aaaaa`  (modifications: 1)
- compression[K %B=="a"]: 'normal' → 'estándar'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, estándar. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 17. single_L2_compression_535485aeb3
- **item_key:** `OEB020agaaa`  (modifications: 1)
- compression[K %B=="g"]: 'en balasto' → 'balasto'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, balasto. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en zona de balasto, incluso el descerne y la entibación de los costados y la posterior reposición del balasto retirado, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 18. single_L2_compression_67648d4bc7
- **item_key:** `OEB020abaaa`  (modifications: 1)
- compression[N %B=="b"  or  %B=="g"]: 'el descerne y la entibación de los costados y la posterior reposición del balasto retirado,' → 'descerne, entibación y reposición del balasto,'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, bajo vías. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce bajo vías, incluso descerne, entibación y reposición del balasto, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 19. single_L2_compression_6af0d30a82
- **item_key:** `OEB020aaaac`  (modifications: 1)
- compression[J %F=c]: 'Cualquier condición de ejecución' → 'Ejecución variable'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno/i >==5 horas/Ejecución variable)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Ejecución variable

## 20. single_L2_compression_6f4e9484f6
- **item_key:** `OEB020ahaaa`  (modifications: 1)
- compression[I %B=="h"]: 'en cruce bajo vías ejecutado con topo' → 'bajo vías con topo'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, con topo. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro bajo vías con topo, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. Incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro. El suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 21. single_L2_compression_6fb00590f9
- **item_key:** `OEB020ahaaa`  (modifications: 1)
- compression[M %B=="h"]: 'Incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro. El suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido.' → 'Construcción del pozo, entibación, tubo guía de 500 mm, hilos guía y sellado con poliuretano.'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, con topo. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce bajo vías ejecutado con topo, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. Construcción del pozo, entibación, tubo guía de 500 mm, hilos guía y sellado con poliuretano. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 22. single_L2_compression_82d5925c6f
- **item_key:** `OEB020aacaa`  (modifications: 1)
- compression[G %C=c]: 'Diurno Excepcional' → 'Diurno Especial'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno Especial/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Especial Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 23. single_L2_compression_8e0be61053
- **item_key:** `OEB020aabaa`  (modifications: 1)
- compression[G %C=b]: 'Nocturno' → 'Noche'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Noche/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Noche Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 24. single_L2_compression_8e9692c00b
- **item_key:** `OEB020adaaa`  (modifications: 1)
- compression[K %B=="d"]: 'en cruce de carretera' → 'en cruce'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en cruce. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce de carretera, incluso  la demolición y la reposición del firme y del pavimento, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 25. single_L2_compression_8fd2aa65e6
- **item_key:** `OEB020aeaaa`  (modifications: 1)
- compression[N %B=="e"]: 'la demolición y la reposición del pavimento y la solera,' → 'demolición y reposición del pavimento y solera,'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en andén. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en andén, incluso demolición y reposición del pavimento y solera, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 26. single_L2_compression_91e565b91c
- **item_key:** `OEB020acaaa`  (modifications: 1)
- compression[I %B=="c"]: 'en terreno rocoso' → 'en roca'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, rocoso. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en roca, incluso la demolición de roca dura, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 27. single_L2_compression_93688ed69a
- **item_key:** `OEB020abaaa`  (modifications: 1)
- compression[K %B=="b"]: 'bajo vías' → 'subvías'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, subvías. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce bajo vías, incluso el descerne y la entibación de los costados y la posterior reposición del balasto retirado, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 28. single_L2_compression_958ed733cf
- **item_key:** `OEB020agaaa`  (modifications: 1)
- compression[I %B=="g"]: 'en zona de balasto' → 'en balasto'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en balasto. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en balasto, incluso el descerne y la entibación de los costados y la posterior reposición del balasto retirado, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 29. single_L2_compression_9d93d0070c
- **item_key:** `OEB020adaaa`  (modifications: 1)
- compression[I %B=="d"]: 'en cruce de carretera' → 'en cruce carretera'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en cruce de carretera. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce carretera, incluso  la demolición y la reposición del firme y del pavimento, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 30. single_L2_compression_aa42af6659
- **item_key:** `OEB020afaaa`  (modifications: 1)
- compression[P %B=="f"]: 'la preparación y nivelación de la solera, suministro y montaje del encofrado, elementos de fijación, desencofrado,' → 'nivelación de la solera, suministro y montaje del encofrado, fijación, desencofrado,'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, adosada. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro adosada o superficial, incluso  el relleno y el compactado de la zanja, nivelación de la solera, suministro y montaje del encofrado, fijación, desencofrado, el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 31. single_L2_compression_ac63113f14
- **item_key:** `OEB020afaaa`  (modifications: 1)
- compression[K %B=="f"]: 'adosada' → 'en muro'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en muro. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro adosada o superficial, incluso  el relleno y el compactado de la zanja, la preparación y nivelación de la solera, suministro y montaje del encofrado, elementos de fijación, desencofrado, el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 32. single_L2_compression_bb1f0aba92
- **item_key:** `OEB020adaaa`  (modifications: 1)
- compression[N %B=="d"]: ' la demolición y la reposición del firme y del pavimento,' → 'demolición y reposición del firme y pavimento,'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en cruce de carretera. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce de carretera, incluso demolición y reposición del firme y pavimento, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 33. single_L2_compression_c173f1aa33
- **item_key:** `OEB020acaaa`  (modifications: 1)
- compression[K %B=="c"]: 'rocoso' → 'rocoso'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, rocoso. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en terreno rocoso, incluso la demolición de roca dura, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 34. single_L2_compression_d73d6b89ab
- **item_key:** `OEB020aafaa`  (modifications: 1)
- compression[G %C=f]: 'Cualquier franja horaria excepcional' → 'Horario Excepcional'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Horario Excepcional/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Horario Excepcional Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 35. single_L2_compression_da387156fd
- **item_key:** `OEB020aadaa`  (modifications: 1)
- compression[G %C=d]: 'Nocturno Excepcional' → 'Nocturno Especial'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Nocturno Especial/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Nocturno Especial Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 36. single_L2_compression_da942113ef
- **item_key:** `OEB020aeaaa`  (modifications: 1)
- compression[I %B=="e"]: 'en andén' → 'en andén'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en andén. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en andén, incluso la demolición y la reposición del pavimento y la solera, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 37. single_L2_compression_e8953c568f
- **item_key:** `OEB020abaaa`  (modifications: 1)
- compression[I %B=="b"]: 'en cruce bajo vías' → 'bajo vías'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, bajo vías. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro bajo vías, incluso el descerne y la entibación de los costados y la posterior reposición del balasto retirado, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 38. single_L2_compression_eb4a58a077
- **item_key:** `OEB020aaeaa`  (modifications: 1)
- compression[G %C=e]: 'Cualquier frana horaria' → 'Cualquier franja'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Cualquier franja/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 39. single_L2_compression_ed82ab9885
- **item_key:** `OEB020aaaaa`  (modifications: 1)
- compression[J %F=a]: 'Volumen relevante' → 'Volumen alto'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno/i >==5 horas/Volumen alto)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen alto

## 40. single_L2_expansion_0b26fc345b
- **item_key:** `OEB020aaaab`  (modifications: 1)
- expansion[J %F=b]: 'Volumen escaso' → 'Volumen escaso, adecuado para instalaciones donde el espacio es limitado y se requiere una solución compacta.'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno/i >==5 horas/Volumen escaso, adecuado para instalaciones donde el espacio es limitado y se requiere una solución compacta.)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen escaso, adecuado para instalaciones donde el espacio es limitado y se requiere una solución compacta.

## 41. single_L2_expansion_204e659e17
- **item_key:** `OEB020abaaa`  (modifications: 1)
- expansion[K %B=="b"]: 'bajo vías' → 'bajo vías, instalada en el subsuelo directamente debajo de las vías férreas para proteger y gestionar el drenaje de aguas subterráneas'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, bajo vías, instalada en el subsuelo directamente debajo de las vías férreas para proteger y gestionar el drenaje de aguas subterráneas. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce bajo vías, incluso el descerne y la entibación de los costados y la posterior reposición del balasto retirado, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 42. single_L2_expansion_22663a6d65
- **item_key:** `OEB020acaaa`  (modifications: 1)
- expansion[K %B=="c"]: 'rocoso' → 'rocoso, adecuado para terrenos con presencia significativa de rocas y piedras, que requieren una canalización robusta para evitar daños.'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, rocoso, adecuado para terrenos con presencia significativa de rocas y piedras, que requieren una canalización robusta para evitar daños.. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en terreno rocoso, incluso la demolición de roca dura, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 43. single_L2_expansion_2c55b000a9
- **item_key:** `OEB020agaaa`  (modifications: 1)
- expansion[I %B=="g"]: 'en zona de balasto' → 'en zona de balasto, específicamente en la capa de piedras que soporta y protege las vías férreas, permitiendo una adecuada drenaje y estabilidad'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en balasto. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en zona de balasto, específicamente en la capa de piedras que soporta y protege las vías férreas, permitiendo una adecuada drenaje y estabilidad, incluso el descerne y la entibación de los costados y la posterior reposición del balasto retirado, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 44. single_L2_expansion_2eae5b90dc
- **item_key:** `OEB020aaaaa`  (modifications: 1)
- expansion[J %F=a]: 'Volumen relevante' → 'Volumen relevante para la instalación, asegurando un suministro adecuado durante la ejecución del proyecto.'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno/i >==5 horas/Volumen relevante para la instalación, asegurando un suministro adecuado durante la ejecución del proyecto.)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante para la instalación, asegurando un suministro adecuado durante la ejecución del proyecto.

## 45. single_L2_expansion_31fc247d6e
- **item_key:** `OEB020aacaa`  (modifications: 1)
- expansion[G %C=c]: 'Diurno Excepcional' → 'Diurno Excepcional, aplicable a situaciones específicas durante el horario de trabajo regular que requieren atención inmediata.'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno Excepcional, aplicable a situaciones específicas durante el horario de trabajo regular que requieren atención inmediata./i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Excepcional, aplicable a situaciones específicas durante el horario de trabajo regular que requieren atención inmediata. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 46. single_L2_expansion_331368e51f
- **item_key:** `OEB020ahaaa`  (modifications: 1)
- expansion[M %B=="h"]: 'Incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro. El suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido.' → 'Incluso la construcción del pozo de ataque, que implica la excavación y preparación del área para la instalación, entibación de los costados para asegurar la estabilidad durante la construcción, instalación de un tubo guía de acero de 500 mm de diámetro para facilitar el alineamiento y posicionamiento. El suministro y montaje de los hilos guía, que dirigen el posicionamiento preciso de la canalización, y el sellado de las embocaduras con poliuretano expandido para garantizar la estanqueidad y protección contra filtraciones.'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, con topo. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce bajo vías ejecutado con topo, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. Incluso la construcción del pozo de ataque, que implica la excavación y preparación del área para la instalación, entibación de los costados para asegurar la estabilidad durante la construcción, instalación de un tubo guía de acero de 500 mm de diámetro para facilitar el alineamiento y posicionamiento. El suministro y montaje de los hilos guía, que dirigen el posicionamiento preciso de la canalización, y el sellado de las embocaduras con poliuretano expandido para garantizar la estanqueidad y protección contra filtraciones. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 47. single_L2_expansion_37dd9e28f2
- **item_key:** `OEB020abaaa`  (modifications: 1)
- expansion[N %B=="b"  or  %B=="g"]: 'el descerne y la entibación de los costados y la posterior reposición del balasto retirado,' → 'el descerne y la entibación de los costados para asegurar la estabilidad durante la operación, seguido de la posterior reposición del balasto retirado para restaurar la superficie de rodadura,'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, bajo vías. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce bajo vías, incluso el descerne y la entibación de los costados para asegurar la estabilidad durante la operación, seguido de la posterior reposición del balasto retirado para restaurar la superficie de rodadura, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 48. single_L2_expansion_48d622d9bc
- **item_key:** `OEB020acaaa`  (modifications: 1)
- expansion[N %B=="c"]: 'la demolición de roca dura,' → 'la demolición de roca dura, incluyendo la fragmentación y el desmantelamiento de la estructura sólida y compacta,'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, rocoso. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en terreno rocoso, incluso la demolición de roca dura, incluyendo la fragmentación y el desmantelamiento de la estructura sólida y compacta, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 49. single_L2_expansion_4f89d317e6
- **item_key:** `OEB020adaaa`  (modifications: 1)
- expansion[K %B=="d"]: 'en cruce de carretera' → 'en cruce de carretera, donde la canalización se integra en el diseño estructural para permitir el paso seguro de vehículos y trenes'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en cruce de carretera, donde la canalización se integra en el diseño estructural para permitir el paso seguro de vehículos y trenes. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce de carretera, incluso  la demolición y la reposición del firme y del pavimento, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 50. single_L2_expansion_5d9a9c16dd
- **item_key:** `OEB020aaaaa`  (modifications: 1)
- expansion[K %B=="a"]: 'normal' → 'instalación estándar en condiciones normales de suelo, sin requerimientos especiales de soporte o protección adicional'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, instalación estándar en condiciones normales de suelo, sin requerimientos especiales de soporte o protección adicional. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 51. single_L2_expansion_5fe5e1ec85
- **item_key:** `OEB020aeaaa`  (modifications: 1)
- expansion[I %B=="e"]: 'en andén' → 'en andén, específicamente en la plataforma destinada para el tránsito y estacionamiento de trenes, asegurando la correcta canalización de aguas pluviales'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en andén. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en andén, específicamente en la plataforma destinada para el tránsito y estacionamiento de trenes, asegurando la correcta canalización de aguas pluviales, incluso la demolición y la reposición del pavimento y la solera, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 52. single_L2_expansion_642cff3c90
- **item_key:** `OEB020afaaa`  (modifications: 1)
- expansion[I %B=="f"]: 'adosada o superficial' → 'instalada adosada o superficialmente, dependiendo de las condiciones del terreno y las especificaciones del proyecto'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, adosada. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro instalada adosada o superficialmente, dependiendo de las condiciones del terreno y las especificaciones del proyecto, incluso  el relleno y el compactado de la zanja, la preparación y nivelación de la solera, suministro y montaje del encofrado, elementos de fijación, desencofrado, el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 53. single_L2_expansion_64e78de8ff
- **item_key:** `OEB020aadaa`  (modifications: 1)
- expansion[G %C=d]: 'Nocturno Excepcional' → 'Nocturno Excepcional, aplicable únicamente durante horarios nocturnos fuera de los estándares habituales.'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Nocturno Excepcional, aplicable únicamente durante horarios nocturnos fuera de los estándares habituales./i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Nocturno Excepcional, aplicable únicamente durante horarios nocturnos fuera de los estándares habituales. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 54. single_L2_expansion_76d6e4d108
- **item_key:** `OEB020aaaac`  (modifications: 1)
- expansion[J %F=c]: 'Cualquier condición de ejecución' → 'Cualquier condición de ejecución, incluyendo variaciones en el terreno o condiciones climáticas adversas, que puedan afectar la instalación.'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno/i >==5 horas/Cualquier condición de ejecución, incluyendo variaciones en el terreno o condiciones climáticas adversas, que puedan afectar la instalación.)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Cualquier condición de ejecución, incluyendo variaciones en el terreno o condiciones climáticas adversas, que puedan afectar la instalación.

## 55. single_L2_expansion_7961e0e4b9
- **item_key:** `OEB020agaaa`  (modifications: 1)
- expansion[K %B=="g"]: 'en balasto' → 'en balasto, que proporciona una base estable y permeable para la canalización, facilitando el drenaje y la estabilidad estructural'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en balasto, que proporciona una base estable y permeable para la canalización, facilitando el drenaje y la estabilidad estructural. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en zona de balasto, incluso el descerne y la entibación de los costados y la posterior reposición del balasto retirado, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 56. single_L2_expansion_87a8954493
- **item_key:** `OEB020ahaaa`  (modifications: 1)
- expansion[K %B=="h"]: 'con topo' → 'con topo, adecuada para instalación en terrenos con topografía irregular'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, con topo, adecuada para instalación en terrenos con topografía irregular. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce bajo vías ejecutado con topo, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. Incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro. El suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 57. single_L2_expansion_9b8af796b7
- **item_key:** `OEB020afaaa`  (modifications: 1)
- expansion[P %B=="f"]: 'la preparación y nivelación de la solera, suministro y montaje del encofrado, elementos de fijación, desencofrado,' → 'la preparación y nivelación meticulosa de la solera, suministro y montaje cuidadoso del encofrado, instalación de elementos de fijación adecuados, y el posterior desencofrado sistemático,'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, adosada. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro adosada o superficial, incluso  el relleno y el compactado de la zanja, la preparación y nivelación meticulosa de la solera, suministro y montaje cuidadoso del encofrado, instalación de elementos de fijación adecuados, y el posterior desencofrado sistemático, el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 58. single_L2_expansion_9d1300f859
- **item_key:** `OEB020aafaa`  (modifications: 1)
- expansion[G %C=f]: 'Cualquier franja horaria excepcional' → 'Cualquier franja horaria excepcional, incluyendo aquellas que no se ajustan a los horarios estándar diurnos o nocturnos, permitiendo flexibilidad en la programación de trabajos.'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Cualquier franja horaria excepcional, incluyendo aquellas que no se ajustan a los horarios estándar diurnos o nocturnos, permitiendo flexibilidad en la programación de trabajos./i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Cualquier franja horaria excepcional, incluyendo aquellas que no se ajustan a los horarios estándar diurnos o nocturnos, permitiendo flexibilidad en la programación de trabajos. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 59. single_L2_expansion_a98a0e073c
- **item_key:** `OEB020aeaaa`  (modifications: 1)
- expansion[N %B=="e"]: 'la demolición y la reposición del pavimento y la solera,' → 'la demolición y la reposición del pavimento y la solera, incluyendo la eliminación de los materiales existentes y la instalación de nuevas capas de pavimento y solera,'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en andén. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en andén, incluso la demolición y la reposición del pavimento y la solera, incluyendo la eliminación de los materiales existentes y la instalación de nuevas capas de pavimento y solera, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 60. single_L2_expansion_add2685bb6
- **item_key:** `OEB020aabaa`  (modifications: 1)
- expansion[G %C=b]: 'Nocturno' → 'Instalación nocturna, programada para ejecutarse durante las horas de la noche para minimizar el impacto en el tráfico ferroviario y la circulación pública.'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Instalación nocturna, programada para ejecutarse durante las horas de la noche para minimizar el impacto en el tráfico ferroviario y la circulación pública./i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Instalación nocturna, programada para ejecutarse durante las horas de la noche para minimizar el impacto en el tráfico ferroviario y la circulación pública. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 61. single_L2_expansion_af2b12a649
- **item_key:** `OEB020aaaaa`  (modifications: 1)
- expansion[I %B=="a"]: 'en cualquier clase de terreno, excepto roca' → 'en cualquier clase de terreno, incluyendo suelos arcillosos, arenosos o limosos, siempre que no se trate de terreno rocoso'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, incluyendo suelos arcillosos, arenosos o limosos, siempre que no se trate de terreno rocoso, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 62. single_L2_expansion_b562dd5c71
- **item_key:** `OEB020aeaaa`  (modifications: 1)
- expansion[K %B=="e"]: 'en andén' → 'en andén, específicamente en la plataforma de embarque o desembarque de pasajeros, donde se requiere una instalación segura y accesible para el tráfico ferroviario'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en andén, específicamente en la plataforma de embarque o desembarque de pasajeros, donde se requiere una instalación segura y accesible para el tráfico ferroviario. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en andén, incluso la demolición y la reposición del pavimento y la solera, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 63. single_L2_expansion_b8c7abcfde
- **item_key:** `OEB020aaaaa`  (modifications: 1)
- expansion[G %C=a]: 'Diurno' → 'Diurno, es decir, durante las horas de luz natural del día, típicamente entre las 6:00 a.m. y las 6:00 p.m.'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno, es decir, durante las horas de luz natural del día, típicamente entre las 6:00 a.m. y las 6:00 p.m./i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno, es decir, durante las horas de luz natural del día, típicamente entre las 6:00 a.m. y las 6:00 p.m. Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 64. single_L2_expansion_bb04151844
- **item_key:** `OEB020afaaa`  (modifications: 1)
- expansion[K %B=="f"]: 'adosada' → 'adosada, integrada directamente en la estructura existente para asegurar estabilidad y continuidad en la canalización.'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, adosada, integrada directamente en la estructura existente para asegurar estabilidad y continuidad en la canalización.. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro adosada o superficial, incluso  el relleno y el compactado de la zanja, la preparación y nivelación de la solera, suministro y montaje del encofrado, elementos de fijación, desencofrado, el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 65. single_L2_expansion_c7e129391b
- **item_key:** `OEB020abaaa`  (modifications: 1)
- expansion[I %B=="b"]: 'en cruce bajo vías' → 'en cruce bajo vías, donde la canalización se instala debajo de las vías férreas, asegurando protección y accesibilidad sin interferir con el tráfico ferroviario'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, bajo vías. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce bajo vías, donde la canalización se instala debajo de las vías férreas, asegurando protección y accesibilidad sin interferir con el tráfico ferroviario, incluso el descerne y la entibación de los costados y la posterior reposición del balasto retirado, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 66. single_L2_expansion_d482ef2a5a
- **item_key:** `OEB020adaaa`  (modifications: 1)
- expansion[I %B=="d"]: 'en cruce de carretera' → 'en cruce de carretera, donde la canalización debe atravesar la intersección de la vía férrea con la carretera, asegurando la integridad estructural y funcional en dicha intersección'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en cruce de carretera. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce de carretera, donde la canalización debe atravesar la intersección de la vía férrea con la carretera, asegurando la integridad estructural y funcional en dicha intersección, incluso  la demolición y la reposición del firme y del pavimento, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 67. single_L2_expansion_ddd958d5b1
- **item_key:** `OEB020aaeaa`  (modifications: 1)
- expansion[G %C=e]: 'Cualquier frana horaria' → 'Cualquier franja horaria, incluyendo todas las posibles divisiones del día para la instalación y mantenimiento.'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Cualquier franja horaria, incluyendo todas las posibles divisiones del día para la instalación y mantenimiento./i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 68. single_L2_expansion_e7173ec876
- **item_key:** `OEB020acaaa`  (modifications: 1)
- expansion[I %B=="c"]: 'en terreno rocoso' → 'en terreno rocoso, donde la dureza y resistencia del sustrato requieren técnicas específicas de excavación y anclaje para asegurar la estabilidad de la canalización.'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, rocoso. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en terreno rocoso, donde la dureza y resistencia del sustrato requieren técnicas específicas de excavación y anclaje para asegurar la estabilidad de la canalización., incluso la demolición de roca dura, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 69. single_L2_expansion_f48da39811
- **item_key:** `OEB020ahaaa`  (modifications: 1)
- expansion[I %B=="h"]: 'en cruce bajo vías ejecutado con topo' → 'en cruce bajo vías ejecutado con topografía precisa para asegurar alineación y nivelación adecuadas'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, con topo. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce bajo vías ejecutado con topografía precisa para asegurar alineación y nivelación adecuadas, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. Incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro. El suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 70. single_L2_expansion_f648f540da
- **item_key:** `OEB020adaaa`  (modifications: 1)
- expansion[N %B=="d"]: ' la demolición y la reposición del firme y del pavimento,' → 'la demolición y la reposición del firme y del pavimento, incluyendo la preparación del terreno y la compactación adecuada para asegurar la estabilidad y durabilidad del nuevo pavimento.'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en cruce de carretera. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce de carretera, incluso la demolición y la reposición del firme y del pavimento, incluyendo la preparación del terreno y la compactación adecuada para asegurar la estabilidad y durabilidad del nuevo pavimento. el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 71. single_L2_paraphrase_076568f136
- **item_key:** `OEB020aeaaa`  (modifications: 1)
- paraphrase[I %B=="e"]: 'en andén' → 'en plataforma de andén'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en andén. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en plataforma de andén, incluso la demolición y la reposición del pavimento y la solera, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 72. single_L2_paraphrase_0a1d194234
- **item_key:** `OEB020afaaa`  (modifications: 1)
- paraphrase[K %B=="f"]: 'adosada' → 'empotrada'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, empotrada. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro adosada o superficial, incluso  el relleno y el compactado de la zanja, la preparación y nivelación de la solera, suministro y montaje del encofrado, elementos de fijación, desencofrado, el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 73. single_L2_paraphrase_12173fdde0
- **item_key:** `OEB020aeaaa`  (modifications: 1)
- paraphrase[N %B=="e"]: 'la demolición y la reposición del pavimento y la solera,' → 'la eliminación y el reemplazo del pavimento y la base,'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en andén. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en andén, incluso la eliminación y el reemplazo del pavimento y la base, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 74. single_L2_paraphrase_17ec3dc06b
- **item_key:** `OEB020aaaaa`  (modifications: 1)
- paraphrase[K %B=="a"]: 'normal' → 'estándar'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, estándar. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 75. single_L2_paraphrase_366c0b58a1
- **item_key:** `OEB020adaaa`  (modifications: 1)
- paraphrase[I %B=="d"]: 'en cruce de carretera' → 'en intersección con carretera'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en cruce de carretera. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en intersección con carretera, incluso  la demolición y la reposición del firme y del pavimento, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 76. single_L2_paraphrase_42c3943736
- **item_key:** `OEB020ahaaa`  (modifications: 1)
- paraphrase[M %B=="h"]: 'Incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro. El suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido.' → 'Incluye la edificación del pozo de ataque, la entibación lateral, y la colocación de un tubo guía de acero de 500 mm de diámetro. Además, se suministran y montan los hilos guía, y se sellan las embocaduras con poliuretano expandido.'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, con topo. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce bajo vías ejecutado con topo, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. Incluye la edificación del pozo de ataque, la entibación lateral, y la colocación de un tubo guía de acero de 500 mm de diámetro. Además, se suministran y montan los hilos guía, y se sellan las embocaduras con poliuretano expandido. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 77. single_L2_paraphrase_67257fb687
- **item_key:** `OEB020agaaa`  (modifications: 1)
- paraphrase[K %B=="g"]: 'en balasto' → 'sobre balasto'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, sobre balasto. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en zona de balasto, incluso el descerne y la entibación de los costados y la posterior reposición del balasto retirado, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 78. single_L2_paraphrase_72fe98b8d1
- **item_key:** `OEB020aeaaa`  (modifications: 1)
- paraphrase[K %B=="e"]: 'en andén' → 'en plataforma'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en plataforma. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en andén, incluso la demolición y la reposición del pavimento y la solera, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 79. single_L2_paraphrase_7d0ee17daa
- **item_key:** `OEB020adaaa`  (modifications: 1)
- paraphrase[N %B=="d"]: ' la demolición y la reposición del firme y del pavimento,' → 'la eliminación y la restauración del firme y del pavimento,'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en cruce de carretera. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce de carretera, incluso la eliminación y la restauración del firme y del pavimento, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 80. single_L2_paraphrase_7d2057270c
- **item_key:** `OEB020ahaaa`  (modifications: 1)
- paraphrase[K %B=="h"]: 'con topo' → 'con topografía'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, con topografía. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce bajo vías ejecutado con topo, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. Incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro. El suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 81. single_L2_paraphrase_7f713a8434
- **item_key:** `OEB020aabaa`  (modifications: 1)
- paraphrase[G %C=b]: 'Nocturno' → 'Horario Nocturno'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Horario Nocturno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Horario Nocturno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 82. single_L2_paraphrase_926f000eae
- **item_key:** `OEB020aaaaa`  (modifications: 1)
- paraphrase[G %C=a]: 'Diurno' → 'Horario de día'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Horario de día/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Horario de día Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 83. single_L2_paraphrase_92acca32ef
- **item_key:** `OEB020abaaa`  (modifications: 1)
- paraphrase[K %B=="b"]: 'bajo vías' → 'subvías'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, subvías. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce bajo vías, incluso el descerne y la entibación de los costados y la posterior reposición del balasto retirado, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 84. single_L2_paraphrase_99c33c9fcd
- **item_key:** `OEB020aaeaa`  (modifications: 1)
- paraphrase[G %C=e]: 'Cualquier frana horaria' → 'Todas las franjas horarias'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Todas las franjas horarias/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 85. single_L2_paraphrase_9b73652914
- **item_key:** `OEB020aaaaa`  (modifications: 1)
- paraphrase[I %B=="a"]: 'en cualquier clase de terreno, excepto roca' → 'en cualquier tipo de suelo, salvo en roca'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier tipo de suelo, salvo en roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 86. single_L2_paraphrase_a56ee84cba
- **item_key:** `OEB020aaaab`  (modifications: 1)
- paraphrase[J %F=b]: 'Volumen escaso' → 'Volumen mínimo'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno/i >==5 horas/Volumen mínimo)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen mínimo

## 87. single_L2_paraphrase_ab1f476d66
- **item_key:** `OEB020acaaa`  (modifications: 1)
- paraphrase[N %B=="c"]: 'la demolición de roca dura,' → 'la fragmentación de roca compacta,'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, rocoso. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en terreno rocoso, incluso la fragmentación de roca compacta, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 88. single_L2_paraphrase_b2f7359562
- **item_key:** `OEB020aacaa`  (modifications: 1)
- paraphrase[G %C=c]: 'Diurno Excepcional' → 'Horario Diurno Especial'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Horario Diurno Especial/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Horario Diurno Especial Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 89. single_L2_paraphrase_c2b533009a
- **item_key:** `OEB020aaaaa`  (modifications: 1)
- paraphrase[J %F=a]: 'Volumen relevante' → 'Volumen considerable'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno/i >==5 horas/Volumen considerable)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen considerable

## 90. single_L2_paraphrase_cc4b8ac802
- **item_key:** `OEB020afaaa`  (modifications: 1)
- paraphrase[I %B=="f"]: 'adosada o superficial' → 'en superficie o adosada'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, adosada. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en superficie o adosada, incluso  el relleno y el compactado de la zanja, la preparación y nivelación de la solera, suministro y montaje del encofrado, elementos de fijación, desencofrado, el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 91. single_L2_paraphrase_cf0549a476
- **item_key:** `OEB020abaaa`  (modifications: 1)
- paraphrase[I %B=="b"]: 'en cruce bajo vías' → 'bajo intersección de vías'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, bajo vías. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro bajo intersección de vías, incluso el descerne y la entibación de los costados y la posterior reposición del balasto retirado, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 92. single_L2_paraphrase_d56dedd0d3
- **item_key:** `OEB020agaaa`  (modifications: 1)
- paraphrase[I %B=="g"]: 'en zona de balasto' → 'en área de balasto'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en balasto. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en área de balasto, incluso el descerne y la entibación de los costados y la posterior reposición del balasto retirado, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 93. single_L2_paraphrase_d6668d2d78
- **item_key:** `OEB020afaaa`  (modifications: 1)
- paraphrase[P %B=="f"]: 'la preparación y nivelación de la solera, suministro y montaje del encofrado, elementos de fijación, desencofrado,' → 'nivelación de la base, provisión y colocación del encofrado, elementos de sujeción, retirada del encofrado,'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, adosada. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro adosada o superficial, incluso  el relleno y el compactado de la zanja, nivelación de la base, provisión y colocación del encofrado, elementos de sujeción, retirada del encofrado, el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 94. single_L2_paraphrase_e0e78c29a0
- **item_key:** `OEB020acaaa`  (modifications: 1)
- paraphrase[K %B=="c"]: 'rocoso' → 'en terreno pedregoso'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en terreno pedregoso. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en terreno rocoso, incluso la demolición de roca dura, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 95. single_L2_paraphrase_e2dbb6d04d
- **item_key:** `OEB020adaaa`  (modifications: 1)
- paraphrase[K %B=="d"]: 'en cruce de carretera' → 'en intersección vial'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en intersección vial. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce de carretera, incluso  la demolición y la reposición del firme y del pavimento, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 96. single_L2_paraphrase_ecb4259b18
- **item_key:** `OEB020aadaa`  (modifications: 1)
- paraphrase[G %C=d]: 'Nocturno Excepcional' → 'Nocturno Especial'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Nocturno Especial/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Nocturno Especial Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 97. single_L2_paraphrase_ed954dd613
- **item_key:** `OEB020abaaa`  (modifications: 1)
- paraphrase[N %B=="b"  or  %B=="g"]: 'el descerne y la entibación de los costados y la posterior reposición del balasto retirado,' → 'la excavación y el soporte lateral, seguido de la reinstalación del balasto extraído,'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, bajo vías. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce bajo vías, incluso la excavación y el soporte lateral, seguido de la reinstalación del balasto extraído, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 98. single_L2_paraphrase_f1cc9e8005
- **item_key:** `OEB020acaaa`  (modifications: 1)
- paraphrase[I %B=="c"]: 'en terreno rocoso' → 'en suelo de roca'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, rocoso. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en suelo de roca, incluso la demolición de roca dura, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 99. single_L2_paraphrase_f555cfa48b
- **item_key:** `OEB020ahaaa`  (modifications: 1)
- paraphrase[I %B=="h"]: 'en cruce bajo vías ejecutado con topo' → 'en intersección subterránea de vías realizada con topografía'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, con topo. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en intersección subterránea de vías realizada con topografía, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. Incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro. El suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido. Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 100. single_L2_paraphrase_f6db9b35d6
- **item_key:** `OEB020aaaac`  (modifications: 1)
- paraphrase[J %F=c]: 'Cualquier condición de ejecución' → 'Condiciones diversas de ejecución'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno/i >==5 horas/Condiciones diversas de ejecución)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Condiciones diversas de ejecución

## 101. single_L2_paraphrase_fa5f258112
- **item_key:** `OEB020aafaa`  (modifications: 1)
- paraphrase[G %C=f]: 'Cualquier franja horaria excepcional' → 'Todas las franjas horarias especiales'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Todas las franjas horarias especiales/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Todas las franjas horarias especiales Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 102. single_L3_omission_198ffa7f0b
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- omission[RESUMEN]: 'Canalización hormigonada de $A T, PVC 110 mm, $K. ($G(%C)/$H(%D)/$J(%F))' → 'Canalización hormigonada de $A T, PVC 110 mm, $K. ($H(%D)/$J(%F))'

## 103. single_L3_omission_42b0d8ce59
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- omission[RESUMEN]: 'Canalización hormigonada de $A T, PVC 110 mm, $K. ($G(%C)/$H(%D)/$J(%F))' → 'Canalización hormigonada de $A T, PVC 110 mm, $K. ($G(%C)/$J(%F))'

## 104. single_L3_omission_a1c78df96a
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- omission[RESUMEN]: 'Canalización hormigonada de $A T, PVC 110 mm, $K. ($G(%C)/$H(%D)/$J(%F))' → 'Canalización hormigonada de $A T, PVC 110 mm. ($G(%C)/$H(%D)/$J(%F))'

## 105. single_L3_omission_bcf77418a4
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- omission[RESUMEN]: 'Canalización hormigonada de $A T, PVC 110 mm, $K. ($G(%C)/$H(%D)/$J(%F))' → 'Canalización hormigonada de $A T, PVC 110 mm, $K. ($G(%C)/$H(%D))'

## 106. single_L3_omission_d41e60cfb7
- **item_key:** _(no materialized leaves)_  (modifications: 1)
- omission[RESUMEN]: 'Canalización hormigonada de $A T, PVC 110 mm, $K. ($G(%C)/$H(%D)/$J(%F))' → 'Canalización hormigonada, PVC 110 mm, $K. ($G(%C)/$H(%D)/$J(%F))'

## 107. single_L3_reorder_e29a1970f4
- **item_key:** `OEB020aaaaa`  (modifications: 1)
- reorder[RESUMEN]: 'Canalización hormigonada de $A T, PVC 110 mm, $K. ($G(%C)/$H(%D)/$J(%F))' → 'Canalización hormigonada de $A T, PVC 110 mm, ($G(%C)/$H(%D)/$J(%F)) $K.'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, (Diurno/i >==5 horas/Volumen relevante) normal.
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 108. single_L3_reorder_e73e945a99
- **item_key:** `OEB020aaaaa`  (modifications: 1)
- reorder[TEXTO]: 'Canalización hormigonada de $A tubos de PVC de 110 mm de diámetro $I, incluso $N el relleno y el compactado de la zanja, $P el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F' → 'Canalización hormigonada de $A tubos de PVC de 110 mm de diámetro $I, incluso $P el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, $N el relleno y el compactado de la zanja, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, normal. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cualquier clase de terreno, excepto roca, incluso  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar,  el relleno y el compactado de la zanja, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 109. stacked_2_2be7401733
- **item_key:** `OEB020adaaa`  (modifications: 2)
- compression[I %B=="d"]: 'en cruce de carretera' → 'en cruce carretera'
- paraphrase[N %B=="d"]: ' la demolición y la reposición del firme y del pavimento,' → 'la demolición y la reposición del firme y del pavimento,'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, en cruce de carretera. (Diurno/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en cruce carretera, incluso la demolición y la reposición del firme y del pavimento, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Diurno Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante

## 110. stacked_3_4dcd872296
- **item_key:** _(no materialized leaves)_  (modifications: 3)
- compression[I %B=="g"]: 'en zona de balasto' → 'en balasto'
- expansion[J %F=b]: 'Volumen escaso' → 'Volumen escaso, adecuado para instalaciones donde el espacio es limitado o se requiere una mínima ocupación del terreno.'
- omission[RESUMEN]: 'Canalización hormigonada de $A T, PVC 110 mm, $K. ($G(%C)/$H(%D)/$J(%F))' → 'Canalización hormigonada de $A T, PVC 110 mm. ($G(%C)/$H(%D)/$J(%F))'

## 111. stacked_4_2d05a41374
- **item_key:** _(no materialized leaves)_  (modifications: 3)
- compression[I %B=="b"]: 'en cruce bajo vías' → 'bajo vías'
- compression[N %B=="c"]: 'la demolición de roca dura,' → 'demolición de roca,'
- omission[RESUMEN]: 'Canalización hormigonada de $A T, PVC 110 mm, $K. ($G(%C)/$H(%D)/$J(%F))' → 'Canalización hormigonada, PVC 110 mm, $K. ($G(%C)/$H(%D)/$J(%F))'

## 112. stacked_5plus_08fff2b666
- **item_key:** `OEB020aceaa`  (modifications: 5)
- compression[G %C=e]: 'Cualquier frana horaria' → 'Cualquier franja'
- compression[I %B=="f"]: 'adosada o superficial' → 'superficial'
- expansion[K %B=="h"]: 'con topo' → 'con topo, adecuada para instalación en terrenos con topografía irregular'
- expansion[K %B=="f"]: 'adosada' → 'adosada, integrada directamente en la estructura existente para asegurar estabilidad y continuidad en la canalización.'
- compression[I %B=="c"]: 'en terreno rocoso' → 'en roca'
- **resumen:** Canalización hormigonada de  2  T, PVC 110 mm, rocoso. (Cualquier franja/i >==5 horas/Volumen relevante)
- **texto:** Canalización hormigonada de  2  tubos de PVC de 110 mm de diámetro en roca, incluso la demolición de roca dura, el relleno y el compactado de la zanja,  el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo.  Trabajo: Cualquier franja horaria Banda de mantenimiento:  i >= 5 horas Condiciones de ejecución: Volumen relevante
