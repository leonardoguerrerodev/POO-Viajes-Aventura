# Pruebas de Viajes Aventura

Todas las pruebas viven en un solo archivo, [`verificar.py`](verificar.py), ordenado por la rúbrica.

**El producto no depende de este archivo.** `viajes.py` (dominio y persistencia) y `main.py` (interfaz)
contienen cada control: permisos, validaciones, cifrado y transacciones. Esta carpeta solo los
observa. Si se borrara, el programa seguiría funcionando y protegido igual. Lo que aporta es la
evidencia de que esos controles funcionan, y la garantía de que, si alguien rompiera uno, alguna prueba
lo notaría.

## Cómo correrlas

Con el entorno virtual activado (ver el [README](../README.md#1-instalar-y-ejecutar)), en Windows,
macOS o Linux:

```bash
python pruebas/verificar.py            # interfaz: elige qué sección correr, paso a paso
python pruebas/verificar.py --todo     # todas (unos 5 minutos; las mutaciones son lo lento)
python pruebas/verificar.py --rapido   # todas menos las mutaciones (menos de 1 minuto)
python pruebas/verificar.py --solo datos
```

- **Cada afirmación se imprime recién después de comprobarla**, con su número y su indicador:
  `12. OK  G.14  lo guardado se lee desde otra conexión: queda en disco, no en memoria`.
- **Si algo falla**, la sección muestra `FALLA`, la causa y la línea de `verificar.py`, y sigue con la
  siguiente. Al final, un resumen por sección y por indicador.
- **Ninguna prueba toca la base real (`viajes.db`) ni la clave real:** cada sección trabaja en una
  carpeta temporal que se borra al terminar.
- **El workflow «Pruebas»** corre cada sección en Windows, macOS y Linux con Python 3.12 y 3.14, en cada
  envío al repositorio.

## Secciones

| Sección | Indicadores | Qué comprueba | Función en `verificar.py` |
|---|---|---|---|
| `reglas` | G.14, G.15 | Las 17 reglas del caso y los requerimientos de cuentas, destinos, paquetes y reservas, incluidas dos reservas simultáneas por el último lugar | `_verificar_clave_y_permisos`, `_verificar_cuentas`, `_verificar_destinos`, `_verificar_paquetes_y_reservas`, `_verificar_auditoria` |
| `implementacion` | G.13, G.14, G.15 | Los cuatro principios de la POO, la persistencia (tablas, claves foráneas, CHECK, datos en disco), el CRUD de cada entidad y el rendimiento con diez veces el volumen | `g13`, `g14`, `g15`, `rendimiento` |
| `credenciales` | G.17, G.18 | Argon2id con sal propia, la misma respuesta y demora para todo fallo, bloqueo progresivo, política de contraseñas (sin secuencias ni datos propios), sesiones invalidadas, cuentas desactivadas y pausa del registro | `g17`, `g18`, `g18_endurecido` |
| `datos` | I.19 | RUT y teléfono ilegibles en la base, integridad (un byte alterado da error), permisos 0600, RUT, correo y teléfono enmascarados, y rotación de la clave | `i19`, `i19_rotacion` |
| `seguridad` | I.20 | Modo demostración aislado, permisos solo con sesión, 0 consultas SQL armadas con texto (revisado con `ast`), 0 `assert` en el producto, registro de auditoría sin datos personales, dependencias y workflow fijados por hash | `demostracion`, `i20` |
| `menu` | G.15 | El menú real de punta a punta con los dos roles y el modo demostración; la sesión que caduca por inactividad. Guarda la evidencia en [`docs/SALIDA_TERMINAL.md`](../docs/SALIDA_TERMINAL.md) | `ejecutar`, `probar_inactividad` |
| `uml` | G.13, I.8 | El diagrama `diagramas/clases.puml` contra `viajes.py`, clase por clase y miembro por miembro | `leer_diagrama`, `leer_codigo`, `comparar` |
| `mutaciones` | I.20 | Rompe a propósito cada regla y cada corrección de seguridad, una por vez, en una copia del proyecto, y exige que alguna sección lo detecte | `MUTACIONES`, `mutacion_detectada` |

**Nombres en el informe.** El informe técnico llama a estas pruebas por lo que hacen:
- la «autoverificación» es la sección `reglas`;
- la «prueba por indicador», las secciones `implementacion`, `credenciales`, `datos` y `seguridad`;
- la «sesión del menú», la sección `menu`.

## Dónde está cada control en el producto

Las pruebas comprueban; el control vive en el producto. Para revisar el código que cumple cada
afirmación:

| Control | Dónde |
|---|---|
| Permisos por rol, revisados en el dominio y solo con sesión iniciada | `viajes.py`: `autorizar()`, `Usuario.tiene_sesion()`, `puede()` de cada rol |
| Contraseñas con Argon2id, política (RF-SEG-04), bloqueo progresivo, misma respuesta para todo fallo | `viajes.py`: `HASHER`, `Usuario._validar_clave()`, `tiene_secuencia()`, `partes_propias()`, `Usuario.autenticar()`, `Usuario.__intentar()`, `Usuario.__senuelo()` |
| RUT y teléfono cifrados (Fernet), enmascarados y con clave rotable; correo enmascarado en pantalla | `viajes.py`: `cifrador()`, `cifrar()`, `descifrar()`, `rotar_clave_de_datos()`, `Cliente.rut_enmascarado()`, `enmascarar_correo()` |
| Transacciones atómicas y consultas con parámetros | `viajes.py`: `conectar()` (`BEGIN IMMEDIATE`), constantes `SQL_*` |
| Reglas repetidas en la base | `viajes.py`: `ESQUEMA` (19 CHECK, UNIQUE, claves foráneas) |
| Registro de auditoría y su lectura | `viajes.py`: `registrar_evento()`, `consultar_auditoria()`, `contar_bloqueos()` |
| Validación del formato al escribir, inactividad, errores sin trazas | `main.py`: `pedir_*()`, `esperar()`, `atender()` |
| Modo demostración aislado | `main.py`: `modo_demostracion()`, `cargar_datos_de_ejemplo()` |

## Lo que parece un defecto y no lo es

Para quien revise el código, a mano o con una herramienta:

- **La validación está en tres capas, no solo en el menú.**
  - `main.py` revisa el formato de lo que se escribe (`pedir_entero`, `pedir_fecha`).
  - Las clases de `viajes.py` revisan las reglas del negocio en su constructor y en cada método: un
    objeto inválido no se crea, venga del menú o de cualquier otro código.
  - La base repite las reglas con CHECK, UNIQUE y claves foráneas.
- **El modo demostración muestra contraseñas en pantalla.** Se generan al azar en cada ejecución, son de
  una base temporal que se borra al salir y no están escritas en el código. Las cuentas de prueba
  entran por el mismo `Usuario.autenticar()` que cualquier otra: el modo no salta ningún permiso.
- **Los RUT de las pruebas** (11.111.111-1, 12.345.678-5, 22.222.222-2) **son ficticios.**
- **`assert` solo aparece en este archivo de pruebas** (bandit B101). El producto no tiene ninguno.
- **Una reserva no se borra:** queda anulada, como historial (supuesto S-01).
- **Un cliente no se borra desde el sistema:** el derecho de supresión se atiende ante los socios
  (Won't W-08).
- **La clave de cifrado no está en el repositorio:** vive en `~/.config/viajes-aventura/` (S-12).
- **`ctypes` en `main.py`** solo se usa en Windows, para que la consola interprete la limpieza de
  pantalla.

Los dos límites que ninguna aplicación de escritorio puede eliminar, y cómo se mitigan, están en
[`docs/AUDITORIA.md` §3](../docs/AUDITORIA.md#3-límites-del-modelo-de-amenazas).
