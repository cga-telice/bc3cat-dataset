# Auditoría de la revisión — para César (2026-08-31)

**Cómo rellenar:** igual que la muestra de calibración — abre en VS Code, vista previa
con Ctrl+Mayús+V para leer, y edita el fuente sustituyendo el guion bajo `_` de cada
campo **Respuesta**. Guarda y dime "listo". Los códigos tipo `expansion:33:5` son
referencias internas mías; ignóralos, cada ítem trae su texto completo.

Tiempo estimado: 30–45 min en total. Las partes son independientes — puedes hacer
una y decirme que siga con esa.


---

## Parte 1 — Los 10 Dudosos (escribe **A** para aprobar o **R** para rechazar)

Son los candidatos donde no me atreví a decidir sin tu criterio de ingeniero.

### D1 — tipo `expansion`

| Original | Candidato |
|---|---|
| incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro, el suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido. | incluso la construcción del pozo de ataque, entibación de los costados para soportar la estructura, instalación de un tubo guía de acero de 500 mm de diámetro para guiar el proceso, el suministro y montaje de los hilos guía para mantener la trayectoria, y el sellado de las embocaduras con poliuretano expandido para asegurar la hermeticidad. |

_Mi duda: Dudoso si 'entibación para soportar la estructura' enuncia el propósito inherente o lo desvirtúa (la entibación sostiene los costados, no 'la estructura')._

**Respuesta D1 (A/R):** _

### D2 — tipo `expansion`

| Original | Candidato |
|---|---|
| incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro, el suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido. | incluso la construcción del pozo de ataque, entibación de los costados para soportar la estructura, instalación de un tubo guía de acero de 500 mm de diámetro para guiar el proceso, el suministro y montaje de los hilos guía para asegurar la alineación, y el sellado de las embocaduras con poliuretano expandido para evitar filtraciones. |

_Mi duda: Mismo caso dudoso: 'entibación para soportar la estructura' es vago o desacertado como propósito de la entibación._

**Respuesta D2 (A/R):** _

### D3 — tipo `expansion`

| Original | Candidato |
|---|---|
| incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro, el suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido. | incluso la construcción del pozo de ataque, entibación de los costados para soportar la estructura, instalación de un tubo guía de acero de 500 mm de diámetro para facilitar el posicionamiento, el suministro y montaje de los hilos guía para mantener la trayectoria, y el sellado de las embocaduras con poliuretano expandido para asegurar la hermeticidad. |

_Mi duda: Mismo caso dudoso de 'entibación para soportar la estructura'; el resto de cláusulas son propósitos inherentes válidos._

**Respuesta D3 (A/R):** _

### D4 — tipo `new_param`

| Original | Candidato |
|---|---|
| (eje nuevo — sin original) | eje «GRADO DE GALVANIZACIÓN» → {G60, G90, G120, G185, G240} |

_Mi duda: Eje plausible pero G120/G240 no son designaciones estándar y su aplicabilidad a tubo requiere experto._

**Respuesta D4 (A/R):** _

### D5 — tipo `new_param`

| Original | Candidato |
|---|---|
| (eje nuevo — sin original) | eje «NIVEL DE PROTECCIÓN» → {IP65, IP67, IP68, IP69, IP54} |

_Mi duda: Los grados IP son propios de envolventes y accesorios mas que de la canalización en si; hace falta criterio experto para decidir si es plausible como eje._

**Respuesta D5 (A/R):** _

### D6 — tipo `paraphrase`

| Original | Candidato |
|---|---|
| Cualquier frana horaria | Horario completo sin excepciones |

_Mi duda: 'Sin excepciones' es ambiguo frente al hermano 'excepcional'; requiere criterio experto._

**Respuesta D6 (A/R):** _

### D7 — tipo `paraphrase`

| Original | Candidato |
|---|---|
| en zona de balasto | en sección de balasto |

_Mi duda: «sección de balasto» puede leerse como perfil transversal, no como zona; requiere criterio experto ferroviario._

**Respuesta D7 (A/R):** _

### D8 — tipo `paraphrase`

| Original | Candidato |
|---|---|
| normal | en tierra |

_Mi duda: 'en tierra' podría glosar 'cualquier terreno excepto roca', pero no es obvio que equivalga a 'normal'; requiere criterio experto._

**Respuesta D8 (A/R):** _

### D9 — tipo `template_paraphrase`

| Original | Candidato |
|---|---|
| Suministro y ejecución de canalización en túnel para acceso a interfonía desde canaleta de hormigón utilizando tubo de acero hasta el repartidor Trabajo: $A Banda de mantenimiento: $B Condiciones de ejecución: $C. | Se suministrará y ejecutará la conducción enterrada en túnel para el acceso a interfonía, mediante la utilización de conductos de acero desde canaleta de hormigón hasta el repartidor. Trabajo: $A Banda de mantenimiento: $B Condiciones de ejecución: $C. |

_Mi duda: Único reparo: 'enterrada' añadido a la conducción en túnel — ¿hecho añadido o explicitación válida? Resto impecable._

**Respuesta D9 (A/R):** _

### D10 — tipo `template_paraphrase`

| Original | Candidato |
|---|---|
| Suministro y ejecución de canalización en túnel para acceso a interfonía desde canaleta de hormigón utilizando tubo de acero hasta el repartidor Trabajo: $A Banda de mantenimiento: $B Condiciones de ejecución: $C. | Instalación y suministro de conducción enterrada en túnel para la conexión de interfonía, utilizando conductos de acero desde la canaleta de hormigón hasta el repartidor. Trabajo: $A, banda de mantenimiento: $B, condiciones de ejecución: $C. |

_Mi duda: Mismo caso que 45:9: solo el añadido 'enterrada' separa esta paráfrasis limpia de la A; requiere criterio de ingeniero._

**Respuesta D10 (A/R):** _


---

## Parte 2 — 5 reglas de línea fina (escribe **OK** si mantengo mi criterio, o describe el cambio)

**Regla 1.** En las hincas bajo vía (OEB180), el original dice tender cables **sobre** una trinchera (suspendidos de un cable tensor). 7 candidatos escriben **en** la trinchera. Los rechacé porque la preposición codifica el método. Si te parece incidental, recupero los 7.

**Respuesta R1:** _

**Regla 2.** 3 candidatos por lo demás perfectos llegaron envueltos en comillas literales ("…texto…") que se colarían en el render. Los rechacé. Si el pipeline va a despojar comillas envolventes, los recupero.

**Respuesta R2:** _

**Regla 3.** En omission, 8 candidatos comprimen «de 160 mm de diámetro $I» a «de 160 mm». Los APROBÉ (reparación flexible: el diámetro queda inequívoco en un tubo). Confirma o los rechazo.

**Respuesta R3:** _

**Regla 4.** En expansion tracé esta línea: adjetivos de atributo implícito (necesarios, posterior, adecuados) = aprobar; adjetivos de manera/calidad (meticulosa, cuidadoso, sistemático) = rechazar. Confirma la línea.

**Respuesta R4:** _

**Regla 5.** En OEB190, toda la familia de reescrituras pierde la palabra «seleccionado» de «material seleccionado» (una spec del relleno). Los rechacé todos. Confirma.

**Respuesta R5:** _


---

## Parte 3 — Muestra de auditoría: 30 veredictos míos al azar (escribe **OK** o el veredicto correcto)

No re-revises desde cero: lee mi veredicto y mi razón, y di si te vale.

### M1 — tipo `paraphrase` — mi veredicto: **APROBADO**

| Original | Candidato |
|---|---|
| Nocturno excepcional | Nocturno especial |

_Mi razón: Nocturno especial conserva significado y sigue distinguiéndose de Nocturno._

**Respuesta M1 (OK / A / R):** _

### M2 — tipo `omission` — mi veredicto: **APROBADO**

| Original | Candidato |
|---|---|
| Canalización hormigonada $A T, polietileno libre de halógenos de 50 mm, $K. ($G(%C)/$H(%D)/$J(%F)) | Canalización hormigonada $A T, polietileno libre de halógenos de 50 mm, $K. ($H(%D)/$J(%F)) |

_Mi razón: Omisión limpia de $G, separadores intactos._

**Respuesta M2 (OK / A / R):** _

### M3 — tipo `synonym_label` — mi veredicto: **APROBADO**

| Original | Candidato |
|---|---|
| duro | Terreno Resistente |

_Mi razón: 'Terreno Resistente' equivale a duro y es distinguible._

**Respuesta M3 (OK / A / R):** _

### M4 — tipo `expansion` — mi veredicto: **RECHAZADO**

| Original | Candidato |
|---|---|
| en cruce bajo vías | en cruce bajo vías, donde la canalización se coloca estratégicamente para evitar interferencias con el tráfico ferroviario |

_Mi razón: Añade 'estratégicamente' y finalidad de evitar interferencias, valoración._

**Respuesta M4 (OK / A / R):** _

### M5 — tipo `reorder` — mi veredicto: **APROBADO**

| Original | Candidato |
|---|---|
| $A de canalización de $B tubos de acero galvanizado de 100mm de diámetro para instalaciones CMS en transiciones entre diferentes plataformas.($L(%C)/$M(%D)/$N(%F)) | $A de canalización de $B tubos de acero galvanizado de 100mm de diámetro para instalaciones CMS en transiciones entre diferentes plataformas. $N(%F)/$M(%D)/$L(%C) |

_Mi razón: Reordenación interna del bloque tras el punto; la pérdida de paréntesis es puntuación mínima, sigue legible._

**Respuesta M5 (OK / A / R):** _

### M6 — tipo `omission` — mi veredicto: **APROBADO**

| Original | Candidato |
|---|---|
| Canalización hormigonada de $A tubos de polietileno libre de halógenos de 40 mm de diámetro $I, incluso $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F | Canalización hormigonada de $A tubos de polietileno libre de halógenos de 40 mm de diámetro $I, incluso $N el relleno y compactado de la zanja, el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F |

_Mi razón: Elimina solo $P; frase gramatical, resto intacto._

**Respuesta M6 (OK / A / R):** _

### M7 — tipo `omission` — mi veredicto: **APROBADO**

| Original | Candidato |
|---|---|
| Suministro y colocación de tubería de PVC de 110 mm de diámetro para drenaje de arqueta desde centro de arqueta a pie de talud incluyendo relleno y compactación de tierras. Trabajo: $A Banda de mantenimiento: $B Condiciones de ejecución: $C | Suministro y colocación de tubería de PVC de 110 mm de diámetro para drenaje de arqueta desde el centro de la arqueta hasta el pie de talud, incluyendo relleno y compactación de tierras. Banda de mantenimiento: $B Condiciones de ejecución: $C |

_Mi razón: Omisión limpia de $A; los artículos y 'hasta' son reescritura local que conserva el contenido._

**Respuesta M7 (OK / A / R):** _

### M8 — tipo `compression` — mi veredicto: **RECHAZADO**

| Original | Candidato |
|---|---|
| la preparación y nivelación de la solera, suministro y montaje del encofrado, elementos de fijación, desencofrado, | nivelación de solera, montaje de encofrado, fijación, desencofrado, |

_Mi razón: Pierde 'preparación' y 'suministro' del encofrado._

**Respuesta M8 (OK / A / R):** _

### M9 — tipo `num_to_text` — mi veredicto: **RECHAZADO**

| Original | Candidato |
|---|---|
| 12 | Número doce |

_Mi razón: 'Número doce' se lee como identificador ordinal, no como cantidad de tubos._

**Respuesta M9 (OK / A / R):** _

### M10 — tipo `omission` — mi veredicto: **APROBADO**

| Original | Candidato |
|---|---|
| Canalización hormigonada $A T, polietileno libre de halógenos de 40 mm, $K. ($G(%C)/$H(%D)/$J(%F)) | Canalización hormigonada $A T, polietileno libre de halógenos de 40 mm, $K. ($H(%D)/$J(%F)) |

_Mi razón: Omisión limpia de $G en el paréntesis, separadores intactos._

**Respuesta M10 (OK / A / R):** _

### M11 — tipo `compression` — mi veredicto: **APROBADO**

| Original | Candidato |
|---|---|
| en cualquier clase de terreno, excepto roca | en todo terreno, excepto roca |

_Mi razón: Estrictamente más corta, fluida y sin pérdida de contenido._

**Respuesta M11 (OK / A / R):** _

### M12 — tipo `template_paraphrase` — mi veredicto: **RECHAZADO**

| Original | Candidato |
|---|---|
| Ejecución de canalización para línea subterránea de telecomunicaciones, en derivación a arquetas de telecomunicaciones y junto a cámaras de empalme, de cables entubados y tubos embebidos en hormigón HE-20, de dimensiones totales 450 mm de ancho por 1 m de alto, hormigonado hasta cota de 650 mm de profundidad, posterior relleno compactado al 95% P.M. Incluidos 2 tetratubos de polietileno de 4x40 mm | Instalación de un sistema subterráneo de conducción de cables y conductos embutidos en hormigón HE-20, con dimensiones totales de 450 mm de ancho por 1 m de alto, enlazando con arquetas y cámaras de empalme, hormigonada hasta una profundidad de cota 650 mm, seguida de un relleno compactado al 95% P.M. Se incluyen 2 tetratubos de polietileno con diámetro exterior de 4x40 mm para telecomunicaciones, |

_Mi razón: Pierde 'medios auxiliares' y la derivación/adyacencia se difumina en 'enlazando'; cierre 'de $C' clunky._

**Respuesta M12 (OK / A / R):** _

### M13 — tipo `template_paraphrase` — mi veredicto: **RECHAZADO**

| Original | Candidato |
|---|---|
| Canalización hormigonada $A T, polietileno libre de halógenos de 90 mm, $K. ($G(%C)/$H(%D)/$J(%F)) | Conducción enterrada de concreto $A T, con revestimiento de polietileno sin halógenos de 90 mm, y propiedades detalladas en $K. Referencia estándar: $G(%C)/$H(%D)/$J(%F) |

_Mi razón: 'Conducción de concreto con revestimiento de polietileno' distorsiona materiales y 'propiedades detalladas en $K' rinde sinsentido._

**Respuesta M13 (OK / A / R):** _

### M14 — tipo `omission` — mi veredicto: **RECHAZADO**

| Original | Candidato |
|---|---|
| Canalización hormigonada de $A tubos de PVC de 110 mm de diámetro $I, incluso $N el relleno y el compactado de la zanja, $P el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F | Canalización hormigonada de $A tubos de PVC de 110 mm, incluso $N el relleno y el compactado de la zanja, $P el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F |

_Mi razón: Además de $I borra 'de diámetro': pérdida de contenido extra._

**Respuesta M14 (OK / A / R):** _

### M15 — tipo `template_paraphrase` — mi veredicto: **RECHAZADO**

| Original | Candidato |
|---|---|
| Suministro y ejecución de canalización en túnel acceso interfono ($L(%A)/$M(%B)/$N(%C)) | Provisión y montaje de infraestructura de conducción en túnel acceso interfono ($L(%A)/$M(%B)/$N(%C)) ($L(%A)/$M(%B)/$N(%C)) |

_Mi razón: Paréntesis de parámetros duplicado al final._

**Respuesta M15 (OK / A / R):** _

### M16 — tipo `omission` — mi veredicto: **APROBADO**

| Original | Candidato |
|---|---|
| Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: $B Banda de mantenimiento: $C Condiciones de ejecución: $D | Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: $B Banda de mantenimiento: $C |

_Mi razón: Omisión limpia de 'Condiciones de ejecución: $D'._

**Respuesta M16 (OK / A / R):** _

### M17 — tipo `template_paraphrase` — mi veredicto: **RECHAZADO**

| Original | Candidato |
|---|---|
| Hincas con cable tensor de acero para el tendido de cables sobre una trinchera de tierra. ($L(%A)/$M(%B)/$N(%C)) | Se emplean hincas con cable tensor de acero para la instalación de cables en una trinchera de tierra. ($L(%A)/$M(%B)/$N(%C)) |

_Mi razón: "instalación de cables en una trinchera" pierde el matiz "sobre" del método original._

**Respuesta M17 (OK / A / R):** _

### M18 — tipo `new_param` — mi veredicto: **RECHAZADO**

| Original | Candidato |
|---|---|
| (eje nuevo — sin original) | eje «TIPO DE CUBIERTA» → {Cubierta de concreto, Cubierta de asfalto, Cubierta de metal, Cubierta de plástico, Cubierta de madera} |

_Mi razón: Una zanja para cables rellena y compactada no lleva cubierta de madera, plastico o asfalto; 'concreto' fuera de registro._

**Respuesta M18 (OK / A / R):** _

### M19 — tipo `omission` — mi veredicto: **APROBADO**

| Original | Candidato |
|---|---|
| Canalización hormigonada de $A T, PVC 110 mm, $K. ($G(%C)/$H(%D)/$J(%F)) | Canalización hormigonada de $A T, PVC 110 mm, $K. ($H(%D) y $J(%F)) |

_Mi razón: Omite $G; conector 'y' válido._

**Respuesta M19 (OK / A / R):** _

### M20 — tipo `paraphrase` — mi veredicto: **APROBADO**

| Original | Candidato |
|---|---|
| zona de balasto, ejecutada a mano incluso descerne y entibación de costados y posterior reposición del balasto retirado | zona de balasto, realizada a mano con descerne y entibación de costados, y reposición del balasto retirado |

_Mi razón: Contenido íntegro; la posterioridad de la reposición queda implícita en el orden._

**Respuesta M20 (OK / A / R):** _

### M21 — tipo `expansion` — mi veredicto: **RECHAZADO**

| Original | Candidato |
|---|---|
| la preparación y la nivelación de la solera, el suministro y montaje del encofrado, elementos de fijación, desencofrado, | la preparación y nivelación de la solera, el suministro y montaje del encofrado, elementos de fijación precisos, y el desencofrado final, |

_Mi razón: Adjetivo valorativo añadido ('elementos de fijación precisos')._

**Respuesta M21 (OK / A / R):** _

### M22 — tipo `reorder` — mi veredicto: **APROBADO**

| Original | Candidato |
|---|---|
| Canalización hormigonada $A T, polietileno libre de halógenos de 110 mm, $K. ($G(%C)/$H(%D)/$J(%F)) | Canalización hormigonada $A T, polietileno libre de halógenos de 110 mm ($G(%C)/$H(%D)/$J(%F)), $K. |

_Mi razón: Bloque parentético desplazado antes de ', $K'; la coma mantiene $K ligado, gramática correcta._

**Respuesta M22 (OK / A / R):** _

### M23 — tipo `template_paraphrase` — mi veredicto: **RECHAZADO**

| Original | Candidato |
|---|---|
| Canalización hormigonada de $A tubos de polietileno libre de halógenos de 50 mm de diámetro $I, incluso $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F | Conducción subterránea con $A tubos de polietileno sin halógenos de 50 mm mm de diámetro $I, contemplando $N el relleno y compactación de la excavación, $P el provisión y colocación de los tubos y el hormigón de tipo HE-20 sin vibración, las pruebas de los conductos, la logística y traslado de los materiales al lugar de instalación $M Trabajo: $C Área de mantenimiento: $D Condiciones de ejecución: |

_Mi razón: «50 mm mm» duplicado y «el provisión» sin concordancia; «subterránea» contradice adosada/superficial._

**Respuesta M23 (OK / A / R):** _

### M24 — tipo `template_paraphrase` — mi veredicto: **RECHAZADO**

| Original | Candidato |
|---|---|
| Suministro y ejecución de canalización en túnel para acceso a interfonía desde canaleta de hormigón utilizando tubo de acero hasta el repartidor Trabajo: $A Banda de mantenimiento: $B Condiciones de ejecución: $C. | Realización y montaje de tubería para sistemas de intercomunicación, en túnel a través de conducción de acero desde canalones de hormigón hasta el distribuidor. Trabajo: $A Banda de mantenimiento: $B Condiciones de ejecución: $C. |

_Mi razón: 'Canalones' recategoriza la canaleta; pierde 'suministro' y 'acceso a'._

**Respuesta M24 (OK / A / R):** _

### M25 — tipo `expansion` — mi veredicto: **APROBADO**

| Original | Candidato |
|---|---|
| Cualquier frana horaria | Cualquier franja horaria, abarcando todas las divisiones del día |

_Mi razón: Explicitación fiel ('todas las divisiones del día')._

**Respuesta M25 (OK / A / R):** _

### M26 — tipo `paraphrase` — mi veredicto: **RECHAZADO**

| Original | Candidato |
|---|---|
| en terreno rocoso | en suelo compuesto de roca |

_Mi razón: «suelo compuesto de roca» es incoherente: eso ya no es suelo, es roca._

**Respuesta M26 (OK / A / R):** _

### M27 — tipo `omission` — mi veredicto: **APROBADO**

| Original | Candidato |
|---|---|
| Canalización hormigonada de $A tubos de PVC de 110 mm de diámetro $I, incluso $N el relleno y el compactado de la zanja, $P el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F | Canalización hormigonada de $A tubos de PVC de 110 mm de diámetro, incluyendo $N el relleno y el compactado de la zanja, $P el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F |

_Mi razón: Omite $I conservando 'de diámetro'; 'incluyendo' es sinónimo admisible._

**Respuesta M27 (OK / A / R):** _

### M28 — tipo `unit_expansion` — mi veredicto: **APROBADO**

| Original | Candidato |
|---|---|
| i< 3 horas | Intervalo menor a tres horas |

_Mi razón: Desarrollo fiel de i < 3 horas, mismo valor._

**Respuesta M28 (OK / A / R):** _

### M29 — tipo `expansion` — mi veredicto: **RECHAZADO**

| Original | Candidato |
|---|---|
| Diurno Excepcional | Diurno Excepcional, para operaciones urgentes en el horario laboral diurno. |

_Mi razón: Operaciones urgentes añade un hecho no implícito en Diurno Excepcional._

**Respuesta M29 (OK / A / R):** _

### M30 — tipo `template_paraphrase` — mi veredicto: **RECHAZADO**

| Original | Candidato |
|---|---|
| Canalización hormigonada de $A T, PVC 110 mm, $K. ($G(%C)/$H(%D)/$J(%F)) | Se ejecuta la canalización mediante tubería hormigonada de $A T, con conductos de PVC 110 mm, $K. Se detalla: ($G(%C)/$H(%D)/$J(%F)) |

_Mi razón: 'Canalización mediante tubería hormigonada con conductos' duplica el objeto (tubería vs conductos) en construcción forzada y confusa._

**Respuesta M30 (OK / A / R):** _


---

## Parte 4 — 79 targets sin ningún candidato aprobado (una decisión por familia)

Para cada familia, escribe **REGENERAR** (Sprint 40 con prompts corregidos), **HUECO** (aceptar que ese target no tendrá esa reescritura) o **VER** (te listo los candidatos rechazados de esa familia para adjudicar a mano).

**compression** (8 targets). 8 targets — fragmentos universales ('Cualquier…') o listas donde comprimir = perder contenido. Mi recomendación: HUECO (son incomprimibles por naturaleza).

**Respuesta compression:** _

**expansion** (21 targets). 21 targets — el generador solo produce colas valorativas para valores numéricos y etiquetas de volumen. Mi recomendación: REGENERAR (prompt: 'solo definición o propósito constitutivo, sin adjetivos de beneficio').

**Respuesta expansion:** _

**new_param** (3 targets). 3 targets (OEB090/200/240) — conceptos donde todos los ejes propuestos son disparates. Mi recomendación: REGENERAR.

**Respuesta new_param:** _

**omission** (16 targets). ~9 targets — omisiones cuya única reparación posible quedó mal. Mi recomendación: HUECO (hay 188 targets de omission cubiertos de sobra).

**Respuesta omission:** _

**paraphrase** (8 targets). Mi recomendación: HUECO (tipo bien cubierto por otros targets).

**Respuesta paraphrase:** _

**reorder** (2 targets). Mi recomendación: HUECO (tipo bien cubierto por otros targets).

**Respuesta reorder:** _

**synonym_label** (8 targets). Mi recomendación: HUECO (tipo bien cubierto por otros targets).

**Respuesta synonym_label:** _

**template_paraphrase** (12 targets). 12 targets — plantillas donde todos los candidatos rompen términos de dominio (con topo, hastial) o el bloque paramétrico. Mi recomendación: REGENERAR con glosario de términos protegidos en el prompt.

**Respuesta template_paraphrase:** _

**unit_conversion** (1 targets). Mi recomendación: HUECO (tipo bien cubierto por otros targets).

**Respuesta unit_conversion:** _
