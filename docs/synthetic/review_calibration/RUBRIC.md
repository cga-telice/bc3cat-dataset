# Rúbrica de revisión de menús BC3CAT-Syn — v1 (2026-08-31)

**Regla única: un candidato se APRUEBA solo si cumple LOS CINCO criterios. Si falla
cualquiera, se RECHAZA. Ante duda genuina, el veredicto es DUDOSO (nunca se fuerza).**

| Veredicto | Código | Significado |
|---|---|---|
| Aprobar | **A** | Cumple los 5 criterios |
| Rechazar | **R** | Falla al menos uno |
| Dudoso | **D** | No se puede decidir con confianza (se escala) |

## Los cinco criterios

1. **Fluidez** — español técnico natural, gramática y concordancia correctas, registro de
   catálogo de construcción ferroviaria. Se rechaza el "español de traductor" y las
   construcciones forzadas.
2. **Preservación semántica** — mismo significado que el original: sin hechos añadidos,
   sin matices perdidos, sin términos de dominio alterados (*con topo* = con tuneladora;
   *ternas*; *entibación*; *balasto*; *mandrilado*…). Las cantidades y variables ya están
   garantizadas mecánicamente — aquí se juzga lo cualitativo.
3. **Seguridad para recuperación** — el reescrito debe seguir denotando *ese* ítem sin
   volverse confundible con un hermano (otro valor del mismo eje, otro fragmento de la
   misma variable). Si el candidato podría describir igual de bien a un hermano listado
   en el contexto, se rechaza.
4. **Semántica del tipo** — debe ser una instancia genuina de su tipo de reescritura:
   - `synonym_label`: sinónimo o etiqueta equivalente, distinguible de los hermanos.
   - `num_to_text`: el número en letras, preferiblemente conservando el sustantivo.
   - `unit_conversion`: conversión aritméticamente correcta.
   - `unit_expansion`: unidad/expresión desarrollada, mismo valor.
   - `paraphrase` (L2): mismo contenido del fragmento con otras palabras.
   - `expansion` (L2): explicita lo implícito; **prohibido añadir hechos** ("ideal para
     áreas urbanas", "asegurando durabilidad" ⇒ R).
   - `compression` (L2): estrictamente más corta, sin perder contenido.
   - `omission` (L3): la plantilla sin la mención omitida, gramaticalmente reparada.
   - `reorder` (L3): mismas palabras/cláusulas en otro orden.
   - `template_paraphrase` (L3): la plantilla completa reescrita (léxico y/o estructura).
   - `new_param`: eje nuevo plausible en ingeniería, sin colisionar con ejes existentes;
     valores mutuamente excluyentes y sensatos.
5. **Coherencia técnica** — nada que un ingeniero de obra civil marcaría como disparate
   (materiales imposibles, procedimientos sin sentido, anglicismos crudos tipo "túnel
   boring").

## Condiciones de aplicación

- **Rechazo por defecto**: un falso aprobado contamina el corpus; un falso rechazo solo
  pierde un candidato (hay excedente). En caso de duda entre A y R sin llegar a D: R.
- **A ciegas de procedencia**: el modelo proponente (phi4/qwen) no se muestra ni se
  considera durante el juicio.
- **Con contexto**: cada candidato se juzga viendo el original y sus hermanos (valores
  del mismo eje / fragmentos de la misma variable / ejes existentes del concepto).

## Protocolo de calibración (decidido 2026-08-31)

1. Muestra estratificada de **100 candidatos** (`CALIBRATION_SAMPLE.md`), semilla fija.
2. Claude produce sus veredictos sobre los 100 **antes** de la revisión de César y
   compromete en git el SHA-256 del archivo (independencia verificable); el archivo se
   revela al recibir los veredictos de César.
3. César revisa los mismos 100 (columnas original/candidato + contexto) y entrega A/R/D.
4. Se calcula el acuerdo (kappa de Cohen sobre A/R; los D se examinan aparte). Si el
   acuerdo es aceptable para César, Claude pasa sobre los 11 menús completos con tres
   veredictos; los D y una muestra de los A van a auditoría de César.
