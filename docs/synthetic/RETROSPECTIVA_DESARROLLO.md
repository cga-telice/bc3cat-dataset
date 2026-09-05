# BC3CAT-Syn — Retrospectiva del desarrollo del corpus sintético

**Rama:** `synthetic` · **Autor:** César · **Fecha:** 2026-09-02 · **Release descrito:** `6b52053`

---

## Resumen

Este informe documenta el desarrollo de **BC3CAT-Syn**, la versión «estresada» del
benchmark de recuperación BC3CAT, desde su motivación inicial hasta la existencia del
primer corpus piloto (8 687 ítems, generación reproducible byte a byte). No es un informe
de resultados de recuperación —esos experimentos viven en el repositorio hermano
`bc3cat-retrieval` y aún no se han ejecutado sobre este corpus—, sino una **crónica
metodológica**: qué se intentó en cada fase, por qué varias de esas tentativas fracasaron,
qué revelaron sobre la naturaleza del catálogo y del problema, y qué correcciones nos
llevaron al estado actual. El propósito es doble: dejar registro trazable de las
decisiones de diseño y justificar por qué consideramos que el proyecto está en condiciones
de pasar a la fase de evaluación de recuperación.

El hilo conductor de la travesía es un mismo tipo de adversario que reaparece bajo
distintos disfraces —el **fallo silencioso**: mutaciones que no mutan, objetivos que se
descartan sin ruido— y la disciplina que acabó neutralizándolo: hacer que el sistema falle
de forma ruidosa y grabar todo lo que produce para poder reproducirlo sin coste.

---

## 1. Contexto y objetivo

### 1.1 El hueco de evaluación

BC3CAT es un benchmark de recuperación construido sobre el catálogo paramétrico de precios
de la construcción de ADIF (formato FIEBDC/BC3). Las consultas son las descripciones cortas
del catálogo (*resumen*) y los documentos son las descripciones largas (*texto*). El
problema es estructural: **ambas superficies se generan con las mismas reglas**, de modo que
comparten raíces léxicas, abreviaturas, convenciones de unidades, orden de constituyentes y
etiquetas de parámetros. Un recuperador de solapamiento léxico explota esa coincidencia
directamente: BM25 con tokenización paramétrica alcanza el **97,4 % de acierto a nivel de
ítem**, mientras que los modelos densos, pese a rozar el 96–99 % a nivel de concepto, se
desploman al 12–45 % a nivel de ítem.

Ese número casi perfecto de BM25 debe leerse con cautela. En un despliegue real —un
estimador de costes que mapea especificaciones de proyecto a partidas de catálogo, un jefe
de obra que reconcilia partes diarios con líneas presupuestarias— la consulta la redacta una
persona con vocabulario propio, terminología regional y abreviaturas de empresa. El
benchmark actual mide un **escenario de mejor caso léxico** que no representa esa
variabilidad.

> **Objetivo.** Producir variabilidad lingüística *controlada* que preserve el significado
> paramétrico, con **trazabilidad completa** de cada transformación aplicada, de modo que la
> degradación de cada método de recuperación pueda atribuirse a un tipo concreto de cambio y
> no a «ruido» agregado.

### 1.2 La decisión de partida: mutar la regla, no el texto

Existían dos estrategias para inyectar variabilidad. La primera, **reescritura *a
posteriori*** (parafrasear con un LLM el texto ya generado), es barata pero pierde la
trazabilidad: una frase reescrita mezcla en un solo paso el intercambio de sinónimos, la
reordenación y la compresión, y ya no se pueden separar. La segunda, **modificación de la
regla de generación**, aplica cada cambio en la gramática *antes* de renderizar el texto.

Elegimos la segunda. Los ítems de BC3 no son texto libre: los emite una gramática explícita
de tres capas (valores de parámetro → variables de texto → plantillas de salida). Modificar
esa gramática produce un catálogo sintético con tres propiedades que la reescritura *a
posteriori* no puede ofrecer: mismo motor de generación, trazabilidad heredada por
construcción, y evaluación segmentable por tipo de transformación. Sobre esa base definimos
una taxonomía de **12 tipos de modificación distribuidos en 4 capas**.

Esta decisión —correcta, y que mantenemos— es también la raíz de casi todas las
dificultades que siguen: operar sobre la gramática obliga a entenderla en detalle, y el
catálogo real resultó ser bastante menos regular de lo que suponían nuestros primeros
modelos mentales.

---

## 2. La travesía

Cada episodio sigue la misma estructura: **qué intentamos**, **por qué falló**, un **ejemplo
ilustrativo** y **qué hicimos a continuación**.

### 2.1 Arquitectura: «cuatro inyecciones» que en realidad era una

**Qué intentamos.** El diseño inicial concebía la mutación como cuatro puntos de inyección
*intercalados* a lo largo del pipeline: modificar los parámetros antes de la etapa de
expansión (s03), las variables de texto antes de su evaluación (s04) y las plantillas antes
del renderizado (s05).

**Por qué falló.** Las implementaciones de los mutadores contradecían ese plano. El pipeline
es una cascada JSON → JSON, y la forma del diccionario cambia en cada etapa: tras s03 las
claves ya no son de concepto sino de hoja; en s04 las variables de texto están resueltas a
valores concretos; en s05 las plantillas ya están instanciadas. **Ninguna capa podía
consumir la salida de una etapa posterior a la suya.** El modelo mental de «cuatro puntos»
era, sencillamente, irrealizable con la estructura de datos real.

**Ejemplo.** Una mutación L2 sobre una variable de texto necesita el fragmento en su forma
`"normal" * (%B=a) + …`; pero después de s04 ese fragmento ya no existe: se ha convertido en
la cadena evaluada `{evaluated: "normal"}`. No hay nada que mutar.

**Qué hicimos (Sprint 18).** Consolidamos todo en una **única inyección** sobre el registro
de concepto *previo* a la expansión, aplicando las cuatro familias en orden fijo
(PD → L1 → L2 → L3) sobre el mismo registro, seguida de una sola re-ejecución del pipeline
de s03 a s07. Como la etapa de expansión copia idénticamente las variables y plantillas a
cada hoja, mutar el padre y re-expandir es *equivalente* a mutar las hojas —y mucho más
barato. Esto además estableció una separación limpia entre dos módulos que se mantendría
hasta el final: **Stage A** (proponer y catalogar variantes, sin ejecutar el pipeline) y
**Stage B** (aplicar reglas y re-ejecutar).

### 2.2 La reproducibilidad como cimiento

**Qué intentamos.** Delegar las reescrituras a un LLM. Cada propuesta —un sinónimo, una
paráfrasis— la genera un modelo de lenguaje a partir de un prompt en español.

**El riesgo.** Los LLM son caros (en tiempo de GPU) y no deterministas. Un proyecto que
tuviera que volver a llamar al modelo cada vez que se corrige un bug de *fontanería* sería
inviable: cada iteración costaría horas.

**Qué hicimos (Fases C).** Antes de generar nada a escala, construimos una capa de
grabación: `RecordingClient` envuelve cualquier cliente LLM y persiste en disco cada
respuesta, direccionada por el hash del prompt; `ReplayClient` sirve esas respuestas sin
tocar el modelo. Con temperatura 0, **cualquier re-ejecución posterior es offline,
determinista y gratuita**. Los modelos corren en local vía Ollama, de modo que el coste de
nube es cero por diseño.

En su momento esto pareció mera higiene de ingeniería. Resultó ser la decisión que hizo
posible iterar: como se verá en §2.7, un bug que afectaba a 133 respuestas se corrigió y se
regeneraron los once menús completos en **0,2 segundos y sin GPU**, reproduciendo las
respuestas ya grabadas.

### 2.3 El piloto F1: la maquinaria funciona, el modelo no

**Qué intentamos.** Un piloto de calidad de extremo a extremo sobre un único concepto
(`OEB070$`, canalización de polietileno) con el modelo `llama3.1:8b` (Ollama, temperatura 0,
semilla 7). El objetivo era validar los cuatro criterios de la propuesta: español
gramatical, preservación del significado paramétrico, ejes nuevos distinguibles, y metadatos
fieles.

**Por qué falló.** La maquinaria produjo correctamente 48 variantes, sus metadatos de
trazabilidad y una cola de revisión al 100 %. Pero al *leer* el texto renderizado, de 43
modificaciones distintas **solo entre 6 y 8 superaban el listón de calidad**. El fallo
dominante era la **deriva semántica del modelo** en las reescrituras de variables de texto:
`llama3.1:8b` no comprimía ni parafraseaba, sino que colapsaba un valor de parámetro sobre
otro distinto.

**Ejemplos.**

| Tipo | Original | Propuesta del modelo | Problema |
|------|----------|----------------------|----------|
| paráfrasis | «Diurno Excepcional» | «Día normal» | descarta el cualificador *Excepcional* y añade *normal* |
| paráfrasis | «Nocturno» | «Bajo la luz de la luna» | registro inadmisible en un catálogo técnico |
| paráfrasis | «Volumen relevante» | «Volumen de excavación» | cambia magnitud por tipo — no equivalente |

**Qué hicimos.** Registramos el veredicto —`llama3.1:8b` fue adecuado para *des-arriesgar el
proceso*, pero inadecuado como modelo de generación— y fijamos la secuencia de modelo:
probar **`phi4:latest`** (14 B) primero, con Claude (API nativa de mensajes) como reserva si
la calidad no bastaba. El piloto, además, destapó dos hallazgos más profundos que se tratan
por separado a continuación.

### 2.4 El descubrimiento del doble encoding *resumen*/*texto*

**Qué creíamos.** Una primera lectura del piloto sugería una regla limpia: las mutaciones L1
(valores de parámetro) cambian solo el *texto*, las L2 (variables de texto) cambian solo el
*resumen*.

**Por qué esa regla era falsa.** El comportamiento real depende de **cómo referencia cada
plantilla a cada eje**, y las dos plantillas de `OEB070` leen los mismos ejes de *fuentes
distintas*:

```
RESUMEN:  …canalización de $A tubo(s)… con topo bajo vías ($L(%B)/$M(%C)/$N(%D))
TEXTO:    …canalización de $A tubo(s)…
          Trabajo: $B   Banda de mantenimiento: $C   Condiciones de ejecución: $D
```

El eje B (TRABAJO) aparece en el *resumen* a través de la variable de texto `$L(%B)`, pero en
el *texto* a través del valor de parámetro crudo `$B`. Son **dos copias independientes** de la
misma etiqueta. En consecuencia, una modificación de una sola capa toca solo una de las dos
superficies y deja la otra intacta.

**Ejemplo.** La redundancia es visible incluso *antes* de cualquier mutación: en las hojas
originales, el eje «banda de mantenimiento» se renderiza como `i >==5 horas` en el *resumen*
(desde `$M`, con una errata del catálogo fuente) pero como `i >= 5 horas` en el *texto* (desde
`$C`, sin la errata). Las dos superficies ya discrepan en la forma del mismo valor.

**Qué hicimos.** Esto obligó a reencuadrar qué es una variante «que preserva el significado
del *par* consulta+documento». Decidimos (a) extender el mutador para **coordinar** la
reescritura del valor de parámetro con la de su variable-gemela cuando el eje tiene
representación doble *indexada* (`$L(%B)` ↔ `$B`), de modo que ambas superficies cambien a la
vez; y (b) aceptar como válida, *por diseño*, la variabilidad de una sola superficie cuando
las dos variables son redacciones independientes que el autor del catálogo introdujo a
propósito (etiqueta corta frente a frase larga descriptiva). Esta segunda familia de variantes
corresponde precisamente a la variabilidad *del lado de la consulta* que la propuesta
contempla como línea de trabajo, y queda registrada como tal en los metadatos.

### 2.5 El no-op silencioso de L2

**Qué intentamos.** Aplicar mutaciones a las variables de texto (paráfrasis, expansión,
compresión) de forma sistemática sobre todos los conceptos.

**Por qué falló.** Muchas mutaciones **no producían ningún cambio, en silencio**. El
enumerador de objetivos solo reconocía las variables de texto con forma de cadena plana, y
en los datos reales coexisten **tres formas**: lista posicional (`['"Diurno"', …]`), fórmula
con condiciones (`'"normal" * (%B=="a") + …'`) y lista de condicionales. Las dos formas de
lista se saltaban sin error ni aviso. La forma correcta de re-renderizado, además, depende de
cómo referencie la plantilla a la variable.

**Ejemplo.** Sobre `OEB070$`, los objetivos de paráfrasis enumerables eran 0 —el concepto usa
variables en forma de lista— cuando en realidad tenía 9 fragmentos parafraseables. El sistema
informaba de «nada que mutar» y seguía adelante.

**Qué hicimos (Sprint 26, `l2_repr`).** Un adaptador consciente del estilo de referencia que
convierte las tres formas a una representación enumerable para Stage A y las restaura a su
forma nativa para el re-render. Lo verificamos con una condición estricta: **round-trip byte a
byte** sobre las 4 608 hojas de `OEB020$` sin mutar (el corpus regenerado debe ser idéntico al
original si no se aplica ninguna modificación). Tras el adaptador, los objetivos de paráfrasis
enumerables pasaron de 20 a 31 en un concepto y de 0 a 9 en otro. Nada vuelve a saltarse en
silencio: cada variable produce una entrada en un informe con su categoría.

### 2.6 Cambio de estrategia: revisión «menú primero»

**Qué intentamos originalmente.** Generar el corpus completo y después revisar una muestra
estratificada del *output* renderizado.

**Por qué no escalaba.** El output son cientos de miles de líneas renderizadas. Revisar una
muestra representativa de ítems finales, con todas sus combinaciones de parámetros, es
intratable para una sola persona, y además revisa muchas veces la misma reescritura (el
mismo valor «Diurno» reescrito aparece en decenas de conceptos).

**Qué hicimos (Sprints 37–38).** Invertimos el flujo. La revisión pasa a operar sobre la
**regla**, no sobre el resultado:

1. **Deduplicación de objetivos** a nivel de capítulo: un valor como «Diurno» que aparece en
   20 conceptos se revisa **una sola vez**. En el subconjunto OEB esto redujo los objetivos
   de 3 847 a 562 aplicando el gate de aplicabilidad — un **ahorro del 83 %**.
2. El modelo propone **10 alternativas por objetivo único**.
3. Se emiten dos ficheros por tipo de reescritura: un **JSONL** legible por máquina y un
   **Markdown con casillas** para la revisión humana (marcar `[x]` aprueba; rechazo por
   defecto).
4. Un *parser* traduce las casillas marcadas a ficheros de veredicto estructurados que
   consume el muestreador.

### 2.7 Los artefactos de los datos reales

**Qué intentamos.** La primera pasada de generación en vivo con `phi4:latest` sobre los 25
conceptos del subconjunto OEB (92 min de GPU local, 636 llamadas, 2 918 candidatos). Sobre el
papel, un éxito.

**Por qué falló.** Una comprobación mecánica *antes* de la revisión manual reveló que los
menús estaban incompletos por causas puramente de *fontanería*, no del modelo:

- **La barra invertida del FIEBDC.** El catálogo almacena cada descripción larga como
  `\TEXTO\ … \`. El constructor de prompts mostraba el texto crudo, el modelo copiaba de
  vuelta la `\` inicial dentro de su respuesta JSON, y JSON no admite una barra suelta — de
  modo que el lector **rechazaba la respuesta entera** y marcaba el objetivo como omitido.
  Afectó a **133 de 502 respuestas grabadas**.
- **127 objetivos de `TEXTO` omitidos en silencio**, casi todos descripciones largas — es
  decir, justo las reescrituras que más importan para recuperación.
- Un **timeout de 60 s** insuficiente para prompts que pedían 10 alternativas de golpe.
- Tipos apuntados a valores donde no tienen sentido (sinónimo sobre valores numéricos como
  `1,10 m`, compresión sobre fragmentos de dos palabras).

**Ejemplo.** La respuesta del modelo era correcta —`{"paraphrase": "\Canalización…"}`— pero el
`\` inicial la hacía JSON inválido, así que el objetivo aparecía como «omitido» pese a que el
contenido era bueno.

**Qué hicimos (Sprint 38.5).** Lector tolerante a la barra (solo se intenta tras fallar la
lectura estricta, de modo que nada más cambia), timeout a 5 minutos, filtrado de tipos mal
apuntados antes de preguntar, y reducción de 10 a 3 alternativas en los tipos de baja
variedad. Como **ningún prompt cambió**, pudimos regenerar los once menús **desde los
transcripts grabados: 484 llamadas reproducidas en 0,2 segundos, cero GPU**. Los objetivos de
`TEXTO` en el tipo *omission* pasaron de 18 a 110. Aquí es donde la inversión en
reproducibilidad de §2.2 se pagó por completo. Todas las correcciones llevan tests de
regresión.

### 2.8 La crisis de diversidad

**Qué intentamos.** Con los menús ya recuperados, revisar el tipo estrella para
recuperación: `template_paraphrase`, la reescritura de plantillas completas.

**Por qué falló.** El menú era **aburrido**: diez variaciones casi idénticas de una misma
paráfrasis por objetivo. La métrica lo confirmó — similitud media entre candidatos de un
objetivo (Jaccard de tokens) de **0,76**: prácticamente clones. El diagnóstico tenía cuatro
causas: (1) a temperatura 0 el modelo toma el camino de decodificación más seguro, el
intercambio de sinónimos; (2) pedir «10 ordenadas de mejor a peor» ancla las candidatas 2–10
en la primera; (3) el prompt era todo frenos y ningún acelerador —nunca *pedía* cambio
estructural; (4) un modelo de 14 B se repliega a cambios de palabra ante frases de 150
palabras densas en dimensiones.

**Qué hicimos (Sprints 38.6 y 38.6-B).** Reescribimos por completo el proponente de este
tipo:

- **Rondas × modelos a temperatura 0,8.** Por objetivo, tres rondas con consigna de
  transformación distinta (R1 voz y marco; R2 arquitectura de cláusulas; R3 reestructuración
  libre, prohibiendo los comienzos ya usados) × **dos modelos locales** (`phi4:latest` +
  `qwen2.5:14b`).
- **Enmascarado de invariantes.** Para que la libertad de la temperatura alta no destruyera
  lo intocable, los placeholders y las cantidades se sustituyen por centinelas opacos
  (`[[P1]]`, `[[Q1]]`) antes de generar y se restauran exactos después. La preservación queda
  garantizada por construcción; aun así, la pila completa de validadores vuelve a correr sobre
  el texto restaurado. Verificado: **902 de 902 superficies del catálogo hacen round-trip
  idéntico.**
- **Rescate por remask.** Los modelos «se des-enmascaran» solos (escriben `$A` en vez de
  `[[P1]]` porque el prompt les muestra el token real en la línea de contexto). Un rescate
  vuelve a ocultar el literal cuando aparece exactamente una vez, lo que es demostrablemente
  inocuo.

Resultados frente a los objetivos del sprint:

| Métrica | Base | Objetivo | Logrado |
|---------|------|----------|---------|
| similitud entre candidatos (`p_sim`) | 0,76 | ≤ 0,55 | **0,41** |
| distancia al original (`d_orig`) | 0,41 | ≥ 0,45 | **0,55** |
| candidatos (49 objetivos) | 406 | — | **709** |

**Incidente de entorno (registrado por honestidad).** El primer intento reventó con un error
`CUDA OOM`. La causa no eran los modelos sino una máquina virtual de WSL2 atascada (la RAM del
host había caído a 8,3 de 64 GB con E/S colgada); se resolvió reiniciando Docker/WSL y
adoptando **carga de modelos en dos fases** para no tener ambos residentes a la vez en la GPU
de 24 GB.

### 2.9 La validación y la rúbrica calibrada

**Qué intentamos.** Establecer un criterio de calidad reproducible para aceptar o rechazar
cada reescritura candidata, con separación de roles para que la validación fuera creíble.

**Por qué el primer intento fue insatisfactorio.** Con una rúbrica estricta (v1.1), la pasada
completa sobre 2 811 candidatos aprobó solo el **41,1 %** (1 155 aprobadas / 1 646 rechazadas
/ 10 dudosas). Ese listón, calibrado para exigir preservación semántica fina, resultaba
demasiado severo para lo que es —recuérdese— un benchmark *de estrés*, cuyo propósito es
introducir precisamente la variabilidad que un listón estricto rechaza.

**Ejemplo de la tensión.** El tipo *expansion* produce sistemáticamente colas valorativas
(«garantizando una instalación duradera») que la rúbrica estricta rechaza por añadir
información; pero para un banco de estrés, esa deriva léxica es *ruido útil*, no un defecto.
Caso aparte —y este sí se mantuvo como rechazo— es la deriva de dominio: «Con topo» → «con
topografía» es erróneo, porque en este contexto un *topo* es una tuneladora, no una
topografía.

**Qué hicimos (Sprint 38.7).** El protocolo de validación se documentó tal cual es, sin
inflarlo:

1. **Calibración con sello de independencia.** Los veredictos de Claude sobre 100 ítems se
   sellaron por SHA-256 en git *antes* de recibir los de César (verificado al revelar: el hash
   coincide). César aprobó 100/100 y delegó la revisión con auditoría dirigida.
2. **Rúbrica v2**, calibrada al criterio del propietario del benchmark: *aprobar por
   defecto*; rechazar solo por (a) rotura estructural del render, (b) borrado de más en
   *omission*, o (c) residuo de generación.
3. **Re-juicio de los 1 646 rechazos** bajo v2: 1 444 recuperados, 202 confirmados como
   rechazos (roturas de render verificadas contra los valores reales de los ejes). Resultado
   final: **2 609 aprobadas / 202 rechazadas (92,8 %)**.

La afirmación publicable, expresada con precisión, es: *«filtrado mecánico-estructural
verificado + listón semántico permisivo definido y auditado por el autor»*, no revisión
humana exhaustiva. Se registra así deliberadamente.

### 2.10 La generación del corpus

**Qué intentamos.** Convertir las reescrituras aprobadas en un corpus real. La maquinaria:
una *despensa* (`pantry`) que une menús y veredictos en 1 931 reescrituras aprobadas de 9
tipos (se excluyen *omission* y *new_param* por decisión del autor), un fichero de
presupuestos como configuración, un **muestreador determinista** y un **driver** que emite
reglas, compone, materializa y empaqueta.

**Por qué falló al principio.** Reapareció el villano de siempre —el no-op silencioso— con una
cara nueva. Una reescritura del valor «Diurno» solo debe aparecer en las hojas que
*seleccionan* Diurno; pero una coincidencia textual simple también disparaba en «Diurno
Excepcional», produciendo reescrituras que no reescribían nada. La tasa de no-ops llegaba al
**26 %** en los peores tipos. Un segundo problema fue de rendimiento: la materialización
ingenua, variante a variante, tardaba horas.

**Ejemplo.** El plan asignaba la reescritura «Diurno → Jornada de día» a una hoja cuyo eje
TRABAJO valía en realidad «Diurno Excepcional»; el motor buscaba «Diurno» como subcadena, lo
encontraba dentro de «Diurno Excepcional», y —según el caso— o no cambiaba nada o corrompía el
valor.

**Qué hicimos (Sprint 39).**

- **Compatibilidad hoja↔reescritura por valor exacto:** el muestreador exige coincidencia del
  par `(eje, valor)` tomado del parquet original, con un *fallback* textual por frontera de
  palabra. La tasa de no-ops cayó a **0,5 %**; el filtro de no-ops del driver queda como
  salvaguarda contada.
- **Materialización agrupada y paralela:** las variantes que comparten `(concepto, conjunto de
  reglas)` se materializan **una sola vez por grupo** en un pool de procesos. El tiempo pasó de
  horas a **~60 min con 8 workers**, con salida byte-idéntica independientemente del número de
  workers (fijado por test).
- **Requisito del checkpoint (2026-09-02):** todo ítem de la condición `all_combined` debe
  reescribir **ambas plantillas** (una `template_paraphrase` de RESUMEN y otra de TEXTO). Esto
  forzó una regeneración y elevó la distancia media de token en `all_combined` de 73,7 a 90,0.

**Resultado.** El corpus piloto (release `6b52053`) contiene **8 687 ítems de 8 734
planificados**; 45 no-ops descartados (0,5 %), 2 duplicados exactos, y **cero fallos duros** de
emisión, composición o residuo de placeholders. Dos ejecuciones completas resultaron **byte a
byte idénticas** (SHA-256 verificados). El determinismo está comprobado a tres niveles: plan,
driver y corpus completo.

---

## 3. Estado actual del corpus piloto

| Métrica | Valor |
|---------|-------|
| Ítems producidos | **8 687** (de 8 734 planificados) |
| Condiciones | 10 — nueve `single_<tipo>` + `all_combined` |
| Reescrituras aprobadas en despensa | 1 931 (9 tipos; *omission* y *new_param* excluidos) |
| Descartados | 45 no-ops (0,5 %), 2 duplicados exactos |
| Fallos duros | 0 |
| Reproducibilidad | dos ejecuciones byte-idénticas (SHA-256) |
| Tiempo de generación | ~60 min con 8 workers (CPU pura, sin LLM) |
| Suite de tests | 1 092 verdes |

**Déficits aceptados a conciencia.** Dos tipos finos quedan por debajo de su objetivo por
tener una despensa pequeña bajo el tope de reutilización de 20× que protege la diversidad
lingüística: `unit_expansion` 373/650 y `unit_conversion` 209/350 (márgenes del 95 % en el
peor caso ≈ ±5,1 / ±6,8). Su regeneración está en el backlog del Sprint 40.

**Artefactos documentados como estrés.** Algunos subproductos de la despensa se mantienen sin
veto, documentados y trazables por ítem a través del *sidecar* de modificaciones: «tubos
tubos» (~376 ítems), «mm mm» (~280) y «con topo» → «con topografía» (~245, deriva semántica).
El análisis posterior puede segmentarlos si conviene.

---

## 4. Lecciones metodológicas

1. **El fallo silencioso es el adversario recurrente.** Tres de los peores episodios
   —mutaciones que no mutaban (§2.5), objetivos omitidos sin ruido (§2.7), reescrituras no-op
   (§2.10)— comparten firma: el sistema seguía adelante sin avisar. La respuesta constante fue
   hacerlo **fallar de forma ruidosa** (verificación de residuos que lanza excepción,
   round-trips byte a byte, informes por variable) en lugar de tolerar el silencio.

2. **Grabar es poder reproducir.** Direccionar por hash cada respuesta del LLM convirtió una
   corrección que habría costado ~90 min de GPU en una regeneración de 0,2 s. La
   reproducibilidad no fue un lujo: fue lo que hizo posible iterar sobre errores de datos
   reales sin volver a pagar el modelo.

3. **Coste de nube cero.** Todo el corpus se generó con modelos locales (`phi4:latest`,
   `qwen2.5:14b`) vía Ollama. La generación final del corpus es CPU pura, sin ningún LLM en el
   bucle.

4. **El humano en el bucle debe estar calibrado y declarado.** La calidad no la fija una
   rúbrica abstracta sino la vara del autor del benchmark, sellada criptográficamente antes de
   la revisión y auditada de forma dirigida. La afirmación que se publica describe exactamente
   ese protocolo, ni más ni menos.

5. **El catálogo real es menos regular que el modelo mental.** El doble encoding
   *resumen*/*texto* (§2.4) y las tres formas de variable de texto (§2.5) no estaban en el
   diseño inicial; emergieron de los datos. Operar sobre la gramática obliga a auditarla, y esa
   auditoría fue la fuente de la mayoría de las correcciones.

---

## 5. Por qué podemos pasar a la fase de recuperación

Lo técnicamente arriesgado —construir un corpus sintético que preserve el significado
paramétrico, con trazabilidad por ítem y reproducibilidad byte a byte— **está hecho y
verificado**. El release vive en `data/synthetic/processed/` y se consume desde el repositorio
hermano `bc3cat-retrieval` a través de la API congelada `synthetic.loaders`: dos ficheros (el
parquet de ítems y el *sidecar* JSONL de modificaciones), el *join* por `original_key` para la
evaluación pareada, y la condición derivable sin ambigüedad a partir del recuento de
modificaciones. **Nada de lo que queda pendiente bloquea empezar a medir.**

Las preguntas que motivaron todo el proyecto —¿qué transformación degrada más a cada familia
de recuperadores? ¿sobrevive el abismo entre BM25 y los modelos densos cuando cambia la
redacción pero se preserva el significado?— disponen por fin de un banco de pruebas sobre el
que ejecutarse. Esa es la fase que este trabajo desbloquea.

### Próximos pasos

- **Iniciar la evaluación de recuperación.** `bc3cat-retrieval` puede consumir el corpus
  piloto ya; ver [`HANDOFF.md`](HANDOFF.md) para el esquema y el *join* pareado.
- **Sprint 40 — escalado.** De los 25 conceptos del subconjunto OEB a los 451 de OBRA CIVIL,
  con la misma maquinaria y menús nuevos a escala; incluye las correcciones diferidas (eliminar
  la barra del FIEBDC en la construcción del prompt, sustituir el LLM por aritmética en
  conversión de unidades y número-a-texto) y la regeneración de los tipos finos.
- **F4 — validación de calidad.** Revisión estratificada de ítems renderizados y
  `QUALITY_REPORT.md`.

---

## Referencias internas

- [`RESEARCH_PROPOSAL.md`](RESEARCH_PROPOSAL.md) — objetivos, motivación y taxonomía de
  modificaciones.
- [`RESEARCH_PROTOCOL.md`](RESEARCH_PROTOCOL.md) — hoja de ruta de implementación y contrato de
  etapas.
- [`RESEARCH_LOG.md`](RESEARCH_LOG.md) — registro de decisiones y resultados por sprint.
- [`F1_FINDINGS.md`](F1_FINDINGS.md) — análisis del piloto F1 (§2.3–§2.4 de este informe).
- [`STATUS_2026-09-02.md`](STATUS_2026-09-02.md) — informe de estado que este documento amplía.
- [`sprints/SPRINT_39_corpus_report.md`](sprints/SPRINT_39_corpus_report.md) — detalle por
  condición del corpus piloto.
- [`HANDOFF.md`](HANDOFF.md) — memorando de traspaso a `bc3cat-retrieval`.
