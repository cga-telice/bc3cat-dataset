# Informe de reconciliación v1 (notebooks) vs v2 (bc3param)

Fuente común: `data/raw/BPA_2024_v2_OEB_mod_utf8.txt`. Capítulo: OEB#.

- v2 combinaciones totales: 47508 | válidas: 40407 | inválidas por %E (ausentes en un uso normal): 7101

## RESUMEN

- v1 claves: 47508 | v2 claves: 47508 | comunes: 47508
- solo en v1: 0 | solo en v2: 0
- iguales exactos: 636
- iguales salvo espacios (cosmético): 11322
- difieren solo por la corrupción de literales de v1 (v2 corrige): 35550
- otras diferencias de fondo: 0

Ejemplos donde v2 corrige la corrupción de v1:

- `OEB020hdbbc`
  - v1: Canalización hormigonada de 24 T, PVC 110 mm, en cruce de carretera. (Nocturno/3 >== i > "5" horas/Cualquier condición de ejecución)
  - v2: Canalización hormigonada de 24 T, PVC 110 mm, en cruce de carretera. (Nocturno/3 >= i > 5 horas/Cualquier condición de ejecución)
- `OEB230dcdab`
  - v1: Canalización hormigonada 4 T, polietileno libre de halógenos de 200 mm, rocoso. (Nocturno excepcional/i >== 5 horas/Volumen escaso)
  - v2: Canalización hormigonada 4 T, polietileno libre de halógenos de 200 mm, rocoso. (Nocturno excepcional/i >= 5 horas/Volumen escaso)
- `OEB190bcfcc`
  - v1: Zanja para cables de 0,80 a 1,00 m de profundidad a mano, balasto, en material balasto. (Cualquier franja horaria excepcional/i < "3" horas/Cualquier condición de ejecución)
  - v2: Zanja para cables de 0,80 a 1,00 m de profundidad a mano, balasto, en material balasto. (Cualquier franja horaria excepcional/i < 3 horas/Cualquier condición de ejecución)
- `OEB250bccba`
  - v1: Suministro y montaje de canalización de 6 tubos de acero galvanizado de 100mm de diámetro para instalaciones CMS en transiciones entre diferentes plataformas.(No aplica/3 <== i < "5" horas/Volumen rel
  - v2: Suministro y montaje de canalización de 6 tubos de acero galvanizado de 100mm de diámetro para instalaciones CMS en transiciones entre diferentes plataformas.(No aplica/3 <= i < 5 horas/Volumen releva

## TEXTO

- v1 claves: 47508 | v2 claves: 47508 | comunes: 47508
- solo en v1: 0 | solo en v2: 0
- iguales exactos: 0
- iguales salvo espacios (cosmético): 47508
- difieren solo por la corrupción de literales de v1 (v2 corrige): 0
- otras diferencias de fondo: 0

## Conclusión

- El conjunto de claves (ítems derivados) es idéntico entre v1 y v2.
- TEXTO: coincide al 100 % salvo espacios en blanco (v2 colapsa espacios repetidos).
- RESUMEN: no hay ninguna diferencia inexplicada. Todas las que no son de espacios se deben a que v2 corrige la corrupción de literales de v1 (`>==`, `<==`, comillas espurias como `"3"`), producida por la reescritura de fórmulas con expresiones regulares sobre texto entre comillas.
- v2 añade además precio y descompuesto por ítem, que v1 no calculaba, y marca 7101 combinaciones como inválidas por la sentencia `%E` (no existen en el uso normal del catálogo). No tienen equivalente en v1, que las incluía.

Fuente de v2 en esta comparación: el mismo fichero `_mod` que usó v1, para que las diferencias reflejen el motor y no la elección de fichero.

