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
| SonarCloud | 7 observaciones de las pruebas nuevas | 7 | |

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

### Pruebas de mutación: cada corrección tiene una prueba que la vigila

Se deshizo cada corrección por separado en una copia del código y se corrieron las tres pruebas
(autoverificación, driver del menú y prueba por indicador). Las 12 mutaciones fueron detectadas.

| Corrección deshecha | Detectada por |
|---|---|
| H-08 `BEGIN` diferido en vez de `BEGIN IMMEDIATE` | autoverificación, prueba por indicador |
| H-09 techo antiguo del total | autoverificación, prueba por indicador |
| H-04/H-05 descifrar al leer de la base | autoverificación, prueba por indicador |
| H-10 cambiar la contraseña sin comparar el hash | autoverificación, prueba por indicador |
| H-16 sin la lista de contraseñas comunes | autoverificación, prueba por indicador |
| H-14 aceptar el RUT 0 | autoverificación, prueba por indicador |
| H-02 reserva sin registro de auditoría | autoverificación, prueba por indicador |
| H-17 hora local en el bloqueo | autoverificación, prueba por indicador |
| H-01 clave dentro de la carpeta del proyecto | prueba por indicador |
| H-11 plazo de inactividad solo en el menú | driver |
| H-12 `int()` sin límite de largo | driver |
| H-13 mensajes distintos para «no existe» y «no publicado» | driver |

## 3. Declarados: riesgos aceptados y su motivo

| Riesgo | Por qué se acepta en esta versión | Qué lo mitiga hoy | Cómo se resolvería |
|---|---|---|---|
| **H-03** No se puede desactivar la cuenta de un socio que se va, ni suprimir los datos de un cliente | El alcance del caso (§6) no lo pide, y exige cambiar el esquema y el CHECK de cliente, más una acción nueva en el modelo. La Ley 21.719 rige desde el 1-dic-2026 | El derecho de supresión se atiende a mano (el aviso del registro indica escribir a la agencia); el plazo legal es de 30 días | Columna `activa`, filtro en `autenticar`, `Administrador.desactivarCuenta()` sin permitir desactivar al último, y anonimizar al cliente conservando sus reservas |
| H-06 Enumeración de correos por el registro público | Sin verificación por correo no se puede evitar: el registro tiene que decir que el correo ya existe | El bloqueo de 5 × 5 minutos y que los intentos quedan en el registro de auditoría | Verificar el correo con un enlace (envío de correos fuera del alcance, §6) |
| H-10 No se cuentan los intentos de la contraseña actual al cambiarla | Para llegar a esa opción ya hay una sesión iniciada | La sesión vence tras 10 minutos sin uso, también dentro de la acción (H-11) | Reutilizar el contador de `__intentar` |
| H-13 La autorización del dominio confía en la instancia | La frontera de confianza es el proceso: quien puede importar `viajes.py` ya puede abrir la base | Los permisos se revisan en el dominio y en el menú | Un servidor con sesiones firmadas (fuera del alcance) |
| H-17 Bloqueo fijo, no progresivo | RF-SEG-03 fija 5 intentos y 5 minutos; cambiarlo cambia un requerimiento del cliente | Con Argon2id y contraseñas de 12 o más caracteres no comunes, unos 1.440 intentos diarios por cuenta no alcanzan para adivinar | Bloqueo de 5, 15 y 60 minutos, previa conversación con los socios |
| Quien tiene la cuenta del sistema operativo lee la base y la clave | Es el modelo de una aplicación de escritorio sin servidor (S-11) | Permisos 0600, clave fuera del proyecto, equipo con usuario propio | Un servidor con la clave en un gestor de secretos |
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
| A01 Broken Access Control | Permiso revisado en el dominio (`autorizar`) y en el menú; anular exige ser el titular en el objeto y en el SQL; el historial filtra por el id propio; el menú se arma con `puede()` |
| A02 Security Misconfiguration | Base y clave en 0600, `umask` 077, clave fuera del proyecto, ninguna credencial por omisión (S-04) |
| A03 Software Supply Chain Failures | Dependencias fijadas con `==` y hash de todas las plataformas, `pip-audit` sin hallazgos, workflow en 6 combinaciones |
| A04 Cryptographic Failures | Argon2id para contraseñas; Fernet (AES-128-CBC + HMAC-SHA256) para RUT y teléfono, que da confidencialidad e integridad; clave en archivo aparte |
| A05 Injection | SQL solo con parámetros y como texto literal; `texto()` rechaza caracteres de control y marcas bidireccionales que se reimprimen en la terminal |
| A06 Insecure Design | Transacciones atómicas (H-08), cupo calculado y no guardado, precio fijado al publicar, descifrado diferido (H-04), reglas repetidas en CHECK de la base |
| A07 Authentication Failures | Bloqueo 5 × 5 min en una sentencia atómica y con hora UTC, mismo mensaje y demora en los tres fallos, política de contraseña con lista de comunes, sesión que vence a los 10 minutos también dentro de una acción |
| A08 Software or Data Integrity Failures | Fernet rechaza un dato alterado; hashes en `requirements.txt` |
| A09 Security Logging and Alerting Failures | Registro de auditoría de 22 acciones, en la misma transacción, sin datos personales (H-02) |
| A10 Mishandling of Exceptional Conditions | Cadena de `except` por tipo con `except Exception` final en el menú y en `main()`; ningún mensaje con trazas, rutas ni datos; techo de todo entero (H-12) y del total (H-09) |

## 6. Cómo repetir la auditoría

```bash
pip install bandit pip-audit
bandit -r viajes.py main.py herramientas pruebas     # esperado: 0 B608; solo B101 en código de prueba
pip-audit -r requirements.txt --require-hashes        # esperado: No known vulnerabilities found
git log --all --name-only --format= | sort -u | grep -E '\.env$|\.db$'   # esperado: nada
python viajes.py && python herramientas/driver.py && python pruebas/prueba_rubrica.py
```
