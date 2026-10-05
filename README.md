# Viajes Aventura

[![Pruebas](https://github.com/leonardoguerrerodev/POO-Viajes-Aventura/actions/workflows/pruebas.yml/badge.svg)](https://github.com/leonardoguerrerodev/POO-Viajes-Aventura/actions/workflows/pruebas.yml)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=leonardoguerrerodev_POO-Viajes-Aventura&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=leonardoguerrerodev_POO-Viajes-Aventura)

Sistema de gestión de destinos, paquetes turísticos y reservas para la agencia Viajes Aventura
(Valparaíso). Aplicación de terminal en Python con persistencia en `sqlite3`, autenticación con
contraseñas protegidas y cifrado de los datos personales del cliente.

Evaluación Sumativa 4 de Programación Orientada a Objeto Seguro (TI3021), INACAP Valparaíso.
Trabajo individual de Leonardo Guerrero.

**Para el corrector:** [`ENTREGA.md`](ENTREGA.md) enlaza la evidencia de cada indicador de la rúbrica.

## 1. Instalar y ejecutar

Funciona igual en **Windows, macOS y Linux**: el workflow «Pruebas» lo comprueba en los tres en cada
envío al repositorio. No necesita un servidor de base de datos ni internet, salvo para instalar.

**Requisitos:** Python **3.12 o superior** y Git.

| Sistema | Cómo tener Python 3.12 o superior |
|---|---|
| Windows | Instalador de [python.org](https://www.python.org/downloads/), marcando «Add python.exe to PATH». Queda el comando `py` |
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
python viajes.py
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
python viajes.py
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
- `python viajes.py` es la autoverificación de las reglas del negocio, sobre una base temporal:
  debe terminar en `OK`.
- `python main.py` abre el programa.

**Para volver a ejecutar** otro día basta con entrar a la carpeta, activar el entorno
(`source .venv/bin/activate` o `.venv\Scripts\Activate.ps1`) y correr `python main.py`.

## 2. Primer uso

`python main.py` abre una pantalla previa con dos caminos:

```
1. Entrar al sistema        la base real (viajes.db)
2. Modo demostración        base temporal con datos de ejemplo; se borra al salir
```

**Para probar todo sin ingresar datos: opción 2, «Modo demostración».**
- Carga 5 destinos, 3 paquetes (2 publicados y 1 en borrador), 1 socio y 2 clientes con reservas.
- Muestra en pantalla las cuentas de prueba con sus contraseñas, generadas al azar en esa ejecución:
  no hay ninguna escrita en el código.
- Ofrece «Entrar como socio» y «Entrar como cliente». Las dos pasan por el mismo inicio de sesión que
  el resto del sistema, así que los permisos de cada rol se aplican igual.
- Todo ocurre en una carpeta temporal. Al salir se borra, y **la base y la clave reales no se tocan**.
- Para recorrer el CRUD completo:
  - como socio: editar un destino, publicar el paquete en borrador, cambiar un cupo y ver las
    reservas de un paquete;
  - como cliente: reservar el paquete «Altiplano y desierto», que tiene un solo lugar libre, por más
    personas (lo rechaza la regla R14), y anular una reserva.

**Opción 1, «Entrar al sistema»:**
- **No hay usuarios ni contraseñas en el código.** La primera vez, la base está vacía y el programa
  pide crear la cuenta del primer administrador: un correo y una contraseña de 12 caracteres o más,
  distinta del correo, que no sea de las más comunes y con al menos 5 caracteres distintos.
- Después aparece la pantalla de inicio:
  - **1. Iniciar sesión (socios y clientes):** la misma entrada para los dos roles; la cuenta decide
    qué menú aparece;
  - **2. Registrarse como cliente:** pide nombre, RUT, correo, teléfono y contraseña, después de
    mostrar el aviso de datos personales;
  - **3. Ver los paquetes disponibles,** sin iniciar sesión.
- El administrador es un socio de la agencia (el caso no tiene otro personal). Crea las cuentas de los
  otros socios en «Cuentas → Crear la cuenta de un socio».
- **Qué hace cada rol:**
  - el administrador crea destinos y paquetes de 2 a 5 destinos, los publica y ve sus reservas;
  - el cliente reserva, ve sus reservas y las anula.
- Toda opción que pide un id muestra antes la lista correspondiente.
- **`x`** en cualquier dato cancela la acción sin guardar. La sesión se cierra sola tras 10 minutos sin
  uso.

**Dónde quedan los datos:**

| Archivo | Ubicación | Qué es |
|---|---|---|
| `viajes.db` | Junto al código | La base de datos |
| `respaldos/` | Junto al código | Copias de la base, desde la opción «Respaldar la base de datos» del administrador |
| `clave.env` | Linux y macOS: `~/.config/viajes-aventura/`<br>Windows: `C:\Users\<usuario>\.config\viajes-aventura\` | La clave que cifra el RUT y el teléfono. Se crea con el primer cliente, fuera del proyecto |

- **La clave se respalda aparte:** sin ella, los RUT y teléfonos guardados no se pueden leer, y el
  programa se niega a crear otra si ya hay datos cifrados.
- **Permisos:** en Linux y macOS, la base, los respaldos y la clave quedan en `0600` (solo su
  dueño). En Windows esos permisos no existen: la protección la da la carpeta del usuario, así que
  el proyecto debe clonarse dentro de ella (por ejemplo, en `Documentos`).
- Para **empezar de cero**, se borran `viajes.db` y `clave.env`.

## 3. Verificar

Con el entorno activado, en cualquiera de los tres sistemas:

```bash
python viajes.py                     # autoverificación de las reglas R1 a R17: imprime OK
python pruebas/prueba_rubrica.py     # una afirmación verificable por indicador de la rúbrica
python herramientas/uml_vs_codigo.py # el diagrama de clases contra el código: 0 diferencias
python herramientas/driver.py        # recorre el menú con los dos roles y reescribe docs/SALIDA_TERMINAL.md
python herramientas/mutaciones.py    # rompe 28 reglas a propósito y exige que alguna prueba lo detecte
```

Las cinco corren en cada envío al repositorio: las cuatro primeras en Windows, macOS y Linux con
Python 3.12 y 3.14, y las mutaciones en Linux (tardan unos minutos). Ninguna toca `viajes.db` ni la
clave real: trabajan sobre archivos temporales.

## 4. Problemas frecuentes

| Mensaje | Causa | Solución |
|---|---|---|
| `Faltan las librerías del proyecto` | El entorno virtual no está activado | Activarlo (sección 1) y volver a ejecutar |
| `requiere Python 3.12 o superior` | Se usó un Python antiguo (en macOS, el del sistema) | Instalar Python de python.org y crear el entorno con ese |
| `python` o `py` «no se reconoce» (Windows) | Python no quedó en el PATH | Reinstalar marcando «Add python.exe to PATH» |
| PowerShell no deja ejecutar `Activate.ps1` | La política de scripts de Windows | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` y activar de nuevo |
| `ensurepip is not available` (Ubuntu o Debian) | Falta el módulo `venv` | `sudo apt install python3-venv` y crear el entorno de nuevo |
| `Password input may be echoed` | El programa se abrió desde la consola de un editor, no desde una terminal | Ejecutarlo en la terminal del sistema, para que la contraseña no se vea |

## 5. Estructura

| Ruta | Contenido |
|---|---|
| `viajes.py` | Dominio: las clases del diagrama, su persistencia (todo el SQL) y la autoverificación |
| `main.py` | Menú de terminal, sin SQL |
| `requirements.txt` | Las dependencias, con versión exacta y los hashes de Windows, macOS y Linux |
| `diagramas/` | Diagrama de clases (`clases.puml`, la fuente), casos de uso y BPMN, con sus generadores |
| `herramientas/` | Driver del menú, comparador del diagrama con el código y pruebas de mutación |
| `pruebas/` | Prueba por indicador de la rúbrica |
| `docs/` | Auditoría de seguridad, análisis del uso de IA, sesión real del menú, transcripciones de la IA e informe técnico |
