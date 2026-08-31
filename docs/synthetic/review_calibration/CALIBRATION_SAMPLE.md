# Muestra de calibración — 100 candidatos (semilla 38, 2026-08-31)

**Instrucciones:** para cada ítem, compara *Original* y *Candidato*, mira el contexto,
y escribe tu veredicto sustituyendo el guion bajo: **A** (aprobar: cumple los 5 criterios
de [RUBRIC.md](RUBRIC.md)), **R** (rechazar: falla alguno), **D** (dudoso).
Rechazo por defecto. La procedencia de modelo está oculta a propósito.
Tiempo estimado: 45–60 min.

---

### 1. `reorder` — RESUMEN template (OEB280$)

_Criterio del tipo: mismas palabras/cláusulas en otro orden_

| Original | Candidato |
|---|---|
| Canalización hormigonada $A T, polietileno libre de halógenos de 40 mm, $K. ($G(%C)/$H(%D)/$J(%F)) | Canalización hormigonada $A T, polietileno libre de halógenos de 40 mm, ($G(%C)/$H(%D)/$J(%F)) $K. |

**Veredicto 1:** A

---

### 2. `expansion` — $G / %C=f: Cualquier franja horaria excepcional

_Criterio del tipo: explicita lo implícito; PROHIBIDO añadir hechos_

| Original | Candidato |
|---|---|
| Cualquier franja horaria excepcional | Cualquier franja horaria excepcional, que no se limita a las franjas horarias diurnas o nocturnas habituales |

> Fragmentos hermanos de la variable: "Diurno"; "Nocturno"; "Diurno Excepcional"; "Nocturno Excepcional"; "Cualquier frana horaria"

**Veredicto 2:** A

---

### 3. `num_to_text` — Nº TUBOS / 1

_Criterio del tipo: número en letras, conservando el sustantivo_

| Original | Candidato |
|---|---|
| 1 | Unidad |

> Hermanos del eje «Nº TUBOS»:  1 ;  2 ;  3 ;  4 ;  5 ;  6 ;  8 ;  12 ;  16 ;  18 ;  24 

**Veredicto 3:** A

---

### 4. `paraphrase` — $L / %C=a: Volumen relevante

_Criterio del tipo: mismo contenido del fragmento, otras palabras_

| Original | Candidato |
|---|---|
| Volumen relevante | Volumen de magnitud considerable |

> Fragmentos hermanos de la variable: "Volumen escaso"; "Cualquier condición de ejecución"

**Veredicto 4:** A

---

### 5. `unit_expansion` — PROFUNDIDAD / 0,80 a 1,00 m

_Criterio del tipo: unidad/expresión desarrollada, mismo valor_

| Original | Candidato |
|---|---|
| 0,80 a 1,00 m | profundidad entre 0,80 y 1,00 metros |

> Hermanos del eje «PROFUNDIDAD»: hasta 0,80 m; 1,10 m

**Veredicto 5:** A

---

### 6. `template_paraphrase` — TEXTO template (OEB010$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Ejecución de canalización para línea subterránea de doble circuito de 220 o 400 kV de cables entubados y tubos embebidos en hormigón HM-20, de dimensiones totales 2 m de ancho por 1,60 m de alto, hormigonado hasta cota de 760 mm de profundidad, posterior relleno compactado al 95% P.M. Incluidos 2 ternas de tubos de polietileno (PE) de alta densidad de 250 mm de diámetro exterior para los cables de potencia; 4 tubos de polietileno de doble pared de diámetro exterior 110 mm para la puesta a tierra; 2 tetratubos de polietileno de 4x40 mm de diámetro exterior para telecomunicaciones. Incluidos separadores para 3 tubos de diámetro 250 mm, 2 tubos de diámetro 110 mm y testigo soporte para tetratubo de diámetro 40 mm. Con cintas de señalización de riesgo eléctrico de 150 mm de ancho a 150 mm de profundidad del firme existente. Incluida la excavación, la preparación de la superficie de asiento, la compactación y la nivelación. Incluido el propio suministro, el transporte, la carga y la descarga del material a pie de obra, la ejecución, los desplazamientos, pequeño material, herramientas, maquinaria y medios auxiliares y el mandrilado de tubos. En terreno $A, $B de pavimento. Condiciones de ejecución: $C. | Para la instalación de una canalización subterránea de doble circuito de 220 o 400 kV se utilizarán cables en tubos y tubos encajados en hormigón HM-20, con dimensiones totales de 2 m de ancho por 1,60 m de alto. El hormigonado se extenderá hasta una profundidad de 760 mm, seguido de un relleno compactado al 95% P.M. Se incluyen 2 ternas de conductos de polietileno (PE) de 250 mm de diámetro exterior para los cables de potencia; 4 conductos de polietileno con doble pared de diámetro exterior 110 mm para puesta a tierra; y 2 tetratubos de polietileno de 4x40 mm de diámetro para telecomunicaciones. Se proporcionan separadores para 3 conductos de diámetro 250 mm, 2 de diámetro 110 mm y soporte testigo para un tetratubo de diámetro 40 mm.. Se colocarán cintas de señalización de riesgo eléctrico de 150 mm de ancho hasta una profundidad de 150 mm del firme existente. Se incluye la excavación, la preparación de la superficie de apoyo, la compactación y el nivelado. Se suministrará, transportará, cargará y descargará el material en el lugar de la obra, así como se ejecutará la instalación, se manejarán los desplazamientos, materiales de pequeño tamaño, herramientas, maquinaria y medios auxiliares, y se realizará el mandrilado de tubos. En terreno $A, $B de pavimento. Condiciones de ejecución: $C. |

**Veredicto 6:** A

---

### 7. `unit_conversion` — PROFUNDIDAD / hasta 0,80 m

_Criterio del tipo: conversión aritméticamente correcta_

| Original | Candidato |
|---|---|
| hasta 0,80 m | 80 cm |

> Hermanos del eje «PROFUNDIDAD»: 0,80 a 1,00 m; 1,10 m

**Veredicto 7:** A

---

### 8. `omission` — RESUMEN — omit $M (OEB170$)

_Criterio del tipo: plantilla sin la mención omitida, gramaticalmente reparada_

| Original | Candidato |
|---|---|
| Canalización metálica superficial con $A tubos de acero galvanizado de $B de diámetro. ($L(%C)/$M(%D)/$N(%F)) | Canalización metálica superficial con $A tubos de acero galvanizado de $B de diámetro. ($L(%C)/$N(%F)) |

> Variable omitida: $M

**Veredicto 8:** A

---

### 9. `new_param` — NEW_PARAM on OEB190$

_Criterio del tipo: eje nuevo plausible, sin colisionar; valores excluyentes y sensatos_

| Original | Candidato |
|---|---|
| (nuevo eje sobre el concepto — no hay original) | eje «TIPO DE INSPECCIÓN» → {Visual, Termográfica, Acústica, Mecánica, Robótica} |

> Ejes existentes del concepto: PROFUNDIDAD; TIPO DE TERRENO; TRABAJO; BANDA DE MANTENIMIENTO; CONDICIONES DE EJECUCIÓN

**Veredicto 9:** A

---

### 10. `paraphrase` — $N / %B=="d": la demolición y la reposición del firme y del pavimento,

_Criterio del tipo: mismo contenido del fragmento, otras palabras_

| Original | Candidato |
|---|---|
| la demolición y la reposición del firme y del pavimento, | la desmantelación y la reubicación del firme y del pavimento, |

> Fragmentos hermanos de la variable: "el descerne y la entibación de los costados y la posterior reposición del balasto retirado,"; "la demolición de roca dura,"; "la demolición y la reposición del pavimento y la solera,"

**Veredicto 10:** A

---

### 11. `expansion` — $X / %A=c: 40 cm

_Criterio del tipo: explicita lo implícito; PROHIBIDO añadir hechos_

| Original | Candidato |
|---|---|
| 40 cm | 40 centímetros de profundidad, garantizando protección adecuada para cables instalados manualmente |

> Fragmentos hermanos de la variable: "20 cm"; "20 cm"

**Veredicto 11:** A

---

### 12. `omission` — RESUMEN — omit $L (OEB190$)

_Criterio del tipo: plantilla sin la mención omitida, gramaticalmente reparada_

| Original | Candidato |
|---|---|
| Zanja para cables de $A de profundidad a mano, $B, en material $B. ($L(%C)/$M(%D)/$N(%F)) | Zanja para cables de $A de profundidad a mano, $B, en material $B. ($M(%D)/$N(%F)) |

> Variable omitida: $L

**Veredicto 12:** A

---

### 13. `omission` — RESUMEN — omit $L (OEB050$)

_Criterio del tipo: plantilla sin la mención omitida, gramaticalmente reparada_

| Original | Candidato |
|---|---|
| Ejecución de canalización de comunicaciones para línea subterranea doble circuito de 220 ó 400 kV en terreno $A, $B de pavimento. (-/-/$L(%C)) | Ejecución de canalización de comunicaciones para línea subterránea doble circuito de 220 ó 400 kV en terreno $A y $B de pavimento. |

> Variable omitida: $L

**Veredicto 13:** A

---

### 14. `synonym_label` — TIPO DE TERRENO / Adosada

_Criterio del tipo: sinónimo/etiqueta equivalente, distinguible de los hermanos_

| Original | Candidato |
|---|---|
| Adosada | Contigua |

> Hermanos del eje «TIPO DE TERRENO»: Normal; Bajo vías; Rocoso; Cruce de carretera; Andén; Balasto; Con topo

**Veredicto 14:** A

---

### 15. `new_param` — NEW_PARAM on OEB190$

_Criterio del tipo: eje nuevo plausible, sin colisionar; valores excluyentes y sensatos_

| Original | Candidato |
|---|---|
| (nuevo eje sobre el concepto — no hay original) | eje «TIPO DE ACCESO» → {Ninguno, Puerta, Trampilla, Escalera, Túnel} |

> Ejes existentes del concepto: PROFUNDIDAD; TIPO DE TERRENO; TRABAJO; BANDA DE MANTENIMIENTO; CONDICIONES DE EJECUCIÓN

**Veredicto 15:** A

---

### 16. `reorder` — RESUMEN template (OEB130$)

_Criterio del tipo: mismas palabras/cláusulas en otro orden_

| Original | Candidato |
|---|---|
| Entronque de tubos de 110 mm en arqueta o cámara existente. ($L(%A)/$M(%B)/$N(%C)) | Entronque de tubos de 110 mm en arqueta o cámara existente. ($N(%C)/$L(%A)/$M(%B)) |

**Veredicto 16:** A

---

### 17. `paraphrase` — $K / %B=="b": bajo vías

_Criterio del tipo: mismo contenido del fragmento, otras palabras_

| Original | Candidato |
|---|---|
| bajo vías | en subrasante de las vías |

> Fragmentos hermanos de la variable: "normal"; "rocoso"; "en cruce de carretera"; "en andén"; "adosada"; "en balasto"; "con topo"

**Veredicto 17:** A

---

### 18. `compression` — $R / %B=c: zona de balasto, ejecutada a mano incluso descerne y entibación de costados y posterior reposición del balasto retirado

_Criterio del tipo: estrictamente más corta, sin perder contenido_

| Original | Candidato |
|---|---|
| zona de balasto, ejecutada a mano incluso descerne y entibación de costados y posterior reposición del balasto retirado | balasto, ejecutada a mano con descerne, entibación y reposición |

> Fragmentos hermanos de la variable: "ejecutada por excavación manual en cualquier tipo de terreno excepto roca"; "ejecutada por excavación manual en terreno rocoso, incluso excavación con explosivos"

**Veredicto 18:** A

---

### 19. `template_paraphrase` — RESUMEN template (OEB040$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Canalización hormigonada $A T, polietileno libre de halógenos de 160 mm, $K. ($G(%C)/$H(%D)/$J(%F)) | Conductos de hormigón armado $A T, en polietileno sin halógenos de 160 mm, categoría $K. Datos esenciales: ($G(%C)/$H(%D)/$J(%F)) |

**Veredicto 19:** A

---

### 20. `omission` — TEXTO — omit $F (OEB300$)

_Criterio del tipo: plantilla sin la mención omitida, gramaticalmente reparada_

| Original | Candidato |
|---|---|
| Canalización hormigonada de $A tubos de polietileno libre de halógenos de 90 mm de diámetro $I, incluso $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F | Canalización hormigonada de $A tubos de polietileno libre de halógenos de 90 mm de diámetro $I, incluso $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo $M Trabajo: $C Banda de mantenimiento: $D, asegurando la calidad del proceso. |

> Variable omitida: $F

**Veredicto 20:** A

---

### 21. `template_paraphrase` — RESUMEN template (OEB100$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Suministro y ejecución de canalización en túnel acceso interfono ($L(%A)/$M(%B)/$N(%C)) | $L(%A)/$M(%B)/$N(%C) suministro e instalación de conducciones enterradas en túnel de acceso interfono ($L(%A)/$M(%B)/$N(%C)) |

**Veredicto 21:** A

---

### 22. `omission` — TEXTO — omit $I (OEB040$)

_Criterio del tipo: plantilla sin la mención omitida, gramaticalmente reparada_

| Original | Candidato |
|---|---|
| Canalización hormigonada de $A tubos de polietileno libre de halógenos de 160 mm de diámetro $I, incluso $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F | Canalización hormigonada de $A tubos de polietileno libre de halógenos de 160 mm, incluso $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F |

> Variable omitida: $I

**Veredicto 22:** A

---

### 23. `new_param` — NEW_PARAM on OEB110$

_Criterio del tipo: eje nuevo plausible, sin colisionar; valores excluyentes y sensatos_

| Original | Candidato |
|---|---|
| (nuevo eje sobre el concepto — no hay original) | eje «PROTECCIÓN CONTRA CORROSIÓN» → {Sin protección, Recubrimiento, Inyección, Anodizado, Galvanizado} |

> Ejes existentes del concepto: TRABAJO; BANDA DE MANTENIMIENTO; CONDICIONES DE EJECUCIÓN

**Veredicto 23:** A

---

### 24. `expansion` — $L / %B=e: Cualquier franja horaria

_Criterio del tipo: explicita lo implícito; PROHIBIDO añadir hechos_

| Original | Candidato |
|---|---|
| Cualquier franja horaria | Cualquier franja horaria, incluyendo tanto las horas regulares como las excepcionales |

> Fragmentos hermanos de la variable: "Diurno"; "Nocturno"; "Diurno excepcional"; "Nocturno excepcional"; "Cualquier franja horaria excepcional"

**Veredicto 24:** A

---

### 25. `omission` — RESUMEN — omit $L (OEB120$)

_Criterio del tipo: plantilla sin la mención omitida, gramaticalmente reparada_

| Original | Candidato |
|---|---|
| Suministro y ejecución de embocadura canalización de $A tubos en arqueta o cámara existente ($L(%B)/$M(%C)/$N(%D)) | Suministro y ejecución de embocadura canalización de $A tubos en arqueta o cámara existente, incluyendo las especificaciones $M(%C) y $N(%D) |

> Variable omitida: $L

**Veredicto 25:** A

---

### 26. `expansion` — $G / %C=b: Nocturno

_Criterio del tipo: explicita lo implícito; PROHIBIDO añadir hechos_

| Original | Candidato |
|---|---|
| Nocturno | Nocturno, realización de trabajos en horario nocturno para facilitar la coordinación y reducir el impacto. |

> Fragmentos hermanos de la variable: "Diurno"; "Diurno Excepcional"; "Nocturno Excepcional"; "Cualquier frana horaria"; "Cualquier franja horaria excepcional"

**Veredicto 26:** A

---

### 27. `expansion` — $N / %B=="b"  or  %B=="g": el descerne y la entibación de los costados y la posterior reposición del balasto retirado,

_Criterio del tipo: explicita lo implícito; PROHIBIDO añadir hechos_

| Original | Candidato |
|---|---|
| el descerne y la entibación de los costados y la posterior reposición del balasto retirado, | el descerne y la entibación de los costados, seguido de la reposición del balasto retirado previamente, |

> Fragmentos hermanos de la variable: "la demolición de roca dura,"; " la demolición y la reposición del firme y del pavimento,"; "la demolición y la reposición del pavimento y la solera,"

**Veredicto 27:** A

---

### 28. `unit_conversion` — DIÁMETRO / 21mm

_Criterio del tipo: conversión aritméticamente correcta_

| Original | Candidato |
|---|---|
| 21mm | 21 milímetros |

> Hermanos del eje «DIÁMETRO»: 29mm; 36mm; 40mm; 48mm

**Veredicto 28:** A

---

### 29. `paraphrase` — $R / %B=b: ejecutada por excavación manual en terreno rocoso, incluso excavación con explosivos

_Criterio del tipo: mismo contenido del fragmento, otras palabras_

| Original | Candidato |
|---|---|
| ejecutada por excavación manual en terreno rocoso, incluso excavación con explosivos | construida a mano en terreno rocoso, con la opción de utilizar explosivos |

> Fragmentos hermanos de la variable: "ejecutada por excavación manual en cualquier tipo de terreno excepto roca"; "zona de balasto, ejecutada a mano incluso descerne y entibación de costados y posterior reposición del balasto retirado"

**Veredicto 29:** A

---

### 30. `expansion` — $K / %B=="g": en balasto

_Criterio del tipo: explicita lo implícito; PROHIBIDO añadir hechos_

| Original | Candidato |
|---|---|
| en balasto | en balasto, proporcionando una base firme y amortiguadora |

> Fragmentos hermanos de la variable: "normal"; "bajo vías"; "rocoso"; "en cruce de carretera"; "en andén"; "adosada"; "con topo"

**Veredicto 30:** A

---

### 31. `template_paraphrase` — RESUMEN template (OEB120$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Suministro y ejecución de embocadura canalización de $A tubos en arqueta o cámara existente ($L(%B)/$M(%C)/$N(%D)) | Ejecución de entrada de conductos de $A en arqueta o cámara preexistente ($L(%B)/$M(%C)/$N(%D)) |

**Veredicto 31:** A

---

### 32. `omission` — TEXTO — omit $B (OEB050$)

_Criterio del tipo: plantilla sin la mención omitida, gramaticalmente reparada_

| Original | Candidato |
|---|---|
| Ejecución de canalización para línea subterránea de telecomunicaciones, en derivación a arquetas de telecomunicaciones y junto a cámaras de empalme, de cables entubados y tubos embebidos en hormigón HE-20, de dimensiones totales 450 mm de ancho por 1 m de alto, hormigonado hasta cota de 650 mm de profundidad, posterior relleno compactado al 95% P.M. Incluidos 2 tetratubos de polietileno de 4x40 mm de diámetro exterior para telecomunicaciones y los separadores correspondientes. Con cinta de señalización de riesgo eléctrico de 150 mm de ancho a 150 mm de profundidad del firme existente. Incluso excavación, preparación de la superficie de asiento, compactación y nivelación. Incluido el propio suministro, el transporte, la carga y la descarga del material a pie de obra, la ejecución, los desplazamientos, pequeño material, herramientas, maquinaria y medios auxiliares y el mandrilado de tubos. En terreno $A, $B de pavimento. Condiciones de ejecución: $C. | Ejecución de canalización para línea subterránea de telecomunicaciones, en derivación a arquetas de telecomunicaciones y junto a cámaras de empalme, de cables entubados y tubos embebidos en hormigón HE-20, de dimensiones totales 450 mm de ancho por 1 m de alto, hormigonado hasta cota de 650 mm de profundidad, posterior relleno compactado al 95% P.M. Incluidos 2 tetratubos de polietileno de 4x40 mm de diámetro exterior para telecomunicaciones y los separadores correspondientes. Con cinta de señalización de riesgo eléctrico de 150 mm de ancho a 150 mm de profundidad del firme existente. Incluso excavación, preparación de la superficie de asiento, compactación y nivelación. Incluido el propio suministro, el transporte, la carga y la descarga del material a pie de obra, la ejecución, los desplazamientos, pequeño material, herramientas, maquinaria y medios auxiliares y el mandrilado de tubos. En terreno $A de pavimento. Condiciones de ejecución: $C. |

> Variable omitida: $B

**Veredicto 32:** A

---

### 33. `compression` — $P / %B=="f": la preparación y la nivelación de la solera, el suministro y montaje del encofrado, elementos de fijación, desencofrado,

_Criterio del tipo: estrictamente más corta, sin perder contenido_

| Original | Candidato |
|---|---|
| la preparación y la nivelación de la solera, el suministro y montaje del encofrado, elementos de fijación, desencofrado, | nivelación de la solera, suministro del encofrado, desencofrado, |

**Veredicto 33:** A

---

### 34. `synonym_label` — TIPO DE TERRENO / Adosada

_Criterio del tipo: sinónimo/etiqueta equivalente, distinguible de los hermanos_

| Original | Candidato |
|---|---|
| Adosada | Contigua a |

> Hermanos del eje «TIPO DE TERRENO»: Normal; Bajo vías; Rocoso; Cruce de carretera; Andén; Balasto; Con topo

**Veredicto 34:** A

---

### 35. `template_paraphrase` — RESUMEN template (OEB190$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Zanja para cables de $A de profundidad a mano, $B, en material $B. ($L(%C)/$M(%D)/$N(%F)) | Excavación manual para cables de $A de profundidad, con $B, empleando $B. ($L(%C)/$M(%D)/$N(%F)) |

**Veredicto 35:** A

---

### 36. `synonym_label` — TIPO DE TERRENO / Normal

_Criterio del tipo: sinónimo/etiqueta equivalente, distinguible de los hermanos_

| Original | Candidato |
|---|---|
| Normal | Terreno Estándar |

> Hermanos del eje «TIPO DE TERRENO»: Bajo vías; Rocoso; Cruce de carretera; Andén; Adosada; Balasto; Con topo

**Veredicto 36:** A

---

### 37. `num_to_text` — Nº TUBOS / 2

_Criterio del tipo: número en letras, conservando el sustantivo_

| Original | Candidato |
|---|---|
| 2 | Dos unidades |

> Hermanos del eje «Nº TUBOS»:  2 ;  4 ;  6 ;  8 ;  12 ;  16 ;  18 ;  24 

**Veredicto 37:** A

---

### 38. `template_paraphrase` — TEXTO template (OEB280$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Canalización hormigonada de $A tubos de polietileno libre de halógenos de 40 mm de diámetro $I, incluso $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F | Se efectúa la instalación de tubería enterrada de $A conductos de polietileno sin halógenos de 40 mm de diámetro $I, comprendiendo $N el relleno y compactación de la zanja, $P el abastecimiento y colocación de los conductos y concreto tipo HE-20 sin vibrar, la verificación de los conductos, el traslado y retirada de los materiales al área de uso $M Trabajo: $C Área de mantenimiento: $D Criterios de ejecución: $F |

**Veredicto 38:** A

---

### 39. `paraphrase` — $G / %C=c: Diurno Excepcional

_Criterio del tipo: mismo contenido del fragmento, otras palabras_

| Original | Candidato |
|---|---|
| Diurno Excepcional | Horario Diurno Especial |

> Fragmentos hermanos de la variable: "Diurno"; "Nocturno"; "Nocturno Excepcional"; "Cualquier frana horaria"; "Cualquier franja horaria excepcional"

**Veredicto 39:** A

---

### 40. `template_paraphrase` — RESUMEN template (OEB160$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Mandrilado de canalización existente. ($N(%A)/-/-) | Aplicación de mandrilado en conducciones ya instaladas, $N(%A)/-/-. |

**Veredicto 40:** A

---

### 41. `expansion` — $R / %B=b: ejecutada por excavación manual en terreno rocoso, incluso excavación con explosivos

_Criterio del tipo: explicita lo implícito; PROHIBIDO añadir hechos_

| Original | Candidato |
|---|---|
| ejecutada por excavación manual en terreno rocoso, incluso excavación con explosivos | ejecutada por excavación manual en terreno rocoso, incluyendo el uso de explosivos para facilitar la fragmentación de rocas |

> Fragmentos hermanos de la variable: "ejecutada por excavación manual en cualquier tipo de terreno excepto roca"; "zona de balasto, ejecutada a mano incluso descerne y entibación de costados y posterior reposición del balasto retirado"

**Veredicto 41:** A

---

### 42. `template_paraphrase` — TEXTO template (OEB250$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| $A de canalización de $B tubos de acero galvanizado de 100mm de diámetro para instalaciones CMS en transiciones entre diferentes plataformas. $Q(%A) Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F | Sistema de canalización $A de $B conductos de acero galvanizado de 100mm de diámetro para sistemas CMS en las transiciones entre plataformas. $Q(%A) Operación: $C Franja de mantenimiento: $D Condiciones de implementación: $F |

**Veredicto 42:** A

---

### 43. `compression` — $L / %C=c: Cualquier condición de ejecución

_Criterio del tipo: estrictamente más corta, sin perder contenido_

| Original | Candidato |
|---|---|
| Cualquier condición de ejecución | Ejecución flexible |

> Fragmentos hermanos de la variable: "Volumen relevante"; "Volumen escaso"

**Veredicto 43:** A

---

### 44. `synonym_label` — CONDICIONES DE EJECUCIÓN / Volumen escaso

_Criterio del tipo: sinónimo/etiqueta equivalente, distinguible de los hermanos_

| Original | Candidato |
|---|---|
| Volumen escaso | Bajo volumen |

> Hermanos del eje «CONDICIONES DE EJECUCIÓN»: Volumen relevante; Cualquier condición de ejecución

**Veredicto 44:** A

---

### 45. `expansion` — $K / %B=="c": rocoso

_Criterio del tipo: explicita lo implícito; PROHIBIDO añadir hechos_

| Original | Candidato |
|---|---|
| rocoso | rocoso, ideal para entornos con suelos compuestos en gran parte por rocas |

> Fragmentos hermanos de la variable: "normal"; "bajo vías"; "en cruce de carretera"; "en andén"; "adosada"; "en balasto"; "con topo"

**Veredicto 45:** A

---

### 46. `paraphrase` — $R / %B=a: ejecutada por excavación manual en cualquier tipo de terreno excepto roca

_Criterio del tipo: mismo contenido del fragmento, otras palabras_

| Original | Candidato |
|---|---|
| ejecutada por excavación manual en cualquier tipo de terreno excepto roca | hecha por excavación manual en cualquier terreno, a excepción de roca |

> Fragmentos hermanos de la variable: "ejecutada por excavación manual en terreno rocoso, incluso excavación con explosivos"; "zona de balasto, ejecutada a mano incluso descerne y entibación de costados y posterior reposición del balasto retirado"

**Veredicto 46:** A

---

### 47. `paraphrase` — $L / %C=a: Volumen relevante

_Criterio del tipo: mismo contenido del fragmento, otras palabras_

| Original | Candidato |
|---|---|
| Volumen relevante | Volumen notable |

> Fragmentos hermanos de la variable: "Volumen escaso"; "Cualquier condición de ejecución"

**Veredicto 47:** A

---

### 48. `omission` — TEXTO — omit $B (OEB120$)

_Criterio del tipo: plantilla sin la mención omitida, gramaticalmente reparada_

| Original | Candidato |
|---|---|
| Suministro y ejecución de embocadura canalización de $A tubos en arqueta o cámara existente Trabajo: $B Banda de mantenimiento: $C Condiciones de ejecución: $D | Suministro y ejecución de embocadura canalización de $A tubos en arqueta o cámara existente. Banda de mantenimiento: $C, Condiciones de ejecución: $D. |

> Variable omitida: $B

**Veredicto 48:** A

---

### 49. `template_paraphrase` — TEXTO template (OEB040$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Canalización hormigonada de $A tubos de polietileno libre de halógenos de 160 mm de diámetro $I, incluso $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F | Estructura de conducción con $A tubos de polietileno sin halógenos de 160 mm, de diámetro nominal $I, que incluye $N la carga y compactación del terreno, $P el suministro y ubicación de los tubos y la preparación del hormigón tipo HE-20 por compresión natural, la comprobación de los conductos, el desplazamiento y eliminación de los materiales en los alrededores de trabajo $M, Trabajo: $C, Banda de mantenimiento: $D, Condiciones de ejecución: $F |

**Veredicto 49:** A

---

### 50. `expansion` — $G / %C=f: Cualquier franja horaria excepcional

_Criterio del tipo: explicita lo implícito; PROHIBIDO añadir hechos_

| Original | Candidato |
|---|---|
| Cualquier franja horaria excepcional | Cualquier franja horaria excepcional, que no se limita a las franjas diurnas o nocturnas habituales |

> Fragmentos hermanos de la variable: "Diurno"; "Nocturno"; "Diurno Excepcional"; "Nocturno Excepcional"; "Cualquier frana horaria"

**Veredicto 50:** A

---

### 51. `paraphrase` — $L / %B=d: Nocturno excepcional

_Criterio del tipo: mismo contenido del fragmento, otras palabras_

| Original | Candidato |
|---|---|
| Nocturno excepcional | Nocturno privilegiado |

> Fragmentos hermanos de la variable: "Diurno"; "Nocturno"; "Diurno excepcional"; "Cualquier franja horaria"; "Cualquier franja horaria excepcional"

**Veredicto 51:** A

---

### 52. `num_to_text` — Nº TUBOS / 5

_Criterio del tipo: número en letras, conservando el sustantivo_

| Original | Candidato |
|---|---|
| 5 | Cinco tubos |

> Hermanos del eje «Nº TUBOS»:  1 ;  2 ;  3 ;  4 ;  5 ;  6 ;  8 ;  12 ;  16 ;  18 ;  24 

**Veredicto 52:** A

---

### 53. `template_paraphrase` — RESUMEN template (OEB110$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Tubería de PVC de 110 mm de diámetro para drenaje de arqueta ($L(%A)/$M(%B)/$N(%C)) | $L(%A)/$M(%B)/$N(%C) canalización de PVC con diámetro nominal 110 mm para evacuación en arquetas |

**Veredicto 53:** A

---

### 54. `template_paraphrase` — RESUMEN template (OEB080$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Canalización tubo corrugado de $A con alma de acero. (-/-/$L(%B)) | Se realiza la canalización empleando tubo corrugado de $A con recubrimiento de acero. (-/-/$L(%B)) |

**Veredicto 54:** A

---

### 55. `template_paraphrase` — TEXTO template (OEB160$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Mandrilado de canalización existente. Condiciones de ejecución: $A. | Condiciones de ejecución para el mandrilado de canalización preinstalada: $A. |

**Veredicto 55:** A

---

### 56. `omission` — RESUMEN — omit $K (OEB280$)

_Criterio del tipo: plantilla sin la mención omitida, gramaticalmente reparada_

| Original | Candidato |
|---|---|
| Canalización hormigonada $A T, polietileno libre de halógenos de 40 mm, $K. ($G(%C)/$H(%D)/$J(%F)) | Canalización hormigonada $A T, polietileno libre de halógenos de 40 mm. ($G(%C)/$H(%D)/$J(%F)) |

> Variable omitida: $K

**Veredicto 56:** A

---

### 57. `new_param` — NEW_PARAM on OEB030$

_Criterio del tipo: eje nuevo plausible, sin colisionar; valores excluyentes y sensatos_

| Original | Candidato |
|---|---|
| (nuevo eje sobre el concepto — no hay original) | eje «DIÁMETRO INTERNO» → {100 mm, 110 mm, 120 mm, 130 mm, 140 mm} |

> Ejes existentes del concepto:  Nº TUBOS ;  TIPO DE TERRENO ; TRABAJO; BANDA DE MANTENIMIENTO; CONDICIONES DE EJECUCIÓN

**Veredicto 57:** A

---

### 58. `expansion` — $I / %B=="c": en terreno rocoso

_Criterio del tipo: explicita lo implícito; PROHIBIDO añadir hechos_

| Original | Candidato |
|---|---|
| en terreno rocoso | en terreno rocoso, donde la canalización debe considerar la estabilidad del sustrato |

> Fragmentos hermanos de la variable: "en cualquier clase de terreno, excepto roca"; "en cruce bajo vías"; "en cruce de carretera"; "en andén"; "adosada o superficial"; "en zona de balasto"; "en cruce bajo vías ejecutado con topo"

**Veredicto 58:** A

---

### 59. `paraphrase` — $M / %B=="h": Incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro. El suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido.

_Criterio del tipo: mismo contenido del fragmento, otras palabras_

| Original | Candidato |
|---|---|
| Incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro. El suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido. | Incluye la construcción del pozo de ataque, la entibación lateral, y la instalación de un tubo guía de acero de 500 mm de diámetro. Se suministran y montan los hilos guía, y se sellan las aberturas con poliuretano expandido. |

**Veredicto 59:** A

---

### 60. `paraphrase` — $I / %B=="b": en cruce bajo vías

_Criterio del tipo: mismo contenido del fragmento, otras palabras_

| Original | Candidato |
|---|---|
| en cruce bajo vías | en intersección inferior a las vías |

> Fragmentos hermanos de la variable: "en cualquier clase de terreno, excepto roca"; "en terreno rocoso"; "en cruce de carretera"; "en andén"; "adosada o superficial"; "en zona de balasto"; "en cruce bajo vías ejecutado con topo"

**Veredicto 60:** A

---

### 61. `template_paraphrase` — RESUMEN template (OEB120$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Suministro y ejecución de embocadura canalización de $A tubos en arqueta o cámara existente ($L(%B)/$M(%C)/$N(%D)) | Se suministrarán y ejecutarán los adaptadores para canalización de $A conductos en arqueta o cámara existente ($L(%B)/$M(%C)/$N(%D)) |

**Veredicto 61:** A

---

### 62. `reorder` — RESUMEN template (OEB200$)

_Criterio del tipo: mismas palabras/cláusulas en otro orden_

| Original | Candidato |
|---|---|
| Zanja para cables de $A de profundidad a máquina, $B, en material $B. ($L(%C)/$M(%D)/$N(%F)) | Zanja para cables de $B, en material $B, de $A de profundidad a máquina. ($N(%F)/$M(%D)/$L(%C)) |

**Veredicto 62:** A

---

### 63. `new_param` — NEW_PARAM on OEB050$

_Criterio del tipo: eje nuevo plausible, sin colisionar; valores excluyentes y sensatos_

| Original | Candidato |
|---|---|
| (nuevo eje sobre el concepto — no hay original) | eje «TIPO DE PROTECCIÓN» → {Sin protección, Protección mecánica, Protección química, Protección eléctrica, Protección combinada} |

> Ejes existentes del concepto:  TERRENO ;  PAVIMENTO ; CONDICIONES DE EJECUCIÓN

**Veredicto 63:** A

---

### 64. `template_paraphrase` — TEXTO template (OEB070$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: $B Banda de mantenimiento: $C Condiciones de ejecución: $D | Se proporcionará y ejecutará la canalización de $A conducto(s) de polietileno 110 mm 5 At. con sección inferior a las vías. Trabajos a realizar: $B, Banda de mantenimiento: $C, Condiciones de ejecución: $D |

**Veredicto 64:** A

---

### 65. `reorder` — TEXTO template (OEB150$)

_Criterio del tipo: mismas palabras/cláusulas en otro orden_

| Original | Candidato |
|---|---|
| Limpieza de tubo de canalización existente incluyendo la localización de obstrucciones y su limpieza, previo al tendido de nuevos cables. Trabajo: $A Banda de mantenimiento: $B Condiciones de ejecución: $C. | Limpieza de tubo de canalización existente incluyendo la localización de obstrucciones y su limpieza, previo al tendido de nuevos cables. Banda de mantenimiento: $B Condiciones de ejecución: $C Trabajo: $A. |

**Veredicto 65:** A

---

### 66. `expansion` — $G / %C=a: Diurno

_Criterio del tipo: explicita lo implícito; PROHIBIDO añadir hechos_

| Original | Candidato |
|---|---|
| Diurno | Diurno, en el periodo de actividad diurna, para operaciones normales |

> Fragmentos hermanos de la variable: "Nocturno"; "Diurno Excepcional"; "Nocturno Excepcional"; "Cualquier frana horaria"; "Cualquier franja horaria excepcional"

**Veredicto 66:** A

---

### 67. `paraphrase` — $N / %B=="d": la demolición y reposición del firme y del pavimento,

_Criterio del tipo: mismo contenido del fragmento, otras palabras_

| Original | Candidato |
|---|---|
| la demolición y reposición del firme y del pavimento, | la desmantelación y reinstalación del pavimento y el firme, |

> Fragmentos hermanos de la variable: "el descerne y la entibación de los costados y la posterior reposición del balasto retirado,"; "la demolición de roca dura,"; "la demolición y reposición del pavimento y la solera,"

**Veredicto 67:** A

---

### 68. `template_paraphrase` — TEXTO template (OEB240$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Relleno localizado en obras de instalaciones ferroviarias, emplazamientos y accesos, con $W(%A), i/ carga, descarga y transporte al lugar asignado en el interior de la obra, extendido, humectación, compactación, terminación, i/herramientas y medios auxiliares. Trabajo: $B. Banda de mantenimiento: $C. | Relleno localizado $W(%A), i/ compactado y material en obras de instalaciones ferroviarias, con $W(%A). Incluye transporte al lugar asignado dentro de la obra, extendido, humectación, compactación y finalización. Herramientas y medios auxiliares son proporcionados. Trabajo: $B. Banda de mantenimiento: $C. |

**Veredicto 68:** A

---

### 69. `synonym_label` — TRABAJO / Diurno excepcional

_Criterio del tipo: sinónimo/etiqueta equivalente, distinguible de los hermanos_

| Original | Candidato |
|---|---|
| Diurno excepcional | Horario de Día Extraordinario |

> Hermanos del eje «TRABAJO»: Diurno; Nocturno; Nocturno excepcional; Cualquier franja horaria; Cualquier franja horaria excepcional

**Veredicto 69:** A

---

### 70. `template_paraphrase` — TEXTO template (OEB160$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Mandrilado de canalización existente. Condiciones de ejecución: $A. | Procedimiento de mandrilado para canalización existente, condiciones de ejecución: $A. |

**Veredicto 70:** A

---

### 71. `template_paraphrase` — RESUMEN template (OEB090$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Tubo de acero galvanizado de $A ($L(%B)/$M(%C)/$N(%D)) | Se dispone de conducto de acero galvanizado con especificaciones de $A ($L(%B)/$M(%C)/$N(%D)) |

**Veredicto 71:** A

---

### 72. `unit_expansion` — BANDA DE MANTENIMIENTO / i< 3 horas

_Criterio del tipo: unidad/expresión desarrollada, mismo valor_

| Original | Candidato |
|---|---|
| i< 3 horas | Mantenimiento cada menos de tres horas |

> Hermanos del eje «BANDA DE MANTENIMIENTO»: i >= 5 horas; 3 <= i < 5 horas; No necesita intervalo

**Veredicto 72:** A

---

### 73. `omission` — TEXTO — omit $B (OEB140$)

_Criterio del tipo: plantilla sin la mención omitida, gramaticalmente reparada_

| Original | Candidato |
|---|---|
| Apertura y tapado de cata para localización de canalización existente, con reparación, en su caso, para la localización de canalización, obstrucciones,  reparación, y el tapado de la canalización. Trabajo: $A Banda de mantenimiento: $B Condiciones de ejecución: $C | Apertura y tapado de cata para localización de canalización existente, con reparación, en su caso, para la localización de canalización, obstrucciones, reparación, y el tapado de la canalización. Trabajo: $A. Condiciones de ejecución: $C |

> Variable omitida: $B

**Veredicto 73:** A

---

### 74. `expansion` — $N / %B=="d": la demolición y la reposición del firme y del pavimento,

_Criterio del tipo: explicita lo implícito; PROHIBIDO añadir hechos_

| Original | Candidato |
|---|---|
| la demolición y la reposición del firme y del pavimento, | la demolición y la reposición del firme y del pavimento, con especial atención a la adherencia y cohesión de los materiales utilizados, |

> Fragmentos hermanos de la variable: "el descerne y la entibación de los costados y la posterior reposición del balasto retirado,"; "la demolición de roca dura,"; "la demolición y la reposición del pavimento y la solera,"

**Veredicto 74:** A

---

### 75. `new_param` — NEW_PARAM on OEB080$

_Criterio del tipo: eje nuevo plausible, sin colisionar; valores excluyentes y sensatos_

| Original | Candidato |
|---|---|
| (nuevo eje sobre el concepto — no hay original) | eje «TIPO DE RESISTENCIA A LA CORROSIÓN» → {Alta resistencia, Resistencia media, Baja resistencia, Resistencia química, Sin tratamiento} |

> Ejes existentes del concepto: DIÁMETRO; CONDICIONES DE EJECUCIÓN

**Veredicto 75:** A

---

### 76. `template_paraphrase` — TEXTO template (OEB140$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Apertura y tapado de cata para localización de canalización existente, con reparación, en su caso, para la localización de canalización, obstrucciones,  reparación, y el tapado de la canalización. Trabajo: $A Banda de mantenimiento: $B Condiciones de ejecución: $C | Realización de apertura y cierre de cata para la identificación de la conducción enterrada existente, con reparación si fuera necesario, para detectar obstrucciones y realizar las correcciones pertinentes, finalizando con el cierre de la conducción. Trabajo: $A Banda de mantenimiento: $B Condiciones de ejecución: $C |

**Veredicto 76:** A

---

### 77. `omission` — TEXTO — omit $B (OEB090$)

_Criterio del tipo: plantilla sin la mención omitida, gramaticalmente reparada_

| Original | Candidato |
|---|---|
| Suministro y montaje de tubo de acero galvanizado de $A , incluida parte proporcional de herrajes de sujeción y de caja de registro, incluso mandrilado. Trabajo: $B Banda de mantenimiento: $C Condiciones de ejecución: $D | Suministro y montaje de tubo de acero galvanizado de $A , incluida parte proporcional de herrajes de sujeción y de caja de registro, incluso mandrilado. Con banda de mantenimiento: $C y condiciones de ejecución: $D |

> Variable omitida: $B

**Veredicto 77:** A

---

### 78. `paraphrase` — $W / %A=a: material de la traza

_Criterio del tipo: mismo contenido del fragmento, otras palabras_

| Original | Candidato |
|---|---|
| material de la traza | material de la línea de tren |

> Fragmentos hermanos de la variable: "material de cantera"

**Veredicto 78:** A

---

### 79. `unit_expansion` — BANDA DE MANTENIMIENTO / 3 <= i < 5 horas

_Criterio del tipo: unidad/expresión desarrollada, mismo valor_

| Original | Candidato |
|---|---|
| 3 <= i < 5 horas | intervalo entre tres y cinco horas |

> Hermanos del eje «BANDA DE MANTENIMIENTO»:  i >= 5 horas; i < 3 horas; No necesita intervalo

**Veredicto 79:** A

---

### 80. `unit_conversion` — DIÁMETRO / 29mm

_Criterio del tipo: conversión aritméticamente correcta_

| Original | Candidato |
|---|---|
| 29mm | 0.029 m |

> Hermanos del eje «DIÁMETRO»: 21mm; 36mm; 40mm; 48mm

**Veredicto 80:** A

---

### 81. `omission` — TEXTO — omit $A (OEB020$)

_Criterio del tipo: plantilla sin la mención omitida, gramaticalmente reparada_

| Original | Candidato |
|---|---|
| Canalización hormigonada de $A tubos de PVC de 110 mm de diámetro $I, incluso $N el relleno y el compactado de la zanja, $P el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F | Canalización hormigonada de tubos de PVC de 110 mm de diámetro $I, incluso $N el relleno y el compactado de la zanja, $P el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F |

> Variable omitida: $A

**Veredicto 81:** A

---

### 82. `omission` — TEXTO — omit $B (OEB140$)

_Criterio del tipo: plantilla sin la mención omitida, gramaticalmente reparada_

| Original | Candidato |
|---|---|
| Apertura y tapado de cata para localización de canalización existente, con reparación, en su caso, para la localización de canalización, obstrucciones,  reparación, y el tapado de la canalización. Trabajo: $A Banda de mantenimiento: $B Condiciones de ejecución: $C | Apertura y tapado de cata para localización de canalización existente, con reparación, en su caso, para la localización de canalización, obstrucciones, reparación, y el tapado de la canalización. Trabajo: $A. Condiciones de ejecución: $C. |

> Variable omitida: $B

**Veredicto 82:** A

---

### 83. `new_param` — NEW_PARAM on OEB050$

_Criterio del tipo: eje nuevo plausible, sin colisionar; valores excluyentes y sensatos_

| Original | Candidato |
|---|---|
| (nuevo eje sobre el concepto — no hay original) | eje «MÉTODO DE INSTALACIÓN» → {Túnel, Corte y relleno, Microtúnel, Tubería enterrada, Caja de hormigón} |

> Ejes existentes del concepto:  TERRENO ;  PAVIMENTO ; CONDICIONES DE EJECUCIÓN

**Veredicto 83:** A

---

### 84. `paraphrase` — $I / %B=="e": en andén

_Criterio del tipo: mismo contenido del fragmento, otras palabras_

| Original | Candidato |
|---|---|
| en andén | en zona de andén |

> Fragmentos hermanos de la variable: "en cualquier clase de terreno, excepto roca"; "en cruce bajo vías"; "en terreno rocoso"; "en cruce de carretera"; "adosada o superficial"; "en zona de balasto"; "en cruce bajo vías ejecutado con topo"

**Veredicto 84:** A

---

### 85. `template_paraphrase` — TEXTO template (OEB120$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Suministro y ejecución de embocadura canalización de $A tubos en arqueta o cámara existente Trabajo: $B Banda de mantenimiento: $C Condiciones de ejecución: $D | Realización y suministro de boca de embocadura para la conducción de $A conductos en una arqueta o cámara ya existente. Trabajo: $B, Banda de mantenimiento: $C, Condiciones de ejecución: $D |

**Veredicto 85:** A

---

### 86. `template_paraphrase` — RESUMEN template (OEB290$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Canalización hormigonada $A T, polietileno libre de halógenos de 50 mm, $K. ($G(%C)/$H(%D)/$J(%F)) | La canalización de hormigón $A T está hecha con polietileno sin halógenos y un diámetro de 50 mm, $K. Se detallan en las especificaciones ($G(%C)/$H(%D)/$J(%F)) |

**Veredicto 86:** A

---

### 87. `reorder` — TEXTO template (OEB300$)

_Criterio del tipo: mismas palabras/cláusulas en otro orden_

| Original | Candidato |
|---|---|
| Canalización hormigonada de $A tubos de polietileno libre de halógenos de 90 mm de diámetro $I, incluso $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F | Canalización hormigonada de $A tubos de polietileno libre de halógenos de 90 mm de diámetro $I, incluso $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, $N el relleno y compactado de la zanja, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F |

**Veredicto 87:** A

---

### 88. `omission` — RESUMEN — omit $B (OEB250$)

_Criterio del tipo: plantilla sin la mención omitida, gramaticalmente reparada_

| Original | Candidato |
|---|---|
| $A de canalización de $B tubos de acero galvanizado de 100mm de diámetro para instalaciones CMS en transiciones entre diferentes plataformas.($L(%C)/$M(%D)/$N(%F)) | $A de canalización de tubos de acero galvanizado de 100mm de diámetro para instalaciones CMS en transiciones.($L(%C)/$M(%D)/$N(%F)) |

> Variable omitida: $B

**Veredicto 88:** A

---

### 89. `num_to_text` — Nº TUBOS / 4

_Criterio del tipo: número en letras, conservando el sustantivo_

| Original | Candidato |
|---|---|
| 4 | Número cuatro |

> Hermanos del eje «Nº TUBOS»:  2 ;  4 ;  6 ;  8 ;  12 ;  16 ;  18 ;  24 

**Veredicto 89:** A

---

### 90. `expansion` — $G / %C=c: Diurno Excepcional

_Criterio del tipo: explicita lo implícito; PROHIBIDO añadir hechos_

| Original | Candidato |
|---|---|
| Diurno Excepcional | Diurno Excepcional, referido a intervenciones urgentes durante el horario de oficina. |

> Fragmentos hermanos de la variable: "Diurno"; "Nocturno"; "Nocturno Excepcional"; "Cualquier frana horaria"; "Cualquier franja horaria excepcional"

**Veredicto 90:** A

---

### 91. `template_paraphrase` — RESUMEN template (OEB230$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Canalización hormigonada $A T, polietileno libre de halógenos de 200 mm, $K. ($G(%C)/$H(%D)/$J(%F)) | Se instala conducción enterrada con hormigón $A T y se utiliza material de polietileno que no contiene halógenos de 200 mm, $K. Se indica la verificación ($G(%C)/$H(%D)/$J(%F)). |

**Veredicto 91:** A

---

### 92. `omission` — RESUMEN — omit $H (OEB040$)

_Criterio del tipo: plantilla sin la mención omitida, gramaticalmente reparada_

| Original | Candidato |
|---|---|
| Canalización hormigonada $A T, polietileno libre de halógenos de 160 mm, $K. ($G(%C)/$H(%D)/$J(%F)) | Canalización hormigonada $A T, polietileno libre de halógenos de 160 mm, $K. ($G(%C) y $J(%F)) |

> Variable omitida: $H

**Veredicto 92:** A

---

### 93. `omission` — RESUMEN — omit $M (OEB120$)

_Criterio del tipo: plantilla sin la mención omitida, gramaticalmente reparada_

| Original | Candidato |
|---|---|
| Suministro y ejecución de embocadura canalización de $A tubos en arqueta o cámara existente ($L(%B)/$M(%C)/$N(%D)) | Suministro y ejecución de embocadura canalización de $A tubos en arqueta o cámara existente ($L(%B) y $N(%D)) |

> Variable omitida: $M

**Veredicto 93:** A

---

### 94. `unit_conversion` — PROFUNDIDAD / 1,10 m

_Criterio del tipo: conversión aritméticamente correcta_

| Original | Candidato |
|---|---|
| 1,10 m | 1,1 m |

> Hermanos del eje «PROFUNDIDAD»: hasta 0,80 m; 0,80 a 1,00 m

**Veredicto 94:** A

---

### 95. `compression` — $I / %B=="a": en cualquier clase de terreno, excepto roca

_Criterio del tipo: estrictamente más corta, sin perder contenido_

| Original | Candidato |
|---|---|
| en cualquier clase de terreno, excepto roca | en cualquier terreno, salvo roca |

> Fragmentos hermanos de la variable: "en cruce bajo vías"; "en terreno rocoso"; "en cruce de carretera"; "en andén"; "adosada o superficial"; "en zona de balasto"; "en cruce bajo vías ejecutado con topo"

**Veredicto 95:** A

---

### 96. `synonym_label` — TRABAJO / Nocturno Excepcional

_Criterio del tipo: sinónimo/etiqueta equivalente, distinguible de los hermanos_

| Original | Candidato |
|---|---|
| Nocturno Excepcional | Horario Nocturno Extra |

> Hermanos del eje «TRABAJO»: Diurno; Nocturno; Diurno Excepcional; Cualquier franja horaria; Cualquier franja horaria excepcional

**Veredicto 96:** A

---

### 97. `unit_expansion` — BANDA DE MANTENIMIENTO / 3 <= i < 5 horas

_Criterio del tipo: unidad/expresión desarrollada, mismo valor_

| Original | Candidato |
|---|---|
| 3 <= i < 5 horas | entre tres y cinco horas |

> Hermanos del eje «BANDA DE MANTENIMIENTO»:  i >= 5 horas; i < 3 horas; No necesita intervalo

**Veredicto 97:** A

---

### 98. `new_param` — NEW_PARAM on OEB130$

_Criterio del tipo: eje nuevo plausible, sin colisionar; valores excluyentes y sensatos_

| Original | Candidato |
|---|---|
| (nuevo eje sobre el concepto — no hay original) | eje «MATERIAL DE TUBERÍA» → {PVC, Policloruro de vinilo, Hierro fundido, Acero inoxidable, Cobre} |

> Ejes existentes del concepto: TRABAJO; BANDA DE MANTENIMIENTO; CONDICIONES DE EJECUCIÓN

**Veredicto 98:** A

---

### 99. `template_paraphrase` — TEXTO template (OEB110$)

_Criterio del tipo: plantilla completa reescrita (léxico y/o estructura)_

| Original | Candidato |
|---|---|
| Suministro y colocación de tubería de PVC de 110 mm de diámetro para drenaje de arqueta desde centro de arqueta a pie de talud incluyendo relleno y compactación de tierras. Trabajo: $A Banda de mantenimiento: $B Condiciones de ejecución: $C | Se proveerá y colocará tubería de PVC de 110 mm de diámetro para el drenaje de arquetas, desde el centro de la arqueta hasta el pie de talud, incluyendo el relleno y compactación de tierras. Se realizará el trabajo: $A. Se establecerá una banda de mantenimiento: $B. Se tendrán en cuenta las condiciones de ejecución: $C. |

**Veredicto 99:** A

---

### 100. `expansion` — $N / %B=="e": la demolición y reposición del pavimento y la solera,

_Criterio del tipo: explicita lo implícito; PROHIBIDO añadir hechos_

| Original | Candidato |
|---|---|
| la demolición y reposición del pavimento y la solera, | la demolición y reposición del pavimento y la solera, incluyendo la instalación de juntas de dilatación, |

> Fragmentos hermanos de la variable: "el descerne y la entibación de los costados y la posterior reposición del balasto retirado,"; "la demolición de roca dura,"; " la demolición y reposición del firme y del pavimento,"

**Veredicto 100:** A
