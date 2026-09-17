# OE — hojas con el TEXTO idéntico (corpus entregado)

Medido sobre `data/synthetic/processed_OE/OE_target_long.parquet` (70 242 hojas),
a raíz del hallazgo del sprint S2 de `bc3cat-retrieval` (2026-09-17).

- grupos: **292**, hojas implicadas: **776**
- **todos los grupos son intra-concepto**: ningún grupo mezcla dos conceptos, así que
  la puntuación a nivel de concepto (`parent_key`) no tiene techo por esto. El techo
  afecta solo a la identificación de la hoja exacta: 776/70 242 = 1,10 %.
- el RESUMEN distingue los 292 grupos, y por eso la deduplicación —que compara la
  pareja (resumen, texto)— los conservó.

## Causa

No se pierde ninguna variable al renderizar. La plantilla del TEXTO de esos conceptos
**no cita uno de los ejes de parámetros**, así que las hojas que solo difieren en ese
eje rinden el mismo TEXTO.

| concepto | grupos | hojas | ejes | ejes que usa el TEXTO | eje ausente |
|---|---|---|---|---|---|
| `OEA050$` CANALETA DE HORMIGÓN | 192 | 576 | A, B, C, D | A, B, C | D (CONDICIONES DE EJECUCIÓN) |
| `OEG050$` CIMENTACIONES PRISMÁTICAS | 100 | 200 | A, B, C, D | A, B | C (Acceso) |

En `OEG050$` el RESUMEN sí separa las hojas porque indexa la misma tabla de consulta
por otro eje (`$L(b,%C)` frente a `$L(b,%D)` en el TEXTO); es una peculiaridad de la
plantilla del propio catálogo BPA 2026.

## Pendiente de decisión

Colapsar estas hojas cambiaría el conjunto de objetivos ya entregado, así que queda
como decisión de César, igual que las duplicadas intra-concepto de `OEG010$`
señaladas en su día. Alternativa menos invasiva: marcar cada grupo en los registros
del corpus para que el consumidor pueda excluirlas o agruparlas al puntuar.

## Grupos

### `OEA050$` — 192 grupos

- `OEA050aaaa` · `OEA050aaab` · `OEA050aaac`
- `OEA050aaba` · `OEA050aabb` · `OEA050aabc`
- `OEA050aaca` · `OEA050aacb` · `OEA050aacc`
- `OEA050aada` · `OEA050aadb` · `OEA050aadc`
- `OEA050abaa` · `OEA050abab` · `OEA050abac`
- `OEA050abba` · `OEA050abbb` · `OEA050abbc`
- `OEA050abca` · `OEA050abcb` · `OEA050abcc`
- `OEA050abda` · `OEA050abdb` · `OEA050abdc`
- `OEA050acaa` · `OEA050acab` · `OEA050acac`
- `OEA050acba` · `OEA050acbb` · `OEA050acbc`
- `OEA050acca` · `OEA050accb` · `OEA050accc`
- `OEA050acda` · `OEA050acdb` · `OEA050acdc`
- `OEA050adaa` · `OEA050adab` · `OEA050adac`
- `OEA050adba` · `OEA050adbb` · `OEA050adbc`
- `OEA050adca` · `OEA050adcb` · `OEA050adcc`
- `OEA050adda` · `OEA050addb` · `OEA050addc`
- `OEA050baaa` · `OEA050baab` · `OEA050baac`
- `OEA050baba` · `OEA050babb` · `OEA050babc`
- `OEA050baca` · `OEA050bacb` · `OEA050bacc`
- `OEA050bada` · `OEA050badb` · `OEA050badc`
- `OEA050bbaa` · `OEA050bbab` · `OEA050bbac`
- `OEA050bbba` · `OEA050bbbb` · `OEA050bbbc`
- `OEA050bbca` · `OEA050bbcb` · `OEA050bbcc`
- `OEA050bbda` · `OEA050bbdb` · `OEA050bbdc`
- `OEA050bcaa` · `OEA050bcab` · `OEA050bcac`
- `OEA050bcba` · `OEA050bcbb` · `OEA050bcbc`
- `OEA050bcca` · `OEA050bccb` · `OEA050bccc`
- `OEA050bcda` · `OEA050bcdb` · `OEA050bcdc`
- `OEA050bdaa` · `OEA050bdab` · `OEA050bdac`
- `OEA050bdba` · `OEA050bdbb` · `OEA050bdbc`
- `OEA050bdca` · `OEA050bdcb` · `OEA050bdcc`
- `OEA050bdda` · `OEA050bddb` · `OEA050bddc`
- `OEA050caaa` · `OEA050caab` · `OEA050caac`
- `OEA050caba` · `OEA050cabb` · `OEA050cabc`
- `OEA050caca` · `OEA050cacb` · `OEA050cacc`
- `OEA050cada` · `OEA050cadb` · `OEA050cadc`
- `OEA050cbaa` · `OEA050cbab` · `OEA050cbac`
- `OEA050cbba` · `OEA050cbbb` · `OEA050cbbc`
- `OEA050cbca` · `OEA050cbcb` · `OEA050cbcc`
- `OEA050cbda` · `OEA050cbdb` · `OEA050cbdc`
- `OEA050ccaa` · `OEA050ccab` · `OEA050ccac`
- `OEA050ccba` · `OEA050ccbb` · `OEA050ccbc`
- `OEA050ccca` · `OEA050cccb` · `OEA050cccc`
- `OEA050ccda` · `OEA050ccdb` · `OEA050ccdc`
- `OEA050cdaa` · `OEA050cdab` · `OEA050cdac`
- `OEA050cdba` · `OEA050cdbb` · `OEA050cdbc`
- `OEA050cdca` · `OEA050cdcb` · `OEA050cdcc`
- `OEA050cdda` · `OEA050cddb` · `OEA050cddc`
- `OEA050daaa` · `OEA050daab` · `OEA050daac`
- `OEA050daba` · `OEA050dabb` · `OEA050dabc`
- `OEA050daca` · `OEA050dacb` · `OEA050dacc`
- `OEA050dada` · `OEA050dadb` · `OEA050dadc`
- `OEA050dbaa` · `OEA050dbab` · `OEA050dbac`
- `OEA050dbba` · `OEA050dbbb` · `OEA050dbbc`
- `OEA050dbca` · `OEA050dbcb` · `OEA050dbcc`
- `OEA050dbda` · `OEA050dbdb` · `OEA050dbdc`
- `OEA050dcaa` · `OEA050dcab` · `OEA050dcac`
- `OEA050dcba` · `OEA050dcbb` · `OEA050dcbc`
- `OEA050dcca` · `OEA050dccb` · `OEA050dccc`
- `OEA050dcda` · `OEA050dcdb` · `OEA050dcdc`
- `OEA050ddaa` · `OEA050ddab` · `OEA050ddac`
- `OEA050ddba` · `OEA050ddbb` · `OEA050ddbc`
- `OEA050ddca` · `OEA050ddcb` · `OEA050ddcc`
- `OEA050ddda` · `OEA050dddb` · `OEA050dddc`
- `OEA050eaaa` · `OEA050eaab` · `OEA050eaac`
- `OEA050eaba` · `OEA050eabb` · `OEA050eabc`
- `OEA050eaca` · `OEA050eacb` · `OEA050eacc`
- `OEA050eada` · `OEA050eadb` · `OEA050eadc`
- `OEA050ebaa` · `OEA050ebab` · `OEA050ebac`
- `OEA050ebba` · `OEA050ebbb` · `OEA050ebbc`
- `OEA050ebca` · `OEA050ebcb` · `OEA050ebcc`
- `OEA050ebda` · `OEA050ebdb` · `OEA050ebdc`
- `OEA050ecaa` · `OEA050ecab` · `OEA050ecac`
- `OEA050ecba` · `OEA050ecbb` · `OEA050ecbc`
- `OEA050ecca` · `OEA050eccb` · `OEA050eccc`
- `OEA050ecda` · `OEA050ecdb` · `OEA050ecdc`
- `OEA050edaa` · `OEA050edab` · `OEA050edac`
- `OEA050edba` · `OEA050edbb` · `OEA050edbc`
- `OEA050edca` · `OEA050edcb` · `OEA050edcc`
- `OEA050edda` · `OEA050eddb` · `OEA050eddc`
- `OEA050faaa` · `OEA050faab` · `OEA050faac`
- `OEA050faba` · `OEA050fabb` · `OEA050fabc`
- `OEA050faca` · `OEA050facb` · `OEA050facc`
- `OEA050fada` · `OEA050fadb` · `OEA050fadc`
- `OEA050fbaa` · `OEA050fbab` · `OEA050fbac`
- `OEA050fbba` · `OEA050fbbb` · `OEA050fbbc`
- `OEA050fbca` · `OEA050fbcb` · `OEA050fbcc`
- `OEA050fbda` · `OEA050fbdb` · `OEA050fbdc`
- `OEA050fcaa` · `OEA050fcab` · `OEA050fcac`
- `OEA050fcba` · `OEA050fcbb` · `OEA050fcbc`
- `OEA050fcca` · `OEA050fccb` · `OEA050fccc`
- `OEA050fcda` · `OEA050fcdb` · `OEA050fcdc`
- `OEA050fdaa` · `OEA050fdab` · `OEA050fdac`
- `OEA050fdba` · `OEA050fdbb` · `OEA050fdbc`
- `OEA050fdca` · `OEA050fdcb` · `OEA050fdcc`
- `OEA050fdda` · `OEA050fddb` · `OEA050fddc`
- `OEA050gaaa` · `OEA050gaab` · `OEA050gaac`
- `OEA050gaba` · `OEA050gabb` · `OEA050gabc`
- `OEA050gaca` · `OEA050gacb` · `OEA050gacc`
- `OEA050gada` · `OEA050gadb` · `OEA050gadc`
- `OEA050gbaa` · `OEA050gbab` · `OEA050gbac`
- `OEA050gbba` · `OEA050gbbb` · `OEA050gbbc`
- `OEA050gbca` · `OEA050gbcb` · `OEA050gbcc`
- `OEA050gbda` · `OEA050gbdb` · `OEA050gbdc`
- `OEA050gcaa` · `OEA050gcab` · `OEA050gcac`
- `OEA050gcba` · `OEA050gcbb` · `OEA050gcbc`
- `OEA050gcca` · `OEA050gccb` · `OEA050gccc`
- `OEA050gcda` · `OEA050gcdb` · `OEA050gcdc`
- `OEA050gdaa` · `OEA050gdab` · `OEA050gdac`
- `OEA050gdba` · `OEA050gdbb` · `OEA050gdbc`
- `OEA050gdca` · `OEA050gdcb` · `OEA050gdcc`
- `OEA050gdda` · `OEA050gddb` · `OEA050gddc`
- `OEA050haaa` · `OEA050haab` · `OEA050haac`
- `OEA050haba` · `OEA050habb` · `OEA050habc`
- `OEA050haca` · `OEA050hacb` · `OEA050hacc`
- `OEA050hada` · `OEA050hadb` · `OEA050hadc`
- `OEA050hbaa` · `OEA050hbab` · `OEA050hbac`
- `OEA050hbba` · `OEA050hbbb` · `OEA050hbbc`
- `OEA050hbca` · `OEA050hbcb` · `OEA050hbcc`
- `OEA050hbda` · `OEA050hbdb` · `OEA050hbdc`
- `OEA050hcaa` · `OEA050hcab` · `OEA050hcac`
- `OEA050hcba` · `OEA050hcbb` · `OEA050hcbc`
- `OEA050hcca` · `OEA050hccb` · `OEA050hccc`
- `OEA050hcda` · `OEA050hcdb` · `OEA050hcdc`
- `OEA050hdaa` · `OEA050hdab` · `OEA050hdac`
- `OEA050hdba` · `OEA050hdbb` · `OEA050hdbc`
- `OEA050hdca` · `OEA050hdcb` · `OEA050hdcc`
- `OEA050hdda` · `OEA050hddb` · `OEA050hddc`
- `OEA050iaaa` · `OEA050iaab` · `OEA050iaac`
- `OEA050iaba` · `OEA050iabb` · `OEA050iabc`
- `OEA050iaca` · `OEA050iacb` · `OEA050iacc`
- `OEA050iada` · `OEA050iadb` · `OEA050iadc`
- `OEA050ibaa` · `OEA050ibab` · `OEA050ibac`
- `OEA050ibba` · `OEA050ibbb` · `OEA050ibbc`
- `OEA050ibca` · `OEA050ibcb` · `OEA050ibcc`
- `OEA050ibda` · `OEA050ibdb` · `OEA050ibdc`
- `OEA050icaa` · `OEA050icab` · `OEA050icac`
- `OEA050icba` · `OEA050icbb` · `OEA050icbc`
- `OEA050icca` · `OEA050iccb` · `OEA050iccc`
- `OEA050icda` · `OEA050icdb` · `OEA050icdc`
- `OEA050idaa` · `OEA050idab` · `OEA050idac`
- `OEA050idba` · `OEA050idbb` · `OEA050idbc`
- `OEA050idca` · `OEA050idcb` · `OEA050idcc`
- `OEA050idda` · `OEA050iddb` · `OEA050iddc`
- `OEA050jaaa` · `OEA050jaab` · `OEA050jaac`
- `OEA050jaba` · `OEA050jabb` · `OEA050jabc`
- `OEA050jaca` · `OEA050jacb` · `OEA050jacc`
- `OEA050jada` · `OEA050jadb` · `OEA050jadc`
- `OEA050jbaa` · `OEA050jbab` · `OEA050jbac`
- `OEA050jbba` · `OEA050jbbb` · `OEA050jbbc`
- `OEA050jbca` · `OEA050jbcb` · `OEA050jbcc`
- `OEA050jbda` · `OEA050jbdb` · `OEA050jbdc`
- `OEA050jcaa` · `OEA050jcab` · `OEA050jcac`
- `OEA050jcba` · `OEA050jcbb` · `OEA050jcbc`
- `OEA050jcca` · `OEA050jccb` · `OEA050jccc`
- `OEA050jcda` · `OEA050jcdb` · `OEA050jcdc`
- `OEA050jdaa` · `OEA050jdab` · `OEA050jdac`
- `OEA050jdba` · `OEA050jdbb` · `OEA050jdbc`
- `OEA050jdca` · `OEA050jdcb` · `OEA050jdcc`
- `OEA050jdda` · `OEA050jddb` · `OEA050jddc`
- `OEA050kaaa` · `OEA050kaab` · `OEA050kaac`
- `OEA050kaba` · `OEA050kabb` · `OEA050kabc`
- `OEA050kaca` · `OEA050kacb` · `OEA050kacc`
- `OEA050kada` · `OEA050kadb` · `OEA050kadc`
- `OEA050kbaa` · `OEA050kbab` · `OEA050kbac`
- `OEA050kbba` · `OEA050kbbb` · `OEA050kbbc`
- `OEA050kbca` · `OEA050kbcb` · `OEA050kbcc`
- `OEA050kbda` · `OEA050kbdb` · `OEA050kbdc`
- `OEA050kcaa` · `OEA050kcab` · `OEA050kcac`
- `OEA050kcba` · `OEA050kcbb` · `OEA050kcbc`
- `OEA050kcca` · `OEA050kccb` · `OEA050kccc`
- `OEA050kcda` · `OEA050kcdb` · `OEA050kcdc`
- `OEA050kdaa` · `OEA050kdab` · `OEA050kdac`
- `OEA050kdba` · `OEA050kdbb` · `OEA050kdbc`
- `OEA050kdca` · `OEA050kdcb` · `OEA050kdcc`
- `OEA050kdda` · `OEA050kddb` · `OEA050kddc`
- `OEA050laaa` · `OEA050laab` · `OEA050laac`
- `OEA050laba` · `OEA050labb` · `OEA050labc`
- `OEA050laca` · `OEA050lacb` · `OEA050lacc`
- `OEA050lada` · `OEA050ladb` · `OEA050ladc`
- `OEA050lbaa` · `OEA050lbab` · `OEA050lbac`
- `OEA050lbba` · `OEA050lbbb` · `OEA050lbbc`
- `OEA050lbca` · `OEA050lbcb` · `OEA050lbcc`
- `OEA050lbda` · `OEA050lbdb` · `OEA050lbdc`
- `OEA050lcaa` · `OEA050lcab` · `OEA050lcac`
- `OEA050lcba` · `OEA050lcbb` · `OEA050lcbc`
- `OEA050lcca` · `OEA050lccb` · `OEA050lccc`
- `OEA050lcda` · `OEA050lcdb` · `OEA050lcdc`
- `OEA050ldaa` · `OEA050ldab` · `OEA050ldac`
- `OEA050ldba` · `OEA050ldbb` · `OEA050ldbc`
- `OEA050ldca` · `OEA050ldcb` · `OEA050ldcc`
- `OEA050ldda` · `OEA050lddb` · `OEA050lddc`

### `OEG050$` — 100 grupos

- `OEG050aaaa` · `OEG050aaba`
- `OEG050aaab` · `OEG050aabb`
- `OEG050aaac` · `OEG050aabc`
- `OEG050aaad` · `OEG050aabd`
- `OEG050abaa` · `OEG050abba`
- `OEG050abab` · `OEG050abbb`
- `OEG050abac` · `OEG050abbc`
- `OEG050abad` · `OEG050abbd`
- `OEG050acaa` · `OEG050acba`
- `OEG050acab` · `OEG050acbb`
- `OEG050acac` · `OEG050acbc`
- `OEG050acad` · `OEG050acbd`
- `OEG050adaa` · `OEG050adba`
- `OEG050adab` · `OEG050adbb`
- `OEG050adac` · `OEG050adbc`
- `OEG050adad` · `OEG050adbd`
- `OEG050aeaa` · `OEG050aeba`
- `OEG050aeab` · `OEG050aebb`
- `OEG050aeac` · `OEG050aebc`
- `OEG050aead` · `OEG050aebd`
- `OEG050baaa` · `OEG050baba`
- `OEG050baab` · `OEG050babb`
- `OEG050baac` · `OEG050babc`
- `OEG050baad` · `OEG050babd`
- `OEG050bbaa` · `OEG050bbba`
- `OEG050bbab` · `OEG050bbbb`
- `OEG050bbac` · `OEG050bbbc`
- `OEG050bbad` · `OEG050bbbd`
- `OEG050bcaa` · `OEG050bcba`
- `OEG050bcab` · `OEG050bcbb`
- `OEG050bcac` · `OEG050bcbc`
- `OEG050bcad` · `OEG050bcbd`
- `OEG050bdaa` · `OEG050bdba`
- `OEG050bdab` · `OEG050bdbb`
- `OEG050bdac` · `OEG050bdbc`
- `OEG050bdad` · `OEG050bdbd`
- `OEG050beaa` · `OEG050beba`
- `OEG050beab` · `OEG050bebb`
- `OEG050beac` · `OEG050bebc`
- `OEG050bead` · `OEG050bebd`
- `OEG050caaa` · `OEG050caba`
- `OEG050caab` · `OEG050cabb`
- `OEG050caac` · `OEG050cabc`
- `OEG050caad` · `OEG050cabd`
- `OEG050cbaa` · `OEG050cbba`
- `OEG050cbab` · `OEG050cbbb`
- `OEG050cbac` · `OEG050cbbc`
- `OEG050cbad` · `OEG050cbbd`
- `OEG050ccaa` · `OEG050ccba`
- `OEG050ccab` · `OEG050ccbb`
- `OEG050ccac` · `OEG050ccbc`
- `OEG050ccad` · `OEG050ccbd`
- `OEG050cdaa` · `OEG050cdba`
- `OEG050cdab` · `OEG050cdbb`
- `OEG050cdac` · `OEG050cdbc`
- `OEG050cdad` · `OEG050cdbd`
- `OEG050ceaa` · `OEG050ceba`
- `OEG050ceab` · `OEG050cebb`
- `OEG050ceac` · `OEG050cebc`
- `OEG050cead` · `OEG050cebd`
- `OEG050daaa` · `OEG050daba`
- `OEG050daab` · `OEG050dabb`
- `OEG050daac` · `OEG050dabc`
- `OEG050daad` · `OEG050dabd`
- `OEG050dbaa` · `OEG050dbba`
- `OEG050dbab` · `OEG050dbbb`
- `OEG050dbac` · `OEG050dbbc`
- `OEG050dbad` · `OEG050dbbd`
- `OEG050dcaa` · `OEG050dcba`
- `OEG050dcab` · `OEG050dcbb`
- `OEG050dcac` · `OEG050dcbc`
- `OEG050dcad` · `OEG050dcbd`
- `OEG050ddaa` · `OEG050ddba`
- `OEG050ddab` · `OEG050ddbb`
- `OEG050ddac` · `OEG050ddbc`
- `OEG050ddad` · `OEG050ddbd`
- `OEG050deaa` · `OEG050deba`
- `OEG050deab` · `OEG050debb`
- `OEG050deac` · `OEG050debc`
- `OEG050dead` · `OEG050debd`
- `OEG050eaaa` · `OEG050eaba`
- `OEG050eaab` · `OEG050eabb`
- `OEG050eaac` · `OEG050eabc`
- `OEG050eaad` · `OEG050eabd`
- `OEG050ebaa` · `OEG050ebba`
- `OEG050ebab` · `OEG050ebbb`
- `OEG050ebac` · `OEG050ebbc`
- `OEG050ebad` · `OEG050ebbd`
- `OEG050ecaa` · `OEG050ecba`
- `OEG050ecab` · `OEG050ecbb`
- `OEG050ecac` · `OEG050ecbc`
- `OEG050ecad` · `OEG050ecbd`
- `OEG050edaa` · `OEG050edba`
- `OEG050edab` · `OEG050edbb`
- `OEG050edac` · `OEG050edbc`
- `OEG050edad` · `OEG050edbd`
- `OEG050eeaa` · `OEG050eeba`
- `OEG050eeab` · `OEG050eebb`
- `OEG050eeac` · `OEG050eebc`
- `OEG050eead` · `OEG050eebd`

