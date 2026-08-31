# Revisión completa de los 11 menús — informe (2026-08-31)

Revisor: Claude (rúbrica v1.1, a ciegas de modelo). Veredictos por candidato en
`<tipo>_verdicts.jsonl`. Ticks `[x]` aplicados en `docs/synthetic/menus/*.md`
(solo los A; los D quedan sin marcar a la espera de César).

## Totales por tipo

| tipo | A | R | D | targets con ≥1 A / poblados |
|---|---|---|---|---|
| compression | 31 | 76 | 0 | ver consolidación |
| expansion | 150 | 301 | 3 | ver consolidación |
| new_param | 50 | 199 | 2 | ver consolidación |
| num_to_text | 24 | 9 | 0 | ver consolidación |
| omission | 354 | 142 | 0 | ver consolidación |
| paraphrase | 175 | 242 | 3 | ver consolidación |
| reorder | 93 | 39 | 0 | ver consolidación |
| synonym_label | 74 | 84 | 0 | ver consolidación |
| template_paraphrase | 164 | 543 | 2 | ver consolidación |
| unit_conversion | 10 | 8 | 0 | ver consolidación |
| unit_expansion | 30 | 3 | 0 | ver consolidación |
| **TOTAL** | **1155** | **1646** | **10** | |

## Consistencia intra-revisor (los 100 de calibración re-juzgados)

Acuerdo 89/100; desacuerdos: #14 synonym_label R→A, #39 paraphrase R→A, #40 template_paraphrase A→R, #55 template_paraphrase R→A, #57 new_param A→R, #63 new_param R→A, #66 expansion R→A, #69 synonym_label R→A, #76 template_paraphrase R→A, #77 omission A→R, #99 template_paraphrase R→A.

## Dudosos (adjudicación de César)

- `expansion:33:2` — $M / %B=="h": incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro, el suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido.
  - Original: incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro, el suministro y montaje de los hilos guía y el sellado de las emboca
  - Candidato: incluso la construcción del pozo de ataque, entibación de los costados para soportar la estructura, instalación de un tubo guía de acero de 500 mm de diámetro para guiar el proceso, el suministro y mo
  - Duda: Dudoso si 'entibación para soportar la estructura' enuncia el propósito inherente o lo desvirtúa (la entibación sostiene los costados, no 'la estructura').
- `expansion:33:5` — $M / %B=="h": incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro, el suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido.
  - Original: incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro, el suministro y montaje de los hilos guía y el sellado de las emboca
  - Candidato: incluso la construcción del pozo de ataque, entibación de los costados para soportar la estructura, instalación de un tubo guía de acero de 500 mm de diámetro para guiar el proceso, el suministro y mo
  - Duda: Mismo caso dudoso: 'entibación para soportar la estructura' es vago o desacertado como propósito de la entibación.
- `expansion:33:9` — $M / %B=="h": incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro, el suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido.
  - Original: incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro, el suministro y montaje de los hilos guía y el sellado de las emboca
  - Candidato: incluso la construcción del pozo de ataque, entibación de los costados para soportar la estructura, instalación de un tubo guía de acero de 500 mm de diámetro para facilitar el posicionamiento, el sum
  - Duda: Mismo caso dudoso de 'entibación para soportar la estructura'; el resto de cláusulas son propósitos inherentes válidos.
- `new_param:7:4` — NEW_PARAM on OEB090$
  - Original: 
  - Candidato: GRADO DE GALVANIZACIÓN
  - Duda: Eje plausible pero G120/G240 no son designaciones estándar y su aplicabilidad a tubo requiere experto.
- `new_param:21:3` — NEW_PARAM on OEB250$
  - Original: 
  - Candidato: NIVEL DE PROTECCIÓN
  - Duda: Los grados IP son propios de envolventes y accesorios mas que de la canalización en si; hace falta criterio experto para decidir si es plausible como eje.
- `paraphrase:3:7` — $G / %C=e: Cualquier frana horaria
  - Original: Cualquier frana horaria
  - Candidato: Horario completo sin excepciones
  - Duda: 'Sin excepciones' es ambiguo frente al hermano 'excepcional'; requiere criterio experto.
- `paraphrase:32:1` — $I / %B=="g": en zona de balasto
  - Original: en zona de balasto
  - Candidato: en sección de balasto
  - Duda: «sección de balasto» puede leerse como perfil transversal, no como zona; requiere criterio experto ferroviario.
- `paraphrase:43:3` — $K / %B=="a": normal
  - Original: normal
  - Candidato: en tierra
  - Duda: 'en tierra' podría glosar 'cualquier terreno excepto roca', pero no es obvio que equivalga a 'normal'; requiere criterio experto.
- `template_paraphrase:45:9` — TEXTO template (OEB100$)
  - Original: Suministro y ejecución de canalización en túnel para acceso a interfonía desde canaleta de hormigón utilizando tubo de acero hasta el repartidor Trabajo: $A Banda de mantenimiento: $B Condiciones de e
  - Candidato: Se suministrará y ejecutará la conducción enterrada en túnel para el acceso a interfonía, mediante la utilización de conductos de acero desde canaleta de hormigón hasta el repartidor. Trabajo: $A Band
  - Duda: Único reparo: 'enterrada' añadido a la conducción en túnel — ¿hecho añadido o explicitación válida? Resto impecable.
- `template_paraphrase:45:13` — TEXTO template (OEB100$)
  - Original: Suministro y ejecución de canalización en túnel para acceso a interfonía desde canaleta de hormigón utilizando tubo de acero hasta el repartidor Trabajo: $A Banda de mantenimiento: $B Condiciones de e
  - Candidato: Instalación y suministro de conducción enterrada en túnel para la conexión de interfonía, utilizando conductos de acero desde la canaleta de hormigón hasta el repartidor. Trabajo: $A, banda de manteni
  - Duda: Mismo caso que 45:9: solo el añadido 'enterrada' separa esta paráfrasis limpia de la A; requiere criterio de ingeniero.

## Targets sin ningún aprobado (79)

Decisión pendiente: adjudicar a mano, regenerar con prompt corregido, o aceptar el hueco.

- (6 cand.) `compression` — $L / %C=c: Cualquier condición de ejecución
- (9 cand.) `compression` — $G / %C=f: Cualquier franja horaria excepcional
- (5 cand.) `compression` — $I / %B=="h": en cruce bajo vías ejecutado con topo
- (4 cand.) `compression` — $M / %B=="h": incluso la construcción del pozo de ataque, entibación de los costados, instalación de un tubo guía de acero de 500 mm de diámetro, el suministro y montaje de los hilos guía y el sellado de las embocaduras con poliuretano expandido.
- (8 cand.) `compression` — $P / %B=="f": la preparación y la nivelación de la solera, el suministro y montaje del encofrado, elementos de fijación, desencofrado,
- (6 cand.) `compression` — $P / %B=="f": la preparación y nivelación de la solera, suministro y montaje del encofrado, elementos de fijación, desencofrado,
- (3 cand.) `compression` — $W / %A=a: material de la traza
- (1 cand.) `compression` — $R / %B=c: zona de balasto, ejecutada a mano incluso descerne y entibación de costados y posterior reposición del balasto retirado
- (10 cand.) `expansion` — $X / %A=a: 20 cm
- (10 cand.) `expansion` — $X / %A=c: 40 cm
- (10 cand.) `expansion` — $G / %C=c: Diurno Excepcional
- (10 cand.) `expansion` — $L / %C=c: No aplica
- (10 cand.) `expansion` — $L / %B=d: Nocturno excepcional
- (10 cand.) `expansion` — $L / %C=b: Volumen escaso
- (10 cand.) `expansion` — $L / %C=a: Volumen relevante
- (10 cand.) `expansion` — $N / %F=b: Voumen escaso
- (10 cand.) `expansion` — $K / %B=="f": adosada
- (10 cand.) `expansion` — $K / %B=="h": con topo
- (10 cand.) `expansion` — $I / %B=="e": en andén
- (10 cand.) `expansion` — $K / %B=="g": en balasto
- (10 cand.) `expansion` — $I / %B=="h": en cruce bajo vías ejecutado con topo
- (10 cand.) `expansion` — $I / %B=="d": en cruce de carretera
- (10 cand.) `expansion` — $I / %B=="a": en cualquier clase de terreno, excepto roca
- (10 cand.) `expansion` — $N / %B=="c": la demolición de roca dura,
- (10 cand.) `expansion` — $N / %B=="d": la demolición y la reposición del firme y del pavimento,
- (10 cand.) `expansion` — $N / %B=="e": la demolición y la reposición del pavimento y la solera,
- (10 cand.) `expansion` — $N / %B=="d": la demolición y reposición del firme y del pavimento,
- (10 cand.) `expansion` — $N / %B=="e": la demolición y reposición del pavimento y la solera,
- (10 cand.) `expansion` — $K / %B=="c": rocoso
- (10 cand.) `new_param` — NEW_PARAM on OEB090$
- (10 cand.) `new_param` — NEW_PARAM on OEB200$
- (10 cand.) `new_param` — NEW_PARAM on OEB240$
- (1 cand.) `omission` — RESUMEN — omit $B (OEB050$)
- (1 cand.) `omission` — RESUMEN — omit $B (OEB010$)
- (3 cand.) `omission` — RESUMEN — omit $N (OEB160$)
- (3 cand.) `omission` — RESUMEN — omit $A (OEB190$)
- (1 cand.) `omission` — RESUMEN — omit $A (OEB200$)
- (3 cand.) `omission` — TEXTO — omit $B (OEB050$)
- (3 cand.) `omission` — TEXTO — omit $C (OEB020$)
- (1 cand.) `omission` — TEXTO — omit $A (OEB030$)
- (3 cand.) `omission` — TEXTO — omit $I (OEB030$)
- (3 cand.) `omission` — TEXTO — omit $A (OEB040$)
- (3 cand.) `omission` — TEXTO — omit $A (OEB230$)
- (3 cand.) `omission` — TEXTO — omit $A (OEB280$)
- (1 cand.) `omission` — TEXTO — omit $A (OEB300$)
- (3 cand.) `omission` — TEXTO — omit $A (OEB160$)
- (3 cand.) `omission` — TEXTO — omit $A (OEB120$)
- (3 cand.) `omission` — TEXTO — omit $X (OEB190$)
- (7 cand.) `paraphrase` — $L / %C=c: Cualquier condición de ejecución
- (10 cand.) `paraphrase` — $K / %B=="f": adosada
- (10 cand.) `paraphrase` — $I / %B=="f": adosada o superficial
- (10 cand.) `paraphrase` — $K / %B=="h": con topo
- (9 cand.) `paraphrase` — $I / %B=="h": en cruce bajo vías ejecutado con topo
- (10 cand.) `paraphrase` — $W / %A=b: material de cantera
- (10 cand.) `paraphrase` — $W / %A=a: material de la traza
- (10 cand.) `paraphrase` — $K / %B=="a": normal
- (3 cand.) `reorder` — RESUMEN template (OEB080$)
- (3 cand.) `reorder` — RESUMEN template (OEB050$)
- (5 cand.) `synonym_label` — BANDA DE MANTENIMIENTO / No necesita intervalo
- (2 cand.) `synonym_label` — CONDICIONES DE EJECUCIÓN / Cualquier condición de ejecución
- (6 cand.) `synonym_label` — MATERIAL / de la traza
- (4 cand.) `synonym_label` — TIPO DE TERRENO / Andén
- (2 cand.) `synonym_label` — TIPO DE TERRENO / Bajo vías
- (2 cand.) `synonym_label` — TIPO DE TERRENO / Balasto
- (1 cand.) `synonym_label` — TIPO DE TERRENO / Con topo
- (3 cand.) `synonym_label` — TIPO DE TERRENO / Rocoso
- (7 cand.) `template_paraphrase` — TEXTO template (OEB010$)
- (11 cand.) `template_paraphrase` — TEXTO template (OEB050$)
- (6 cand.) `template_paraphrase` — TEXTO template (OEB250$)
- (3 cand.) `template_paraphrase` — TEXTO template (OEB020$)
- (15 cand.) `template_paraphrase` — TEXTO template (OEB040$)
- (6 cand.) `template_paraphrase` — TEXTO template (OEB230$)
- (7 cand.) `template_paraphrase` — TEXTO template (OEB280$)
- (12 cand.) `template_paraphrase` — TEXTO template (OEB290$)
- (7 cand.) `template_paraphrase` — TEXTO template (OEB300$)
- (16 cand.) `template_paraphrase` — TEXTO template (OEB130$)
- (12 cand.) `template_paraphrase` — TEXTO template (OEB070$)
- (6 cand.) `template_paraphrase` — TEXTO template (OEB190$)
- (3 cand.) `unit_conversion` — PROFUNDIDAD / hasta 0,80 m

## Decisiones de línea fina aplicadas (revisables)

1. `sobre una trinchera` → `en una trinchera` (OEB180, 7 candidatos): rechazados —
   la preposición codifica el método de suspensión. Si la lees como incidental, se recuperan 7 A.
2. Comillas envolventes literales (3 candidatos de OEB150/160, por lo demás perfectos):
   rechazados por residuo de render; si el pipeline las despoja, se recuperan.
3. `de 160 mm de diámetro $I` comprimido a `de 160 mm` en omission (8 candidatos): aprobados
   (reparación flexible; el diámetro queda inequívoco en un tubo).
4. Adjetivos en expansion: atributo implícito (necesarios/posterior) = A; de manera
   (meticulosa/cuidadoso) = R.
5. Pérdida de `material seleccionado` en OEB190 (toda la familia): rechazados (pérdida de spec).

## Muestra de auditoría (30 ítems: confirma o corrige mi razón)

- **A** `paraphrase:45:1` — $R / %B=c: zona de balasto, ejecutada a mano incluso descerne y entibación de costados y posterior reposición del balasto retirado
  - Original: zona de balasto, ejecutada a mano incluso descerne y entibación de costados y posterior reposición del balasto retirado
  - Candidato: zona de balasto, realizada a mano con descerne y entibación de costados, y reposición del balasto retirado
  - Razón: Contenido íntegro; la posterioridad de la reposición queda implícita en el orden.
  - ¿De acuerdo? ___
- **A** `paraphrase:14:0` — $L / %B=d: Nocturno excepcional
  - Original: Nocturno excepcional
  - Candidato: Nocturno especial
  - Razón: Nocturno especial conserva significado y sigue distinguiéndose de Nocturno.
  - ¿De acuerdo? ___
- **A** `omission:116:2` — TEXTO — omit $I (OEB020$)
  - Original: Canalización hormigonada de $A tubos de PVC de 110 mm de diámetro $I, incluso $N el relleno y el compactado de la zanja, $P el suministro y el montaje de los tu
  - Candidato: Canalización hormigonada de $A tubos de PVC de 110 mm de diámetro, incluyendo $N el relleno y el compactado de la zanja, $P el suministro y el montaje de los tu
  - Razón: Omite $I conservando 'de diámetro'; 'incluyendo' es sinónimo admisible.
  - ¿De acuerdo? ___
- **A** `omission:39:1` — RESUMEN — omit $G (OEB020$)
  - Original: Canalización hormigonada de $A T, PVC 110 mm, $K. ($G(%C)/$H(%D)/$J(%F))
  - Candidato: Canalización hormigonada de $A T, PVC 110 mm, $K. ($H(%D) y $J(%F))
  - Razón: Omite $G; conector 'y' válido.
  - ¿De acuerdo? ___
- **A** `reorder:2:1` — RESUMEN template (OEB030$)
  - Original: Canalización hormigonada $A T, polietileno libre de halógenos de 110 mm, $K. ($G(%C)/$H(%D)/$J(%F))
  - Candidato: Canalización hormigonada $A T, polietileno libre de halógenos de 110 mm ($G(%C)/$H(%D)/$J(%F)), $K.
  - Razón: Bloque parentético desplazado antes de ', $K'; la coma mantiene $K ligado, gramática correcta.
  - ¿De acuerdo? ___
- **A** `omission:194:0` — TEXTO — omit $D (OEB070$)
  - Original: Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: $B Banda de mantenimiento: $C Condiciones de ejecu
  - Candidato: Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: $B Banda de mantenimiento: $C
  - Razón: Omisión limpia de 'Condiciones de ejecución: $D'.
  - ¿De acuerdo? ___
- **A** `unit_expansion:3:0` — BANDA DE MANTENIMIENTO / i< 3 horas
  - Original: i< 3 horas
  - Candidato: Intervalo menor a tres horas
  - Razón: Desarrollo fiel de i < 3 horas, mismo valor.
  - ¿De acuerdo? ___
- **A** `omission:188:2` — TEXTO — omit $A (OEB110$)
  - Original: Suministro y colocación de tubería de PVC de 110 mm de diámetro para drenaje de arqueta desde centro de arqueta a pie de talud incluyendo relleno y compactación
  - Candidato: Suministro y colocación de tubería de PVC de 110 mm de diámetro para drenaje de arqueta desde el centro de la arqueta hasta el pie de talud, incluyendo relleno 
  - Razón: Omisión limpia de $A; los artículos y 'hasta' son reescritura local que conserva el contenido.
  - ¿De acuerdo? ___
- **A** `reorder:0:1` — RESUMEN template (OEB250$)
  - Original: $A de canalización de $B tubos de acero galvanizado de 100mm de diámetro para instalaciones CMS en transiciones entre diferentes plataformas.($L(%C)/$M(%D)/$N(%
  - Candidato: $A de canalización de $B tubos de acero galvanizado de 100mm de diámetro para instalaciones CMS en transiciones entre diferentes plataformas. $N(%F)/$M(%D)/$L(%
  - Razón: Reordenación interna del bloque tras el punto; la pérdida de paréntesis es puntuación mínima, sigue legible.
  - ¿De acuerdo? ___
- **A** `compression:10:3` — $I / %B=="a": en cualquier clase de terreno, excepto roca
  - Original: en cualquier clase de terreno, excepto roca
  - Candidato: en todo terreno, excepto roca
  - Razón: Estrictamente más corta, fluida y sin pérdida de contenido.
  - ¿De acuerdo? ___
- **A** `omission:151:0` — TEXTO — omit $P (OEB280$)
  - Original: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 40 mm de diámetro $I, incluso $N el relleno y compactado de la zanja, $P el suministro
  - Candidato: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 40 mm de diámetro $I, incluso $N el relleno y compactado de la zanja, el suministro y 
  - Razón: Elimina solo $P; frase gramatical, resto intacto.
  - ¿De acuerdo? ___
- **A** `expansion:3:5` — $G / %C=e: Cualquier frana horaria
  - Original: Cualquier frana horaria
  - Candidato: Cualquier franja horaria, abarcando todas las divisiones del día
  - Razón: Explicitación fiel ('todas las divisiones del día').
  - ¿De acuerdo? ___
- **A** `synonym_label:10:4` — TERRENO / duro
  - Original: duro
  - Candidato: Terreno Resistente
  - Razón: 'Terreno Resistente' equivale a duro y es distinguible.
  - ¿De acuerdo? ___
- **A** `omission:29:0` — RESUMEN — omit $G (OEB290$)
  - Original: Canalización hormigonada $A T, polietileno libre de halógenos de 50 mm, $K. ($G(%C)/$H(%D)/$J(%F))
  - Candidato: Canalización hormigonada $A T, polietileno libre de halógenos de 50 mm, $K. ($H(%D)/$J(%F))
  - Razón: Omisión limpia de $G, separadores intactos.
  - ¿De acuerdo? ___
- **A** `omission:24:0` — RESUMEN — omit $G (OEB280$)
  - Original: Canalización hormigonada $A T, polietileno libre de halógenos de 40 mm, $K. ($G(%C)/$H(%D)/$J(%F))
  - Candidato: Canalización hormigonada $A T, polietileno libre de halógenos de 40 mm, $K. ($H(%D)/$J(%F))
  - Razón: Omisión limpia de $G en el paréntesis, separadores intactos.
  - ¿De acuerdo? ___
- **R** `template_paraphrase:34:6` — TEXTO template (OEB290$)
  - Original: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 50 mm de diámetro $I, incluso $N el relleno y compactado de la zanja, $P el suministro
  - Candidato: Conducción subterránea con $A tubos de polietileno sin halógenos de 50 mm mm de diámetro $I, contemplando $N el relleno y compactación de la excavación, $P el p
  - Razón: «50 mm mm» duplicado y «el provisión» sin concordancia; «subterránea» contradice adosada/superficial.
  - ¿De acuerdo? ___
- **R** `omission:116:1` — TEXTO — omit $I (OEB020$)
  - Original: Canalización hormigonada de $A tubos de PVC de 110 mm de diámetro $I, incluso $N el relleno y el compactado de la zanja, $P el suministro y el montaje de los tu
  - Candidato: Canalización hormigonada de $A tubos de PVC de 110 mm, incluso $N el relleno y el compactado de la zanja, $P el suministro y el montaje de los tubos y hormigón 
  - Razón: Además de $I borra 'de diámetro': pérdida de contenido extra.
  - ¿De acuerdo? ___
- **R** `expansion:39:5` — $P / %B=="f": la preparación y la nivelación de la solera, el suministro y montaje del encofrado, elementos de fijación, desencofrado,
  - Original: la preparación y la nivelación de la solera, el suministro y montaje del encofrado, elementos de fijación, desencofrado,
  - Candidato: la preparación y nivelación de la solera, el suministro y montaje del encofrado, elementos de fijación precisos, y el desencofrado final,
  - Razón: Adjetivo valorativo añadido ('elementos de fijación precisos').
  - ¿De acuerdo? ___
- **R** `new_param:18:6` — NEW_PARAM on OEB200$
  - Original: 
  - Candidato: TIPO DE CUBIERTA
  - Razón: Una zanja para cables rellena y compactada no lleva cubierta de madera, plastico o asfalto; 'concreto' fuera de registro.
  - ¿De acuerdo? ___
- **R** `template_paraphrase:19:7` — RESUMEN template (OEB100$)
  - Original: Suministro y ejecución de canalización en túnel acceso interfono ($L(%A)/$M(%B)/$N(%C))
  - Candidato: Provisión y montaje de infraestructura de conducción en túnel acceso interfono ($L(%A)/$M(%B)/$N(%C)) ($L(%A)/$M(%B)/$N(%C))
  - Razón: Paréntesis de parámetros duplicado al final.
  - ¿De acuerdo? ___
- **R** `template_paraphrase:26:2` — TEXTO template (OEB050$)
  - Original: Ejecución de canalización para línea subterránea de telecomunicaciones, en derivación a arquetas de telecomunicaciones y junto a cámaras de empalme, de cables e
  - Candidato: Instalación de un sistema subterráneo de conducción de cables y conductos embutidos en hormigón HE-20, con dimensiones totales de 450 mm de ancho por 1 m de alt
  - Razón: Pierde 'medios auxiliares' y la derivación/adyacencia se difumina en 'enlazando'; cierre 'de $C' clunky.
  - ¿De acuerdo? ___
- **R** `template_paraphrase:14:9` — RESUMEN template (OEB180$)
  - Original: Hincas con cable tensor de acero para el tendido de cables sobre una trinchera de tierra. ($L(%A)/$M(%B)/$N(%C))
  - Candidato: Se emplean hincas con cable tensor de acero para la instalación de cables en una trinchera de tierra. ($L(%A)/$M(%B)/$N(%C))
  - Razón: "instalación de cables en una trinchera" pierde el matiz "sobre" del método original.
  - ¿De acuerdo? ___
- **R** `template_paraphrase:7:17` — RESUMEN template (OEB300$)
  - Original: Canalización hormigonada $A T, polietileno libre de halógenos de 90 mm, $K. ($G(%C)/$H(%D)/$J(%F))
  - Candidato: Conducción enterrada de concreto $A T, con revestimiento de polietileno sin halógenos de 90 mm, y propiedades detalladas en $K. Referencia estándar: $G(%C)/$H(%
  - Razón: 'Conducción de concreto con revestimiento de polietileno' distorsiona materiales y 'propiedades detalladas en $K' rinde sinsentido.
  - ¿De acuerdo? ___
- **R** `expansion:7:6` — $G / %C=c: Diurno Excepcional
  - Original: Diurno Excepcional
  - Candidato: Diurno Excepcional, para operaciones urgentes en el horario laboral diurno.
  - Razón: Operaciones urgentes añade un hecho no implícito en Diurno Excepcional.
  - ¿De acuerdo? ___
- **R** `expansion:27:3` — $I / %B=="b": en cruce bajo vías
  - Original: en cruce bajo vías
  - Candidato: en cruce bajo vías, donde la canalización se coloca estratégicamente para evitar interferencias con el tráfico ferroviario
  - Razón: Añade 'estratégicamente' y finalidad de evitar interferencias, valoración.
  - ¿De acuerdo? ___
- **R** `template_paraphrase:45:17` — TEXTO template (OEB100$)
  - Original: Suministro y ejecución de canalización en túnel para acceso a interfonía desde canaleta de hormigón utilizando tubo de acero hasta el repartidor Trabajo: $A Ban
  - Candidato: Realización y montaje de tubería para sistemas de intercomunicación, en túnel a través de conducción de acero desde canalones de hormigón hasta el distribuidor.
  - Razón: 'Canalones' recategoriza la canaleta; pierde 'suministro' y 'acceso a'.
  - ¿De acuerdo? ___
- **R** `template_paraphrase:8:10` — RESUMEN template (OEB020$)
  - Original: Canalización hormigonada de $A T, PVC 110 mm, $K. ($G(%C)/$H(%D)/$J(%F))
  - Candidato: Se ejecuta la canalización mediante tubería hormigonada de $A T, con conductos de PVC 110 mm, $K. Se detalla: ($G(%C)/$H(%D)/$J(%F))
  - Razón: 'Canalización mediante tubería hormigonada con conductos' duplica el objeto (tubería vs conductos) en construcción forzada y confusa.
  - ¿De acuerdo? ___
- **R** `compression:19:1` — $P / %B=="f": la preparación y nivelación de la solera, suministro y montaje del encofrado, elementos de fijación, desencofrado,
  - Original: la preparación y nivelación de la solera, suministro y montaje del encofrado, elementos de fijación, desencofrado,
  - Candidato: nivelación de solera, montaje de encofrado, fijación, desencofrado,
  - Razón: Pierde 'preparación' y 'suministro' del encofrado.
  - ¿De acuerdo? ___
- **R** `paraphrase:31:2` — $I / %B=="c": en terreno rocoso
  - Original: en terreno rocoso
  - Candidato: en suelo compuesto de roca
  - Razón: «suelo compuesto de roca» es incoherente: eso ya no es suelo, es roca.
  - ¿De acuerdo? ___
- **R** `num_to_text:1:1` — Nº TUBOS / 12
  - Original: 12
  - Candidato: Número doce
  - Razón: 'Número doce' se lee como identificador ordinal, no como cantidad de tubos.
  - ¿De acuerdo? ___