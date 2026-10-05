# Viajes Aventura

[![Pruebas](https://github.com/leonardoguerrerodev/POO-Viajes-Aventura/actions/workflows/pruebas.yml/badge.svg)](https://github.com/leonardoguerrerodev/POO-Viajes-Aventura/actions/workflows/pruebas.yml)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=leonardoguerrerodev_POO-Viajes-Aventura&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=leonardoguerrerodev_POO-Viajes-Aventura)

Sistema de gestión de destinos, paquetes turísticos y reservas para la agencia Viajes Aventura
(Valparaíso). Aplicación de terminal en Python con persistencia en `sqlite3`, autenticación con
contraseñas protegidas y cifrado de los datos personales del cliente.

Evaluación Sumativa 4 de Programación Orientada a Objeto Seguro (TI3021), INACAP Valparaíso.
Trabajo individual de Leonardo Guerrero.

**Informe técnico:** [`docs/Informe_Tecnico.pdf`](docs/Informe_Tecnico.pdf) (requerimientos, modelos UML y
BPMN, planificación, implementación, seguridad y trazabilidad).

**Por dónde empezar:**
- **Probar el programa sin ingresar datos:** instalar (§1) y elegir “Modo demostración” (§2).
- **Corregir la evaluación:** [`docs/EVIDENCIA_RUBRICA.md`](docs/EVIDENCIA_RUBRICA.md) enlaza la evidencia de cada indicador de la rúbrica.
- **Revisar la seguridad:** el resumen de §4 y, en detalle, [`docs/AUDITORIA.md`](docs/AUDITORIA.md) y
  [`docs/PRIVACIDAD.md`](docs/PRIVACIDAD.md).

## 1. Instalar y ejecutar

Funciona igual en **Windows, macOS y Linux**: el workflow “Pruebas” lo comprueba en los tres en cada
envío al repositorio. No necesita un servidor de base de datos ni internet, salvo para instalar.

**Requisitos:** Python **3.12 o superior** y Git.

| Sistema | Cómo tener Python 3.12 o superior |
|---|---|
| Windows | Instalador de [python.org](https://www.python.org/downloads/), marcando “Add python.exe to PATH”. Queda el comando `py` |
| macOS | Instalador de [python.org](https://www.python.org/downloads/). El `python3` que trae macOS es 3.9 y no sirve: el programa avisa y se cierra |
| Linux | El de la distribución, si es 3.12 o superior. En Ubuntu y Debian además: `sudo apt install python3-venv` |

**Versión entregada:** el último commit de `main` hasta el **5-10-2026 a las 23:00, hora de Chile**.
El `git checkout` de abajo deja el repositorio exactamente en esa versión.

**Linux y macOS (Terminal):**

```bash
git clone https://github.com/leonardoguerrerodev/POO-Viajes-Aventura.git
cd POO-Viajes-Aventura
git checkout $(git rev-list -n 1 --before="2026-10-05 23:00:00 -0300" main)
python3 -m venv .venv
source .venv/bin/activate
pip install --only-binary :all: --require-hashes -r requirements.txt
python pruebas/verificar.py --rapido
python main.py
```

**Windows (PowerShell):**

```powershell
git clone https://github.com/leonardoguerrerodev/POO-Viajes-Aventura.git
cd POO-Viajes-Aventura
git checkout (git rev-list -n 1 --before="2026-10-05 23:00:00 -0300" main)
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install --only-binary :all: --require-hashes -r requirements.txt
python pruebas/verificar.py --rapido
python main.py
```

En el Símbolo del sistema (`cmd`), el entorno se activa con `.venv\Scripts\activate.bat`; el resto es
igual.

**Qué hace cada paso:**
- `git checkout …` deja el código en la versión entregada.
- `venv` crea un Python aislado para el proyecto, en la carpeta `.venv`. Se activa una vez por
  terminal; mientras está activo, el comando es `python` en los tres sistemas.
- `pip install` instala las dos librerías del proyecto, `argon2-cffi` (contraseñas) y `cryptography`
  (cifrado), más las tres de las que dependen. Cada archivo se verifica contra su hash: se instala
  exactamente lo que se probó.
- `python pruebas/verificar.py --rapido` corre las pruebas, menos las mutaciones, sobre una base
  temporal; debe terminar en “ninguna falla”. No hace falta para usar el programa: el programa no
  depende de las pruebas.
- `python main.py` abre el programa.

**Para volver a ejecutar** otro día basta con entrar a la carpeta, activar el entorno
(`source .venv/bin/activate` o `.venv\Scripts\Activate.ps1`) y correr `python main.py`.

## 2. Primer uso

`python main.py`, con el entorno virtual activado (§1), abre una pantalla previa con dos caminos:

```
1. Entrar al sistema        la base real (viajes.db)
2. Modo demostración        base temporal con datos de ejemplo; se borra al salir
```

**Para probar todo sin ingresar datos: opción 2, “Modo demostración”.**
- Carga 5 destinos, 3 paquetes (2 publicados y 1 en borrador), 1 socio y 2 clientes con reservas.
- Muestra en pantalla las cuentas de prueba con sus contraseñas, generadas al azar en esa ejecución:
  no hay ninguna escrita en el código.
- Ofrece “Entrar como socio” y “Entrar como cliente”. Las dos pasan por el mismo inicio de sesión que
  el resto del sistema, así que los permisos de cada rol se aplican igual.
- Todo ocurre en una carpeta temporal. Al salir se borra, y **la base y la clave reales no se tocan**.
- Para recorrer el CRUD completo:
  - como socio: editar un destino, publicar el paquete en borrador, cambiar un cupo y ver las
    reservas de un paquete;
  - como cliente: reservar el paquete “Altiplano y desierto”, que tiene un solo lugar libre, por más
    personas (lo rechaza la regla R14 del caso; las 17 reglas están en el informe, §2.1), y anular
    una reserva.

**Opción 1, “Entrar al sistema”:**
- **No hay usuarios ni contraseñas en el código.** La primera vez, la base está vacía y el programa
  pide crear la cuenta del primer administrador: un correo y una contraseña de 12 caracteres o más,
  distinta del correo, que no sea de las más comunes, con al menos 5 caracteres distintos, sin
  secuencias como `1234` o `abcd` y sin partes del correo (en los clientes, tampoco del nombre ni del
  teléfono). No se exigen mayúsculas ni símbolos.
- Después aparece la pantalla de inicio:
  - **1. Iniciar sesión (socios y clientes):** la misma entrada para los dos roles; la cuenta decide
    qué menú aparece;
  - **2. Registrarse como cliente:** pide nombre, RUT, correo, teléfono y contraseña, después de
    mostrar el aviso de datos personales;
  - **3. Ver los paquetes disponibles,** sin iniciar sesión.
- El administrador es un socio de la agencia (el caso no tiene otro personal). Crea las cuentas de los
  otros socios en “Cuentas → Crear la cuenta de un socio”.
- **Qué hace cada rol:**
  - el administrador crea destinos y paquetes de 2 a 5 destinos, los publica y ve sus reservas. Además
    administra la seguridad: crea y desactiva cuentas, respalda la base, rota la clave de cifrado y
    lee el registro de auditoría. Al entrar, se le avisa si hubo cuentas bloqueadas en las últimas 24
    horas;
  - el cliente reserva, ve sus reservas y las anula, y actualiza su nombre y su teléfono. Sus datos
    se muestran enmascarados, también para él: `12.***.***-5`, `j*******9@g****.com`, `+56 9 ******* 4`.
- Toda opción que pide un id muestra antes la lista correspondiente.
- **`x`** en cualquier dato cancela la acción sin guardar; la primera pregunta de cada acción lo
  recuerda. Lo que no se puede deshacer pide confirmación (eliminar, publicar, anular una reserva, crear
  o desactivar una cuenta, rotar la clave). La sesión se cierra sola tras 10 minutos sin uso.

**Dónde quedan los datos:**

| Archivo | Ubicación | Qué es |
|---|---|---|
| `viajes.db` | Junto al código | La base de datos |
| `respaldos/` | Junto al código | Copias de la base, desde la opción “Respaldar la base de datos” del administrador |
| `clave.env` | Linux y macOS: `~/.config/viajes-aventura/`<br>Windows: `C:\Users\<usuario>\.config\viajes-aventura\` | La clave que cifra el RUT y el teléfono. Se crea con el primer cliente, fuera del proyecto |
| `clave.env.anterior-<fecha>` | Junto a `clave.env` | La clave anterior, si se rotó desde el menú. Sirve para leer los respaldos hechos antes de la rotación; si no hay ninguno, se puede borrar |

- **La clave se respalda aparte:** sin ella, los RUT y teléfonos guardados no se pueden leer, y el
  programa se niega a crear otra si ya hay datos cifrados.
- **Permisos:** en Linux y macOS, la base, los respaldos y la clave quedan en `0600` (solo su
  dueño). En Windows esos permisos no existen: la protección la da la carpeta del usuario, así que
  el proyecto debe clonarse dentro de ella (por ejemplo, en `Documentos`).
- Para **empezar de cero**, se borran `viajes.db` y `clave.env`.

## 3. Verificar

Todas las pruebas están en un solo archivo, ordenado por la rúbrica. Con el entorno activado, en
cualquiera de los tres sistemas:

```bash
python pruebas/verificar.py            # interfaz: elige la sección y la corre paso a paso
python pruebas/verificar.py --todo     # todo, incluidas 45 mutaciones (unos 6 minutos)
python pruebas/verificar.py --rapido   # todo menos las mutaciones (menos de 1 minuto)
```

**Secciones:**
- reglas del negocio;
- POO, persistencia y CRUD;
- autenticación y credenciales;
- datos personales;
- seguridad;
- recorrido del menú real, que reescribe [`docs/SALIDA_TERMINAL.md`](docs/SALIDA_TERMINAL.md);
- diagrama de clases contra código;
- mutaciones.

**Cómo leer el resultado:** cada afirmación se imprime recién después de comprobarse, con su indicador
de la rúbrica. Qué prueba cada una, y dónde está el control en el código, se explica en
[`pruebas/README.md`](pruebas/README.md).

**Dónde corren:** todas, en cada envío al repositorio, en Windows, macOS y Linux con Python 3.12 y
3.14 (las mutaciones, en Linux). Ninguna toca `viajes.db` ni la clave real: trabajan sobre archivos
temporales.

## 4. Seguridad en breve

| Riesgo | Control |
|---|---|
| Contraseñas robadas de la base | Solo se guarda su resumen Argon2id (argon2-cffi), con sal propia; la política rechaza contraseñas comunes, secuencias y datos de la propia persona |
| Adivinar contraseñas | Bloqueo progresivo de 5, 15 y 60 minutos, también al cambiarla; el mismo mensaje y la misma demora para todo fallo |
| Datos personales expuestos | RUT y teléfono cifrados con Fernet (AES + HMAC); la clave vive fuera del proyecto y se puede rotar; en pantalla, RUT, correo y teléfono enmascarados |
| Acceso indebido | Permisos por rol revisados en el dominio, solo con sesión iniciada; la sesión vence a los 10 minutos; las cuentas se desactivan |
| Inyección SQL | Todas las consultas son texto literal con parámetros `?` |
| Rastro de lo ocurrido | Registro de auditoría de actividad y seguridad, sin datos personales, legible por los socios |

La evaluación completa, con los hallazgos, su decisión y los límites del modelo de amenazas, está en
[`docs/AUDITORIA.md`](docs/AUDITORIA.md); la conservación de los datos y qué hacer ante un incidente, en
[`docs/PRIVACIDAD.md`](docs/PRIVACIDAD.md).

## 5. Problemas frecuentes

| Mensaje | Causa | Solución |
|---|---|---|
| `Faltan las librerías del proyecto` | El entorno virtual no está activado | Activarlo (sección 1) y volver a ejecutar |
| `requiere Python 3.12 o superior` | Se usó un Python antiguo (en macOS, el del sistema) | Instalar Python de python.org y crear el entorno con ese |
| `python` o `py` “no se reconoce” (Windows) | Python no quedó en el PATH | Reinstalar marcando “Add python.exe to PATH” |
| PowerShell no deja ejecutar `Activate.ps1` | La política de scripts de Windows | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` y activar de nuevo |
| `ensurepip is not available` (Ubuntu o Debian) | Falta el módulo `venv` | `sudo apt install python3-venv` y crear el entorno de nuevo |
| `Password input may be echoed` | El programa se abrió desde la consola de un editor, no desde una terminal | Ejecutarlo en la terminal del sistema, para que la contraseña no se vea |

## 6. Estructura

| Ruta | Contenido |
|---|---|
| [`viajes.py`](viajes.py) | El producto: las clases del diagrama, su persistencia (todo el SQL), la autenticación y el cifrado. Sin pruebas |
| [`main.py`](main.py) | Menú de terminal, pantalla previa y modo demostración. Sin SQL |
| [`requirements.txt`](requirements.txt) | Las dependencias, con versión exacta y los hashes de Windows, macOS y Linux |
| [`diagramas/`](diagramas/) | Diagrama de clases (`clases.puml`, la fuente), casos de uso y BPMN, con sus generadores |
| [`pruebas/`](pruebas/) | `verificar.py`, todas las pruebas por indicador de la rúbrica, y su índice [`README.md`](pruebas/README.md) |
| [`docs/Informe_Tecnico.pdf`](docs/Informe_Tecnico.pdf) | El informe técnico entregado |
| [`docs/AUDITORIA.md`](docs/AUDITORIA.md) | Evaluación de la seguridad: hallazgos de la IA y propios, su decisión, pruebas de mutación, límites del modelo de amenazas y alcances futuros |
| [`docs/PRIVACIDAD.md`](docs/PRIVACIDAD.md) | Conservación de los datos, incidentes (Ley 21.719), derechos de los clientes y qué protege el cifrado |
| [`docs/ANALISIS_IA.md`](docs/ANALISIS_IA.md) | Cada contribución de la IA, adoptada, modificada o descartada, con su motivo |
| [`docs/SALIDA_TERMINAL.md`](docs/SALIDA_TERMINAL.md) | Una sesión real del menú con los dos roles, generada por las pruebas |
| [`docs/EVIDENCIA_RUBRICA.md`](docs/EVIDENCIA_RUBRICA.md) | Dónde está la evidencia de cada indicador de la rúbrica: la guía para corregir |
| [`docs/transcripciones_ia/`](docs/transcripciones_ia/) | Prompts y respuestas íntegros de las conversaciones con la IA que el análisis y la auditoría citan |
| [`.github/workflows/pruebas.yml`](.github/workflows/pruebas.yml) | El workflow que corre las pruebas en Windows, macOS y Linux en cada envío |

## Autoría y uso

Trabajo académico individual de Leonardo Guerrero para la Evaluación Sumativa 4 de Programación
Orientada a Objeto Seguro (TI3021), INACAP Valparaíso, 2026. El repositorio es público para que se pueda
revisar; no tiene licencia de reutilización.
