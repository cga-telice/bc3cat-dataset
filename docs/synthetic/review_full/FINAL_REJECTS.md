# Rechazos finales (v2) — lista para el vistazo de César

Total: 202 rechazados de 2811 (aprobación 92.8%).
Todos por defecto duro: rotura estructural de render, borrado extra en omission,
o residuo de generación. Si alguno te parece recuperable, dime su número.

1. `expansion:1:0` [v2] — $X / %A=c: 40 cm
   - Texto: 40 centímetros de profundidad, adecuado para instalaciones estándar de cables a mano
   - Motivo: clase 1: la cola añadida rompe el marco «cama de arena de $X de espesor» — render «cables a mano de espesor» ilegible
2. `expansion:1:1` [v2] — $X / %A=c: 40 cm
   - Texto: 40 centímetros de profundidad, permitiendo una instalación segura y eficiente a mano
   - Motivo: clase 1: cola interpuesta antes de «de espesor» del marco — render «a mano de espesor» ilegible
3. `expansion:1:2` [v2] — $X / %A=c: 40 cm
   - Texto: 40 centímetros de profundidad, garantizando protección adecuada para cables instalados manualmente
   - Motivo: clase 1: cola interpuesta antes de «de espesor» del marco — render «manualmente de espesor» ilegible
4. `expansion:1:3` [v2] — $X / %A=c: 40 cm
   - Texto: 40 centímetros de profundidad, cumpliendo con estándares de seguridad para instalaciones manuales
   - Motivo: clase 1: cola interpuesta antes de «de espesor» del marco — render «instalaciones manuales de espesor» ilegible
5. `expansion:1:4` [v2] — $X / %A=c: 40 cm
   - Texto: 40 centímetros de profundidad, ideal para la colocación manual de cables en condiciones normales
   - Motivo: clase 1: cola interpuesta antes de «de espesor» del marco — render «condiciones normales de espesor» ilegible
6. `expansion:1:5` [v2] — $X / %A=c: 40 cm
   - Texto: 40 centímetros de profundidad, asegurando una instalación manual eficaz y segura
   - Motivo: clase 1: cola interpuesta antes de «de espesor» del marco — render «segura de espesor» ilegible
7. `expansion:1:6` [v2] — $X / %A=c: 40 cm
   - Texto: 40 centímetros de profundidad, proporcionando una base sólida para la instalación manual de cables
   - Motivo: clase 1: cola interpuesta antes de «de espesor» del marco — render «cables de espesor» ilegible
8. `expansion:1:7` [v2] — $X / %A=c: 40 cm
   - Texto: 40 centímetros de profundidad, facilitando una instalación manual precisa y confiable
   - Motivo: clase 1: cola interpuesta antes de «de espesor» del marco — render «confiable de espesor» ilegible
9. `expansion:1:8` [v2] — $X / %A=c: 40 cm
   - Texto: 40 centímetros de profundidad, diseñado para una instalación manual eficiente y segura
   - Motivo: clase 1: cola interpuesta antes de «de espesor» del marco — render «segura de espesor» ilegible
10. `expansion:1:9` [v2] — $X / %A=c: 40 cm
   - Texto: 40 centímetros de profundidad, adecuado para la instalación manual de cables en terrenos estándar
   - Motivo: clase 1: cola interpuesta antes de «de espesor» del marco — render «terrenos estándar de espesor» ilegible
11. `omission:101:0` [v2] — TEXTO — omit $B (OEB050$)
   - Texto: Ejecución de canalización para línea subterránea de telecomunicaciones, en derivación a arquetas de telecomunicaciones y junto a cámaras de empalme, de cables entubados y tubos embebidos en hormigón HE-20, de dimensiones totales 450 mm de ancho por 1
   - Motivo: rotura de render (clase 1): 'terreno $A de pavimento' deja complemento huérfano — renderiza 'terreno duro de pavimento'
12. `omission:101:1` [v2] — TEXTO — omit $B (OEB050$)
   - Texto: Ejecución de canalización para línea subterránea de telecomunicaciones, en derivación a arquetas de telecomunicaciones y junto a cámaras de empalme, de cables entubados y tubos embebidos en hormigón HE-20, de dimensiones totales 450 mm de ancho por 1
   - Motivo: rotura de render (clase 1): mismo huérfano 'terreno $A de pavimento' al sustituir valores
13. `omission:101:2` [v2] — TEXTO — omit $B (OEB050$)
   - Texto: Ejecución de canalización para línea subterránea de telecomunicaciones, en derivación a arquetas de telecomunicaciones y junto a cámaras de empalme, de cables entubados y tubos embebidos en hormigón HE-20, de dimensiones totales 450 mm de ancho por 1
   - Motivo: rotura de render (clase 1): mismo huérfano 'terreno $A de pavimento' al sustituir valores
14. `omission:105:1` [v2] — TEXTO — omit $C (OEB250$)
   - Texto: $A de canalización de $B tubos de acero galvanizado de 100mm de diámetro para instalaciones CMS en transiciones entre diferentes plataformas. $Q(%A) Mantenimiento: $D Condiciones de ejecución: $F
   - Motivo: borrado extra en omission (clase 2): recorta 'Banda de mantenimiento' a 'Mantenimiento', ajeno a la omisión de $C
15. `omission:105:2` [v2] — TEXTO — omit $C (OEB250$)
   - Texto: $A de canalización de $B tubos de acero galvanizado de 100mm de diámetro para instalaciones CMS en transiciones entre diferentes plataformas. $Q(%A) Banda de mantenimiento: $D Condiciones: $F
   - Motivo: borrado extra en omission (clase 2): recorta 'Condiciones de ejecución' a 'Condiciones', ajeno a la omisión de $C
16. `omission:113:0` [v2] — TEXTO — omit $C (OEB020$)
   - Texto: Canalización hormigonada de $A tubos de PVC de 110 mm de diámetro $I, incluso $N el relleno y el compactado de la zanja, $P el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retir
   - Motivo: rotura de render (clase 1): etiqueta 'Trabajo:' huérfana sin valor — 'Trabajo: Banda de mantenimiento: $D' es marco roto
17. `omission:116:1` [cesar] — TEXTO — omit $I (OEB020$)
   - Texto: Canalización hormigonada de $A tubos de PVC de 110 mm, incluso $N el relleno y el compactado de la zanja, $P el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los prod
   - Motivo: borrado extra en omission (clase 2): elimina 'de diámetro' además de $I [R ratificado por César]
18. `omission:120:0` [v2] — TEXTO — omit $A (OEB030$)
   - Texto: Tubos de polietileno libre de halógenos de 110 mm de diámetro $I, incluso $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los
   - Motivo: Borra 'Canalización hormigonada de' además de $A: pérdida de contenido extra (clase 2)
19. `omission:124:0` [v2] — TEXTO — omit $I (OEB030$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 110 mm, incluso $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la
   - Motivo: Borra 'de diámetro' además de $I: pérdida de contenido extra (clase 2)
20. `omission:124:1` [v2] — TEXTO — omit $I (OEB030$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 110 mm, incluyendo $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y
   - Motivo: Borra 'de diámetro' además de $I: pérdida de contenido extra (clase 2)
21. `omission:124:2` [v2] — TEXTO — omit $I (OEB030$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 110 mm, además de $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y 
   - Motivo: Borra 'de diámetro' además de $I (clase 2); el cambio incluso→además de sería admisible
22. `omission:126:0` [v2] — TEXTO — omit $N (OEB030$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 110 mm de diámetro $I, el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte 
   - Motivo: Borra 'incluso' además de $N sin reemplazo: pérdida de contenido extra (clase 2)
23. `omission:128:0` [v2] — TEXTO — omit $A (OEB040$)
   - Texto: Tubos de polietileno libre de halógenos de 160 mm de diámetro $I, incluso $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los
   - Motivo: Borra 'Canalización hormigonada de' además de $A (clase 2)
24. `omission:128:1` [v2] — TEXTO — omit $A (OEB040$)
   - Texto: Tubos de polietileno libre de halógenos de 160 mm de diámetro $I, incluyendo $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de 
   - Motivo: Borra 'Canalización hormigonada de' además de $A (clase 2)
25. `omission:128:2` [v2] — TEXTO — omit $A (OEB040$)
   - Texto: Tubos de polietileno libre de halógenos de 160 mm de diámetro $I, incluidos $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de l
   - Motivo: Borra 'Canalización hormigonada de' además de $A (clase 2)
26. `omission:132:2` [v2] — TEXTO — omit $I (OEB040$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 160 mm, además de $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y 
   - Motivo: Borra 'de diámetro' además de $I (clase 2)
27. `omission:134:0` [v2] — TEXTO — omit $N (OEB040$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 160 mm de diámetro $I, el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte 
   - Motivo: Borra 'incluso' además de $N sin reemplazo (clase 2)
28. `omission:136:0` [v2] — TEXTO — omit $A (OEB230$)
   - Texto: Tubos de polietileno libre de halógenos de 200 mm de diámetro $I, incluso $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los
   - Motivo: Borra 'Canalización hormigonada de' además de $A (clase 2)
29. `omission:136:1` [v2] — TEXTO — omit $A (OEB230$)
   - Texto: Tubos de polietileno libre de halógenos de 200 mm de diámetro $I, incluyendo $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de 
   - Motivo: Borra 'Canalización hormigonada de' además de $A (clase 2)
30. `omission:136:2` [v2] — TEXTO — omit $A (OEB230$)
   - Texto: Tubos de polietileno libre de halógenos de 200 mm de diámetro $I, incluyendo $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de 
   - Motivo: Borra 'Canalización hormigonada de' y trunca 'Banda de mantenimiento' (clase 2)
31. `omission:13:0` [v2] — RESUMEN — omit $A (OEB040$)
   - Texto: Canalización hormigonada T, polietileno libre de halógenos de 160 mm, $K. ($G(%C)/$H(%D)/$J(%F))
   - Motivo: Deja 'hormigonada T,' con la unidad T huérfana sin numeral: marco mutilado al renderizar (clase 1)
32. `omission:13:2` [v2] — RESUMEN — omit $A (OEB040$)
   - Texto: Canalización hormigonada T, polietileno libre de halógenos de 160 mm, $K. ($G(%C), $H(%D), $J(%F))
   - Motivo: Deja la unidad T huérfana sin numeral: marco mutilado al renderizar (clase 1); el cambio de separadores del bloque sería admisible
33. `omission:140:2` [v2] — TEXTO — omit $I (OEB230$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 200 mm, además de $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y 
   - Motivo: Borra 'de diámetro' además de $I (clase 2)
34. `omission:144:0` [v2] — TEXTO — omit $A (OEB280$)
   - Texto: Tubos de polietileno libre de halógenos de 40 mm de diámetro $I, incluso $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los 
   - Motivo: Borra 'Canalización hormigonada de' además de $A (clase 2)
35. `omission:144:1` [v2] — TEXTO — omit $A (OEB280$)
   - Texto: Tubos de polietileno libre de halógenos de 40 mm de diámetro $I, incluyendo $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de l
   - Motivo: Borra 'Canalización hormigonada de' además de $A (clase 2)
36. `omission:144:2` [v2] — TEXTO — omit $A (OEB280$)
   - Texto: Tubos de polietileno libre de halógenos de 40 mm de diámetro $I, incluyendo $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de l
   - Motivo: Borra 'Canalización hormigonada de' y trunca 'Banda de mantenimiento' (clase 2)
37. `omission:147:2` [v2] — TEXTO — omit $F (OEB280$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 40 mm de diámetro $I, incluyendo $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, e
   - Motivo: Trunca 'Banda de mantenimiento' a 'Mantenimiento': borrado ajeno a la omisión de $F (clase 2)
38. `omission:148:2` [v2] — TEXTO — omit $I (OEB280$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 40 mm, además de $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y l
   - Motivo: Borra 'de diámetro' además de $I (clase 2)
39. `omission:150:0` [v2] — TEXTO — omit $N (OEB280$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 40 mm de diámetro $I, el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y
   - Motivo: Borra 'incluso' además de $N sin reemplazo (clase 2)
40. `omission:152:0` [v2] — TEXTO — omit $A (OEB290$)
   - Texto: Tubos de polietileno libre de halógenos de 50 mm de diámetro $I, incluso $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los 
   - Motivo: Borra 'Canalización hormigonada de' además de $A (clase 2)
41. `omission:156:2` [v2] — TEXTO — omit $I (OEB290$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 50 mm, además de $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y l
   - Motivo: Borra 'de diámetro' además de $I (clase 2)
42. `omission:160:0` [v2] — TEXTO — omit $A (OEB300$)
   - Texto: Tubos de polietileno libre de halógenos de 90 mm de diámetro $I, incluso $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los 
   - Motivo: Borra 'Canalización hormigonada de' además de $A (clase 2)
43. `omission:164:1` [v2] — TEXTO — omit $I (OEB300$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 90 mm, incluso $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la 
   - Motivo: Borra 'de diámetro' además de $I (clase 2)
44. `omission:168:1` [v2] — TEXTO — omit $A (OEB170$)
   - Texto: Canalización metálica superficial con tubos de acero galvanizado de $B de diámetro, diseñada para taludes de excesiva inclinación o rocosos, sobre hastial de túnel o puente, incluye sellado de sus extremos, herramientas y medios auxiliares necesarios
   - Motivo: Borra 'de medida interior' además de $A (clase 2); el cambio en→diseñada para sería admisible
45. `omission:176:1` [v2] — TEXTO — omit $B (OEB130$)
   - Texto: Trabajos de entronque de canalización hormigonada de tubos de 110 mm con una cámara o arqueta existente, incluyendo demolición y reposición de paramentos de hormigón o ladrillo. Trabajo: $A Condiciones de ejecución: $C
   - Motivo: Borra 'Ejecución de los', 'de registro' y 'fábrica de' además de $B (clase 2)
46. `omission:176:2` [v2] — TEXTO — omit $B (OEB130$)
   - Texto: Ejecución de trabajos de entronque de canalización hormigonada de tubos de 110 mm con una cámara o arqueta existente, incluyendo demolición y reposición de paramentos de hormigón o ladrillo. Trabajo: $A Condiciones de ejecución: $C
   - Motivo: Borra 'de registro' y 'fábrica de' además de $B (clase 2)
47. `omission:177:1` [v2] — TEXTO — omit $C (OEB130$)
   - Texto: Trabajos de entronque de canalización hormigonada de tubos de 110 mm con una cámara o arqueta existente, incluyendo demolición y reposición de paramentos de hormigón o ladrillo. Trabajo: $A Banda de mantenimiento: $B
   - Motivo: Borra 'Ejecución de', 'de registro' y 'fábrica de' además de $C (clase 2)
48. `omission:177:2` [v2] — TEXTO — omit $C (OEB130$)
   - Texto: Ejecución de trabajos de entronque de canalización hormigonada de tubos de 110 mm con cámara o arqueta existente, incluyendo demolición y reposición de paramentos de hormigón o ladrillo. Trabajo: $A Banda de mantenimiento: $B
   - Motivo: Borra 'de registro' y 'fábrica de' además de $C (clase 2)
49. `omission:18:0` [v2] — RESUMEN — omit $A (OEB230$)
   - Texto: Canalización hormigonada T, polietileno libre de halógenos de 200 mm, $K. ($G(%C)/$H(%D)/$J(%F))
   - Motivo: Deja 'hormigonada T,' con la unidad T huérfana sin numeral: marco mutilado al renderizar (clase 1)
50. `omission:191:2` [v2] — TEXTO — omit $A (OEB070$)
   - Texto: Suministro y ejecución de canalización de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: $B Banda de mantenimiento: $C Condiciones de ejecución: $D
   - Motivo: Borra 'tubo(s) de' además de $A: desaparecen los tubos (clase 2)
51. `omission:198:0` [v2] — TEXTO — omit $A (OEB120$)
   - Texto: Suministro y ejecución de embocadura canalización en arqueta o cámara existente Trabajo: $B Banda de mantenimiento: $C Condiciones de ejecución: $D
   - Motivo: Borra 'tubos' además de $A: pérdida de contenido extra (clase 2)
52. `omission:198:1` [v2] — TEXTO — omit $A (OEB120$)
   - Texto: Suministro y ejecución de embocadura en arqueta o cámara existente Trabajo: $B Banda de mantenimiento: $C Condiciones de ejecución: $D
   - Motivo: Clase 2: borra 'canalización de $A tubos' entero — pierde 'canalización' y 'tubos', deleción más allá de la mención omitida ($A) y su reparación.
53. `omission:198:2` [v2] — TEXTO — omit $A (OEB120$)
   - Texto: Suministro y ejecución de embocadura canalización en arqueta o cámara existente Trabajo: $B Mantenimiento: $C Condiciones de ejecución: $D
   - Motivo: Clase 2: además de $A borra 'tubos' y recorta 'Banda de mantenimiento' a 'Mantenimiento' — texto perdido ajeno a la omisión.
54. `omission:1:1` [v2] — RESUMEN — omit $B (OEB250$)
   - Texto: $A de canalización de tubos de acero galvanizado de 100mm de diámetro para instalaciones CMS en transiciones entre plataformas.($L(%C)/$M(%D)/$N(%F))
   - Motivo: Clase 2: además de $B elimina 'diferentes' — pérdida de texto más allá de la mención omitida (patrón M14).
55. `omission:1:2` [v2] — RESUMEN — omit $B (OEB250$)
   - Texto: $A de canalización de tubos de acero galvanizado de 100mm de diámetro para instalaciones CMS en transiciones.($L(%C)/$M(%D)/$N(%F))
   - Motivo: Clase 2: elimina 'entre diferentes plataformas' entero además de $B — borrado de contenido extra.
56. `omission:202:0` [v2] — TEXTO — omit $A (OEB090$)
   - Texto: Suministro y montaje, incluida parte proporcional de herrajes de sujeción y de caja de registro, incluso mandrilado. Trabajo: $B Banda de mantenimiento: $C Condiciones de ejecución: $D
   - Motivo: Clase 2: borra 'de tubo de acero galvanizado de $A' entero — pierde el objeto del suministro, mucho más que la mención de $A.
57. `omission:202:2` [v2] — TEXTO — omit $A (OEB090$)
   - Texto: Suministro y montaje de tubo de acero galvanizado, incluida parte proporcional de herrajes de sujeción y de caja de registro, incluso mandrilado. Trabajo: $B Mantenimiento: $C Condiciones de ejecución: $D
   - Motivo: Clase 2: recorta 'Banda de mantenimiento' a 'Mantenimiento' — texto perdido lejos del punto de omisión de $A.
58. `omission:207:1` [v2] — TEXTO — omit $C (OEB190$)
   - Texto: Zanja para tendido de cables de $A de profundidad y 0,60 m de anchura máxima, $R(%B), y relleno compactado con material seleccionado procedente de la excavación, cama de arena de $X(%A) de espesor, rejilla de plastico identificadora, carga, descarga 
   - Motivo: Clase 2: además de omitir $C recorta 'Banda de mantenimiento' a 'Mantenimiento' — texto perdido ajeno a la omisión.
59. `omission:209:1` [v2] — TEXTO — omit $F (OEB190$)
   - Texto: Zanja para tendido de cables de $A de profundidad y 0,60 m de anchura máxima, $R(%B), relleno compactado con material seleccionado de la excavación, cama de arena de $X(%A) de espesor, rejilla de plástico identificadora, carga, descarga y transporte 
   - Motivo: Clase 2: además de omitir $F borra 'y', 'procedente' y 'el interior de' en sitios lejanos a la omisión — pérdida de texto extra.
60. `omission:209:2` [v2] — TEXTO — omit $F (OEB190$)
   - Texto: Zanja para tendido de cables de $A de profundidad y 0,60 m de anchura máxima, $R(%B), con relleno compactado de material seleccionado de la excavación, cama de arena de $X(%A) de espesor, rejilla de plástico identificadora, carga, descarga y transpor
   - Motivo: Clase 2: borra 'procedente' y 'el interior de' fuera del punto de omisión de $F — pérdida de texto extra.
61. `omission:23:0` [v2] — RESUMEN — omit $A (OEB280$)
   - Texto: Canalización hormigonada T, polietileno libre de halógenos de 40 mm, $K. ($G(%C)/$H(%D)/$J(%F))
   - Motivo: Clase 1: 'Canalización hormigonada T' deja la T huérfana sin numeral — marco sintáctico roto que renderiza ilegible.
62. `omission:28:0` [v2] — RESUMEN — omit $A (OEB290$)
   - Texto: Canalización hormigonada T, polietileno libre de halógenos de 50 mm, $K. ($G(%C)/$H(%D)/$J(%F))
   - Motivo: Clase 1: T huérfana sin numeral ('hormigonada T') — marco roto al renderizar.
63. `omission:33:0` [v2] — RESUMEN — omit $A (OEB300$)
   - Texto: Canalización hormigonada T, polietileno libre de halógenos de 90 mm, $K. ($G(%C)/$H(%D)/$J(%F))
   - Motivo: Clase 1: T huérfana sin numeral ('hormigonada T') — marco roto al renderizar.
64. `omission:33:2` [v2] — RESUMEN — omit $A (OEB300$)
   - Texto: Canalización hormigonada T, polietileno libre de halógenos de 90 mm, $K. ($G(%C), $H(%D), $J(%F))
   - Motivo: Clase 1: mantiene la T huérfana sin numeral — marco roto pese al cambio de separadores del bloque.
65. `omission:51:0` [v2] — RESUMEN — omit $B (OEB050$)
   - Texto: Ejecución de canalización de comunicaciones para línea subterranea doble circuito de 220 ó 400 kV en terreno $A de pavimento. (-/-/$L(%C))
   - Motivo: Clase 1: 'en terreno $A de pavimento' deja 'de pavimento' colgando sin su núcleo (p.ej. 'terreno duro de pavimento') — marco que renderiza ilegible.
66. `omission:52:2` [v2] — RESUMEN — omit $L (OEB050$)
   - Texto: Ejecución de canalización de comunicaciones para línea subterránea doble circuito de 220 ó 400 kV en terreno $A y $B, pavimento.
   - Motivo: Clase 1: 'en terreno $A y $B, pavimento.' deja 'pavimento' suelto sin construcción — marco sintáctico roto al renderizar.
67. `omission:54:0` [v2] — RESUMEN — omit $B (OEB010$)
   - Texto: Ejecución de canalización para línea subterranea doble circuito de 220 ó 400 kV en terreno $A de pavimento. (-/-/$L(%C))
   - Motivo: Clase 1: 'en terreno $A de pavimento' deja 'de pavimento' colgando — marco que renderiza ilegible.
68. `omission:65:0` [v2] — RESUMEN — omit $N (OEB160$)
   - Texto: Mandrilado de canalización existente. (%A/-/-)
   - Motivo: Clase 1: quita la envoltura $N y deja '%A' crudo — placeholder mutilado que no se sustituye al renderizar.
69. `omission:65:1` [v2] — RESUMEN — omit $N (OEB160$)
   - Texto: Mandrilado de canalización existente. (Ejecución: %A/-/-)
   - Motivo: Clase 1: deja '%A' crudo (placeholder mutilado) pese a la etiqueta 'Ejecución:' añadida.
70. `omission:65:2` [v2] — RESUMEN — omit $N (OEB160$)
   - Texto: Mandrilado de canalización existente. (Proceso: %A/-/-)
   - Motivo: Clase 1: deja '%A' crudo (placeholder mutilado) pese a la etiqueta 'Proceso:' añadida.
71. `omission:67:0` [v2] — RESUMEN — omit $M (OEB240$)
   - Texto: Relleno localizado $W(%A), i/ compactado y material en obras de instalaciones ferroviarias. ($L(%B)/-/).
   - Motivo: Clase 1: '($L(%B)/-/).' queda malformado — barra colgante y hueco vacío, paréntesis/estructura del bloque de códigos rota.
72. `omission:67:2` [v2] — RESUMEN — omit $M (OEB240$)
   - Texto: Relleno localizado $W(%A), i/ compactado y material en obras de instalaciones ferroviarias. ($L(%B)/).
   - Motivo: Clase 1: '($L(%B)/).' con barra colgante — bloque de códigos malformado.
73. `omission:87:0` [v2] — RESUMEN — omit $A (OEB190$)
   - Texto: Zanja para cables de profundidad a mano, $B, en material $B. ($L(%C)/$M(%D)/$N(%F))
   - Motivo: Clase 1: 'Zanja para cables de profundidad a mano' deja 'de profundidad' sin valor — marco sintáctico roto, omisión no reparada.
74. `omission:87:1` [v2] — RESUMEN — omit $A (OEB190$)
   - Texto: Zanja para cables, de profundidad a mano, $B, en material $B. ($L(%C)/$M(%D)/$N(%F))
   - Motivo: Clase 1: las comas no reparan 'de profundidad' sin medida — marco sigue roto al renderizar.
75. `omission:87:2` [v2] — RESUMEN — omit $A (OEB190$)
   - Texto: Zanja para cables, de profundidad a mano, en material $B. ($L(%C)/$M(%D)/$N(%F))
   - Motivo: Clase 2: además de $A elimina la primera mención '$B,' (tipo de terreno) — borrado de un placeholder ajeno a la omisión.
76. `omission:8:0` [v2] — RESUMEN — omit $A (OEB030$)
   - Texto: Canalización hormigonada T, polietileno libre de halógenos de 110 mm, $K. ($G(%C)/$H(%D)/$J(%F))
   - Motivo: Clase 1: 'hormigonada T,' con la T huérfana sin numeral — marco roto que renderiza ilegible.
77. `omission:92:0` [v2] — RESUMEN — omit $A (OEB200$)
   - Texto: Zanja para cables de profundidad a máquina, $B, en material $B. ($L(%C)/$M(%D)/$N(%F))
   - Motivo: Clase 1 (rotura estructural): omitir $A deja 'de profundidad' colgando sin valor — 'Zanja para cables de profundidad a máquina' es un marco sintáctico roto al renderizar (extensión conservadora 'render ilegible'; para vistazo de César).
78. `omission:98:0` [v2] — TEXTO — omit $B (OEB010$)
   - Texto: Ejecución de canalización para línea subterránea de doble circuito de 220 o 400 kV de cables entubados y tubos embebidos en hormigón HM-20, de dimensiones totales 2 m de ancho por 1,60 m de alto, hormigonado hasta cota de 760 mm de profundidad, poste
   - Motivo: Clase 1 (rotura estructural): omitir $B deja 'En terreno $A de pavimento' — el complemento 'de pavimento' queda huérfano y el render es ilegible (p. ej. 'terreno blando de pavimento'); plantilla original confirmada en OBRA CIVIL.json ('En terreno $A, $B de pavimento.').
79. `omission:98:1` [v2] — TEXTO — omit $B (OEB010$)
   - Texto: Ejecución de canalización para línea subterránea de doble circuito de 220 o 400 kV de cables entubados y tubos embebidos en hormigón HM-20, de dimensiones totales 2 m de ancho por 1,60 m de alto, hormigonado hasta cota de 760 mm de profundidad, poste
   - Motivo: Clase 2 (borrado extra en omission): elimina también el placeholder $A además del $B omitido — pérdida de contenido más allá de la mención omitida (y deja 'En terreno de pavimento' roto).
80. `reorder:0:2` [v2] — RESUMEN template (OEB250$)
   - Texto: $N(%F)/$M(%D)/$L(%C) $A de canalización de $B tubos de acero galvanizado de 100mm de diámetro para instalaciones CMS en transiciones entre diferentes plataformas.
   - Motivo: Clase 1: parentesis del bloque de codigos eliminados; el bloque '$N(%F)/$M(%D)/$L(%C)' se funde con la frase al renderizar ('...Diurno Excepcional Suministro de canalizacion...').
81. `reorder:10:2` [v2] — RESUMEN template (OEB080$)
   - Texto: Canalización tubo corrugado de $A con alma de acero. ($L(%B)/-/(-))
   - Motivo: Clase 1: bloque de codigos malformado '($L(%B)/-/(-))' con parentesis anidados espurios.
82. `reorder:11:0` [v2] — RESUMEN template (OEB050$)
   - Texto: Ejecución de canalización de comunicaciones para línea subterranea doble circuito de 220 ó 400 kV en terreno $B, $A de pavimento. (-/-/$L(%C))
   - Motivo: Clase 1: intercambio $A/$B renderiza 'terreno sin reposicion, blando de pavimento' — postmodificador 'de pavimento' varado sobre adjetivo, marco ilegible (patron M15).
83. `reorder:23:0` [v2] — RESUMEN template (OEB190$)
   - Texto: Zanja para cables de $B, en material $B, de $A de profundidad a mano. ($L(%C)/$M(%D)/$N(%F))
   - Motivo: Clase 1: 'Zanja para cables de $B' renderiza 'cables de rocoso' (prep + adjetivo desnudo, eje TIPO DE TERRENO = normal/rocoso/balasto); marco ilegible.
84. `reorder:23:1` [v2] — RESUMEN template (OEB190$)
   - Texto: Zanja para cables de $B, en material $B, de $A de profundidad a mano. ($N(%F)/$M(%D)/$L(%C))
   - Motivo: Clase 1: mismo cuerpo que 23:0 ('cables de rocoso'); el reorden del bloque no repara el marco roto.
85. `reorder:24:0` [v2] — RESUMEN template (OEB200$)
   - Texto: Zanja para cables de $B, en material $B, de $A de profundidad a máquina. ($L(%C)/$M(%D)/$N(%F))
   - Motivo: Clase 1: 'cables de $B' renderiza 'cables de normal'/'cables de rocoso'; prep + adjetivo, marco ilegible.
86. `reorder:24:1` [v2] — RESUMEN template (OEB200$)
   - Texto: Zanja para cables de $B, en material $B, de $A de profundidad a máquina. ($N(%F)/$M(%D)/$L(%C))
   - Motivo: Clase 1: mismo cuerpo roto que 24:0; el reorden valido del parentesis no salva el marco.
87. `reorder:25:1` [v2] — TEXTO template (OEB010$)
   - Texto: Ejecución de canalización para línea subterránea de doble circuito de 220 o 400 kV de cables entubados y tubos embebidos en hormigón HM-20, de dimensiones totales 2 m de ancho por 1,60 m de alto, hormigonado hasta cota de 760 mm de profundidad, poste
   - Motivo: Clase 1: intercambia $A/$B — 'En terreno sin reposicion, blando de pavimento' varada el postmodificador; marco ilegible con valores reales (OEB010: A=terreno, B=pavimento).
88. `reorder:25:2` [v2] — TEXTO template (OEB010$)
   - Texto: Ejecución de canalización para línea subterránea de doble circuito de 220 o 400 kV de cables entubados y tubos embebidos en hormigón HM-20, de dimensiones totales 2 m de ancho por 1,60 m de alto, hormigonado hasta cota de 760 mm de profundidad, poste
   - Motivo: Clase 1: mismo intercambio $A/$B; 'blando de pavimento' ilegible al renderizar.
89. `reorder:26:1` [v2] — TEXTO template (OEB050$)
   - Texto: Ejecución de canalización para línea subterránea de telecomunicaciones, en derivación a arquetas de telecomunicaciones y junto a cámaras de empalme, de cables entubados y tubos embebidos en hormigón HE-20, de dimensiones totales 450 mm de ancho por 1
   - Motivo: Clase 1: intercambio $A/$B en OEB050 ('En terreno sin reposicion, blando de pavimento'); postmodificador varado, marco ilegible.
90. `reorder:26:2` [v2] — TEXTO template (OEB050$)
   - Texto: Ejecución de canalización para línea subterránea de telecomunicaciones, en derivación a arquetas de telecomunicaciones y junto a cámaras de empalme, de cables entubados y tubos embebidos en hormigón HE-20, de dimensiones totales 450 mm de ancho por 1
   - Motivo: Clase 1: mismo intercambio $A/$B ademas del movimiento de oracion; marco ilegible al renderizar.
91. `reorder:30:1` [v2] — TEXTO template (OEB030$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 110 mm de diámetro $I, incluso $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, $N el relleno y compactado de la zanja, el transporte y la retirada de 
   - Motivo: Clase 1: 'la prueba de los conductos' desplazada tras $M — con %B=h, $M termina en punto ('...poliuretano expandido.') y renderiza 'expandido., la prueba de los conductos, Trabajo:'; marco roto.
92. `reorder:30:2` [v2] — TEXTO template (OEB030$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 110 mm de diámetro $I, incluso $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, $N el relleno y compactado de la zanja, el transporte y la retirada de 
   - Motivo: Clase 1: mismo desplazamiento tras $M con coma colgante ante campo; renderiza '.,' con %B=h; marco roto.
93. `reorder:31:1` [v2] — TEXTO template (OEB040$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 160 mm de diámetro $I, incluso $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, $N el relleno y compactado de la zanja, el transporte y la retirada de 
   - Motivo: Clase 1: desplazamiento tras $M (clausula con punto final) produce 'expandido., la prueba..., Trabajo:'; marco roto al renderizar.
94. `reorder:31:2` [v2] — TEXTO template (OEB040$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 160 mm de diámetro $I, incluso $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, $N el relleno y compactado de la zanja, el transporte y la retirada de 
   - Motivo: Clase 1: mismo desplazamiento tras $M con coma colgante; marco roto al renderizar.
95. `reorder:32:1` [v2] — TEXTO template (OEB230$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 200 mm de diámetro $I, incluso $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, $N el relleno y compactado de la zanja, el transporte y la retirada de 
   - Motivo: Clase 1: desplazamiento tras $M produce '.,' y coma colgante ante 'Trabajo:'; marco roto al renderizar.
96. `reorder:32:2` [v2] — TEXTO template (OEB230$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 200 mm de diámetro $I, incluso $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, $N el relleno y compactado de la zanja, el transporte y la retirada de 
   - Motivo: Clase 1: mismo desplazamiento tras $M con coma colgante; marco roto al renderizar.
97. `reorder:33:1` [v2] — TEXTO template (OEB280$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 40 mm de diámetro $I, incluso $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, $N el relleno y compactado de la zanja, el transporte y la retirada de l
   - Motivo: Clase 1: desplazamiento tras $M produce '.,' y coma colgante ante 'Trabajo:'; marco roto al renderizar.
98. `reorder:33:2` [v2] — TEXTO template (OEB280$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 40 mm de diámetro $I, incluso $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, $N el relleno y compactado de la zanja, el transporte y la retirada de l
   - Motivo: Clase 1: mismo desplazamiento tras $M con coma colgante; marco roto al renderizar.
99. `reorder:34:1` [v2] — TEXTO template (OEB290$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 50 mm de diámetro $I, incluso $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, $N el relleno y compactado de la zanja, el transporte y la retirada de l
   - Motivo: Clase 1: desplazamiento tras $M produce '.,' y coma colgante ante 'Trabajo:'; marco roto al renderizar.
100. `reorder:34:2` [v2] — TEXTO template (OEB290$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 50 mm de diámetro $I, incluso $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, $N el relleno y compactado de la zanja, el transporte y la retirada de l
   - Motivo: Clase 1: mismo desplazamiento tras $M con coma colgante; marco roto al renderizar.
101. `reorder:35:1` [v2] — TEXTO template (OEB300$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 90 mm de diámetro $I, incluso $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, $N el relleno y compactado de la zanja, el transporte y la retirada de l
   - Motivo: Clase 1: desplazamiento tras $M produce '.,' y coma colgante ante 'Trabajo:'; marco roto al renderizar.
102. `reorder:35:2` [v2] — TEXTO template (OEB300$)
   - Texto: Canalización hormigonada de $A tubos de polietileno libre de halógenos de 90 mm de diámetro $I, incluso $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin vibrar, $N el relleno y compactado de la zanja, el transporte y la retirada de l
   - Motivo: Clase 1: mismo desplazamiento tras $M con coma colgante; marco roto al renderizar.
103. `synonym_label:14:2` [v2] — TIPO DE TERRENO / Adosada
   - Texto: Contigua a
   - Motivo: Rotura estructural (clase 1): 'Contigua a' termina en preposición sin objeto; al renderizar la etiqueta el sintagma queda mutilado (preposición colgante), marco ilegible.
104. `template_paraphrase:0:0` [v2] — RESUMEN template (OEB250$)
   - Texto: Se suministran $A segmentos de canalización compuestos por $B conductos de acero galvanizado de 100mm de diámetro, destinados a instalaciones CMS en las transiciones entre diversas plataformas.($L(%C)/$M(%D)/$N(%F))
   - Motivo: Clase 1: 'Se suministran $A segmentos' con $A='Suministro y montaje' renderiza 'Se suministran Suministro y montaje segmentos' — marco ilegible con valores reales (patron M15).
105. `template_paraphrase:11:13` [v2] — RESUMEN template (OEB050$)
   - Texto: Implementación de conducción subterránea para la línea de doble circuito de 220 ó 400 kV en terreno $A, con un área total de $B de pavimento. (-/-/$L(%C))
   - Motivo: Clase 1: 'con un area total de sin reposicion de pavimento' — valor del eje en hueco de magnitud, asercion sin parse posible (patron M15): marco ilegible al renderizar.
106. `template_paraphrase:12:10` [v2] — RESUMEN template (OEB010$)
   - Texto: Instalación de conducción enterrada para línea subterranea doble circuito de 220 ó 400 kV en terreno $A. $B de pavimento es incluido. (-/-/$L(%C))
   - Motivo: Clase 1: '$B de pavimento es incluido' renderiza 'Sin reposicion de pavimento es incluido.' — sujeto imposible, marco sin parse con valores reales (patron M15).
107. `template_paraphrase:15:6` [v2] — RESUMEN template (OEB150$)
   - Texto: "Sanitización de conductos de tubería preexistentes. ($L(%A)/$M(%B)/$N(%C))"
   - Motivo: Residuo de generacion: comillas literales envolviendo toda la plantilla (defecto v2 clase 3).
108. `template_paraphrase:15:7` [v2] — RESUMEN template (OEB150$)
   - Texto: "Ejecución de desinfección en conductos de tubería instalados previamente. ($L(%A)/$M(%B)/$N(%C))"
   - Motivo: Residuo de generacion: comillas literales envolviendo toda la plantilla (defecto v2 clase 3).
109. `template_paraphrase:15:8` [v2] — RESUMEN template (OEB150$)
   - Texto: "Operación de desobstrucción en conductos de tubería ya colocados. ($L(%A)/$M(%B)/$N(%C))"
   - Motivo: Residuo de generacion: comillas literales envolviendo toda la plantilla (defecto v2 clase 3).
110. `template_paraphrase:16:0` [v2] — RESUMEN template (OEB160$)
   - Texto: "Se realiza el mandrilado de la canalización ya instalada. ($N(%A)/-/-)"
   - Motivo: Residuo de generacion: comillas literales envolviendo toda la plantilla (defecto v2 clase 3).
111. `template_paraphrase:16:1` [v2] — RESUMEN template (OEB160$)
   - Texto: "Operación de mandrilado aplicada a canalizaciones previamente instaladas. ($N(%A)/-/-)"
   - Motivo: Residuo de generacion: comillas literales envolviendo toda la plantilla (defecto v2 clase 3).
112. `template_paraphrase:16:12` [v2] — RESUMEN template (OEB160$)
   - Texto: Procedimiento de mandrilado para tuberías existentes, $N(%A)/-/-.
   - Motivo: Rotura estructural: bloque de codigos sin parentesis (', $N(%A)/-/-.') — parentesis del bloque rotos (defecto v2 clase 1).
113. `template_paraphrase:16:13` [v2] — RESUMEN template (OEB160$)
   - Texto: Procesamiento de conductos preexistentes mediante mandrilado, $N(%A)/-/-.
   - Motivo: Rotura estructural: bloque de codigos sin parentesis (', $N(%A)/-/-.') — parentesis del bloque rotos (defecto v2 clase 1).
114. `template_paraphrase:16:14` [v2] — RESUMEN template (OEB160$)
   - Texto: Aplicación de mandrilado en conducciones ya instaladas, $N(%A)/-/-.
   - Motivo: Rotura estructural: bloque de codigos sin parentesis (', $N(%A)/-/-.') — parentesis del bloque rotos (defecto v2 clase 1).
115. `template_paraphrase:16:2` [v2] — RESUMEN template (OEB160$)
   - Texto: "Se efectúa el mandrilado sobre la canalización ya existente. ($N(%A)/-/-)"
   - Motivo: Residuo de generacion: comillas literales envolviendo toda la plantilla (defecto v2 clase 3).
116. `template_paraphrase:17:3` [v2] — RESUMEN template (OEB240$)
   - Texto: Material en obras de instalaciones ferroviarias, $W(%A)/ relleno localizado i/ compactado. ($L(%B)/$M(%C)/-)
   - Motivo: Rotura estructural: '$W(%A)/ relleno localizado' — barra del bloque de codigos filtrada al cuerpo; renderiza 'material de la traza/ relleno localizado', marco sintactico ilegible (defecto v2 clase 1, extension render ilegible).
117. `template_paraphrase:19:4` [v2] — RESUMEN template (OEB100$)
   - Texto: $L(%A)/$M(%B)/$N(%C) suministro e instalación de conducciones enterradas en túnel de acceso interfono ($L(%A)/$M(%B)/$N(%C))
   - Motivo: Clase 1: bloque $L/$M/$N duplicado en literal (anteposicion sin parentesis + bloque original), render roto.
118. `template_paraphrase:19:5` [v2] — RESUMEN template (OEB100$)
   - Texto: Instalación y suministro de canalización en túnel para interfonía de acceso ($L(%A)/$M(%B)/$N(%C)) $L(%A)/$M(%B)/$N(%C)
   - Motivo: Clase 1: bloque $L/$M/$N duplicado al final fuera del parentesis; render defectuoso.
119. `template_paraphrase:19:6` [v2] — RESUMEN template (OEB100$)
   - Texto: Aprovisionamiento y colocación de conductos en túnel acceso interfono ($L(%A)/$M(%B)/$N(%C)) ($L(%A)/$M(%B)/$N(%C))
   - Motivo: Clase 1: bloque parametrico parentetico duplicado; el render repite el bloque dos veces.
120. `template_paraphrase:19:7` [cesar] — RESUMEN template (OEB100$)
   - Texto: Provisión y montaje de infraestructura de conducción en túnel acceso interfono ($L(%A)/$M(%B)/$N(%C)) ($L(%A)/$M(%B)/$N(%C))
   - Motivo: Clase 1: parentesis de parametros duplicado al final. [R ratificado por César]
121. `template_paraphrase:19:8` [v2] — RESUMEN template (OEB100$)
   - Texto: Suministro y montaje de conductos en túnel acceso interfono ($L(%A)/$M(%B)/$N(%C)) ($L(%A)/$M(%B)/$N(%C))
   - Motivo: Clase 1: parentesis de parametros duplicado al final.
122. `template_paraphrase:20:17` [v2] — RESUMEN template (OEB120$)
   - Texto: Suministro y ejecución de conector para el ensamblaje de conducciones de $A en arqueta o cámara existente ($L(%B)/$M(%C)/$N(%D))
   - Motivo: Clase 1: 'conducciones de $A' renderiza 'conducciones de 4' / 'de 1 o 2' — sustantivo del conteo mutilado, marco ilegible con valores reales.
123. `template_paraphrase:20:3` [v2] — RESUMEN template (OEB120$)
   - Texto: Instalación y provisión de boca de entrada para conductos de $A en arquetas o cámaras ya existentes, especificadas como $L(%B)/$M(%C)/$N(%D)
   - Motivo: Clase 1: 'conductos de $A' renderiza 'conductos de 4' / 'de 1 o 2' — numero tras 'de' sin sustantivo, marco agramatical al instanciar.
124. `template_paraphrase:20:4` [v2] — RESUMEN template (OEB120$)
   - Texto: Ejecución y suministro de entrada de conductos de $A en arquetas o cámaras existentes, detalladas como $L(%B)/$M(%C)/$N(%D)
   - Motivo: Clase 1: 'conductos de $A' renderiza 'conductos de 4' — marco mutilado, ilegible con valores reales.
125. `template_paraphrase:20:5` [v2] — RESUMEN template (OEB120$)
   - Texto: Provisión y colocación de boca de conductos de $A en arquetas o cámaras existentes, con especificaciones $L(%B)/$M(%C)/$N(%D)
   - Motivo: Clase 1: 'boca de conductos de $A' renderiza 'conductos de 4' — marco agramatical al instanciar.
126. `template_paraphrase:20:7` [v2] — RESUMEN template (OEB120$)
   - Texto: Ejecución de entrada de conductos de $A en arqueta o cámara preexistente ($L(%B)/$M(%C)/$N(%D))
   - Motivo: Clase 1: 'conductos de $A' renderiza 'conductos de 4' — marco mutilado con valores reales.
127. `template_paraphrase:21:6` [v2] — RESUMEN template (OEB110$)
   - Texto: $L(%A)/$M(%B)/$N(%C) canalización de PVC con diámetro nominal 110 mm para evacuación en arquetas
   - Motivo: Clase 1: bloque $L/$M/$N anteposicionado sin parentesis (y sin bloque parentetico), renderiza como texto corrido ilegible con valores reales.
128. `template_paraphrase:23:6` [v2] — RESUMEN template (OEB190$)
   - Texto: Excavación de profundidad $B realizada manualmente para cables de $A, fabricada con $B. ($L(%C)/$M(%D)/$N(%F))
   - Motivo: Clase 1: papeles cruzados — 'profundidad $B' rinde 'profundidad rocoso' y 'cables de $A' rinde 'cables de hasta 0,80 m'; marco ilegible con valores reales (tipo M15).
129. `template_paraphrase:23:7` [v2] — RESUMEN template (OEB190$)
   - Texto: Taladros para conducción de cables de $A, excavados manualmente hasta una profundidad de $B, utilizando $B como material. ($L(%C)/$M(%D)/$N(%F))
   - Motivo: Clase 1: 'hasta una profundidad de $B' rinde 'profundidad de rocoso/normal' — terreno en el hueco de profundidad; sinsentido renderizado.
130. `template_paraphrase:23:8` [v2] — RESUMEN template (OEB190$)
   - Texto: Bóveda para cables realizada manualmente con profundidad de $B, diseñada para $A y construida con $B. ($L(%C)/$M(%D)/$N(%F))
   - Motivo: Clase 1: papeles cruzados — 'profundidad de $B' ('profundidad de rocoso') y 'diseñada para $A' ('diseñada para hasta 0,80 m'); ilegible al renderizar.
131. `template_paraphrase:24:10` [v2] — RESUMEN template (OEB200$)
   - Texto: Se diseña una zanja de $A para la instalación de cables relacionada con la $B, hecha con el material $B. Se detallan las medidas ($L(%C)), los materiales de construcción ($M(%D)) y los estándares de calidad ($N(%F)).
   - Motivo: Clase 1: 'instalación de cables relacionada con la $B' rinde 'relacionada con la rocoso' — artículo+adjetivo en marco relacional, sinsentido tipo M15.
132. `template_paraphrase:24:11` [v2] — RESUMEN template (OEB200$)
   - Texto: Se proporciona una zanja con profundidad de máquina de $A para la instalación de cables asociados a la $B, hecha en material $B. Se incluyen las dimensiones ($L(%C)), los materiales ($M(%D)) y los requisitos de calidad ($N(%F)).
   - Motivo: Clase 1: 'cables asociados a la $B' rinde 'asociados a la rocoso/normal' — marco ilegible con los valores reales del eje.
133. `template_paraphrase:24:7` [v2] — RESUMEN template (OEB200$)
   - Texto: Con $B, se efectúa una zanja destinada a $A, de profundidad $B a máquina. ($L(%C)/$M(%D)/$N(%F))
   - Motivo: Clase 1: papeles cruzados — 'zanja destinada a $A' ('destinada a hasta 0,80 m') y 'de profundidad $B a máquina' ('profundidad rocoso'); ilegible al renderizar.
134. `template_paraphrase:24:8` [v2] — RESUMEN template (OEB200$)
   - Texto: Se dispone de una zanja para $A, cuya profundidad a máquina es $B, hecha en $B. ($L(%C)/$M(%D)/$N(%F))
   - Motivo: Clase 1: papeles cruzados — 'zanja para $A' ('para hasta 0,80 m') y 'cuya profundidad a máquina es $B' ('es rocoso'); sinsentido renderizado.
135. `template_paraphrase:24:9` [v2] — RESUMEN template (OEB200$)
   - Texto: Se realiza una zanja para alojar cables a una profundidad de máquina de $A, para la $B, fabricada con $B. Se especifican las dimensiones ($L(%C)), los materiales ($M(%D)) y las normas de calidad ($N(%F)).
   - Motivo: Clase 1: 'para la $B' rinde 'para la rocoso' — artículo+adjetivo sin sustantivo, marco ilegible con valores reales (tipo M15).
136. `template_paraphrase:27:1` [v2] — TEXTO template (OEB250$)
   - Texto: Se contempla un $A de conducciones con $B conductos de acero galvanizado de 100mm de diámetro destinados a instalaciones CMS en las áreas de transición entre distintas plataformas. $Q(%A) El trabajo a ejecutar: $C Asignada a la banda de mantenimiento
   - Motivo: Clase 1: 'Las $F determinarán las condiciones de ejecución' rinde 'Las Volumen relevante determinarán las condiciones de ejecución' — artículo mutilado y circularidad; ilegible con valores reales.
137. `template_paraphrase:27:2` [v2] — TEXTO template (OEB250$)
   - Texto: Se implementará un $A de conducción con $B conductos de acero galvanizado de 100mm de diámetro para sistemas CMS en las conexiones entre diversas plataformas. $Q(%A) Se llevará a cabo el trabajo: $C Banda de mantenimiento correspondiente: $D Las $F s
   - Motivo: Clase 1: 'Las $F serán las condiciones de ejecución' rinde 'Las Volumen relevante serán...' — marco agramatical ilegible con los valores del eje.
138. `template_paraphrase:27:4` [v2] — TEXTO template (OEB250$)
   - Texto: Sistema de canalización $A de $B conductos de acero galvanizado de 100mm de diámetro para sistemas CMS en las transiciones entre plataformas. $Q(%A) Operación: $C Franja de mantenimiento: $D Condiciones de implementación: $F
   - Motivo: Clase 1: 'Sistema de canalización $A' rinde 'Sistema de canalización Suministro' — valor de acción en hueco nominal, sinsentido renderizado.
139. `template_paraphrase:27:5` [v2] — TEXTO template (OEB250$)
   - Texto: Instalación de $A para $B conductos de acero galvanizado de 100mm de diámetro en transiciones de plataforma para sistemas CMS. $Q(%A) Labor: $C Zona de servicio: $D Condición de instalación: $F
   - Motivo: Clase 1: 'Instalación de $A' rinde 'Instalación de Suministro' — marco incompatible con los valores del eje ($A = Suministro / Suministro y montaje).
140. `template_paraphrase:2:1` [v2] — RESUMEN template (OEB030$)
   - Texto: La instalación de conductos de hormigón $A T, con polietileno sin halógenos de 110 mm, se realiza bajo la especificación $K. ($G(%C)/$H(%D)/$J(%F))
   - Motivo: Rotura de render (clase 1): 'bajo la especificación $K' convierte el calificador en nombre de especificación — renderiza 'bajo la especificación bajo vías' / 'rocoso' / 'con topo', ilegible con la mayoría de valores.
141. `template_paraphrase:2:11` [v2] — RESUMEN template (OEB030$)
   - Texto: Conducción de hormigón $A T, que incorpora polietileno libre de halógenos de diámetro nominal 110 mm. Incluye $K. ($G(%C)/$H(%D)/$J(%F))
   - Motivo: Rotura de render (clase 1): 'Incluye $K.' renderiza 'Incluye normal' / 'Incluye con topo' — $K no es partida incluible, marco ilegible con valores reales.
142. `template_paraphrase:2:2` [v2] — RESUMEN template (OEB030$)
   - Texto: Implementación de una conducción de hormigón $A T, realizada con tubos de polietileno sin compuestos halogenados de 110 mm, bajo el estándar $K. ($G(%C)/$H(%D)/$J(%F))
   - Motivo: Rotura de render (clase 1): 'bajo el estándar $K' renderiza 'bajo el estándar rocoso' / 'con topo' — marco de valor ilegible con los valores del eje.
143. `template_paraphrase:2:7` [v2] — RESUMEN template (OEB030$)
   - Texto: Conductos de hormigón $A T, fabricados en polietileno sin halógenos de 110 mm, caracterizados por $K. ($G(%C)/$H(%D)/$J(%F))
   - Motivo: Rotura de render (clase 1): 'caracterizados por $K' renderiza 'caracterizados por normal' / 'por con topo' / 'por bajo vías' — mismo patrón que el ejemplo ratificado 'La espesor es de bajo vías'.
144. `template_paraphrase:2:8` [v2] — RESUMEN template (OEB030$)
   - Texto: Instalación de canalización de hormigón $A T, compuesta por tubos de polietileno exento de halógenos de 110 mm, con $K. ($G(%C)/$H(%D)/$J(%F))
   - Motivo: Rotura de render (clase 1): 'con $K' renderiza 'con con topo' (duplicación literal) y 'con normal' — marco ilegible con valores reales.
145. `template_paraphrase:2:9` [v2] — RESUMEN template (OEB030$)
   - Texto: Conducción enterrada $A T, polietileno libre de halógenos de diámetro nominal 110 mm, incluyendo $K. ($G(%C)/$H(%D)/$J(%F))
   - Motivo: Rotura de render (clase 1): 'incluyendo $K' renderiza 'incluyendo normal' / 'incluyendo con topo' — $K tratado como partida, ilegible.
146. `template_paraphrase:30:0` [v2] — TEXTO template (OEB030$)
   - Texto: Conducción enterrada con $A conductos de polietileno sin halógenos con diámetro nominal 110 mm de $I, incluyendo $N el relleno y compactación de la zanja, $P el abastecimiento y montaje de los conductos junto con hormigón del tipo HE-20 sin vibrar, l
   - Motivo: Rotura de render (clase 1): '110 mm de $I' renderiza 'de en terreno rocoso' — apilamiento de preposiciones que hace ilegible el ítem.
147. `template_paraphrase:30:1` [v2] — TEXTO template (OEB030$)
   - Texto: Conducción enterrada con $A conductos de polietileno exento de halógenos de 110 mm de $I, que incluye $N el llenado y compactado de la zanja, $P la provisión y ensamblaje de los conductos y hormigón de clase HE-20 sin vibrar, la inspección de los con
   - Motivo: Rotura de render (clase 1): pierde 'diámetro' y deja '110 mm de $I' → '110 mm de en cruce bajo vías', ilegible.
148. `template_paraphrase:30:2` [v2] — TEXTO template (OEB030$)
   - Texto: Conducción enterrada compuesta por $A conductos de polietileno sin halógenos de diámetro 110 mm de $I, incluyendo $N el llenado y amasado de la zanja, $P el abastecimiento y colocación de los conductos y hormigón de tipo HE-20 sin vibración, la compr
   - Motivo: Rotura de render (clase 1): 'diámetro 110 mm de $I' renderiza 'de en terreno rocoso' — marco roto.
149. `template_paraphrase:30:3` [v2] — TEXTO template (OEB030$)
   - Texto: Conducción enterrada con $A conductos de polietileno libre de halógenos de diámetro nominal 110 mm de $I. Incluye $N el relleno y compactado de la zanja, $P el suministro y colocación de los conductos y hormigón tipo HE-20 sin vibrar, la verificación
   - Motivo: Rotura de render (clase 1): '110 mm de $I.' con $I locativo renderiza 'de en terreno rocoso', ilegible.
150. `template_paraphrase:30:5` [v2] — TEXTO template (OEB030$)
   - Texto: Instalación de canalización hormigonada con $A conductos de polietileno libre de halógenos, de diámetro nominal $I, marca 110 mm. $P Incluye la logística y montaje de los conductos y hormigón tipo HE-20 sin vibrar, $N la preparación de la zanja y com
   - Motivo: Rotura de render (clase 1): 'diámetro nominal $I, marca 110 mm' trata el locativo como valor ('diámetro nominal en terreno rocoso'); además '$P Incluye' deja el fragmento de $P colgando sin sintaxis.
151. `template_paraphrase:30:6` [v2] — TEXTO template (OEB030$)
   - Texto: Instalación de canalización enterrada con $A conductos de polietileno libre de halógenos 110 mm, diámetro nominal $I. $N Se incluyen los servicios de relleno y compactado de la zanja, $P la entrega y montaje de los conductos y hormigón tipo HE-20 sin
   - Motivo: Rotura de render (clase 1): 'diámetro nominal $I.' trata el locativo como valor; '$N Se incluyen' renderiza 'la demolición de roca dura, Se incluyen...' — arranque de frase roto.
152. `template_paraphrase:31:1` [v2] — TEXTO template (OEB040$)
   - Texto: Ejecución de una canalización enterrada con $A conductos de polietileno libre de halógenos de 160 mm y un diámetro $I. Se incluye $N el relleno y compactado de la zanja, $P el aporte y colocación de los conductos y hormigón tipo HE-20 sin vibración, 
   - Motivo: Rotura de render (clase 1): '160 mm y un diámetro $I' renderiza 'un diámetro en cruce de carretera' — $I locativo en hueco de valor.
153. `template_paraphrase:31:10` [v2] — TEXTO template (OEB040$)
   - Texto: Conducción enterrada compuesta por $A conductos de polietileno libre de halógenos 160 mm con un diámetro nominal de $I. El servicio incluye las tareas de relleno y compactación de la zanja $N, el suministro de tubos y hormigón tipo HE-20 $P, la prueb
   - Motivo: Rotura de render (clase 1): 'con un diámetro nominal de $I' renderiza 'de en terreno rocoso'; $N/$P pospuestos generan yuxtaposiciones rotas con fragmentos reales.
154. `template_paraphrase:31:11` [v2] — TEXTO template (OEB040$)
   - Texto: Conducción enterrada con $A conductos de polietileno libre de halógenos 160 mm de diámetro nominal $I. Este servicio abarca la prueba de conductos, el transporte y la retirada de los productos al lugar de empleo $M, así como el relleno y la compactac
   - Motivo: Rotura de render (clase 1): $N/$P pospuestos tras 'la zanja'/'sin vibrar' renderizan 'la compactación de la zanja el descerne y la entibación..., y el suministro' — run-on ilegible con los fragmentos no vacíos.
155. `template_paraphrase:31:12` [v2] — TEXTO template (OEB040$)
   - Texto: Instalación de $A conductos de polietileno sin halógenos de 160 mm con diámetro nominal de $I, incluyendo $N la preparación de la zanja, $P el suministro y colocación de los conductos y hormigón tipo HE-20 de compresión natural, así como la prueba de
   - Motivo: Rotura de render (clase 1): 'con diámetro nominal de $I' renderiza 'de en cruce bajo vías' — marco de valor con $I locativo.
156. `template_paraphrase:31:2` [v2] — TEXTO template (OEB040$)
   - Texto: La instalación consistirá en una conducción enterrada con $A conductos de polietileno libre de halógenos de 160 mm y diámetro $I. Se contempla $N el relleno y compactado de la zanja, $P el abastecimiento y ensamblaje de los conductos y hormigón tipo 
   - Motivo: Rotura de render (clase 1): '160 mm y diámetro $I' desacopla la medida y renderiza 'y diámetro en cruce de carretera' — ilegible.
157. `template_paraphrase:31:3` [v2] — TEXTO template (OEB040$)
   - Texto: Conducción enterrada en hormigón de $A conductos de polietileno sin halógenos de 160 mm y diámetro $I, incluido $N el relleno y compactado de la zanja. Se incluye también $P el suministro y montaje de los conductos y hormigón tipo HE-20 sin vibrar, l
   - Motivo: Rotura de render (clase 1): '160 mm y diámetro $I' renderiza 'y diámetro en terreno rocoso' — $I locativo en hueco de valor.
158. `template_paraphrase:31:4` [v2] — TEXTO template (OEB040$)
   - Texto: Conjunto para conducción enterrada en hormigón, compuesto de $A tubos de polietileno sin halógenos de 160 mm y diámetro $I, incluyendo $N el relleno y compactado de la zanja. Además, se contempla $P la provisión y colocación de los tubos y hormigón t
   - Motivo: Rotura de render (clase 1): '160 mm y diámetro $I' renderiza agramatical con $I locativo.
159. `template_paraphrase:31:5` [v2] — TEXTO template (OEB040$)
   - Texto: Instalación de conducción enterrada en hormigón con $A conductos de polietileno sin halógenos de 160 mm y diámetro $I. Se incluye $N el relleno y compactado de la zanja, además de $P la provisión y colocación de los conductos y hormigón tipo HE-20 si
   - Motivo: Rotura de render (clase 1): '160 mm y diámetro $I' con $I locativo renderiza sinsentido ilegible.
160. `template_paraphrase:31:6` [v2] — TEXTO template (OEB040$)
   - Texto: Conducción enterrada formada por $A conductos de polietileno sin halógenos de 160 mm mm con un diámetro de $I, incluyendo $N el relleno y compactación de la excavación, $P la entrega y montaje de los conductos y hormigón de calidad HE-20 no vibrado, 
   - Motivo: Rotura de render (clase 1): 'con un diámetro de $I' renderiza 'de en terreno rocoso' ('mm mm' por sí solo sería cosmético aprobado).
161. `template_paraphrase:31:8` [v2] — TEXTO template (OEB040$)
   - Texto: Instalación de conductos en hormigón conformada por $A tuberías de polietileno sin halógenos de 160 mm mm y de diámetro $I, incluido $N el llenado y compactación de la zanja, $P la provisión y emplazamiento de las tuberías y hormigón HE-20 no vibrado
   - Motivo: Rotura de render (clase 1): '160 mm mm y de diámetro $I' separa la medida y renderiza 'y de diámetro en terreno rocoso' — ilegible.
162. `template_paraphrase:31:9` [v2] — TEXTO template (OEB040$)
   - Texto: Conducción enterrada con $A conductos de polietileno libre de halógenos 160 mm de diámetro nominal $I, incluyendo la colocación de los tubos y hormigón tipo HE-20, la prueba de los conductos, el transporte y la retirada de los productos al lugar de e
   - Motivo: Rotura de render (clase 1): $N/$P pospuestos ('la compactación de la zanja $N y el suministro de tubos y hormigón $P') renderizan run-ons rotos con los fragmentos reales.
163. `template_paraphrase:32:2` [v2] — TEXTO template (OEB230$)
   - Texto: Realización de canalización hormigonada con $A conductos de polietileno libre de halógenos de 200 mm con diámetro $I, $N que incluye el relleno y compactado de la zanja, $P el suministro y montaje de los conductos con hormigón tipo HE-20 sin vibrar, 
   - Motivo: Rotura de render (clase 1): '200 mm con diámetro $I' renderiza 'con diámetro en terreno rocoso'; '$N que incluye' subordina el relleno al fragmento rendido.
164. `template_paraphrase:32:3` [v2] — TEXTO template (OEB230$)
   - Texto: Conducción enterrada de $A conductos de polietileno libre de halógenos de 200 mm mm y diámetro $I, incluyendo $N el relleno y compactación de la zanja, $P el abastecimiento y montaje de los conductos y hormigón tipo HE-20 sin vibración, las pruebas d
   - Motivo: Rotura de render (clase 1): '200 mm mm y diámetro $I' renderiza 'y diámetro en terreno rocoso' — $I locativo en hueco de valor (el 'mm mm' solo sería cosmético).
165. `template_paraphrase:32:4` [v2] — TEXTO template (OEB230$)
   - Texto: Implementación de conducción enterrada con $A tuberías de polietileno sin halógenos de 200 mm mm y diámetro $I, comprendiendo $N el relleno y compactación de la zanja, $P el suministro y colocación de las tuberías y hormigón tipo HE-20 sin vibración,
   - Motivo: Rotura de render (clase 1): 'y diámetro $I' queda agramatical al renderizar el locativo como valor de diámetro.
166. `template_paraphrase:32:5` [v2] — TEXTO template (OEB230$)
   - Texto: Instalación de conducción enterrada con $A tubos de polietileno libre de halógenos 200 mm y diámetro nominal $I. La instalación incluye también $N el relleno y compactado de la zanja, $P el suministro y montaje de los tubos y hormigón tipo HE-20 sin 
   - Motivo: Rotura de render (clase 1): '200 mm y diámetro nominal $I' renderiza 'y diámetro nominal en cruce de carretera' — ilegible; 'enterrada' por sí sola sería deriva aprobada.
167. `template_paraphrase:33:6` [v2] — TEXTO template (OEB280$)
   - Texto: Se realizará la instalación de $A conductos de polietileno libre de halógenos de 40 mm con un diámetro de $I, incluyendo la preparación de la zanja ($N), el suministro y montaje ($P) de los tubos y hormigón tipo HE-20 sin vibración, así como la prueb
   - Motivo: Rotura de render (clase 1): 'con un diámetro de $I' renderiza 'de en terreno rocoso'; además '($N)'/'($P)' renderizan fragmentos con coma final entre paréntesis — bloques rotos.
168. `template_paraphrase:34:1` [v2] — TEXTO template (OEB290$)
   - Texto: Se implementará la conducción de hormigón con $A conductos de polietileno sin halógenos de $I de diámetro 50 mm, abarcando $N el relleno y compactación de la zanja, $P la entrega y ensamblaje de los conductos y hormigón tipo HE-20 sin vibrar, la insp
   - Motivo: Rotura de render (clase 1): 'de $I de diámetro 50 mm' renderiza 'de en terreno rocoso de diámetro 50 mm' — apilamiento de preposiciones ilegible.
169. `template_paraphrase:34:10` [v2] — TEXTO template (OEB290$)
   - Texto: Conducción enterrada de $A conductos de polietileno libre de halógenos de 50 mm de diámetro nominal $I, $P incluida la instalación de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos
   - Motivo: Rotura de render (clase 1): $N pospuesto tras 'la zanja' renderiza 'compactado de la zanja el descerne y la entibación...,,' — yuxtaposición sin conector, ilegible con fragmentos reales.
170. `template_paraphrase:34:11` [v2] — TEXTO template (OEB290$)
   - Texto: Colocación de $A conductos en polietileno libre de halógenos de 50 mm con diámetro nominal $I, $P incluyendo la instalación de tubos y hormigón tipo HE-20 sin vibrar, la prueba de conductos, el transporte y la retirada de materiales al lugar de traba
   - Motivo: Rotura estructural de render (clase 1): $N pospuesto a 'la zanja' colisiona sin conector con sus valores reales ('...compactado de la zanja la demolición de roca dura,, trabajo:') — ilegible para B=b,c,d,e,g.
171. `template_paraphrase:35:0` [v2] — TEXTO template (OEB300$)
   - Texto: Se realizará una conducción enterrada con $A conductos de polietileno libre de halógenos de diámetro nominal $I 90 mm mm, incluyendo $N el relleno y compactado de la zanja, $P el suministro y montaje de los conductos y hormigón tipo HE-20 sin vibrar,
   - Motivo: Rotura estructural de render (clase 1): 'de diámetro nominal $I 90 mm mm' interpone la frase de ubicación entre etiqueta y valor ('diámetro nominal en terreno rocoso 90 mm mm') — marco mutilado e ilegible.
172. `template_paraphrase:42:12` [v2] — TEXTO template (OEB240$)
   - Texto: Relleno localizado $W(%A), i/ compactado y material en obras de instalaciones ferroviarias, con $W(%A). Incluye transporte al lugar asignado dentro de la obra, extendido, humectación, compactación y finalización. Herramientas y medios auxiliares son 
   - Motivo: Rotura estructural: placeholder $W(%A) duplicado en literal (aparece dos veces en el texto).
173. `template_paraphrase:42:15` [v2] — TEXTO template (OEB240$)
   - Texto: Material de relleno localizado $W(%A), i/ compactado y distribuido en instalaciones ferroviarias, sitios de construcción y vías de acceso, aplicándose con $W(%A), i/ traslado, colocación, humectación, compactación y finalización del trabajo en la obr
   - Motivo: Rotura estructural: placeholder $W(%A) duplicado (aparece al inicio y en 'aplicándose con $W(%A)').
174. `template_paraphrase:42:16` [v2] — TEXTO template (OEB240$)
   - Texto: Material de relleno especificado $W(%A), i/ compactado y colocado en proyectos ferroviarios, áreas de construcción y vías de acceso, manejándose con $W(%A), i/ desplazamiento, colocación, humectación, compactación y terminación del trabajo en el luga
   - Motivo: Rotura estructural: placeholder $W(%A) duplicado (aparece en 'Material de relleno especificado $W(%A)' y en 'manejándose con $W(%A)').
175. `template_paraphrase:42:17` [v2] — TEXTO template (OEB240$)
   - Texto: Relleno localizado $W(%A), i/ compactado y entregado en instalaciones ferroviarias, zonas de construcción y vías de acceso, gestionado con $W(%A), i/ traslado, colocación, humectación, compactación y finalización del proyecto en la obra. Ejecución: $
   - Motivo: Rotura estructural: placeholder $W(%A) duplicado (aparece al inicio y en 'gestionado con $W(%A)').
176. `template_paraphrase:44:3` [v2] — TEXTO template (OEB070$)
   - Texto: Ejecución y suministro de conducción enterrada de $A conducto(s) de polietileno de diámetro nominal 110 mm 5 At.. Trabajo realizado en: $B, dentro de la $C Banda. Las $D
   - Motivo: Clase 1: 'dentro de la $C Banda' renderiza 'dentro de la i >= 5 horas Banda' y 'Las $D' renderiza 'Las Volumen relevante' — marcos rotos ilegibles.
177. `template_paraphrase:44:4` [v2] — TEXTO template (OEB070$)
   - Texto: Suministro y ejecución de conducción enterrada realizada con $A conducto(s) de polietileno de 110 mm de diámetro 5 At., incluso bajo vías. En $B realizado; en la banda de $C. Las $D
   - Motivo: Clase 1: 'En $B realizado' ('En Diurno realizado') y 'Las $D' ('Las Volumen escaso') son marcos mutilados al renderizar.
178. `template_paraphrase:44:5` [v2] — TEXTO template (OEB070$)
   - Texto: Suministro y ejecución de conducción enterrada con $A conducto(s) de polietileno 5 At., de diámetro 110 mm, en condiciones de topo bajo vías. Dentro del trabajo de $B, en la $C banda. Las $D
   - Motivo: Clase 1: 'en la $C banda' renderiza 'en la i >= 5 horas banda' y 'Las $D' queda sin sustantivo — marcos rotos.
179. `template_paraphrase:45:10` [v2] — TEXTO template (OEB100$)
   - Texto: Ejecutarse y suministrarseá la canalización con tubos de acero desde canaleta de hormigón en el túnel para el acceso a interfonía hasta el repartidor. Trabajo: $A Banda de mantenimiento: $B Condiciones de ejecución: $C.
   - Motivo: Clase 1 (extensión render ilegible): 'Ejecutarse y suministrarseá' es un token mutilado morfológicamente imposible que rompe el marco inicial de la frase.
180. `template_paraphrase:48:3` [v2] — TEXTO template (OEB190$)
   - Texto: Se realiza una zanja para el tendido de cables con una profundidad de $A y una anchura máxima de 0,60 m, utilizando $R(%B). Se emplaza un relleno compactado con material procedente de la misma excavación, se instala una cama de arena de $X(%A) de esp
   - Motivo: Clase 1: 'utilizando $R(%B)' renderiza 'utilizando ejecutada por excavación manual...' — el fragmento $R solo funciona como aposición; marco roto ilegible.
181. `template_paraphrase:48:4` [v2] — TEXTO template (OEB190$)
   - Texto: Se diseñó una zanja para el tendido de cables con un espesor de $A, una anchura máxima de 0,60 m, y materiales procedentes de $R(%B). Se establecerá un relleno compactado a partir del material obtenido en la excavación, junto con una cama de arena de
   - Motivo: Clase 1: 'materiales procedentes de $R(%B)' renderiza 'procedentes de ejecutada por excavación manual...' — marco roto ilegible.
182. `template_paraphrase:48:5` [v2] — TEXTO template (OEB190$)
   - Texto: Se efectúa la excavación de zanja para el tendido de cables con una profundidad de $A y una anchura máxima de 0,60 m, empleando materiales de $R(%B). Se colocará un relleno compactado con material de la propia excavación, una cama de arena de $X(%A) 
   - Motivo: Clase 1: 'empleando materiales de $R(%B)' renderiza 'materiales de ejecutada por excavación manual...' — marco roto ilegible.
183. `template_paraphrase:4:5` [v2] — RESUMEN template (OEB230$)
   - Texto: Conductos enterrados de hormigón $A T, de diámetro nominal 200 mm, fabricados en polietileno sin halógenos, $K. $G(%C)/$H(%D)/$J(%F)
   - Motivo: Clase 1: paréntesis del bloque de códigos perdidos ('$K. $G(%C)/$H(%D)/$J(%F)' sin envoltura).
184. `template_paraphrase:5:10` [v2] — RESUMEN template (OEB280$)
   - Texto: Se instala la canalización enterrada, tipo T, hecha del material $A, con un revestimiento de polietileno sin halógenos de 40 mm. El espesor es de $K. Se menciona con las referencias ($G(%C), $H(%D), $J(%F)).
   - Motivo: Clase 1: marco ilegible 'El espesor es de $K' (renderiza 'El espesor es de bajo vías') y marco de conteo mutilado 'hecha del material $A' (renderiza 'del material 4').
185. `template_paraphrase:5:11` [v2] — RESUMEN template (OEB280$)
   - Texto: Se emplea la canalización de tipo T, conformada con el material $A, con tubos de polietileno libre de halógenos de 40 mm. La espesor es de $K. Se cita con las referencias ($G(%C), $H(%D), $J(%F)).
   - Motivo: Clase 1: 'La espesor es de $K' — ejemplo literal ratificado de la rúbrica v2; además 'el material $A' mutila el marco de conteo.
186. `template_paraphrase:5:15` [v2] — RESUMEN template (OEB280$)
   - Texto: Conducción enterrada tipo $A, con tubo de polietileno libre de halógenos de 40 mm y reforzamiento $K. (Certificado $G(%C)/$H(%D)/$J(%F))
   - Motivo: Clase 1: marco de conteo mutilado — 'tipo $A' pierde la T y recaracteriza el nº de tubos (renderiza 'Conducción enterrada tipo 4').
187. `template_paraphrase:5:16` [v2] — RESUMEN template (OEB280$)
   - Texto: Conducción enterrada de tipo $A, integrando tuberías de polietileno sin halógenos de 40 mm, y un sistema de refuerzo $K. (Garantías $G(%C)/$H(%D)/$J(%F))
   - Motivo: Clase 1: marco de conteo mutilado — 'de tipo $A' sin T (renderiza 'de tipo 4', el conteo de tubos desaparece).
188. `template_paraphrase:5:17` [v2] — RESUMEN template (OEB280$)
   - Texto: Conducción enterrada tipo $A, que utiliza tubos de polietileno sin halógenos de 40 mm y sistema de refuerzo $K. (Acreditación $G(%C)/$H(%D)/$J(%F))
   - Motivo: Clase 1: marco de conteo mutilado — 'tipo $A' sin T; el nº de tubos se pierde en el render.
189. `template_paraphrase:5:9` [v2] — RESUMEN template (OEB280$)
   - Texto: Se utiliza la conducción enterrada de tipo T fabricada con el material $A, con un tubo de polietileno libre de halógenos de 40 mm. La espesor es de $K. Se especifica con las referencias ($G(%C), $H(%D), $J(%F)).
   - Motivo: Clase 1: 'La espesor es de $K' (marco ilegible ratificado) y 'el material $A' (marco de conteo mutilado).
190. `template_paraphrase:6:12` [v2] — RESUMEN template (OEB290$)
   - Texto: Conducción enterrada de tipo $A, con revestimiento de polietileno sin halógenos de 50 mm, $K. Incluido en la norma ($G(%C)/$H(%D)/$J(%F))
   - Motivo: Clase 1: marco de conteo mutilado — 'de tipo $A' sin T (renderiza 'de tipo 4'); el placeholder de nº de tubos queda desnaturalizado.
191. `template_paraphrase:6:13` [v2] — RESUMEN template (OEB290$)
   - Texto: Conducción enterrada tipo $A, revestida con polietileno sin halógenos de 50 mm, $K. Se cumple la normativa ($G(%C)/$H(%D)/$J(%F))
   - Motivo: Clase 1: marco de conteo mutilado — 'tipo $A' sin T.
192. `template_paraphrase:6:14` [v2] — RESUMEN template (OEB290$)
   - Texto: Conducción enterrada tipo $A, que incluye revestimiento de polietileno sin halógenos de 50 mm, $K. Normativa: ($G(%C)/$H(%D)/$J(%F))
   - Motivo: Clase 1: marco de conteo mutilado — 'tipo $A' sin T.
193. `template_paraphrase:6:15` [v2] — RESUMEN template (OEB290$)
   - Texto: Conducción enterrada tipo $A, recubierta con polietileno sin halógenos de 50 mm. $K. (Aprobado por $G(%C), certificado en $H(%D), conforme a la norma $J(%F))
   - Motivo: Clase 1: marco de conteo mutilado — 'tipo $A' sin T; además el bloque disuelto en predicados renderiza garbled ('certificado en i >== 5 horas').
194. `template_paraphrase:6:16` [v2] — RESUMEN template (OEB290$)
   - Texto: Conducto de hormigón tipo $A, revestido con material de polietileno libre de halógenos que mide 50 mm. $K. Aprobado según $G(%C), certificado en $H(%D), y conforme a la norma $J(%F).
   - Motivo: Clase 1: marco de conteo mutilado 'tipo $A' y paréntesis del bloque de códigos perdidos (disuelto en prosa 'Aprobado según $G(%C), certificado en $H(%D)...').
195. `template_paraphrase:6:17` [v2] — RESUMEN template (OEB290$)
   - Texto: Tubo de hormigón tipo $A, revestido con polietileno sin halógenos de 50 mm. $K. Aprobado por $G(%C), certificado en $H(%D), y conforme a la norma $J(%F).
   - Motivo: Clase 1: marco de conteo mutilado 'tipo $A' y paréntesis del bloque de códigos perdidos (predicados en prosa para $G/$H/$J).
196. `template_paraphrase:7:10` [v2] — RESUMEN template (OEB300$)
   - Texto: Se emplea una canalización enterrada de tipo $A T, elaborada con polietileno sin halógenos de 90 mm, con la finalidad de proporcionar $K. Las especificaciones dimensionales corresponden a ($G(%C)/$H(%D)/$J(%F)).
   - Motivo: Clase 1: marco ilegible — 'con la finalidad de proporcionar $K' renderiza roto ('proporcionar bajo vías', 'proporcionar en balasto').
197. `template_paraphrase:7:11` [v2] — RESUMEN template (OEB300$)
   - Texto: Se lleva a cabo la instalación de una conducción de tipo $A T, hecha con polietileno que no contiene halógenos y con un diámetro de 90 mm, con el propósito de satisfacer los requerimientos de $K. Las especificaciones técnicas corresponden a ($G(%C)/$
   - Motivo: Clase 1: marco ilegible — 'los requerimientos de $K' renderiza roto ('requerimientos de rocoso', 'de con topo', 'de en balasto').
198. `template_paraphrase:7:17` [v2] — RESUMEN template (OEB300$)
   - Texto: Conducción enterrada de concreto $A T, con revestimiento de polietileno sin halógenos de 90 mm, y propiedades detalladas en $K. Referencia estándar: $G(%C)/$H(%D)/$J(%F)
   - Motivo: Clase 1: paréntesis del bloque de códigos perdidos ('Referencia estándar: $G(%C)/$H(%D)/$J(%F)' sin envoltura); además 'detalladas en $K' renderiza roto ('en en balasto').
199. `template_paraphrase:7:3` [v2] — RESUMEN template (OEB300$)
   - Texto: Conducción enterrada $A T de polietileno sin halógenos de 90 mm, $K. $K. ([$G(%C)/$H(%D)/$J(%F)])
   - Motivo: Clase 1: placeholder $K duplicado ('$K. $K.' renderiza 'bajo vías. bajo vías.') y corchetes espurios en el bloque '([$G...])'.
200. `template_paraphrase:7:4` [v2] — RESUMEN template (OEB300$)
   - Texto: Tubería estructural $A T con polietileno sin halógenos de 90 mm de diámetro, $K. ($G(%C)/$H(%D)/$J(%F)) $K.
   - Motivo: Clase 1: placeholder $K duplicado — '$K' colgando tras el bloque parentético además del interno.
201. `template_paraphrase:7:5` [v2] — RESUMEN template (OEB300$)
   - Texto: Conducto subterráneo $A T hecho de polietileno exento de halógenos con un diámetro de 90 mm, $K. ($G(%C)/$H(%D)/$J(%F)) $K.
   - Motivo: Clase 1: placeholder $K duplicado al final tras el paréntesis.
202. `template_paraphrase:8:2` [v2] — RESUMEN template (OEB020$)
   - Texto: La canalización de hormigón de $A T, constituida por conductos de PVC 110 mm, se encuentra certificada bajo $K. (Características: $G(%C)/$H(%D)/$J(%F))
   - Motivo: Clase 1: marco 'certificada bajo $K' choca con valores de $K que empiezan por preposición ('bajo vías', 'en cruce de carretera', 'en andén', 'con topo') — renderiza ilegible ('certificada bajo bajo vías', 'certificada bajo en andén'), verificado en OBRA CIVIL.json.