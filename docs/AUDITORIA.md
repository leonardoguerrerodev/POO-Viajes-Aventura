# Auditoría de seguridad · Viajes Aventura

Responde a **4.1.5.I.20**: evalúa y optimiza la seguridad del sistema utilizando criterios técnicos y
apoyo de IA. Sábado 3 de octubre de 2026.

| | |
|---|---|
| Alcance | `viajes.py` (dominio y persistencia), `main.py` (menú), dependencias e historial del repositorio |
| Código auditado | commit `525ab10`, antes de cualquier corrección |
| Código corregido | commit `fcfa4f9` y siguientes, rama `feature/auditoria` integrada a `main` |
| Método | «Auditoría de seguridad y privacidad» (método propio, fases 5, 7, 9, 14 y 15), en su versión para un proyecto de una persona |
| Herramientas | bandit 1.9.4 (análisis estático), pip-audit 2.10.1 (dependencias), búsqueda de secretos en el historial de git, SonarCloud (en cada envío), revisión pedida a la IA |
| Revisión con IA | Claude, en un agente nuevo que solo conocía el prompt y los dos archivos. Prompt y respuesta íntegros en [`ia/auditoria_seguridad_ia.md`](ia/auditoria_seguridad_ia.md) |
| Fuera de alcance | No hay interfaz web ni APIs: XSS, CSRF y cabeceras HTTP no aplican |

## Resumen

| Fuente | Hallazgos | Corregidos | Declarados (riesgo aceptado, con motivo) |
|---|---|---|---|
| Revisión con IA | 17 (0 críticos, 0 altos, 4 medios, 10 bajos, 3 informativos) | 16, total o parcialmente | 1 entero (H-03) y la parte no corregida de 5 (H-06, H-10, H-13, H-14 y H-17) |
| bandit | 6 B608 (posible inyección SQL), 93 B101 (`assert`; 102 al final, por las pruebas nuevas) | los 6 B608 | los B101: solo están en código de verificación |
| pip-audit | 0 vulnerabilidades en las 5 dependencias | | |
| Secretos en el historial | 0 (ningún `.env`, `.db` ni clave subida, en ningún commit) | | |
| SonarCloud | 8 observaciones de las pruebas nuevas | 8 | |
| Auditoría final (corrector independiente y revisión propia, 3-oct 22:00) | 10 de seguridad y privacidad (§2.3) | 9 | 1 (plazo de conservación) y 6 riesgos nuevos declarados en §3 |

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
| H-01 | Media | A04 | La clave Fernet vivía en `.env` dentro de la carpeta del proyecto, junto a la base | **Modificada** | La clave pasa a `~/.config/viajes-aventura/clave.env`, fuera del proyecto, con la carpeta en 0700 y el archivo en 0600. Si un respaldo la restaura con permisos abiertos, se cierran solos en vez de rechazarla como proponía la IA: rechazarla dejaría a la agencia sin poder atender. Se verificó que `.env` y `*.db` nunca estuvieron en el historial y se agregaron `*.db-wal` y `*.db-shm` al `.gitignore` | `prueba_rubrica.py` I.19 |
| H-02 | Media | A09 | No había registro de auditoría | **Modificada** | Tabla `auditoria(fecha_utc, usuario_id, accion, detalle)`, escrita en la misma transacción de cada operación (si la operación se deshace, su registro también). Registra 22 acciones: catálogo, paquetes, reservas, cuentas e inicios de sesión (correcto, fallido, bloqueo, rechazado por bloqueo, correo inexistente). Sin la columna «resultado» que proponía la IA: solo se registra lo que ocurrió. El detalle lleva ids y montos, nunca RUT, teléfono, correo ni contraseña; del correo inexistente no se guarda el correo, porque puede ser de otra persona | autoverificación `_verificar_auditoria` |
| H-03 | Media | A07 | No se puede desactivar una cuenta ni suprimir los datos de un cliente | **Descartada** en esta versión | Ver §3 |
| H-04 | Media | A06 | Listar reservas descifraba el RUT y el teléfono de todos los clientes | **Modificada** | En vez de una consulta liviana solo para ese listado, `Cliente` guarda el RUT y el teléfono **cifrados también en memoria** y los descifra solo para enmascararlos. Ninguna lectura de la base descifra nada, y un registro alterado ya no impide listar a los demás | autoverificación (RUT alterado: se entra y se lista) |
| H-05 | Baja | A07 | Iniciar sesión descifraba los datos antes de verificar la contraseña | **Modificada** | Resuelto por el mismo cambio de H-04 | ídem |
| H-06 | Baja | A07 | Enumeración de correos por el registro; señuelo calculado en el primer intento; todo `IntegrityError` se mostraba como «correo repetido» | **Modificada** | El señuelo se calcula al cargar el módulo y solo el `UNIQUE` del correo se traduce a R9. La enumeración por el registro se declara (§3) | autoverificación |
| H-07 | Baja | A07 | El bloqueo se decidía con el objeto leído antes, en otra conexión | **Adoptada** | El estado del bloqueo se vuelve a leer dentro de la transacción del intento | autoverificación (bloqueo) |
| H-08 | Baja | A06 | En su modo por omisión, `sqlite3` abre la transacción en la primera escritura: «consultar y después escribir» no era atómico, aunque el comentario lo afirmaba | **Modificada** | **Error real, comprobado por experimento** (`in_transaction` es `False` después de un `SELECT`). `conectar()` abre siempre con `BEGIN IMMEDIATE` explícito. La IA no advirtió la consecuencia: con IMMEDIATE, una conexión abierta dentro de otra se queda esperando. Había dos casos (`Paquete._listar` y el cifrado dentro de `_insertar`), y el segundo lo encontró el recorrido del menú | autoverificación (reservas simultáneas), mutación |
| H-09 | Baja | A10 | El techo del total (10^11) era menor que el total posible (5,5 × 10^12): la reserva se guardaba y después rompía el historial para siempre | **Adoptada** | **Error real, comprobado por aritmética.** Techo derivado `PRECIO_MAXIMO × CUPO_MAXIMO`, validado antes del INSERT | autoverificación (reserva al total máximo) |
| H-10 | Baja | A07 | `cambiar_clave` comparaba con el hash en memoria y aceptaba la misma contraseña | **Modificada** | El UPDATE exige que la base tenga el hash verificado: una sesión vieja no cambia una contraseña que otra sesión ya cambió. Se rechaza la nueva igual a la actual. No se cuentan los intentos (§3) | autoverificación (dos sesiones) |
| H-11 | Baja | A07 | La inactividad solo se medía en el menú | **Modificada** | Toda espera de un dato (menú, preguntas de una acción, contraseñas, pausa) pasa por `esperar()`, que corta la sesión si venció, y la pantalla se limpia al caducar | driver: sesión que vence dentro de «crear socio» |
| H-12 | Baja | A10 | `int()` con más de 4.300 dígitos lanzaba `ValueError` sin atrapar; `main()` no tenía un último `except` | **Adoptada** | **Error real, comprobado.** Largo antes de `int()`, `except Exception` final en `main()` y `PermissionError` en el primer uso | driver: opción de 5.000 dígitos |
| H-13 | Info. | A01 | El dominio acepta cualquier instancia de `Usuario`; un cliente distinguía «no existe» de «no publicado» | **Modificada** | Mismo mensaje para los dos casos al reservar. Lo demás se declara (§3) | driver |
| H-14 | Info. | A06 | Sin aviso de finalidad al registrarse; `0.000.000-0` pasaba como RUT | **Modificada** | Aviso de finalidad, protección y derechos (Ley 21.719, art. 14 ter) que hay que aceptar antes de registrarse; RUT 0 rechazado (**comprobado**: pasaba). Supresión y portabilidad: §3 | driver y autoverificación |
| H-15 | Baja | A02 | El diario de la base (`-journal`) nacía con la máscara del sistema | **Adoptada** | `os.umask(0o077)` al arrancar | revisión del código |
| H-16 | Baja | A07 | No se revisaban contraseñas comunes | **Modificada** | Lista local de contraseñas comunes de 12 o más caracteres, más un mínimo de 5 caracteres distintos (descarta `aaaaaaaaaaaa`). Una lista de millones de filtradas exigiría un archivo de cientos de MB o una consulta a internet, que la aplicación no tiene | autoverificación |
| H-17 | Info. | A07 | Bloqueo con hora local; sin bloqueo progresivo | **Modificada** | Hora UTC (un cambio de horario ya no alarga ni anula el bloqueo). El bloqueo progresivo se descarta (§3) | autoverificación |
| B608 ×6 | Media | A05 | SQL armado con f-string (solo constantes, no explotable) | Corregido | Contradecía RNF-SEG-03, que pide cero. Consultas como constantes literales y `json_each(?)` para la lista de ids | bandit: 0 B608 |

### 2.1 Los 17 hallazgos de la IA en las cinco partes del docente

Formato de la diapositiva 59: el hallazgo, su evidencia en el código auditado (commit `525ab10`), el
impacto si sigue ocurriendo, la recomendación tomada y el esfuerzo real de la corrección.

| ID | Hallazgo | Evidencia | Impacto | Recomendación aplicada | Esfuerzo |
|---|---|---|---|---|---|
| H-01 | La clave de cifrado estaba en la carpeta del proyecto, junto a la base | `viajes.py`: `RUTA_CLAVE = Path(__file__).with_name(".env")` | Un zip o una copia de la carpeta llevaba el RUT cifrado y su clave juntos: el cifrado no protegía nada | Clave en `~/.config/viajes-aventura/`, permisos 0600 corregidos al leerla | 15 min |
| H-02 | No había registro de quién hizo cada cambio ni de los intentos de acceso | Ninguna escritura usaba `solicitante` después de autorizar | Sin rastro ante un cambio de precio, un paquete borrado o un ataque de fuerza bruta; nada que mostrar ante la Ley 21.719 | Tabla `auditoria` en la misma transacción, sin datos personales | 40 min |
| H-03 | No se puede desactivar una cuenta ni suprimir los datos de un cliente | La acción `cuentas` solo crea | Un socio que se va conserva su acceso; el derecho de supresión no se atiende en el sistema | Declarado (§3): queda para la versión 2 | 120 min estimados |
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
| H-17 | Bloqueo con hora local | `datetime.now()` | Un cambio de horario alargaba o anulaba el bloqueo | Hora UTC; el bloqueo progresivo, declarado | 10 min |

### 2.2 Pruebas de mutación: cada corrección tiene una prueba que la vigila

`herramientas/mutaciones.py` deshace cada corrección y rompe cada regla principal, una por vez, en una
copia temporal del proyecto, y corre las pruebas que deben detectarlo. Falla si alguna mutación
sobrevive. Corre en el workflow, en el job «mutaciones», en cada envío al repositorio.

Resultado: **27 de 27 detectadas**. Son 9 reglas del negocio y 6 de cuentas y permisos; las 12
correcciones de esta auditoría; las de la auditoría final (sesión iniciada, edición a medias,
`rowcount` y «2.5» personas); y los dos errores reales del desarrollo (K-04 y K-05).

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
| 10 | Las mutaciones citadas no se podían repetir | No había un script en el repositorio | Una afirmación que el corrector no puede verificar | `herramientas/mutaciones.py` en el workflow | 45 min |
| 16 | No había forma de respaldar la base | P-14: «si se pierde, se pierde con todo» | La pérdida del equipo era la pérdida de todas las reservas | `Administrador.respaldarBase()`: copia consistente en `respaldos/`, 0600, ignorada por git (RNF-FIA-03) | 30 min |
| 28 | RUT de prueba con dígito verificador válido | `12.345.678-5` y `11.111.111-1` en pruebas y en la sesión del menú | Podrían coincidir con personas reales | Declarado como datos ficticios en el código y en la sesión del menú | 5 min |

## 3. Declarados: riesgos aceptados y su motivo

| Riesgo | Por qué se acepta en esta versión | Qué lo mitiga hoy | Cómo se resolvería |
|---|---|---|---|
| **H-03** No se puede desactivar la cuenta de un socio que se va, ni suprimir los datos de un cliente | El alcance del caso (§6) no lo pide, y exige cambiar el esquema y el CHECK de cliente, más una acción nueva en el modelo. La Ley 21.719 rige desde el 1-dic-2026 | El derecho de supresión se atiende a mano (el aviso del registro indica escribir a la agencia); el plazo legal es de 30 días | Columna `activa`, filtro en `autenticar`, `Administrador.desactivarCuenta()` sin permitir desactivar al último, y anonimizar al cliente conservando sus reservas |
| H-06 Enumeración de correos por el registro público | Sin verificación por correo no se puede evitar: el registro tiene que decir que el correo ya existe | El bloqueo de 5 × 5 minutos y que los intentos quedan en el registro de auditoría | Verificar el correo con un enlace (envío de correos fuera del alcance, §6) |
| H-10 No se cuentan los intentos de la contraseña actual al cambiarla | Para llegar a esa opción ya hay una sesión iniciada | La sesión vence tras 10 minutos sin uso, también dentro de la acción (H-11) | Reutilizar el contador de `__intentar` |
| H-13 (resuelto en la auditoría final) Quien puede ejecutar código dentro del proceso puede saltarse cualquier regla | La autorización exige ahora una sesión iniciada (§2.3, hallazgo 5); por debajo de eso, la frontera es el proceso y la cuenta del sistema | Permisos del sistema, base y clave en 0600 | Un servidor con sesiones firmadas (fuera del alcance) |
| H-17 Bloqueo fijo, no progresivo | RF-SEG-03 fija 5 intentos y 5 minutos; cambiarlo cambia un requerimiento del cliente | Con Argon2id y contraseñas de 12 o más caracteres no comunes, unos 1.440 intentos diarios por cuenta no alcanzan para adivinar | Bloqueo de 5, 15 y 60 minutos, previa conversación con los socios |
| Quien tiene la cuenta del sistema operativo lee la base y la clave | Es el modelo de una aplicación de escritorio sin servidor (S-11) | Permisos 0600, clave fuera del proyecto, equipo con usuario propio | Un servidor con la clave en un gestor de secretos |
| Plazo de conservación | La ley pide conservar los datos solo el tiempo necesario; el caso no fija plazos y las reservas respaldan lo cobrado. El aviso informa el criterio | Las cuentas sin uso se pueden borrar a mano; el registro de auditoría no guarda datos personales | Una tarea de depuración periódica con el plazo que acuerden los socios |
| Registro de incidentes (art. 14 sexies) | Es un procedimiento de la agencia, no una función del sistema | El registro de auditoría deja la evidencia de accesos y bloqueos | Un formato de registro de incidentes y a quién avisar, fuera del software |
| La clave de cifrado no se puede rotar | Rotarla exige volver a cifrar todos los RUT; con un solo equipo y sin incidente, el riesgo es bajo | La clave está fuera del proyecto, en 0600 | `MultiFernet` con la clave nueva y la vieja, y una tarea que vuelva a cifrar |
| Cambiar la contraseña no cierra las otras sesiones abiertas | Las sesiones viven solo en la terminal donde se abrieron y vencen a los 10 minutos sin uso | Inactividad dentro de las acciones (H-11) | Un contador de versión de credenciales en la cuenta, revisado en cada acción |
| Nadie lee el registro de auditoría desde el menú ni recibe alertas | Con tres socios, la consulta es ocasional y se hace con sqlite3 | Los eventos quedan en la misma transacción y sin datos personales | Una opción de consulta para el administrador y un aviso tras N bloqueos |
| Las acciones del workflow se fijan por versión (`@v7`), no por hash | Son acciones oficiales de GitHub, y el token es de solo lectura | `permissions: contents: read` | Fijarlas por hash de commit |
| bandit B101: 102 `assert` | Están solo en la autoverificación, el driver y las pruebas; ninguna regla del programa depende de un `assert` | Las reglas usan `ReglaNegocioError`, `ValueError` y `PermissionError` | No aplica |

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
| A01 Broken Access Control | Permiso revisado en el dominio (`autorizar`, que exige una sesión iniciada) y en el menú; anular exige ser el titular en el objeto y en el SQL; el historial filtra por el id propio; el menú se arma con `puede()` |
| A02 Security Misconfiguration | Base y clave en 0600, `umask` 077, clave fuera del proyecto, ninguna credencial por omisión (S-04) |
| A03 Software Supply Chain Failures | Dependencias fijadas con `==` y hash de todas las plataformas, `pip-audit` sin hallazgos, workflow en 6 combinaciones con un token de solo lectura |
| A04 Cryptographic Failures | Argon2id para contraseñas; Fernet (AES-128-CBC + HMAC-SHA256) para RUT y teléfono, que da confidencialidad e integridad; clave en archivo aparte |
| A05 Injection | SQL solo con parámetros y como texto literal; `texto()` rechaza caracteres de control y marcas bidireccionales que se reimprimen en la terminal |
| A06 Insecure Design | Transacciones atómicas (H-08), cupo calculado y no guardado, precio fijado al publicar, descifrado diferido (H-04), reglas repetidas en CHECK de la base |
| A07 Authentication Failures | Bloqueo 5 × 5 min en una sentencia atómica y con hora UTC, mismo mensaje y demora en los tres fallos, política de contraseña con lista de comunes, sesión que vence a los 10 minutos también dentro de una acción |
| A08 Software or Data Integrity Failures | Fernet rechaza un dato alterado; hashes en `requirements.txt` |
| A09 Security Logging and Alerting Failures | Registro de auditoría de 23 acciones, en la misma transacción, sin datos personales (H-02) |
| A10 Mishandling of Exceptional Conditions | Cadena de `except` por tipo con `except Exception` final en el menú y en `main()`; ningún mensaje con trazas, rutas ni datos; techo de todo entero (H-12) y del total (H-09) |

## 6. Cómo repetir la auditoría

```bash
pip install bandit pip-audit
bandit -r viajes.py main.py herramientas pruebas     # esperado: 0 B608; solo B101 en código de prueba
pip-audit -r requirements.txt --require-hashes        # esperado: No known vulnerabilities found
git log --all --name-only --format= | sort -u | grep -E '\.env$|\.db$'   # esperado: nada
python viajes.py && python herramientas/driver.py && python pruebas/prueba_rubrica.py
python herramientas/mutaciones.py                    # esperado: 27 de 27 mutaciones detectadas
```
