# Análisis del uso de IA

Responde a **4.1.4.I.16**: utiliza, analiza y mejora críticamente el código generado mediante
herramientas de IA. También alimenta 4.1.5.I.20 (la auditoría de seguridad con IA está en
[`AUDITORIA.md`](AUDITORIA.md)).

## Resumen

| Fuente | Adoptados | Modificados | Descartados | Total |
|---|---|---|---|---|
| 1. Requerimientos, modelos y planificación (asistente) | 2 | 3 | 3 | 8 |
| 2. Iteraciones independientes sobre el modelo de clases | 0 | 5 | 11 | 16 |
| 3. Código y pruebas (asistente) | 4 | 16 | 2 | 22 |
| 4. Auditoría de seguridad independiente | 4 | 12 | 1 | 17 |
| **Total** | **10** | **36** | **17** | **63** |

**Adoptado:** se usó tal como vino, después de verificarlo con una prueba o con una medición.
**Modificado:** se tomó la idea y se cambió la forma, o se corrigió un error que encontró una prueba.
**Descartado:** no se usó; el motivo está en la [sección de descartes](#descartados-17).

## Cómo se usó la IA

- **Asistente de desarrollo:** Claude Code (modelo Claude Opus), dirigido por Leo con prompts que
  quedaron registrados íntegros, con fecha y categoría, en el registro de trabajo del informe.
  - **Produjo:** los requerimientos, los diagramas, el código y las pruebas.
  - **Decidió Leo:** el alcance, el modelo de clases (aprobado el 2-oct), lo que va al repositorio y
    lo que se entrega.
- **Segunda opinión independiente:** en dos momentos se le pidió el mismo trabajo a un agente de Claude
  nuevo, que no conocía el proyecto. Recibió solo un prompt y, cuando correspondía, el caso o el código.
  Sirve para contrastar el trabajo del asistente con una mirada que no lo comparte. Las respuestas se
  guardaron íntegras, sin editar:
  - Diseño del modelo de clases, con un prompt pobre y uno con el esquema CLARO (Contexto, Labor,
    Alcance, Rol y Orden): [`ia/modelo_iteracion_1_prompt_pobre_respuesta.md`](ia/modelo_iteracion_1_prompt_pobre_respuesta.md)
    y [`ia/modelo_iteracion_2_prompt_claro_respuesta.md`](ia/modelo_iteracion_2_prompt_claro_respuesta.md).
  - Auditoría de seguridad del código: [`ia/auditoria_seguridad_ia.md`](ia/auditoria_seguridad_ia.md).
- **Ningún resultado se aceptó por haberlo producido la IA.** Todo pasó por al menos una de estas
  verificaciones:
  - `herramientas/trazabilidad.py`: el catálogo de requerimientos contra el caso.
  - `herramientas/uml_vs_codigo.py`: el diagrama contra el código, con 0 diferencias.
  - La autoverificación de `viajes.py`: las reglas R1 a R17.
  - `herramientas/driver.py`: una sesión real del menú, con los dos roles.
  - `pruebas/prueba_rubrica.py`: una afirmación por indicador.
  - Bandit, pip-audit y SonarCloud.
  - **Pruebas de mutación:** romper a propósito una regla y comprobar que alguna prueba falla.
    Detectaron 46 de 46 mutaciones en total.

## 1. Requerimientos, modelos y planificación (asistente)

| ID | Lo que produjo la IA | Decisión | Análisis y fundamento | Dónde quedó |
|---|---|---|---|---|
| R-01 | Catálogo de 42 RF, 16 RNF (ISO/IEC 25010) y 8 Won't, con MoSCoW y criterios de aceptación | **Modificado** | Se auditó contra las diapositivas del docente (bloque 6). Siete RF tenían dos acciones en uno: se separaron en cuatro RF nuevos (RF-DES-10, RF-PAQ-11, RF-SEG-12 y RF-SEG-13) y se reescribieron tres (RF-SEG-01, RF-PAQ-09 y RF-RES-08). El catálogo quedó en 46 RF | Informe, cap. 2 |
| R-02 | 13 supuestos para los vacíos del caso | **Modificado** | Faltaban cuatro vacíos que el docente nombra. Se agregaron S-14 a S-16: migración, destino no disponible dentro de un paquete vendido y quién ve los datos personales | Informe, §2 |
| R-03 | Casos de uso con tres actores, incluido «Visitante» | **Descartado** | El docente pide dos actores. El visitante no tiene datos que el sistema guarde, y ver la oferta sin sesión quedó como supuesto (S-09) | Informe, §3.1 |
| R-04 | Un primer sprint «de análisis» | **Descartado** | «No existe la iteración de análisis» (docente): cada sprint debe entregar algo ejecutable. Pasó a ser un período de preparación declarado con sus horas | Informe, §4.3 |
| R-05 | Leo como Product Owner | **Modificado** | En Scrum el PO representa al cliente: son los socios, y el docente responde por ellos. Leo es Scrum Master, desarrollador y responsable de datos y de seguridad | Informe, §4.1 |
| R-06 | Figuras en PlantUML | **Descartado** | Impresas tenían letra de 4,6 a 5,9 pt. Se rehicieron con coordenadas fijas (`svgkit.py`) a 7,5 pt, como el informe 4+1 de Modelamiento | `diagramas/` |
| R-07 | Diagrama de clases (`clases.puml`) | **Adoptado** | Leo lo aprobó el 2-oct. Después se modificó cinco veces al escribir el código, por las decisiones 7 a 12 del informe, y cada cambio está registrado | `diagramas/clases.puml` |
| R-08 | `trazabilidad.py`, verificador del catálogo | **Adoptado** | Detectó 9 de 9 mutaciones del capítulo de requerimientos y 5 de 5 del backlog | Informe (no viaja al repo) |

## 2. Iteraciones independientes sobre el modelo de clases

El diseño del modelo se pidió dos veces a un agente sin contexto: con un prompt pobre y con un prompt
CLARO que adjuntaba el caso. Cada propuesta se comparó con el modelo del proyecto.

| ID | Lo que propuso la IA | Decisión | Fundamento técnico | Cambio en el modelo |
|---|---|---|---|---|
| P-1 a P-7 | Prompt pobre: clase contenedora `AgenciaViajes`, cupo como contador, precio en `float`, paquete con 1 o más destinos, estados de pago, `Destino.pais`, sin usuarios ni autenticación | **Descartados (7)** | Cada uno contradice una regla del caso: R3, R13, R14, el alcance §6 o el encapsulamiento. El detalle de cada uno está en la sección de descartes | Ninguno |
| C1 | `ReglaNegocioError(regla, mensaje)` con `regla` público | **Modificado** | La idea es buena: el menú distingue el error esperado del inesperado, y el código R# une cada rechazo con su regla. Pero `regla` pasa a privado con `obtenerRegla()`, porque el modelo declara todos los atributos privados | Clase nueva, decisión 7 |
| C2 | `hoy` como parámetro en lugar de `date.today()` adentro | **Modificado** | Hace determinista la prueba de R15. Se le dio un valor por omisión para que el menú no tenga que pasarlo | Decisión 8 |
| C3 | Margen como `Decimal` | **Modificado** | El problema que señala es real: el modelo decía `margen: float`. Pero alcanza con un entero (porcentaje) y aritmética entera redondeada al peso, sin otra biblioteca | Decisión 9 |
| C4 | Clase `Rut` como objeto valor que se oculta en las trazas | **Modificado** | La idea vale (que el RUT no se filtre, R17), pero no hace falta otra clase: `Cliente.__repr__` no muestra el RUT ni el teléfono, y una prueba lo verifica | `Cliente.__repr__` |
| C5 a C8 | Enumeración `Accion`, clase `Catalogo`, `Paquete.reservar()`, sin anulación | **Descartados (4)** | Ver la sección de descartes | Ninguno |
| C9 | Nombre de destino único y normalizado, con `UNIQUE` en la base | **Modificado** | La normalización ya estaba en RF-DES-02, y era más amplia, porque también ignora las tildes, que la IA no consideró. Se tomó la idea de poner el `UNIQUE` sobre la columna normalizada | Tabla `destino` |
| C10 | `Usuario` abstracta, precio fijado al publicar, total guardado, cupo calculado, agregación 2..5, Argon2id, Fernet | Coincidencias | Dos diseños hechos por separado llegan a lo mismo: confirma las decisiones 1 a 6. No se cuentan como contribución | Ninguno |

## 3. Código y pruebas (asistente)

El código lo escribió el asistente. Este es el registro de cómo se validó: qué se adoptó porque pasó sus
verificaciones, y qué error tenía y cómo se encontró.

### Adoptados después de verificarlos (4)

| ID | Pieza | Cómo se validó |
|---|---|---|
| A-01 | Reserva con `BEGIN IMMEDIATE` contra la sobreventa (R14, RNF-FIA-02) | Prueba con dos conexiones simultáneas por el último lugar: solo una reserva queda. La mutación que quita el `BEGIN IMMEDIATE` se detecta |
| A-02 | Precio con aritmética entera `(suma × (100 + margen) + 50) // 100` | 310.000 + 120.000 con 20 % da 516.000, como dice el criterio de RF-PAQ-04. La mutación que usa `float` se detecta |
| A-03 | Contador de intentos y bloqueo en una sola sentencia SQL | Prueba de 5 fallos que bloquean y de un bloqueo que sobrevive a cerrar el programa. La mutación que bloquea a los 6 se detecta |
| A-04 | `normalizar()` sin tildes, mayúsculas ni espacios dobles | «valle del  elqui» y «Valle del Elquí» se rechazan. La mutación que conserva las tildes se detecta |

### Modificados: errores y mejoras encontrados al verificar (16)

| ID | Lo que tenía el código generado | Cómo se detectó | Corrección |
|---|---|---|---|
| K-01 | Argon2id con sus valores por omisión: 98 ms por verificación, bajo los 0,1 s de RNF-REN-02 | Medición | `time_cost=4`, unos 120 ms |
| K-02 | El mensaje de error del teléfono traía un número de ejemplo | La prueba de RF-SEG-13 («el mensaje no repite el dato») lo detectó | Mensaje sin número |
| K-03 | Ninguna clase exponía su id, y `Paquete` no podía leer el de sus destinos (Python oculta los `__privados` entre clases) | Al escribir `Paquete` | `obtenerId()` en el modelo (decisión 10) |
| K-04 | El historial de reservas se armaba con el id de la reserva en lugar del id del cliente (`usuario` y `reserva` tienen columna `id`) | **Error real.** El driver del menú: una cliente no pudo anular su propia reserva | Alias `reserva_id`, y una prueba por el camino del historial |
| K-05 | En una instalación nueva, el primer cliente no podía registrarse: la clave se creaba solo si «no había usuarios», y el primer administrador ya existía | **Error real y grave.** La prueba por indicador. La autoverificación y el driver no lo veían porque preparaban la clave de antemano | La condición pasó a ser «no hay datos cifrados». Las pruebas recorren la instalación real |
| K-06 | Con `BEGIN IMMEDIATE` en cada conexión, una conexión abierta dentro de otra quedaba esperando | El driver: el registro de un cliente se colgaba | Las búsquedas y el cifrado se hacen con la conexión cerrada |
| K-07 | SQL armado con f-string (solo constantes, no explotable) | Bandit B608, contra RNF-SEG-03 | Consultas literales y `json_each(?)` |
| K-08 | `uml_vs_codigo.py` no veía los atributos públicos | Prueba de mutación | Revisa `self.x` públicos |
| K-09 | El comparador tenía una regex superlineal y funciones demasiado complejas | SonarCloud | Lectura por líneas y funciones chicas, con 8 de 8 mutaciones detectadas |
| K-10 | Un guion desalineado del driver pasaba sin error, porque solo buscaba «Traceback» | Al leer la salida | El driver exige una lista de resultados esperados |
| K-11 | Cuatro valores esperados mal calculados en las pruebas (552.000, 5 reservas, el id que SQLite reutiliza y un paquete de apoyo con un destino) | Las propias pruebas fallaron | Valores corregidos a mano, con su cálculo |
| K-12 | La prueba de la clave perdida borraba y reescribía el archivo de la clave | SonarCloud S2083 (falso positivo, pero el patrón sobraba) | La prueba apunta a una ruta inexistente |
| K-13 | La prueba exigía 50 ms como mínimo para Argon2id | El CI: un servidor de GitHub tardó 48 ms | Se exige el costo del hash (64 MiB y t=4), no un tiempo que depende del equipo |
| K-14 | El registro validaba el RUT, el correo y el teléfono recién al final | Al leer la sesión del driver | Validación por campo en el menú (primera de tres capas) |
| K-15 | «Editar paquete» pedía todos los datos antes de avisar que estaba publicado | Al leer el menú | Aviso apenas se elige el paquete |
| K-16 | Las primeras pruebas preparaban la clave por fuera y escondían el orden real de una instalación | Lección de K-05 | Toda prueba parte como el sistema real |

## 4. Auditoría de seguridad independiente

17 hallazgos: **4 adoptados, 12 modificados y 1 descartado**. La validación de cada uno, con las
mutaciones que lo vigilan, está en [`AUDITORIA.md`](AUDITORIA.md).

- Antes de actuar, se comprobaron por experimento cuatro afirmaciones: H-08, H-09, H-12 y H-14. Las
  cuatro eran ciertas y las tres primeras eran errores reales.
- La IA no vio que su propia recomendación H-08 dejaba conexiones anidadas esperando: es el K-06 de
  arriba.

## Descartados (17)

| ID | Propuesta | Por qué se descartó |
|---|---|---|
| R-03 | Actor «Visitante» | El docente pide dos actores; ver la oferta sin sesión es un supuesto (S-09) |
| R-04 | Sprint de análisis | No entrega nada ejecutable; se declaró como preparación |
| R-06 | Figuras PlantUML | Ilegibles impresas (4,6 a 5,9 pt) |
| P-1 | Clase `AgenciaViajes` que guarda listas de todo | Ninguna frase del caso la origina; concentra todo (baja cohesión) y en memoria se pierde al cerrar |
| P-2 | Cupo como contador que se descuenta | Es la causa de las 6 reservas sobre el cupo (P-02): un contador aparte se desincroniza; R14 lo define como un cálculo |
| P-3 | Precio en `float` que se recalcula | R13 exige el total fijo; el peso no tiene decimales |
| P-4 | Paquete con uno o más destinos | R3: entre dos y cinco |
| P-5 | Estados `PENDIENTE` y `CONFIRMADA` | Suponen el pago, fuera del alcance (§6) |
| P-6 | `Destino.pais` | El caso describe el destino por su zona |
| P-7 | Sin usuarios y con atributos públicos | Deja fuera el módulo de seguridad y el encapsulamiento |
| C5 | Enumeración `Accion` para los permisos | Con dos roles, un conjunto fijo de textos validados basta; la enumeración agrega un elemento sin cambiar el comportamiento |
| C6 | Clase `Catalogo` | Ninguna frase del caso le da comportamiento; sus métodos ya están en `Destino` y `Paquete` |
| C7 | `Paquete.reservar()` | Equivale a `Reserva.reservar(paquete, …)`: las reglas ya se validan en un solo lugar |
| C8 | Sin anulación de reservas | El modelo la declara (S-01): completa el CRUD de la reserva (G.15) |
| K-17 | `intentosFallidos` como atributo del objeto | El contador vive solo en la base; nadie lo leía (SonarCloud S4487). Decisión 11 |
| K-18 | Método `Paquete.precio_por_persona()` | Sobraba: `calcular_precio()` y la representación del paquete ya cubren el uso; el comparador lo marcó como no dibujado |
| H-03 | Desactivar cuentas y suprimir datos | Fuera del alcance (§6) y exige cambiar el esquema y el modelo; declarado como riesgo aceptado en `AUDITORIA.md` §3 |

## Qué se aprendió del uso de la IA

1. **El prompt CLARO cambia el resultado.** El prompt pobre produjo 7 propuestas que contradecían el caso,
   y todas se descartaron. El CLARO produjo 5 ideas que se aprovecharon modificadas, más 7 coincidencias
   con el modelo del proyecto.
2. **La IA acierta en lo que se le pregunta y falla en las consecuencias.** La auditoría encontró
   errores reales, pero no vio el efecto de su propia corrección (K-06).
3. **Los errores más graves los encontraron las pruebas que recorren el sistema como lo usa una
   persona:** K-04 y K-05. Las pruebas que preparaban el escenario por fuera los escondían.
4. **Una medición vale más que un valor por omisión:** K-01 y K-13.
