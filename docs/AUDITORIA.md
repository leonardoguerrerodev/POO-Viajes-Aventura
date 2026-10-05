# Auditoría de seguridad · Viajes Aventura

Responde a **4.1.5.I.20**: evalúa y optimiza la seguridad del sistema utilizando criterios técnicos y
apoyo de IA. Sábado 3 de octubre de 2026; riesgos declarados cerrados el lunes 5 de octubre (§2.5).

| | |
|---|---|
| Alcance | `viajes.py` (dominio y persistencia), `main.py` (menú), dependencias e historial del repositorio |
| Código auditado | commit `525ab10`, antes de cualquier corrección |
| Código corregido | commit `fcfa4f9` y siguientes, rama `feature/auditoria` integrada a `main`; cierres del 5-oct en `0a7b54e` |
| Método | «Auditoría de seguridad y privacidad» (método propio, fases 5, 7, 9, 14 y 15), en su versión para un proyecto de una persona |
| Herramientas | bandit 1.9.4 (análisis estático), pip-audit 2.10.1 (dependencias), búsqueda de secretos en el historial de git, SonarCloud (en cada envío), revisión pedida a la IA |
| Revisión con IA | Claude, en un agente nuevo que solo conocía el prompt y los dos archivos. Prompt y respuesta íntegros en [`ia/auditoria_seguridad_ia.md`](ia/auditoria_seguridad_ia.md) |
| Fuera de alcance | No hay interfaz web ni APIs: XSS, CSRF y cabeceras HTTP no aplican |

## Resumen

| Fuente | Hallazgos | Corregidos | Declarados (riesgo aceptado, con motivo) |
|---|---|---|---|
| Revisión con IA | 17 (0 críticos, 0 altos, 4 medios, 10 bajos, 3 informativos) | 17: las partes que el 3-oct quedaron declaradas se cerraron el 5-oct (§2.5) | Ninguno. La supresión pedida por el cliente es una decisión de alcance (W-08), no un riesgo abierto |
| bandit | 6 B608 (posible inyección SQL) y 93 B101 (`assert`) | Los 6 B608. Desde el 5-oct el producto (`viajes.py`, `main.py`) tiene **0 observaciones** de cualquier tipo | Ninguno: los `assert` y el `subprocess` de las mutaciones están solo en `pruebas/verificar.py` |
| pip-audit | 0 vulnerabilidades en las 5 dependencias | | |
| Secretos en el historial | 0 (ningún `.env`, `.db` ni clave subida, en ningún commit) | | |
| SonarCloud | 8 observaciones de las pruebas nuevas | 8 | |
| Auditoría final (corrector independiente y revisión propia, 3-oct 22:00) | 10 de seguridad y privacidad (§2.3) | 10: el plazo de conservación quedó en `PRIVACIDAD.md` | |
| Cierre de los riesgos declarados (5-oct) | 13 riesgos de §3 reevaluados | 11 cerrados, con su prueba y su mutación (§2.5) | 2 límites del modelo de amenazas, cada uno con su mitigación (§3) |

De la IA: **4 adoptados tal como vinieron, 12 modificados y 1 descartado**. Cada decisión, con su
fundamento, está en la sección 2. Tres hallazgos eran errores reales del código y se comprobaron por
experimento antes de corregirlos: H-08, H-09 y H-12.

**Modelo de amenaza.** La aplicación corre con una cuenta del sistema operativo en el equipo de la
oficina (S-11). Los controles internos (bloqueo, roles, enmascarado) protegen frente a quien usa el
menú. El cifrado protege frente a una copia de la base que sale del equipo sin la clave: un respaldo,
un archivo enviado por correo o el repositorio.

## 1. Lo que salió limpio

| Revisión | Evidencia |
|---|---|
| Inyección SQL | Todo dato del usuario va como parámetro `?`. Después de la corrección de los B608 tampoco hay SQL armado con texto: cada consulta es una constante literal y la lista de ids viaja como un solo parámetro JSON (`json_each`). bandit: 0 B608 |
| Dependencias | `pip-audit -r requirements.txt --require-hashes`: «No known vulnerabilities found». Las 5 dependencias están fijadas con `==` y con el hash de cada archivo publicado |
| Secretos | `git log --all` no tiene `.env`, `.db`, `.pem` ni `.key`, ni patrones de claves (Fernet, GitHub, AWS, llaves privadas) |
| Contraseñas | Argon2id (argon2-cffi), 64 MiB y 4 pasadas, sal propia, rehash al entrar, tope de 128 caracteres, mismo mensaje y misma demora en los tres fallos. La IA lo marcó como bien hecho y la prueba por indicador lo verifica |
| Control de acceso | El dominio revisa el permiso aunque el menú no exista; la anulación exige ser el titular en el objeto y en el `WHERE` del SQL |
| SonarCloud | 0 *hotspots* de seguridad en todos los análisis |

## 2. Hallazgos y decisiones

Severidad según la IA. «Decisión» clasifica la recomendación de la IA: **adoptada** (tal como vino),
**modificada** (se tomó la idea y se cambió la forma, con el motivo) o **descartada**.

| ID | Sev. | OWASP 2025 | Hallazgo | Decisión | Qué se hizo y por qué | Prueba que lo vigila |
|---|---|---|---|---|---|---|
| H-01 | Media | A04 | La clave Fernet vivía en `.env` dentro de la carpeta del proyecto, junto a la base | **Modificada** | La clave pasa a `~/.config/viajes-aventura/clave.env`, fuera del proyecto, con la carpeta en 0700 y el archivo en 0600. Si un respaldo la restaura con permisos abiertos, se cierran solos en vez de rechazarla como proponía la IA: rechazarla dejaría a la agencia sin poder atender. Se verificó que `.env` y `*.db` nunca estuvieron en el historial y se agregaron `*.db-wal` y `*.db-shm` al `.gitignore` | `verificar.py`, sección «datos» |
| H-02 | Media | A09 | No había registro de auditoría | **Modificada** | Tabla `auditoria(fecha_utc, usuario_id, accion, detalle)`, escrita en la misma transacción de cada operación (si la operación se deshace, su registro también). Hoy registra 27 acciones: catálogo, paquetes, reservas, cuentas e inicios de sesión (correcto, fallido, bloqueo, rechazado por bloqueo, correo inexistente). Sin la columna «resultado» que proponía la IA: solo se registra lo que ocurrió. El detalle lleva ids y montos, nunca RUT, teléfono, correo ni contraseña; del correo inexistente no se guarda el correo, porque puede ser de otra persona | `verificar.py`, sección «reglas» (`_verificar_auditoria`) |
| H-03 | Media | A07 | No se puede desactivar una cuenta ni suprimir los datos de un cliente | **Modificada** (5-oct) | Desactivar cuentas: `Administrador.desactivarCuenta()` (§2.5). La supresión pedida por el cliente se atiende ante los socios (W-08, `PRIVACIDAD.md`) | `verificar.py`, sección «credenciales» |
| H-04 | Media | A06 | Listar reservas descifraba el RUT y el teléfono de todos los clientes | **Modificada** | En vez de una consulta liviana solo para ese listado, `Cliente` guarda el RUT y el teléfono **cifrados también en memoria** y los descifra solo para enmascararlos. Ninguna lectura de la base descifra nada, y un registro alterado ya no impide listar a los demás | sección «reglas» (RUT alterado: se entra y se lista) |
| H-05 | Baja | A07 | Iniciar sesión descifraba los datos antes de verificar la contraseña | **Modificada** | Resuelto por el mismo cambio de H-04 | ídem |
| H-06 | Baja | A07 | Enumeración de correos por el registro; señuelo calculado en el primer intento; todo `IntegrityError` se mostraba como «correo repetido» | **Modificada** | El señuelo se calcula al cargar el módulo y solo el `UNIQUE` del correo se traduce a R9. Desde el 5-oct, el registro se pausa tras 5 correos repetidos en 10 minutos (§2.5) | sección «reglas» |
| H-07 | Baja | A07 | El bloqueo se decidía con el objeto leído antes, en otra conexión | **Adoptada** | El estado del bloqueo se vuelve a leer dentro de la transacción del intento | sección «reglas» (bloqueo) |
| H-08 | Baja | A06 | En su modo por omisión, `sqlite3` abre la transacción en la primera escritura: «consultar y después escribir» no era atómico, aunque el comentario lo afirmaba | **Modificada** | **Error real, comprobado por experimento** (`in_transaction` es `False` después de un `SELECT`). `conectar()` abre siempre con `BEGIN IMMEDIATE` explícito. La IA no advirtió la consecuencia: con IMMEDIATE, una conexión abierta dentro de otra se queda esperando. Había dos casos (`Paquete._listar` y el cifrado dentro de `_insertar`), y el segundo lo encontró el recorrido del menú | sección «reglas» (reservas simultáneas), mutación |
| H-09 | Baja | A10 | El techo del total (10^11) era menor que el total posible (5,5 × 10^12): la reserva se guardaba y después rompía el historial para siempre | **Adoptada** | **Error real, comprobado por aritmética.** Techo derivado `PRECIO_MAXIMO × CUPO_MAXIMO`, validado antes del INSERT | sección «reglas» (reserva al total máximo) |
| H-10 | Baja | A07 | `cambiar_clave` comparaba con el hash en memoria y aceptaba la misma contraseña | **Modificada** | El UPDATE exige que la base tenga el hash verificado: una sesión vieja no cambia una contraseña que otra sesión ya cambió. Se rechaza la nueva igual a la actual. Desde el 5-oct, la contraseña actual cuenta como intento y una sesión vieja no cambia nada (§2.5) | sección «reglas» (dos sesiones) |
| H-11 | Baja | A07 | La inactividad solo se medía en el menú | **Modificada** | Toda espera de un dato (menú, preguntas de una acción, contraseñas, pausa) pasa por `esperar()`, que corta la sesión si venció, y la pantalla se limpia al caducar | sección «menu»: sesión que vence dentro de «crear socio» |
| H-12 | Baja | A10 | `int()` con más de 4.300 dígitos lanzaba `ValueError` sin atrapar; `main()` no tenía un último `except` | **Adoptada** | **Error real, comprobado.** Largo antes de `int()`, `except Exception` final en `main()` y `PermissionError` en el primer uso | sección «menu»: opción de 5.000 dígitos |
| H-13 | Info. | A01 | El dominio acepta cualquier instancia de `Usuario`; un cliente distinguía «no existe» de «no publicado» | **Modificada** | Mismo mensaje para los dos casos al reservar. Lo demás se resolvió en la auditoría final: `autorizar()` exige una sesión iniciada (hallazgo 5) | sección «menu» |
| H-14 | Info. | A06 | Sin aviso de finalidad al registrarse; `0.000.000-0` pasaba como RUT | **Modificada** | Aviso de finalidad, protección y derechos (Ley 21.719, art. 14 ter) que hay que aceptar antes de registrarse; RUT 0 rechazado (**comprobado**: pasaba). Supresión y portabilidad: se atienden ante los socios (`PRIVACIDAD.md` §3) | secciones «menu» y «reglas» |
| H-15 | Baja | A02 | El diario de la base (`-journal`) nacía con la máscara del sistema | **Adoptada** | `os.umask(0o077)` al arrancar | revisión del código |
| H-16 | Baja | A07 | No se revisaban contraseñas comunes | **Modificada** | Lista local de contraseñas comunes de 12 o más caracteres, más un mínimo de 5 caracteres distintos (descarta `aaaaaaaaaaaa`). Una lista de millones de filtradas exigiría un archivo de cientos de MB o una consulta a internet, que la aplicación no tiene | sección «reglas» |
| H-17 | Info. | A07 | Bloqueo con hora local; sin bloqueo progresivo | **Modificada** | Hora UTC (un cambio de horario ya no alarga ni anula el bloqueo). Desde el 5-oct, bloqueo progresivo de 5, 15 y 60 minutos (§2.5) | sección «reglas» |
| B608 ×6 | Media | A05 | SQL armado con f-string (solo constantes, no explotable) | Corregido | Contradecía RNF-SEG-03, que pide cero. Consultas como constantes literales y `json_each(?)` para la lista de ids | bandit: 0 B608 |

### 2.1 Los 17 hallazgos de la IA en las cinco partes del docente

Formato de la diapositiva 59: el hallazgo, su evidencia en el código auditado (commit `525ab10`), el
impacto si sigue ocurriendo, la recomendación tomada y el esfuerzo real de la corrección.

| ID | Hallazgo | Evidencia | Impacto | Recomendación aplicada | Esfuerzo |
|---|---|---|---|---|---|
| H-01 | La clave de cifrado estaba en la carpeta del proyecto, junto a la base | `viajes.py`: `RUTA_CLAVE = Path(__file__).with_name(".env")` | Un zip o una copia de la carpeta llevaba el RUT cifrado y su clave juntos: el cifrado no protegía nada | Clave en `~/.config/viajes-aventura/`, permisos 0600 corregidos al leerla | 15 min |
| H-02 | No había registro de quién hizo cada cambio ni de los intentos de acceso | Ninguna escritura usaba `solicitante` después de autorizar | Sin rastro ante un cambio de precio, un paquete borrado o un ataque de fuerza bruta; nada que mostrar ante la Ley 21.719 | Tabla `auditoria` en la misma transacción, sin datos personales | 40 min |
| H-03 | No se puede desactivar una cuenta ni suprimir los datos de un cliente | La acción `cuentas` solo crea | Un socio que se va conserva su acceso; el derecho de supresión no se atiende en el sistema | Desactivar cuentas, hecho el 5-oct (§2.5); supresión ante los socios (W-08) | 40 min |
| H-04 | Listar reservas descifraba el RUT y el teléfono de todos | `_listar` construía cada `Cliente` con `descifrar(...)` | RUT en claro en memoria en cada listado; un registro alterado tumbaba el listado completo | Descifrado diferido: solo al enmascarar | 30 min, junto con H-05 |
| H-05 | Iniciar sesión descifraba antes de verificar la contraseña | `autenticar` → `_usuario_desde_fila` | Con una clave equivocada, el mensaje delataba el correo y el intento no contaba para el bloqueo | Resuelto por H-04 | incluido en H-04 |
| H-06 | El registro revela qué correos existen; el señuelo se calculaba en el primer intento | `_insertar`: R9; `_senuelo` perezoso | Permite saber quién es cliente y bloquear su cuenta a propósito | Señuelo al cargar el módulo; R9 solo para el `UNIQUE` del correo; la enumeración, declarada | 10 min |
| H-07 | El bloqueo se decidía con un dato leído en otra conexión | `bloqueada = self.__bloqueado_hasta …` | Dos sesiones en paralelo podían sumar más de 5 intentos | Releer el bloqueo dentro de la transacción del intento | 15 min |
| H-08 | La consulta previa a una escritura no entraba en la transacción | `sqlite3` abre la transacción en la primera escritura (comprobado: `in_transaction` es `False` tras un `SELECT`) | «Revisar y escribir» no era atómico (R8 al guardar paquetes) | `BEGIN IMMEDIATE` explícito en `conectar()` | 30 min |
| H-09 | El techo del total era menor que el total posible | `COSTO_MAXIMO * CUPO_MAXIMO` (10^11) contra 5,5 × 10^12 | Una reserva grande se guardaba y después rompía el historial para siempre | Techo derivado del precio máximo, validado antes del INSERT | 10 min |
| H-10 | Cambiar la contraseña comparaba con el hash en memoria | `cambiar_clave` | Una sesión vieja podía volver a cambiar una contraseña ya cambiada | UPDATE condicionado al hash leído; la nueva distinta de la actual | 15 min |
| H-11 | La inactividad solo se medía en el menú | `usar_sesion` | Una pregunta abierta podía responderse horas después | Plazo revisado en cada espera de un dato | 25 min |
| H-12 | `int()` con más de 4.300 dígitos cerraba el programa con traza | `ejecutar_opcion` (comprobado) | Traza con rutas en pantalla (RNF-SEG-05) | Largo antes de `int()`; `except Exception` final en `main()` | 10 min |
| H-13 | Un cliente distinguía «no existe» de «no publicado» | `reservar` en el menú | Podía deducir los ids de los borradores | Mismo mensaje para los dos casos | 5 min |
| H-14 | Sin aviso de datos; el RUT 0 pasaba la validación | `registrarse`; `validar_rut("0.000.000-0")` (comprobado) | Brecha con el deber de información; cuentas con RUT inválido | Aviso que hay que aceptar y RUT 0 rechazado; el aviso se completó en §2.3 | 15 min |
| H-15 | El diario de la base nacía con permisos abiertos | `crear_tablas` hacía `chmod` después | Otro usuario del equipo podía leer el diario durante una transacción | `os.umask(0o077)` al arrancar | 2 min |
| H-16 | No se rechazaban contraseñas comunes | `_validar_clave` | «contraseña123» era aceptada | Lista local y mínimo de 5 caracteres distintos | 15 min |
| H-17 | Bloqueo con hora local | `datetime.now()` | Un cambio de horario alargaba o anulaba el bloqueo | Hora UTC; el bloqueo progresivo, hecho el 5-oct (§2.5) | 10 min |

### 2.2 Pruebas de mutación: cada corrección tiene una prueba que la vigila

La sección «mutaciones» de `pruebas/verificar.py` deshace cada corrección y rompe cada regla
principal, una por vez, en una copia temporal del proyecto, y corre las secciones que deben
detectarlo. Falla si alguna mutación sobrevive. Corre en el workflow, en el job «mutaciones», en cada
envío al repositorio.

Resultado: **36 de 36 detectadas**. Cubren:
- 9 reglas del negocio y 6 de cuentas y permisos;
- las correcciones de esta auditoría;
- las de la auditoría final: sesión iniciada, edición a medias, `rowcount` y «2.5» personas;
- los dos errores reales del desarrollo, K-04 y K-05;
- el aislamiento del modo demostración (§2.4);
- los 9 cierres del 5-oct (§2.5), incluida una consulta SQL armada pegando textos.

Esa última mutación sobrevivió la primera vez: la prueba solo miraba lo que se pasaba a `execute()`,
no las constantes `SQL_*`. Se amplió la prueba, y ahora la detecta.

El `AND hash_clave = ?` de `cambiar_clave` no tiene mutación propia. Es la defensa ante una carrera
entre dos sesiones, y la revisión de sesión que la precede ya tiene la suya.

### 2.3 Auditoría final (3-oct, 22:00): seguridad y privacidad

Un corrector independiente (agente nuevo, sin contexto) y una revisión propia de todo lo que se
publica y se entrega encontraron estos hallazgos de seguridad y privacidad. Cada uno se comprobó antes
de corregirlo.

| # | Hallazgo | Evidencia | Impacto | Recomendación aplicada | Esfuerzo |
|---|---|---|---|---|---|
| 5 | Un `Administrador` creado sin iniciar sesión tenía permisos | Prueba: `Destino(...).guardar(Administrador("x@y.cl", ...))` guardaba | Contradecía el criterio de RF-SEG-05 («por cualquier vía»); H-13 lo había aceptado como riesgo | `autorizar()` exige una cuenta con sesión iniciada (decisión 13): solo `autenticar()` y el alta de la propia cuenta la dan | 40 min |
| 4 | `editar` dejaba el objeto a medias si fallaba una validación | Prueba: el objeto quedaba con el nombre nuevo y la base con el anterior | Memoria y base dejaban de coincidir | Validar en valores locales y asignar solo después de guardar | 20 min |
| 6 | Quedaba una consulta armada pegando textos | `_insertar`: `"… SELECT ?, …" + condicion` | Contradecía RNF-SEG-03 y lo afirmado en esta auditoría (bandit no lo detecta: no es un f-string) | Dos consultas literales completas | 10 min |
| 20 | Tres escrituras no revisaban si guardaron algo | `cambiar_costo`, `reactivar`, `Destino.editar` | El menú decía «Guardado» aunque otra sesión hubiera borrado el registro | `exigir_una_fila()`: `rowcount` igual a 1 o error | 15 min |
| 3 | «2.5» personas se registraba como 25 | `pedir_entero` borraba todos los puntos | Una reserva de 25 personas cobrada sin querer | El punto solo se acepta como separador de miles | 15 min |
| 14 | El aviso de datos no cumplía el art. 14 ter completo | Faltaban la base legal, la conservación, los destinatarios y tres de los derechos | Deber de información incompleto (Ley 21.719) | Aviso con responsable, finalidad, base legal, destinatarios, conservación, protección y los seis derechos con su plazo | 20 min |
| 25 | El token del workflow no tenía permisos limitados | `pruebas.yml` sin `permissions:` | Una acción comprometida podría escribir en el repositorio (A03) | `permissions: contents: read` | 5 min |
| 10 | Las mutaciones citadas no se podían repetir | No había un script en el repositorio | Una afirmación que el corrector no puede verificar | Mutaciones en el workflow (hoy, la sección «mutaciones» de `pruebas/verificar.py`) | 45 min |
| 16 | No había forma de respaldar la base | P-14: «si se pierde, se pierde con todo» | La pérdida del equipo era la pérdida de todas las reservas | `Administrador.respaldarBase()`: copia consistente en `respaldos/`, 0600, ignorada por git (RNF-FIA-03) | 30 min |
| 28 | RUT de prueba con dígito verificador válido | `12.345.678-5` y `11.111.111-1` en pruebas y en la sesión del menú | Podrían coincidir con personas reales | Declarado como datos ficticios en el código y en la sesión del menú | 5 min |

### 2.4 Modo demostración (5-oct): una puerta de prueba que no salta la seguridad

El corrector y los socios necesitan probar el CRUD con los dos roles sin ingresar todo desde cero.
La pantalla previa ofrece «Entrar al sistema» o «Modo demostración» (RNF-USA-04). Un acceso de prueba
es justo el tipo de función que abre una puerta trasera, así que se diseñó como una decisión de
seguridad:

| Hallazgo | Evidencia | Impacto | Recomendación aplicada | Esfuerzo |
|---|---|---|---|---|
| Un acceso de prueba sin contraseña habría saltado RF-SEG-05 y el hallazgo 5 | Diseño revisado antes de escribirlo | Cualquiera tendría el menú del administrador sobre los datos reales | «Entrar como socio» y «Entrar como cliente» pasan por `Usuario.autenticar()`, como el inicio de sesión: la sesión es real y `autorizar()` la exige igual | 10 min |
| Las cuentas de prueba necesitan contraseña | S-04: ninguna credencial escrita en el código | Una contraseña fija en el código sería pública en el repositorio | Se generan al azar en cada ejecución (`secrets.token_urlsafe`) y solo se muestran en pantalla | 5 min |
| Los datos de prueba podrían mezclarse con los reales | La base y la clave son globales del módulo | Clientes ficticios en la base real, o datos reales cifrados con otra clave | Base y clave en una carpeta temporal, sin la variable de entorno real; todo se restaura al salir (también ante un error o Ctrl+C) y la carpeta se borra | 20 min |
| El aislamiento podía romperse sin que nadie lo notara | Un cambio que quite `usar_base()` escribiría en la base real | Pérdida silenciosa de la separación | `pruebas/verificar.py` (sección «seguridad») comprueba que la base, la clave y la variable reales quedan intactas, y una mutación quita el aislamiento: la prueba la detecta | 15 min |

Los datos de ejemplo se cargan solo con los métodos públicos del dominio. Pasan por las mismas
validaciones que el menú, quedan en el registro de auditoría de la base temporal y usan RUT ficticios
a la vista (11.111.111-1 y 22.222.222-2).

### 2.5 Cierre de los riesgos declarados (5-oct)

El 3-oct, §3 tenía 13 riesgos «aceptados». Se reevaluaron uno por uno con un criterio: lo que se puede
cerrar sin salir del alcance del caso se cierra, con su prueba y su mutación. Lo que no se puede
cerrar en ninguna aplicación de escritorio queda como límite, con su mitigación (§3).

| Riesgo | Evidencia | Impacto | Cierre aplicado | Esfuerzo |
|---|---|---|---|---|
| H-10: la contraseña actual equivocada, al cambiarla, no contaba como intento | `cambiar_clave` usaba `__verificar`, sin contador | Con una sesión abierta ajena se podía probar contraseñas sin bloqueo | Usa `__intentar`, el mismo contador y bloqueo del inicio de sesión; además, una sesión que ya no vale no cambia nada | 20 min |
| H-17: bloqueo fijo de 5 minutos | `BLOQUEO = timedelta(minutes=5)` | Unos 1.440 intentos diarios por cuenta | Progresivo: 5, 15 y 60 minutos mientras siga fallando, con la columna `bloqueos`; un acierto vuelve a empezar. El primero sigue siendo el de RF-SEG-03 | 25 min |
| Cambiar la contraseña no cerraba las otras sesiones | La sesión solo era una marca en el objeto | Quien tuviera una sesión abierta la conservaba después del cambio | `tiene_sesion()` compara el hash de la sesión con el de la base en cada acción; si cambió, la sesión deja de valer y el menú vuelve al inicio | 15 min |
| H-03 (a): no se podía desactivar a un socio que se va | La acción `cuentas` solo creaba | El ex socio conservaba su acceso | `Administrador.desactivarCuenta(correo)` y la columna `activa`. La cuenta no entra (mismo mensaje), pierde sus sesiones abiertas y conserva su historia. Nadie desactiva la propia (RF-SEG-14) | 40 min |
| La clave de cifrado no se podía rotar | Una sola clave, sin procedimiento | Si la clave se filtraba, los datos quedaban expuestos para siempre | `rotar_clave_de_datos()`: `MultiFernet` recifra todos los clientes en una transacción, la clave nueva se instala con `os.replace` y la anterior se archiva en 0600 para los respaldos viejos (RF-SEG-15) | 45 min |
| Nadie leía el registro de auditoría | Solo se escribía | Un ataque de fuerza bruta pasaba desapercibido | «Ver el registro de auditoría» en el menú del socio, y un aviso al entrar si hubo bloqueos en 24 horas (RF-SEG-16) | 25 min |
| H-06: el registro enumeraba correos | El registro dice «ese correo ya tiene una cuenta» | Saber quién es cliente de la agencia | Cada correo repetido queda en el registro; tras 5 en 10 minutos, el registro se pausa (RF-SEG-17). Cerrarlo del todo exige verificar el correo con un enlace, y enviar correos está fuera del alcance (§6 del caso) | 20 min |
| Plazo de conservación y registro de incidentes | La ley los exige (art. 3 c y art. 14 sexies) y el sistema no los fijaba | Incumplimiento del deber de proporcionalidad y del de reportar | Procedimiento escrito en [`PRIVACIDAD.md`](PRIVACIDAD.md), con el texto de la ley, la tabla del registro de incidentes y los pasos (contener con la rotación de la clave y la desactivación de cuentas) | 30 min |
| Las acciones del workflow se fijaban por etiqueta | `uses: actions/checkout@v7` | Una etiqueta movida podía cambiar lo que corre | Fijadas por el hash de su commit | 5 min |
| `assert` en el producto | 64 `assert` de la autoverificación dentro de `viajes.py` | Mezclaba pruebas con producto (bandit B101) | Todas las pruebas pasaron a `pruebas/verificar.py`; el producto tiene 0 | 60 min |

Cada cierre tiene su afirmación en `pruebas/verificar.py` (secciones «credenciales», «datos» y
«seguridad») y su mutación en la sección «mutaciones».

## 3. Límites del modelo de amenazas

Ya no hay riesgos «aceptados»: lo que se podía cerrar dentro del alcance se cerró (§2.5). Quedan dos
límites que ninguna aplicación de escritorio sin servidor puede eliminar, cada uno con su mitigación
implementada. Y una decisión de alcance, que no es un riesgo.

| Límite | Por qué no se puede eliminar | Qué lo mitiga hoy | Qué lo eliminaría |
|---|---|---|---|
| Quien controla la cuenta del sistema operativo de la oficina mientras el programa está abierto controla el programa | Vale para cualquier aplicación local: base, clave y proceso viven en esa cuenta (S-11) | Permisos 0600 y `umask` 077; clave fuera del proyecto; sesión que vence a los 10 minutos; desactivar cuentas; rotar la clave si se sospecha una copia; registro de auditoría con aviso de bloqueos | Un servidor con la clave en un gestor de secretos, o la clave protegida por una frase maestra que el socio escriba al abrir (diseñada, no construida) |
| El registro público dice si un correo ya existe | Sin enviar un correo de verificación, quien se registra tiene que saber que su correo ya tiene cuenta, y enviar correos está fuera del alcance (§6 del caso, W-05) | Pausa del registro tras 5 correos repetidos en 10 minutos, cada intento en el registro de auditoría y el mismo mensaje en el inicio de sesión | Verificar el correo con un enlace (W-05) |

**Decisión de alcance, no riesgo:** la supresión de datos pedida por el propio cliente desde el sistema
es el Won't W-08. El derecho existe y se atiende ante los socios, como indica el aviso que el cliente
acepta (30 días corridos). La Ley 21.719, que obligaría a ofrecerlo con más formalidad, rige desde el
1-dic-2026. El procedimiento está en [`PRIVACIDAD.md`](PRIVACIDAD.md) §3.

## 4. Qué aportó la IA y qué no

- **Aportó** 17 hallazgos con ubicación exacta y una recomendación por cada uno. Se verificaron todas las
  afirmaciones comprobables antes de actuar: H-08, H-09, H-12 y H-14 se confirmaron por experimento o
  por aritmética.
- **Ninguna recomendación se aplicó sin revisarla**: 12 de 17 se modificaron. Cada modificación tiene
  un motivo técnico o del caso: la disponibilidad de la agencia en H-01, la minimización en H-04 y un
  requerimiento del cliente en H-17.
- **No vio** dos consecuencias de su propia recomendación H-08: las conexiones anidadas que quedaban
  esperando. Las encontraron el recorrido del menú y la lectura del código.
- **Tampoco vio** el error más grave de la jornada, que la prueba por indicador había encontrado antes
  de la auditoría: en una instalación nueva, el primer cliente no podía registrarse.

## 5. OWASP Top 10:2025: dónde se atiende cada categoría

| Categoría | Controles en el sistema |
|---|---|
| A01 Broken Access Control | Permiso revisado en el dominio (`autorizar`, que exige una sesión iniciada y vigente: la contraseña no cambió y la cuenta sigue activa) y en el menú; cuentas desactivables; anular exige ser el titular en el objeto y en el SQL; el historial filtra por el id propio; el menú se arma con `puede()` |
| A02 Security Misconfiguration | Base y clave en 0600, `umask` 077, clave fuera del proyecto, ninguna credencial por omisión (S-04) |
| A03 Software Supply Chain Failures | Dependencias fijadas con `==` y hash de todas las plataformas, `pip-audit` sin hallazgos, workflow en 6 combinaciones con un token de solo lectura y acciones fijadas por hash |
| A04 Cryptographic Failures | Argon2id para contraseñas; Fernet (AES-128-CBC + HMAC-SHA256) para RUT y teléfono, que da confidencialidad e integridad; clave en archivo aparte y rotable con `MultiFernet` |
| A05 Injection | SQL solo con parámetros y como texto literal; `texto()` rechaza caracteres de control y marcas bidireccionales que se reimprimen en la terminal |
| A06 Insecure Design | Transacciones atómicas (H-08), cupo calculado y no guardado, precio fijado al publicar, descifrado diferido (H-04), reglas repetidas en CHECK de la base |
| A07 Authentication Failures | Bloqueo progresivo (5, 15 y 60 min) en una sentencia atómica y con hora UTC, también al cambiar la contraseña; sesiones invalidadas al cambiarla; mismo mensaje y demora en los tres fallos, política de contraseña con lista de comunes, sesión que vence a los 10 minutos también dentro de una acción |
| A08 Software or Data Integrity Failures | Fernet rechaza un dato alterado; hashes en `requirements.txt` |
| A09 Security Logging and Alerting Failures | Registro de auditoría de 27 acciones, en la misma transacción, sin datos personales (H-02), legible desde el menú del socio, con aviso de bloqueos (RF-SEG-16) |
| A10 Mishandling of Exceptional Conditions | Cadena de `except` por tipo con `except Exception` final en el menú y en `main()`; ningún mensaje con trazas, rutas ni datos; techo de todo entero (H-12) y del total (H-09) |

## 6. Cómo repetir la auditoría

```bash
pip install bandit pip-audit
bandit -r viajes.py main.py                          # esperado: No issues identified (0 en el producto)
pip-audit -r requirements.txt --require-hashes        # esperado: No known vulnerabilities found
git log --all --name-only --format= | sort -u | grep -E '\.env$|\.db$'   # esperado: nada
python pruebas/verificar.py --todo                    # esperado: ninguna falla; 36 de 36 mutaciones
```
