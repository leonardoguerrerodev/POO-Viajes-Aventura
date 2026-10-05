"""Viajes Aventura: destinos, paquetes turísticos y reservas.

Implementación en Python del diagrama de clases del informe (diagramas/clases.puml). El archivo
contiene, en este orden:

    1. Validaciones y autorización compartidas
    2. Esquema y conexión a la base de datos (sqlite3, biblioteca estándar)
    3. Las clases del diagrama, cada una con su persistencia (CRUD)

Es el producto: no contiene pruebas. Cada control (permisos, validaciones, cifrado, transacciones)
vive aquí, y se comprueba desde afuera con pruebas/verificar.py.

Uso:
    python main.py                 -> la aplicación
    python pruebas/verificar.py    -> las pruebas, paso a paso

Un solo archivo para el dominio y otro para el menú: es la estructura que pidió el docente en la
Unidad 2 (no modularizar clase por clase).
"""

import json                                 # lista de ids como un solo parámetro SQL (json_each)
import os                                   # permisos 0600 de la base y lectura del entorno
import re                                   # patrones de correo, RUT y teléfono
import secrets                              # contraseña aleatoria del hash señuelo
import shutil                               # copia de la clave anterior al rotarla
import sqlite3                              # la base de datos: un archivo, sin servidor
import sys                                  # versión de Python y salida con mensaje claro
import unicodedata                          # quita tildes al comparar nombres de destinos (RF-DES-02)
from abc import ABC, abstractmethod         # Usuario es abstracta: no existe «solo un usuario»
from contextlib import contextmanager       # `with conectar()`: abre y siempre cierra la conexión
from datetime import date, datetime, timedelta, timezone  # fechas, y el bloqueo en hora UTC
from enum import Enum                       # estado de la reserva: un valor mal escrito falla al crearse
from functools import lru_cache             # la clave de cifrado se lee una sola vez
from pathlib import Path                    # rutas que funcionan igual en Windows, macOS y Linux

# Antes de cualquier otra cosa, un mensaje claro en vez de una traza: macOS trae un python3 3.9, y
# sin el entorno virtual activado faltan las librerías (ver README, «Instalar y ejecutar»).
if sys.version_info < (3, 12):
    sys.exit(f"Viajes Aventura requiere Python 3.12 o superior; este es {sys.version.split()[0]}.")
try:
    from argon2 import PasswordHasher       # Argon2id, librería especializada de PyPI (G.17)
    from argon2.exceptions import InvalidHashError, VerificationError
    from cryptography.fernet import Fernet, InvalidToken, MultiFernet  # cifrado autenticado: AES + HMAC (I.19)
except ModuleNotFoundError:
    sys.exit("Faltan las librerías del proyecto: active el entorno virtual (.venv) e instale\n"
             "requirements.txt como indica el README, sección «Instalar y ejecutar».")

# =====================================================================
# 1. VALIDACIONES Y AUTORIZACIÓN COMPARTIDAS
# =====================================================================

# Cada entero que llega del usuario tiene techo: sin techo, un número de 25 dígitos
# termina en OverflowError al guardarlo (regla 8 de EcoTech).
COSTO_MAXIMO = 100_000_000
DURACION_MAXIMA = 365
CUPO_MAXIMO = 1000
MARGEN_PROPUESTO, MARGEN_MAXIMO = 20, 1000      # porcentaje (R6, S-05, RF-PAQ-11)
DESTINOS_MINIMO, DESTINOS_MAXIMO = 2, 5         # R3
# El precio más alto posible: cinco destinos al costo máximo con el margen máximo. El techo del total
# de una reserva se deriva de aquí, para que nunca se guarde una reserva que después no se pueda leer.
PRECIO_MAXIMO = COSTO_MAXIMO * DESTINOS_MAXIMO * (100 + MARGEN_MAXIMO) // 100

# Correo: lineal, sin retroceso exponencial (regla 11 de EcoTech). RUT con o sin puntos y guion.
PATRON_CORREO = re.compile(r"[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+")
PATRON_RUT = re.compile(r"(\d{1,2})\.?(\d{3})\.?(\d{3})-?([\dkK])", re.ASCII)
PATRON_TELEFONO = re.compile(r"(?:\+?56)?([2-9]\d{8})", re.ASCII)
SEPARADORES = re.compile(r"[\s()\-.]")

CLAVE_MINIMA, CLAVE_MAXIMA = 12, 128          # RF-SEG-04; el tope evita hashear textos enormes
# Contraseñas de 12 o más caracteres que igual se adivinan primero (H-16). Además se exigen al
# menos 5 caracteres distintos, que descarta «aaaaaaaaaaaa» o «121212121212».
CLAVES_COMUNES = frozenset({
    "contraseña123", "contrasena123", "contraseña1234", "contrasena1234", "password1234",
    "password12345", "passwordpassword", "123456789012", "1234567890123", "12345678901234",
    "qwertyuiopas", "qwerty123456", "abcdefghijkl", "abc123456789", "iloveyou1234",
    "administrador", "admin1234567", "viajesaventura", "viajes123456", "valparaiso123",
    "chile1234567", "bienvenido123", "123456789abc"})
CLAVE_DISTINTOS = 5

# Argon2id con time_cost=4 y 64 MiB: unos 130 ms por verificación, dentro de lo que pide
# RNF-REN-02 (entre 0,1 y 1 segundo). Con los valores por omisión medía 98 ms.
HASHER = PasswordHasher(time_cost=4)

# La clave que cifra RUT y teléfono vive fuera del código, de la base y de la carpeta del proyecto
# (S-12, H-01 de la auditoría): en el entorno o en la carpeta de configuración del usuario, con
# permisos 0600. Una copia de la carpeta del proyecto ya no se lleva juntos el dato y su clave.
RUTA_CLAVE = Path.home() / ".config" / "viajes-aventura" / "clave.env"
VARIABLE_CLAVE = "VIAJES_CLAVE_DATOS"
CAMPO_NOMBRE = "El nombre"

# Acciones que un rol puede tener. Un texto fuera de este conjunto es un error de
# programación y se rechaza: así un permiso mal escrito no se convierte en un «no» silencioso.
ACCIONES = frozenset({"catalogo", "ver_reservas", "cuentas", "respaldo", "clave", "auditoria",
                      "reservar"})


class ReglaNegocioError(Exception):
    """Rechazo de una regla del negocio, con el código de la regla que lo causó (R1 a R17).

    El menú muestra este mensaje tal cual: es un error esperado. Cualquier otro error
    recibe un mensaje genérico, sin traza (RNF-SEG-05).
    """

    def __init__(self, regla: str, mensaje: str):
        super().__init__(mensaje)
        self.__regla = regla               # privado, como todo atributo del modelo (G.13)

    def obtener_regla(self) -> str:
        return self.__regla


def texto(valor: str, campo: str, maximo: int = 120) -> str:
    """Valida un texto que viene del usuario y lo devuelve sin espacios en los extremos."""
    if not isinstance(valor, str):
        raise TypeError(f"{campo} debe ser texto")
    limpio = valor.strip()
    if not limpio:
        raise ValueError(f"{campo} no puede estar vacío")
    if len(limpio) > maximo:
        raise ValueError(f"{campo} supera los {maximo} caracteres")
    # isprintable rechaza saltos de línea, caracteres de control y marcas bidireccionales:
    # el menú vuelve a imprimir estos textos en la terminal (regla 11 de EcoTech).
    if not limpio.isprintable():
        raise ValueError(f"{campo} contiene caracteres no permitidos")
    return limpio


def entero(valor: int, campo: str, minimo: int, maximo: int, regla: str) -> int:
    """Valida tipo y rango de un entero. El tipo es TypeError; el rango es una regla del negocio."""
    # bool es subclase de int: sin esta exclusión, True pasaría como 1 (lección L3 de la ES2).
    if not isinstance(valor, int) or isinstance(valor, bool):
        raise TypeError(f"{campo} debe ser un número entero")
    if not minimo <= valor <= maximo:
        raise ReglaNegocioError(regla, f"{campo} debe estar entre {minimo:,} y {maximo:,}".replace(",", "."))
    return valor


def fecha(valor: date, campo: str) -> date:
    """Una fecha sin hora. datetime hereda de date, pero compararía también la hora."""
    if not isinstance(valor, date) or isinstance(valor, datetime):
        raise TypeError(f"{campo} debe ser una fecha")
    return valor


def pesos(monto: int) -> str:
    """$1.050.000, como la planilla de la agencia (RNF-USA-02)."""
    return "$" + f"{monto:,}".replace(",", ".")


def normalizar(nombre: str) -> str:
    """Forma comparable de un nombre: sin tildes, sin mayúsculas y con un solo espacio entre palabras.

    «Valle del  Elquí» y «valle del elqui» dan lo mismo (RF-DES-02). La IA propuso mayúsculas y
    espacios; las tildes se agregaron porque el criterio de aceptación las exige.
    """
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", nombre)
                         if not unicodedata.combining(c))
    return " ".join(sin_tildes.casefold().split())


def validar_correo(correo: str) -> str:
    """El correo en minúsculas: «Carolina@Correo.cl» y «carolina@correo.cl» son la misma cuenta (R9)."""
    correo = texto(correo, "El correo", 254).lower()     # el tope va antes de la regex
    if not PATRON_CORREO.fullmatch(correo):
        raise ValueError("El correo no tiene un formato válido")
    return correo


def validar_rut(rut: str) -> str:
    """El RUT en forma canónica (12345678-5), con su dígito verificador módulo 11 (RF-RES-03).

    Ningún mensaje repite el RUT ingresado: es un dato que R17 manda resguardar (RF-SEG-13).
    """
    m = PATRON_RUT.fullmatch(texto(rut, "El RUT", 20))
    if not m:
        raise ValueError("El RUT no tiene un formato válido")
    cuerpo, dv = "".join(m.groups()[:3]), m.group(4).upper()
    if int(cuerpo) == 0:                    # 0.000.000-0 cumple el módulo 11, pero no es un RUT
        raise ValueError("El RUT no es válido")
    suma = sum(int(d) * (2 + i % 6) for i, d in enumerate(reversed(cuerpo)))
    esperado = {10: "K", 11: "0"}.get(11 - suma % 11, str(11 - suma % 11))
    if dv != esperado:
        raise ValueError("El RUT no es válido: revise el dígito verificador")
    return f"{int(cuerpo)}-{dv}"


def validar_telefono(telefono: str) -> str:
    """Los 9 dígitos de un teléfono chileno, sin prefijo ni separadores. El mensaje no lo repite."""
    m = PATRON_TELEFONO.fullmatch(SEPARADORES.sub("", texto(telefono, "El teléfono", 20)))
    if not m:
        raise ValueError("El teléfono no es válido: use los 9 dígitos de un número chileno")
    return m.group(1)


def _leer_clave(ruta: Path) -> str | None:
    """La clave de un archivo «VIAJES_CLAVE_DATOS=...». Si volvió de un respaldo con permisos
    abiertos, se cierran."""
    if os.name == "posix" and ruta.stat().st_mode & 0o077:
        os.chmod(ruta, 0o600)
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        nombre, _, valor = linea.partition("=")
        if nombre.strip() == VARIABLE_CLAVE:
            return valor.strip()
    return None


def _escribir_clave(ruta: Path, clave: str) -> None:
    """O_EXCL: si dos procesos la crean a la vez, uno falla en vez de pisar la clave del otro."""
    ruta.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as archivo:
        archivo.write(f"{VARIABLE_CLAVE}={clave}\n")


def _claves_de_rotacion() -> list[Path]:
    """Claves nuevas de una rotación que se cortó antes de reemplazar el archivo (ver
    rotar_clave_de_datos): con ellas también se lee, para que ningún dato quede ilegible."""
    return sorted(RUTA_CLAVE.parent.glob(RUTA_CLAVE.name + ".nueva-*")) if RUTA_CLAVE.parent.exists() else []


def _claves_vigentes() -> list[str]:
    """La clave principal, del entorno o del archivo; la crea en el primer uso (S-12). Después,
    las de una rotación cortada, que solo sirven para leer."""
    clave = os.environ.get(VARIABLE_CLAVE)
    if not clave and RUTA_CLAVE.exists():
        clave = _leer_clave(RUTA_CLAVE)
    if not clave:
        # Sin la clave, los RUT ya guardados son ilegibles: crear otra los perdería para siempre.
        # La condición es que haya datos cifrados, no usuarios: el primer administrador no tiene
        # RUT, y la clave se crea recién con el primer cliente.
        with conectar() as con:
            cifrados = con.execute("SELECT 1 FROM usuario WHERE rut_cifrado IS NOT NULL LIMIT 1"
                                   ).fetchone()
        if cifrados:
            raise RuntimeError("Falta la clave de cifrado de los datos personales")
        clave = Fernet.generate_key().decode()
        _escribir_clave(RUTA_CLAVE, clave)
    return [clave] + [c for ruta in _claves_de_rotacion() if (c := _leer_clave(ruta))]


@lru_cache(maxsize=1)
def cifrador() -> MultiFernet:
    """Cifra siempre con la clave principal; para leer, prueba también las de una rotación cortada."""
    return MultiFernet([Fernet(c.encode()) for c in _claves_vigentes()])


def cifrar(valor: str) -> str:
    return cifrador().encrypt(valor.encode()).decode()


def descifrar(token: str) -> str:
    """Un dato alterado o cifrado con otra clave da error, nunca un dato falso (RNF-SEG-02)."""
    try:
        return cifrador().decrypt(token.encode()).decode()
    except InvalidToken:
        raise ValueError("Un dato personal no se pudo leer: la clave no corresponde "
                         "o el dato fue alterado") from None


def rotar_clave_de_datos(solicitante: "Usuario") -> tuple[int, str]:
    """Cambia la clave que cifra el RUT y el teléfono, y vuelve a cifrar a todos los clientes (RF-SEG-15).

    Para cuando la clave pudo filtrarse: un respaldo copiado, un socio que dejó la agencia. El orden
    evita que un corte deje datos ilegibles:
      1. la clave nueva se escribe aparte (clave.env.nueva-<fecha>, 0600);
      2. todos los RUT y teléfonos se vuelven a cifrar en una sola transacción: si algo falla, no
         cambia nada y la clave nueva se descarta;
      3. la clave vieja se archiva (clave.env.anterior-<fecha>, para leer respaldos anteriores) y la
         nueva toma su lugar con os.replace, que es atómico.
    Si el programa se corta entre 2 y 3, cifrador() también lee con la clave nueva.
    Devuelve cuántos clientes se volvieron a cifrar y el nombre del archivo de la clave anterior.
    """
    autorizar(solicitante, "clave")
    if os.environ.get(VARIABLE_CLAVE):
        raise RuntimeError("La clave viene de la variable de entorno: se rota donde se define")
    vigentes = [Fernet(c.encode()) for c in _claves_vigentes()]
    sello = f"{datetime.now(timezone.utc):%Y%m%d_%H%M%S_%f}"
    nueva, ruta_nueva = Fernet.generate_key().decode(), RUTA_CLAVE.with_name(f"{RUTA_CLAVE.name}.nueva-{sello}")
    _escribir_clave(ruta_nueva, nueva)
    rotador = MultiFernet([Fernet(nueva.encode()), *vigentes])
    try:
        with conectar() as con:
            filas = con.execute("SELECT id, rut_cifrado, telefono_cifrado FROM usuario"
                                " WHERE rut_cifrado IS NOT NULL").fetchall()
            for fila in filas:
                try:
                    rut = rotador.rotate(fila["rut_cifrado"].encode()).decode()
                    telefono = rotador.rotate(fila["telefono_cifrado"].encode()).decode()
                except InvalidToken:
                    raise ValueError(f"El dato cifrado de la cuenta {fila['id']} está alterado: la"
                                     " clave no se cambió") from None
                con.execute("UPDATE usuario SET rut_cifrado = ?, telefono_cifrado = ? WHERE id = ?",
                            (rut, telefono, fila["id"]))
            registrar_evento(con, solicitante.obtener_id(), "clave.rotar", f"{len(filas)} clientes")
    except BaseException:
        ruta_nueva.unlink(missing_ok=True)
        raise
    anterior = RUTA_CLAVE.with_name(f"{RUTA_CLAVE.name}.anterior-{sello}")
    shutil.copy2(RUTA_CLAVE, anterior)
    os.replace(ruta_nueva, RUTA_CLAVE)
    for vieja in _claves_de_rotacion():      # de rotaciones cortadas antes: ya no hacen falta
        os.replace(vieja, vieja.with_name(vieja.name.replace(".nueva-", ".anterior-")))
    cifrador.cache_clear()
    return len(filas), anterior.name


def autorizar(solicitante: "Usuario", accion: str) -> None:
    """El permiso se revisa en el dominio, no solo en el menú (RF-SEG-05, decisión 6 del modelo)."""
    if accion not in ACCIONES:
        raise ValueError(f"Acción desconocida: {accion!r}")
    # Usuario se define más abajo; la función se llama recién en tiempo de ejecución.
    # Además del rol, exige una cuenta con sesión iniciada: un objeto armado a mano, sin pasar por
    # la contraseña, no tiene permisos «por cualquier vía» (RF-SEG-05, auditoría final, hallazgo 5).
    if (not isinstance(solicitante, Usuario) or not solicitante.tiene_sesion()
            or not solicitante.puede(accion)):
        raise PermissionError("No tiene permiso para esta operación")


# =====================================================================
# 2. BASE DE DATOS
# =====================================================================

# La base vive junto a este archivo, no en el directorio desde donde se ejecuta.
RUTA_ACTIVA = str(Path(__file__).with_name("viajes.db"))

# Las reglas que se pueden expresar en la base se repiten aquí (RNF-FIA-01): si un error del
# código dejara pasar un dato inválido, la base lo rechaza igual.
ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuario (
    id                INTEGER PRIMARY KEY,
    correo            TEXT    NOT NULL UNIQUE CHECK (correo = lower(correo)),          -- R9
    hash_clave        TEXT    NOT NULL CHECK (hash_clave LIKE '$argon2id$%'),         -- R10
    rol               TEXT    NOT NULL CHECK (rol IN ('CLIENTE', 'ADMINISTRADOR')),
    nombre            TEXT,
    rut_cifrado       TEXT,                                                         -- R17
    telefono_cifrado  TEXT,                                                         -- R17
    intentos_fallidos INTEGER NOT NULL DEFAULT 0 CHECK (intentos_fallidos >= 0),
    bloqueado_hasta   TEXT,
    bloqueos          INTEGER NOT NULL DEFAULT 0 CHECK (bloqueos >= 0),                -- H-17
    activa            INTEGER NOT NULL DEFAULT 1 CHECK (activa IN (0, 1)),          -- RF-SEG-14
    -- un cliente tiene sus tres datos personales; un administrador no tiene ninguno
    CHECK ((rol = 'CLIENTE') = (nombre IS NOT NULL AND rut_cifrado IS NOT NULL
                                AND telefono_cifrado IS NOT NULL)),
    CHECK (rol = 'CLIENTE' OR (nombre IS NULL AND rut_cifrado IS NULL
                               AND telefono_cifrado IS NULL))
);
CREATE TABLE IF NOT EXISTS destino (
    id                 INTEGER PRIMARY KEY,
    nombre             TEXT    NOT NULL,
    nombre_normalizado TEXT    NOT NULL UNIQUE,                                     -- R1
    zona               TEXT    NOT NULL,
    descripcion        TEXT    NOT NULL,
    duracion_dias      INTEGER NOT NULL CHECK (duracion_dias BETWEEN 1 AND 365),     -- R1
    costo_base         INTEGER NOT NULL CHECK (costo_base BETWEEN 1 AND 100000000),  -- R2
    disponible         INTEGER NOT NULL DEFAULT 1 CHECK (disponible IN (0, 1)),      -- R8
    fecha_costo        TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS paquete (
    id                 INTEGER PRIMARY KEY,
    nombre             TEXT    NOT NULL,
    fecha_salida       TEXT    NOT NULL,
    fecha_regreso      TEXT    NOT NULL,
    cupo_maximo        INTEGER NOT NULL CHECK (cupo_maximo BETWEEN 1 AND 1000),       -- R5
    margen             INTEGER NOT NULL CHECK (margen BETWEEN 0 AND 1000),           -- R6
    precio_por_persona INTEGER,                                                     -- R7
    publicado          INTEGER NOT NULL DEFAULT 0 CHECK (publicado IN (0, 1)),
    CHECK (fecha_regreso > fecha_salida),                                           -- R5
    CHECK (publicado = 0 OR precio_por_persona > 0)                                 -- R7
);
CREATE TABLE IF NOT EXISTS paquete_destino (
    paquete_id INTEGER NOT NULL REFERENCES paquete(id) ON DELETE CASCADE,
    destino_id INTEGER NOT NULL REFERENCES destino(id),         -- sin cascada: R8 lo protege
    PRIMARY KEY (paquete_id, destino_id)                        -- R3: sin destinos repetidos
);
CREATE TABLE IF NOT EXISTS reserva (
    id             INTEGER PRIMARY KEY,
    cliente_id     INTEGER NOT NULL REFERENCES usuario(id),
    paquete_id     INTEGER NOT NULL REFERENCES paquete(id),     -- sin cascada: RF-PAQ-09
    fecha_emision  TEXT    NOT NULL,                                                -- R12
    personas       INTEGER NOT NULL CHECK (personas BETWEEN 1 AND 1000),             -- R16
    total          INTEGER NOT NULL CHECK (total > 0),                              -- R13
    estado         TEXT    NOT NULL DEFAULT 'VIGENTE' CHECK (estado IN ('VIGENTE', 'ANULADA'))
);
-- Registro de auditoría (H-02): quién hizo qué y cuándo. Nunca datos personales ni contraseñas.
CREATE TABLE IF NOT EXISTS auditoria (
    id         INTEGER PRIMARY KEY,
    fecha_utc  TEXT    NOT NULL,
    usuario_id INTEGER REFERENCES usuario(id),          -- NULL: intento con un correo inexistente
    accion     TEXT    NOT NULL,
    detalle    TEXT    NOT NULL DEFAULT ''
);
-- Índices en las claves foráneas: el historial (R11) y el cupo (R14) se consultan por ellas.
CREATE INDEX IF NOT EXISTS ix_paquete_destino_destino ON paquete_destino(destino_id);
CREATE INDEX IF NOT EXISTS ix_reserva_cliente ON reserva(cliente_id);
CREATE INDEX IF NOT EXISTS ix_reserva_paquete ON reserva(paquete_id);
"""


def usar_base(ruta: str) -> None:
    """Cambia la base activa. La usan la autoverificación y las pruebas, con una base temporal."""
    global RUTA_ACTIVA
    RUTA_ACTIVA = ruta


@contextmanager
def conectar():
    """Abre una conexión dentro de una transacción BEGIN IMMEDIATE y siempre la cierra.

    Confirma al salir sin error y deshace si hubo una excepción: ninguna operación queda a medias.
    La transacción se abre explícitamente y antes de la primera consulta. En su modo por omisión,
    sqlite3 la abre recién en la primera escritura, y una consulta seguida de una escritura (revisar
    el cupo y reservar, revisar que un destino esté libre y borrarlo) no sería atómica (H-08 de la
    auditoría). IMMEDIATE toma el permiso de escritura al empezar: otra sesión espera su turno.
    Por eso nunca se abre una conexión dentro de otra: la de adentro esperaría a la de afuera.
    """
    con = sqlite3.connect(RUTA_ACTIVA, timeout=5, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")     # fuera de la transacción: dentro no tiene efecto
    try:
        con.execute("BEGIN IMMEDIATE")
        try:
            yield con
        except BaseException:
            if con.in_transaction:
                con.execute("ROLLBACK")
            raise
        if con.in_transaction:                  # executescript (crear_tablas) confirma por su cuenta
            con.execute("COMMIT")
    finally:
        con.close()


# Columnas agregadas después de la primera versión: una base creada antes las recibe al abrirse,
# con su valor por omisión y su CHECK. Texto literal, como todo el SQL.
MIGRACIONES = (
    ("bloqueos", "ALTER TABLE usuario ADD COLUMN bloqueos INTEGER NOT NULL DEFAULT 0"
                 " CHECK (bloqueos >= 0)"),
    ("activa", "ALTER TABLE usuario ADD COLUMN activa INTEGER NOT NULL DEFAULT 1"
               " CHECK (activa IN (0, 1))"),
)


def crear_tablas() -> None:
    with conectar() as con:
        con.executescript(ESQUEMA)
    with conectar() as con:
        columnas = {fila["name"] for fila in con.execute("PRAGMA table_info(usuario)")}
        for columna, sql in MIGRACIONES:
            if columna not in columnas:
                con.execute(sql)
    try:
        os.chmod(RUTA_ACTIVA, 0o600)            # sqlite crea el archivo en 0644 (RNF-SEG-04)
    except OSError:
        print("   ! No se pudieron restringir los permisos de la base de datos.")


def registrar_evento(con: sqlite3.Connection, usuario_id: int | None, accion: str, detalle: str = "") -> None:
    """Agrega una línea al registro de auditoría, en la misma transacción de la operación (H-02).

    Si la operación se deshace, su registro también: el registro nunca dice algo que no ocurrió.
    El detalle lleva ids y montos, nunca RUT, teléfono, correo ni contraseña.
    """
    con.execute("INSERT INTO auditoria (fecha_utc, usuario_id, accion, detalle) VALUES (?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(timespec="seconds"), usuario_id, accion, detalle))


def consultar_auditoria(solicitante: "Usuario", limite: int = 30) -> list[tuple[str, str, str, str]]:
    """Los últimos eventos del registro de auditoría, del más reciente al más antiguo (RF-SEG-16).

    Es la pareja de registrar_evento(): lo que se escribe, un socio lo puede leer desde el menú.
    Cada fila: fecha UTC, cuenta que actuó (su correo, o «sin cuenta» si el correo no existía),
    acción y detalle, que solo lleva ids y montos.
    """
    autorizar(solicitante, "auditoria")
    limite = entero(limite, "La cantidad de eventos", 1, 1000, "RF-SEG-16")
    with conectar() as con:
        filas = con.execute("SELECT a.fecha_utc, COALESCE(u.correo, '(sin cuenta)'), a.accion, a.detalle"
                            " FROM auditoria a LEFT JOIN usuario u ON u.id = a.usuario_id"
                            " ORDER BY a.id DESC LIMIT ?", (limite,)).fetchall()
    return [tuple(fila) for fila in filas]


def contar_bloqueos(solicitante: "Usuario", horas: int = 24) -> int:
    """Cuántas cuentas se bloquearon por contraseñas erróneas en las últimas horas (RF-SEG-16): el
    menú del socio lo avisa al entrar, para que nadie adivine contraseñas sin que se note."""
    autorizar(solicitante, "auditoria")
    desde = (datetime.now(timezone.utc) - timedelta(hours=horas)).isoformat(timespec="seconds")
    with conectar() as con:
        return con.execute("SELECT COUNT(*) FROM auditoria WHERE accion = 'sesion.bloqueo'"
                           " AND fecha_utc >= ?", (desde,)).fetchone()[0]


def exigir_una_fila(cur: sqlite3.Cursor, que: str) -> None:
    """Una escritura que no tocó ninguna fila no se informa como «guardado» (hallazgo 20)."""
    if cur.rowcount != 1:
        raise ValueError(f"El {que} ya no existe: otra sesión lo eliminó")


def hay_usuarios() -> bool:
    with conectar() as con:
        return con.execute("SELECT 1 FROM usuario LIMIT 1").fetchone() is not None


# =====================================================================
# 3. CLASES DEL MODELO
# =====================================================================


class Usuario(ABC):
    """tabla: usuario (una sola tabla para los dos roles). Credenciales, bloqueo y autenticación.

    Es abstracta: Cliente y Administrador heredan el inicio de sesión, escrito una sola vez, y
    cada uno responde distinto a puede() (polimorfismo).
    """

    # El contador de intentos fallidos vive solo en la base: lo suma y lo reinicia una sentencia
    # SQL (ver __intentar), y el objeto nunca lo necesita (decisión 11 del modelo).
    # El SQL completo es texto literal: ninguna consulta se arma pegando textos (RNF-SEG-03, bandit B608).
    SQL_INSERTAR = ("INSERT INTO usuario (correo, hash_clave, rol, nombre, rut_cifrado, telefono_cifrado)"
                    " VALUES (?, ?, ?, ?, ?, ?)")
    SQL_INSERTAR_SI_VACIA = ("INSERT INTO usuario (correo, hash_clave, rol, nombre, rut_cifrado,"
                             " telefono_cifrado) SELECT ?, ?, ?, ?, ?, ?"
                             " WHERE NOT EXISTS (SELECT 1 FROM usuario)")
    SQL_POR_CORREO = ("SELECT id, correo, hash_clave, rol, nombre, rut_cifrado, telefono_cifrado, bloqueado_hasta,"
                      " activa FROM usuario WHERE correo = ?")
    SQL_CREDENCIAL = "SELECT hash_clave, activa FROM usuario WHERE id = ?"
    MAX_INTENTOS = 5
    # Bloqueo progresivo (H-17): el primero es el de RF-SEG-03 (5 minutos); si sigue fallando sin
    # acertar nunca, 15 y después 60. Un acierto vuelve a empezar.
    BLOQUEOS = (timedelta(minutes=5), timedelta(minutes=15), timedelta(minutes=60))
    # Hash que se verifica cuando el correo no existe. Se calcula al cargar el módulo: si se
    # calculara en el primer intento, ese intento tardaría el doble y delataría el correo (H-06).
    _senuelo: str = HASHER.hash(secrets.token_urlsafe(16))

    def __init__(self, correo: str, clave: str | None = None, *, id: int | None = None,
                 hash_clave: str | None = None, bloqueado_hasta: datetime | None = None):
        self.__id = id
        self.__correo = validar_correo(correo)
        if hash_clave is None:
            # Cuenta nueva: la clave se valida y se guarda solo su resumen (R10).
            self._validar_clave(clave)
            hash_clave = HASHER.hash(clave)
        self.__hash_clave = hash_clave
        self.__bloqueado_hasta = bloqueado_hasta
        # Solo autenticar() y el alta de la propia cuenta la ponen en True (decisión 13 del modelo).
        self.__sesion_iniciada = False

    def obtener_id(self) -> int | None:
        return self.__id

    def tiene_sesion(self) -> bool:
        """Sesión iniciada, con la contraseña que la cuenta tiene hoy y la cuenta activa. Si otra
        sesión cambió la contraseña o un socio desactivó la cuenta, esta sesión deja de valer."""
        if not self.__sesion_iniciada:
            return False
        with conectar() as con:
            fila = con.execute(self.SQL_CREDENCIAL, (self.__id,)).fetchone()
        return fila is not None and fila["activa"] == 1 and fila["hash_clave"] == self.__hash_clave

    def obtener_correo(self) -> str:
        return self.__correo

    @abstractmethod
    def puede(self, accion: str) -> bool:
        """Cada rol responde a su manera: el menú pregunta sin saber qué rol tiene enfrente."""

    def _validar_clave(self, clave: str) -> None:
        """Política de contraseña (RF-SEG-04): 12 caracteres o más y distinta del correo."""
        if not isinstance(clave, str):
            raise TypeError("La contraseña debe ser texto")
        if not CLAVE_MINIMA <= len(clave) <= CLAVE_MAXIMA:
            raise ReglaNegocioError("RF-SEG-04", f"La contraseña debe tener entre {CLAVE_MINIMA}"
                                    f" y {CLAVE_MAXIMA} caracteres")
        if clave.strip().casefold() == self.__correo:
            raise ReglaNegocioError("RF-SEG-04", "La contraseña no puede ser igual al correo")
        if clave.casefold() in CLAVES_COMUNES or len(set(clave)) < CLAVE_DISTINTOS:
            raise ReglaNegocioError("RF-SEG-04", "Esa contraseña es demasiado común o repetitiva")

    def __verificar(self, clave: str) -> bool:
        try:
            return HASHER.verify(self.__hash_clave, clave)
        except (VerificationError, InvalidHashError):
            return False

    def cambiar_clave(self, actual: str, nueva: str) -> None:
        """RF-SEG-11: exige la contraseña actual antes de aceptar la nueva.

        La contraseña actual cuenta como un intento de inicio de sesión: cinco errores bloquean la
        cuenta igual que en la entrada (H-10). Una sesión que ya no vale (la contraseña cambió en
        otra, o la cuenta se desactivó) no puede cambiarla.
        """
        if not self.tiene_sesion():
            raise PermissionError("La contraseña cambió en otra sesión o la cuenta no está activa:"
                                  " inicie sesión de nuevo")
        if not self.__intentar(actual, al_acertar=None):
            raise PermissionError("La contraseña actual no es correcta, o la cuenta está bloqueada"
                                  " por unos minutos")
        if nueva == actual:
            raise ReglaNegocioError("RF-SEG-11", "La contraseña nueva debe ser distinta de la actual")
        self._validar_clave(nueva)
        nuevo_hash = HASHER.hash(nueva)
        # Solo si la base todavía tiene el hash que se verificó: si otra sesión ya cambió la
        # contraseña, esta no puede volver a cambiarla con la contraseña vieja (H-10).
        with conectar() as con:
            cur = con.execute("UPDATE usuario SET hash_clave = ? WHERE id = ? AND hash_clave = ?",
                              (nuevo_hash, self.__id, self.__hash_clave))
            if cur.rowcount == 1:
                registrar_evento(con, self.__id, "cuenta.cambiar_clave")
        if cur.rowcount != 1:
            raise PermissionError("La contraseña cambió en otra sesión: inicie sesión de nuevo")
        self.__hash_clave = nuevo_hash

    @classmethod
    def autenticar(cls, correo: str, clave: str) -> "Usuario | None":
        """La cuenta si el correo y la contraseña son correctos y no está bloqueada; si no, None.

        Los tres fallos (correo inexistente, contraseña errónea, cuenta bloqueada) devuelven lo
        mismo y tardan lo mismo, porque siempre se verifica un Argon2id: así no se puede deducir
        qué correos están registrados (RF-SEG-02).
        """
        try:
            correo = validar_correo(correo)
        except (TypeError, ValueError):
            correo = None
        fila = None
        if correo:
            with conectar() as con:
                fila = con.execute(cls.SQL_POR_CORREO, (correo,)).fetchone()
        if fila is None:
            cls.__senuelo(clave)
            with conectar() as con:                 # sin el correo: puede ser de otra persona
                registrar_evento(con, None, "sesion.correo_inexistente")
            return None
        usuario = _usuario_desde_fila(fila)
        if not fila["activa"]:
            # Cuenta desactivada (RF-SEG-14): la misma respuesta y la misma demora que una
            # contraseña errónea, y queda en el registro.
            usuario.__verificar(clave if isinstance(clave, str) else "")
            with conectar() as con:
                registrar_evento(con, usuario.__id, "sesion.rechazada_inactiva")
            return None
        if not usuario.__intentar(clave):
            return None
        usuario.__sesion_iniciada = True
        return usuario

    @classmethod
    def __senuelo(cls, clave: str) -> None:
        """Verifica la clave contra un hash al azar: el correo inexistente tarda lo mismo."""
        try:
            HASHER.verify(cls._senuelo, clave if isinstance(clave, str) else "")
        except VerificationError:
            pass

    def __intentar(self, clave: str, al_acertar: str | None = "sesion.inicio") -> bool:
        """Un intento de inicio de sesión sobre esta cuenta: True si entra. Registra el resultado.

        El bloqueo se lee de nuevo dentro de la transacción, no del objeto: así dos sesiones a la
        vez no suman más de 5 intentos, y un acierto no borra un bloqueo recién puesto (H-07). La
        hora va en UTC: un cambio de horario no alarga ni anula el bloqueo (H-17).
        """
        correcta = isinstance(clave, str) and self.__verificar(clave)   # siempre: misma demora
        ahora = datetime.now(timezone.utc)
        with conectar() as con:
            hasta = con.execute("SELECT bloqueado_hasta FROM usuario WHERE id = ?",
                                (self.__id,)).fetchone()["bloqueado_hasta"]
            self.__bloqueado_hasta = datetime.fromisoformat(hasta) if hasta else None
            if self.__bloqueado_hasta is not None and ahora < self.__bloqueado_hasta:
                registrar_evento(con, self.__id, "sesion.rechazada_bloqueada")
                return False
            if correcta:
                # Si los parámetros de Argon2 subieron desde que se creó el hash, se rehace ahora,
                # que es el único momento en que se tiene la contraseña en claro.
                # Solo si la base todavía tiene el hash que se verificó: nunca se escribe un hash
                # viejo encima de una contraseña que otra sesión ya cambió.
                if HASHER.check_needs_rehash(self.__hash_clave):
                    rehecho = HASHER.hash(clave)
                    if con.execute("UPDATE usuario SET hash_clave = ? WHERE id = ? AND hash_clave = ?",
                                   (rehecho, self.__id, self.__hash_clave)).rowcount == 1:
                        self.__hash_clave = rehecho
                con.execute("UPDATE usuario SET intentos_fallidos = 0, bloqueado_hasta = NULL,"
                            " bloqueos = 0 WHERE id = ?", (self.__id,))
                if al_acertar:
                    registrar_evento(con, self.__id, al_acertar)
            else:
                # Una sola sentencia: dos sesiones que fallan a la vez no pierden un intento.
                # SQLite evalúa cada CASE con los valores anteriores a la actualización.
                # El largo del bloqueo depende de cuántos lleva la cuenta sin acertar (H-17).
                primero, segundo, siguientes = ((ahora + b).isoformat() for b in self.BLOQUEOS)
                con.execute(
                    "UPDATE usuario SET"
                    " bloqueado_hasta = CASE WHEN intentos_fallidos + 1 >= ? THEN"
                    "     CASE bloqueos WHEN 0 THEN ? WHEN 1 THEN ? ELSE ? END"
                    "     ELSE bloqueado_hasta END,"
                    " bloqueos = CASE WHEN intentos_fallidos + 1 >= ? THEN bloqueos + 1 ELSE bloqueos END,"
                    " intentos_fallidos = CASE WHEN intentos_fallidos + 1 >= ? THEN 0"
                    "                     ELSE intentos_fallidos + 1 END"
                    " WHERE id = ?",
                    (self.MAX_INTENTOS, primero, segundo, siguientes, self.MAX_INTENTOS,
                     self.MAX_INTENTOS, self.__id))
                bloqueo = con.execute("SELECT bloqueado_hasta > ? FROM usuario WHERE id = ?",
                                      (ahora.isoformat(), self.__id)).fetchone()[0]
                registrar_evento(con, self.__id, "sesion.bloqueo" if bloqueo else "sesion.fallida")
        return correcta

    def _insertar(self, rol: str, datos_cliente: tuple[str, str, str] | None = None,
                  solo_si_vacia: bool = False, autor: "Usuario | None" = None) -> bool:
        """C: INSERT de la cuenta. Las dos subclases lo comparten; no está en el diagrama porque
        es la persistencia común, como los métodos de CRUD."""
        nombre, rut_cifrado, telefono_cifrado = datos_cliente or (None, None, None)
        # Sin sesión, la primera cuenta solo entra si la tabla está vacía: la comprobación y la
        # escritura son una sola sentencia, sin carrera entre las dos (S-04).
        sql = self.SQL_INSERTAR_SI_VACIA if solo_si_vacia else self.SQL_INSERTAR
        try:
            with conectar() as con:
                cur = con.execute(sql, (self.__correo, self.__hash_clave, rol, nombre, rut_cifrado,
                                        telefono_cifrado))
                if cur.rowcount == 1:
                    registrar_evento(con, autor.obtener_id() if autor else cur.lastrowid, "cuenta.crear",
                                     f"cuenta {cur.lastrowid} ({rol.lower()})")
        except sqlite3.IntegrityError as error:
            # Solo el UNIQUE del correo es R9; otra restricción sigue como error de la base (H-06).
            if "usuario.correo" in str(error):
                # Queda en el registro: muchos seguidos son alguien probando qué correos existen (H-06).
                with conectar() as con:
                    registrar_evento(con, autor.obtener_id() if autor else None, "registro.correo_repetido")
                raise ReglaNegocioError("R9", "Ese correo ya tiene una cuenta") from None
            raise
        if cur.rowcount != 1:
            return False
        self.__id = cur.lastrowid
        # Quien se registra o crea la primera cuenta acaba de escribir su contraseña: queda con su
        # sesión. Una cuenta creada por otro (un socio) no: tendrá que iniciar sesión.
        self.__sesion_iniciada = autor is None
        return True


class Cliente(Usuario):
    """Usuario con datos personales. RUT y teléfono se guardan cifrados y se muestran enmascarados.

    También en memoria van cifrados: se descifran solo para enmascararlos. Iniciar sesión o listar
    reservas no descifra el RUT de nadie, y un registro alterado no impide listar los demás
    (H-04 y H-05 de la auditoría; minimización, Ley 21.719).
    """

    def __init__(self, nombre: str, rut: str, correo: str, telefono: str,
                 clave: str | None = None, *, cifrado: bool = False, **cuenta):
        # Los datos se validan antes que la contraseña: el hash es lo caro, y no vale la pena
        # calcularlo para un registro que se va a rechazar.
        self.__nombre = texto(nombre, CAMPO_NOMBRE, 80)
        if cifrado:
            # Viene de la base, donde solo entra validado: se guarda tal cual, sin descifrar.
            self.__rut, self.__telefono = rut, telefono
        else:
            self.__rut = cifrar(validar_rut(rut))
            self.__telefono = cifrar(validar_telefono(telefono))
        super().__init__(correo, clave, **cuenta)

    def __repr__(self) -> str:
        # Nunca el RUT ni el teléfono: una traza o un registro no debe filtrarlos (R17, IA C4).
        return f"Cliente(id={self.obtener_id()}, correo={self.obtener_correo()!r})"

    def puede(self, accion: str) -> bool:
        return accion == "reservar"

    def obtener_nombre(self) -> str:
        return self.__nombre

    def rut_enmascarado(self) -> str:
        """12.***.***-5: el único modo de mostrar el RUT (RF-SEG-10)."""
        cuerpo, dv = descifrar(self.__rut).split("-")
        return f"{cuerpo[:-6]}.***.***-{dv}"

    def telefono_enmascarado(self) -> str:
        """+56 9 **** 1234 (RF-SEG-10)."""
        telefono = descifrar(self.__telefono)
        return f"+56 {telefono[0]} **** {telefono[-4:]}"

    # El registro público tiene que decir si un correo ya existe: es la única forma de enumerar
    # cuentas (H-06). Tras 5 correos repetidos en 10 minutos, el registro se pausa (RF-SEG-17).
    REPETIDOS_MAXIMO = 5
    VENTANA_REGISTRO = timedelta(minutes=10)

    @staticmethod
    def registrar(nombre: str, rut: str, correo: str, telefono: str, clave: str) -> "Cliente":
        """Registro público: siempre crea un cliente, nunca un administrador (RF-SEG-12)."""
        desde = (datetime.now(timezone.utc) - Cliente.VENTANA_REGISTRO).isoformat(timespec="seconds")
        with conectar() as con:
            repetidos = con.execute("SELECT COUNT(*) FROM auditoria WHERE accion = 'registro.correo_repetido'"
                                    " AND fecha_utc >= ?", (desde,)).fetchone()[0]
        if repetidos >= Cliente.REPETIDOS_MAXIMO:
            raise ReglaNegocioError("RF-SEG-17", "Hubo demasiados intentos de registro con correos que"
                                    " ya existen: el registro se pausa unos minutos")
        cliente = Cliente(nombre, rut, correo, telefono, clave)
        cliente._insertar("CLIENTE", (cliente.__nombre, cliente.__rut, cliente.__telefono))
        return cliente

    def historial(self) -> list["Reserva"]:
        """R: todas las reservas propias, pasadas, vigentes y anuladas; nunca las de otro (R11)."""
        return Reserva._listar(Reserva.SQL_DE_CLIENTE, (self.obtener_id(),))

    def tiene_reserva_vigente(self, paquete: "Paquete") -> bool:
        """RF-RES-10: el menú advierte antes de una segunda reserva en el mismo paquete (P-01)."""
        with conectar() as con:
            return con.execute("SELECT 1 FROM reserva WHERE cliente_id = ? AND paquete_id = ?"
                               " AND estado = 'VIGENTE' LIMIT 1",
                               (self.obtener_id(), paquete.obtener_id())).fetchone() is not None

    def actualizar_contacto(self, nombre: str, telefono: str) -> None:
        """U: nombre y teléfono propios (RF-RES-12). El RUT y el correo no cambian."""
        nombre = texto(nombre, CAMPO_NOMBRE, 80)
        telefono = cifrar(validar_telefono(telefono))    # antes de abrir la conexión
        with conectar() as con:
            con.execute("UPDATE usuario SET nombre = ?, telefono_cifrado = ? WHERE id = ?",
                        (nombre, telefono, self.obtener_id()))
            registrar_evento(con, self.obtener_id(), "cliente.contacto")
        self.__nombre, self.__telefono = nombre, telefono


class Administrador(Usuario):
    """Socio de la agencia: mantiene el catálogo, arma los paquetes y crea cuentas de socios."""

    def puede(self, accion: str) -> bool:
        return accion in ("catalogo", "ver_reservas", "cuentas", "respaldo", "clave", "auditoria")

    @staticmethod
    def crear_primero(correo: str, clave: str) -> "Administrador":
        """Primer uso: la primera cuenta es de administrador, sin clave escrita en el código (S-04)."""
        admin = Administrador(correo, clave)
        if not admin._insertar("ADMINISTRADOR", solo_si_vacia=True):
            raise PermissionError("Ya existe una cuenta: inicie sesión para crear otra")
        return admin

    def crear_administrador(self, correo: str, clave: str) -> "Administrador":
        """Cuenta para otro socio (RF-SEG-07): una por persona, para saber quién hizo cada cambio."""
        autorizar(self, "cuentas")
        nuevo = Administrador(correo, clave)
        nuevo._insertar("ADMINISTRADOR", autor=self)
        return nuevo

    def desactivar_cuenta(self, correo: str) -> None:
        """Cierra el acceso de una cuenta sin borrar su historia (RF-SEG-14): un socio que deja la
        agencia, o una cuenta usada para abusar del sistema.

        No vuelve a entrar, y sus sesiones abiertas dejan de valer en la acción siguiente
        (tiene_sesion() revisa la base). Sus reservas y el registro de auditoría se conservan.
        Nadie desactiva su propia cuenta: así siempre queda al menos un administrador activo.
        """
        autorizar(self, "cuentas")
        correo = validar_correo(correo)
        with conectar() as con:
            fila = con.execute("SELECT id FROM usuario WHERE correo = ? AND activa = 1", (correo,)).fetchone()
            if fila is None:
                raise ValueError("No hay una cuenta activa con ese correo")
            if fila["id"] == self.obtener_id():
                raise ReglaNegocioError("RF-SEG-14", "No puede desactivar su propia cuenta")
            con.execute("UPDATE usuario SET activa = 0 WHERE id = ?", (fila["id"],))
            registrar_evento(con, self.obtener_id(), "cuenta.desactivar", f"cuenta {fila['id']}")

    def respaldar_base(self) -> str:
        """Copia consistente de la base en respaldos/, junto a ella (RNF-FIA-03, P-14).

        Usa la API de respaldo de sqlite3, que copia una foto coherente aunque otra sesión esté
        escribiendo. La carpeta es fija: ningún dato del usuario forma la ruta. La clave de cifrado
        no se copia aquí a propósito: va aparte (S-12), para que una copia no lleve dato y clave.
        """
        autorizar(self, "respaldo")
        carpeta = Path(RUTA_ACTIVA).parent / "respaldos"
        carpeta.mkdir(mode=0o700, exist_ok=True)
        destino = carpeta / f"viajes_{datetime.now(timezone.utc):%Y%m%d_%H%M%S_%f}.db"
        origen, copia = sqlite3.connect(RUTA_ACTIVA), sqlite3.connect(destino)
        try:
            origen.backup(copia)
        finally:
            copia.close()
            origen.close()
        if os.name == "posix":
            os.chmod(destino, 0o600)
        with conectar() as con:
            registrar_evento(con, self.obtener_id(), "base.respaldo", destino.name)
        return str(destino)


def _usuario_desde_fila(fila: sqlite3.Row) -> Usuario:
    """La subclase que corresponde al rol guardado. Los datos personales quedan cifrados."""
    hasta = fila["bloqueado_hasta"]
    cuenta = {"id": fila["id"], "hash_clave": fila["hash_clave"],
              "bloqueado_hasta": datetime.fromisoformat(hasta) if hasta else None}
    if fila["rol"] == "CLIENTE":
        return Cliente(fila["nombre"], fila["rut_cifrado"], fila["correo"],
                       fila["telefono_cifrado"], cifrado=True, **cuenta)
    return Administrador(fila["correo"], **cuenta)


class Destino:
    """tabla: destino. R1, R2 y R8."""

    SQL_TODOS = "SELECT id, nombre, zona, descripcion, duracion_dias, costo_base, disponible, fecha_costo FROM destino ORDER BY nombre"
    SQL_DISPONIBLES = ("SELECT id, nombre, zona, descripcion, duracion_dias, costo_base, disponible, fecha_costo FROM destino"
                       " WHERE disponible = 1 ORDER BY nombre")
    SQL_POR_ID = "SELECT id, nombre, zona, descripcion, duracion_dias, costo_base, disponible, fecha_costo FROM destino WHERE id = ?"

    def __init__(self, nombre: str, zona: str, descripcion: str, duracion_dias: int,
                 costo_base: int, id: int | None = None, disponible: bool = True,
                 fecha_costo: date | None = None):
        # El constructor valida todo: un Destino inválido no llega a existir, se cree desde el
        # menú, desde una prueba o desde la base (tercera capa de validación, después del menú
        # y antes del CHECK).
        self.__id = id
        (self.__nombre, self.__zona, self.__descripcion,
         self.__duracion_dias) = self.__validar_datos(nombre, zona, descripcion, duracion_dias)
        self.__costo_base = entero(costo_base, "El costo base", 1, COSTO_MAXIMO, "R2")
        self.__disponible = bool(disponible)
        self.__fecha_costo = fecha_costo or date.today()

    @staticmethod
    def __validar_datos(nombre, zona, descripcion, duracion_dias) -> tuple:
        """Valida los cuatro datos y los devuelve; no toca el objeto. Así, si uno falla, el objeto
        no queda a medio cambiar (auditoría final, hallazgo 4)."""
        return (texto(nombre, CAMPO_NOMBRE, 80), texto(zona, "La zona", 80),
                texto(descripcion, "La descripción", 500),
                entero(duracion_dias, "La duración en días", 1, DURACION_MAXIMA, "R1"))

    def __str__(self) -> str:
        estado = "disponible" if self.__disponible else "no disponible"
        return (f"[{self.__id}] {self.__nombre} · {self.__zona} · {self.__duracion_dias} días · "
                f"{pesos(self.__costo_base)} (costo al {self.__fecha_costo:%d-%m-%Y}) · {estado}")

    def obtener_nombre(self) -> str:
        return self.__nombre

    def obtener_id(self) -> int | None:
        return self.__id

    def obtener_costo_base(self) -> int:
        return self.__costo_base

    def esta_disponible(self) -> bool:
        return self.__disponible

    # --- Persistencia (CRUD) ---------------------------------------------

    def guardar(self, solicitante: "Usuario") -> int:
        """C: INSERT. Un nombre repetido lo rechaza la base, con el nombre normalizado (R1)."""
        autorizar(solicitante, "catalogo")
        if self.__id is not None:
            raise ValueError("El destino ya está guardado")
        try:
            with conectar() as con:
                cur = con.execute(
                    "INSERT INTO destino (nombre, nombre_normalizado, zona, descripcion,"
                    " duracion_dias, costo_base, disponible, fecha_costo)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (self.__nombre, normalizar(self.__nombre), self.__zona, self.__descripcion,
                     self.__duracion_dias, self.__costo_base, int(self.__disponible),
                     self.__fecha_costo.isoformat()))
                registrar_evento(con, solicitante.obtener_id(), "destino.crear", f"destino {cur.lastrowid}")
        except sqlite3.IntegrityError:
            raise ReglaNegocioError("R1", "Ya existe un destino con ese nombre") from None
        self.__id = cur.lastrowid
        return self.__id

    def editar(self, nombre: str, zona: str, descripcion: str, duracion_dias: int,
               solicitante: "Usuario") -> None:
        """U: los datos descriptivos, con las mismas validaciones del registro (RF-DES-04)."""
        autorizar(solicitante, "catalogo")
        datos = self.__validar_datos(nombre, zona, descripcion, duracion_dias)
        try:
            with conectar() as con:
                cur = con.execute(
                    "UPDATE destino SET nombre = ?, nombre_normalizado = ?, zona = ?,"
                    " descripcion = ?, duracion_dias = ? WHERE id = ?",
                    (datos[0], normalizar(datos[0]), datos[1], datos[2], datos[3], self.__id))
                exigir_una_fila(cur, "destino")
                registrar_evento(con, solicitante.obtener_id(), "destino.editar", f"destino {self.__id}")
        except sqlite3.IntegrityError:
            raise ReglaNegocioError("R1", "Ya existe un destino con ese nombre") from None
        # Recién ahora, con la base guardada: memoria y base dicen siempre lo mismo.
        self.__nombre, self.__zona, self.__descripcion, self.__duracion_dias = datos

    def cambiar_costo(self, costo_base: int, solicitante: "Usuario") -> None:
        """U: el costo, con la fecha del cambio (RF-DES-05). Los paquetes publicados no cambian (R7)."""
        autorizar(solicitante, "catalogo")
        costo, hoy = entero(costo_base, "El costo base", 1, COSTO_MAXIMO, "R2"), date.today()
        with conectar() as con:
            cur = con.execute("UPDATE destino SET costo_base = ?, fecha_costo = ? WHERE id = ?",
                              (costo, hoy.isoformat(), self.__id))
            exigir_una_fila(cur, "destino")
            registrar_evento(con, solicitante.obtener_id(), "destino.costo", f"destino {self.__id}: {costo}")
        self.__costo_base, self.__fecha_costo = costo, hoy

    def eliminar(self, solicitante: "Usuario") -> bool:
        """D, según R8: True si se eliminó; False si estaba en un paquete y quedó no disponible."""
        autorizar(solicitante, "catalogo")
        # La consulta y la escritura van en la misma transacción: entre las dos, nadie puede
        # agregar el destino a un paquete.
        with conectar() as con:
            en_paquete = con.execute("SELECT 1 FROM paquete_destino WHERE destino_id = ? LIMIT 1",
                                     (self.__id,)).fetchone()
            if en_paquete:
                con.execute("UPDATE destino SET disponible = 0 WHERE id = ?", (self.__id,))
            else:
                con.execute("DELETE FROM destino WHERE id = ?", (self.__id,))
            registrar_evento(con, solicitante.obtener_id(),
                             "destino.no_disponible" if en_paquete else "destino.eliminar",
                             f"destino {self.__id}")
        self.__disponible = False
        return en_paquete is None

    def reactivar(self, solicitante: "Usuario") -> None:
        """U: vuelve a ofrecer un destino no disponible (RF-DES-09)."""
        autorizar(solicitante, "catalogo")
        with conectar() as con:
            cur = con.execute("UPDATE destino SET disponible = 1 WHERE id = ?", (self.__id,))
            exigir_una_fila(cur, "destino")
            registrar_evento(con, solicitante.obtener_id(), "destino.reactivar", f"destino {self.__id}")
        self.__disponible = True

    @classmethod
    def listar(cls, solo_disponibles: bool = False) -> list["Destino"]:
        """R: todo el catálogo, o solo lo que se puede ofrecer (RF-DES-08, RF-DES-10)."""
        with conectar() as con:
            filas = con.execute(cls.SQL_DISPONIBLES if solo_disponibles else cls.SQL_TODOS).fetchall()
        return [cls._desde_fila(f) for f in filas]

    @classmethod
    def buscar(cls, id: int) -> "Destino | None":
        with conectar() as con:
            fila = con.execute(cls.SQL_POR_ID, (id,)).fetchone()
        return cls._desde_fila(fila) if fila else None

    @classmethod
    def _desde_fila(cls, fila: sqlite3.Row) -> "Destino":
        return cls(fila["nombre"], fila["zona"], fila["descripcion"], fila["duracion_dias"],
                   fila["costo_base"], id=fila["id"], disponible=fila["disponible"],
                   fecha_costo=date.fromisoformat(fila["fecha_costo"]))


class Paquete:
    """tabla: paquete, y paquete_destino para la agregación con Destino. R3 a R8 y R14."""

    SQL_DISPONIBLES = ("SELECT id, nombre, fecha_salida, fecha_regreso, cupo_maximo, margen, precio_por_persona, publicado FROM paquete"
                       " WHERE publicado = 1 AND fecha_salida > ? ORDER BY fecha_salida, id")
    SQL_TODOS = "SELECT id, nombre, fecha_salida, fecha_regreso, cupo_maximo, margen, precio_por_persona, publicado FROM paquete ORDER BY fecha_salida, id"
    SQL_POR_ID = "SELECT id, nombre, fecha_salida, fecha_regreso, cupo_maximo, margen, precio_por_persona, publicado FROM paquete WHERE id = ?"

    def __init__(self, nombre: str, fecha_salida: date, fecha_regreso: date, cupo_maximo: int,
                 destinos: list[Destino], margen: int = MARGEN_PROPUESTO, id: int | None = None,
                 precio_por_persona: int | None = None, publicado: bool = False):
        self.__id = id
        (self.__nombre, self.__fecha_salida, self.__fecha_regreso,
         self.__margen) = self.__validar_datos(nombre, fecha_salida, fecha_regreso, margen)
        self.__cupo_maximo = entero(cupo_maximo, "El cupo máximo", 1, CUPO_MAXIMO, "R5")
        # Un paquete nuevo solo combina destinos disponibles (R8); uno guardado conserva los que
        # tenía aunque después hayan quedado no disponibles (S-15).
        self.__destinos = self.__validar_destinos(destinos, exigir_disponibles=id is None)
        self.__precio_por_persona = precio_por_persona
        self.__publicado = bool(publicado)

    @staticmethod
    def __validar_datos(nombre, fecha_salida, fecha_regreso, margen) -> tuple:
        """Valida y devuelve los datos sin tocar el objeto (auditoría final, hallazgo 4)."""
        salida, regreso = fecha(fecha_salida, "La fecha de salida"), fecha(fecha_regreso, "La fecha de regreso")
        if regreso <= salida:
            raise ReglaNegocioError("R5", "La fecha de regreso debe ser posterior a la de salida")
        return (texto(nombre, CAMPO_NOMBRE, 80), salida, regreso,
                entero(margen, "El margen (%)", 0, MARGEN_MAXIMO, "R6"))

    @staticmethod
    def __validar_destinos(destinos: list[Destino], exigir_disponibles: bool) -> list[Destino]:
        if not isinstance(destinos, list) or not all(isinstance(d, Destino) for d in destinos):
            raise TypeError("Los destinos deben ser una lista de destinos")
        if not DESTINOS_MINIMO <= len(destinos) <= DESTINOS_MAXIMO:
            raise ReglaNegocioError("R3", f"Un paquete combina entre {DESTINOS_MINIMO} y"
                                    f" {DESTINOS_MAXIMO} destinos")
        ids = [d.obtener_id() for d in destinos]
        if None in ids:
            raise ValueError("Todos los destinos deben estar guardados en el catálogo")
        if len(set(ids)) != len(ids):
            raise ReglaNegocioError("R3", "Un destino no puede repetirse en el mismo paquete")
        if exigir_disponibles and not all(d.esta_disponible() for d in destinos):
            raise ReglaNegocioError("R8", "Un destino no disponible no se ofrece en paquetes nuevos")
        return list(destinos)

    def __str__(self) -> str:
        precio = pesos(self.__precio_por_persona or self.calcular_precio())
        nombres = ", ".join(d.obtener_nombre() for d in self.__destinos)
        return (f"[{self.__id}] {self.__nombre} · {self.__fecha_salida:%d-%m-%Y} a "
                f"{self.__fecha_regreso:%d-%m-%Y} · {nombres} · {precio} por persona · "
                f"cupo {self.cupo_disponible()} de {self.__cupo_maximo} · {self.estado()}")

    def obtener_id(self) -> int | None:
        return self.__id

    def calcular_precio(self) -> int:
        """Suma de los costos base más el margen, redondeado al peso (R6, S-05).

        Aritmética entera: (suma × (100 + margen) + 50) // 100 redondea al peso más cercano sin
        pasar por float, que arrastraría errores de representación (IA C3).
        """
        suma = sum(d.obtener_costo_base() for d in self.__destinos)
        return (suma * (100 + self.__margen) + 50) // 100

    def publicar(self, solicitante: "Usuario") -> None:
        """U: fija el precio por persona (R7). Desde aquí ya no cambia aunque cambien los costos."""
        autorizar(solicitante, "catalogo")
        if self.__publicado:
            raise ReglaNegocioError("R7", "El paquete ya está publicado")
        if self.__fecha_salida <= date.today():
            raise ReglaNegocioError("R15", "No se publica un paquete cuya fecha de salida ya llegó")
        if not all(d.esta_disponible() for d in self.__destinos):
            raise ReglaNegocioError("R8", "El paquete tiene un destino que ya no está disponible")
        precio = self.calcular_precio()
        with conectar() as con:
            cur = con.execute("UPDATE paquete SET publicado = 1, precio_por_persona = ?"
                              " WHERE id = ? AND publicado = 0", (precio, self.__id))
            if cur.rowcount == 1:
                registrar_evento(con, solicitante.obtener_id(), "paquete.publicar",
                                 f"paquete {self.__id}: {precio} por persona")
        if cur.rowcount != 1:
            raise ReglaNegocioError("R7", "El paquete ya está publicado")
        self.__publicado, self.__precio_por_persona = True, precio

    def cupo_disponible(self) -> int:
        """Cupo máximo menos las personas de las reservas vigentes (R14). Se calcula, no se guarda."""
        with conectar() as con:
            reservadas = con.execute(
                "SELECT COALESCE(SUM(personas), 0) FROM reserva"
                " WHERE paquete_id = ? AND estado = 'VIGENTE'", (self.__id,)).fetchone()[0]
        return self.__cupo_maximo - reservadas

    def estado(self, hoy: date | None = None) -> str:
        """borrador, publicado o vencido. «Vencido» se calcula con la fecha: nadie tiene que
        acordarse de sacarlo (S-02, P-03)."""
        hoy = hoy or date.today()
        if self.__fecha_salida <= hoy:
            return "vencido"
        return "publicado" if self.__publicado else "borrador"

    def esta_disponible(self, hoy: date | None = None) -> bool:
        return self.estado(hoy) == "publicado" and self.cupo_disponible() > 0

    def listar_destinos(self) -> list[Destino]:
        return list(self.__destinos)          # una copia: nadie cambia los destinos por fuera

    # --- Persistencia (CRUD) ---------------------------------------------

    def guardar(self, solicitante: "Usuario") -> int:
        """C: el paquete y sus destinos en una sola transacción: nunca queda uno sin destinos."""
        autorizar(solicitante, "catalogo")
        if self.__id is not None:
            raise ValueError("El paquete ya está guardado")
        with conectar() as con:
            self.__exigir_disponibles_en_base(con)
            cur = con.execute(
                "INSERT INTO paquete (nombre, fecha_salida, fecha_regreso, cupo_maximo, margen)"
                " VALUES (?, ?, ?, ?, ?)",
                (self.__nombre, self.__fecha_salida.isoformat(), self.__fecha_regreso.isoformat(),
                 self.__cupo_maximo, self.__margen))
            con.executemany("INSERT INTO paquete_destino (paquete_id, destino_id) VALUES (?, ?)",
                            [(cur.lastrowid, d.obtener_id()) for d in self.__destinos])
            registrar_evento(con, solicitante.obtener_id(), "paquete.crear", f"paquete {cur.lastrowid}")
        self.__id = cur.lastrowid
        return self.__id

    def __exigir_disponibles_en_base(self, con: sqlite3.Connection) -> None:
        """R8 contra la base, dentro de la transacción: el objeto en memoria puede estar viejo."""
        ids = [d.obtener_id() for d in self.__destinos]
        # La lista de ids viaja como un solo parámetro JSON: el texto del SQL no cambia nunca.
        disponibles = con.execute(
            "SELECT COUNT(*) FROM destino WHERE disponible = 1"
            " AND id IN (SELECT value FROM json_each(?))", (json.dumps(ids),)).fetchone()[0]
        if disponibles != len(ids):
            raise ReglaNegocioError("R8", "Un destino no disponible no se ofrece en paquetes nuevos")

    def __exigir_borrador(self) -> None:
        if self.__publicado:
            raise ReglaNegocioError("R7", "Un paquete publicado solo puede cambiar su cupo (S-07)")

    def editar(self, nombre: str, fecha_salida: date, fecha_regreso: date, margen: int,
               solicitante: "Usuario") -> None:
        """U: solo en borrador (S-07). Publicado, cambiaría lo que ya se vendió."""
        autorizar(solicitante, "catalogo")
        self.__exigir_borrador()
        datos = self.__validar_datos(nombre, fecha_salida, fecha_regreso, margen)
        with conectar() as con:
            cur = con.execute("UPDATE paquete SET nombre = ?, fecha_salida = ?, fecha_regreso = ?,"
                              " margen = ? WHERE id = ? AND publicado = 0",
                              (datos[0], datos[1].isoformat(), datos[2].isoformat(), datos[3], self.__id))
            if cur.rowcount != 1:      # otra sesión lo publicó o lo eliminó entre medio
                raise ReglaNegocioError("R7", "El paquete ya no está en borrador")
            registrar_evento(con, solicitante.obtener_id(), "paquete.editar", f"paquete {self.__id}")
        self.__nombre, self.__fecha_salida, self.__fecha_regreso, self.__margen = datos

    def reemplazar_destinos(self, destinos: list[Destino], solicitante: "Usuario") -> None:
        """U: los destinos de un borrador, con R3 y R8, en una sola transacción."""
        autorizar(solicitante, "catalogo")
        self.__exigir_borrador()
        anteriores = self.__destinos
        self.__destinos = self.__validar_destinos(destinos, exigir_disponibles=True)
        try:
            with conectar() as con:
                self.__exigir_disponibles_en_base(con)
                con.execute("DELETE FROM paquete_destino WHERE paquete_id = ?", (self.__id,))
                con.executemany("INSERT INTO paquete_destino (paquete_id, destino_id) VALUES (?, ?)",
                                [(self.__id, d.obtener_id()) for d in self.__destinos])
                registrar_evento(con, solicitante.obtener_id(), "paquete.destinos", f"paquete {self.__id}")
        except ReglaNegocioError:
            self.__destinos = anteriores
            raise

    def cambiar_cupo(self, cupo_maximo: int, solicitante: "Usuario") -> None:
        """U: también publicado (S-07), pero nunca por debajo de las personas ya reservadas (R14)."""
        autorizar(solicitante, "catalogo")
        cupo = entero(cupo_maximo, "El cupo máximo", 1, CUPO_MAXIMO, "R5")
        # Una sola sentencia: la suma de reservas y el cambio no se pueden separar.
        with conectar() as con:
            cur = con.execute(
                "UPDATE paquete SET cupo_maximo = ? WHERE id = ? AND ? >= (SELECT"
                " COALESCE(SUM(personas), 0) FROM reserva WHERE paquete_id = ? AND estado = 'VIGENTE')",
                (cupo, self.__id, cupo, self.__id))
            if cur.rowcount == 1:
                registrar_evento(con, solicitante.obtener_id(), "paquete.cupo", f"paquete {self.__id}: {cupo}")
        if cur.rowcount != 1:
            raise ReglaNegocioError("R14", "El cupo no puede quedar bajo las personas ya reservadas")
        self.__cupo_maximo = cupo

    def eliminar(self, solicitante: "Usuario") -> None:
        """D: solo sin reservas, ni siquiera anuladas: son historial (RF-PAQ-09, R11)."""
        autorizar(solicitante, "catalogo")
        with conectar() as con:
            cur = con.execute("DELETE FROM paquete WHERE id = ? AND NOT EXISTS"
                              " (SELECT 1 FROM reserva WHERE paquete_id = ?)", (self.__id, self.__id))
            if cur.rowcount == 1:
                registrar_evento(con, solicitante.obtener_id(), "paquete.eliminar", f"paquete {self.__id}")
        if cur.rowcount != 1:
            raise ReglaNegocioError("RF-PAQ-09", "Un paquete con reservas no se elimina")

    @classmethod
    def listar_disponibles(cls, hoy: date | None = None) -> list["Paquete"]:
        """R: la oferta (RF-PAQ-06, RF-PAQ-07). Sin sesión también se puede ver (S-09)."""
        hoy = hoy or date.today()
        return [p for p in cls._listar(cls.SQL_DISPONIBLES, (hoy.isoformat(),))
                if p.esta_disponible(hoy)]

    @classmethod
    def listar_todos(cls, solicitante: "Usuario") -> list["Paquete"]:
        """R: todos, con su estado, para el administrador (RF-PAQ-10)."""
        autorizar(solicitante, "catalogo")
        return cls._listar(cls.SQL_TODOS, ())

    @classmethod
    def buscar(cls, id: int) -> "Paquete | None":
        encontrados = cls._listar(cls.SQL_POR_ID, (id,))
        return encontrados[0] if encontrados else None

    @classmethod
    def _listar(cls, sql: str, parametros: tuple) -> list["Paquete"]:
        # sql es siempre una de las constantes SQL_ de esta clase; los datos van como parámetros.
        with conectar() as con:
            filas = con.execute(sql, parametros).fetchall()
            ids = {f["id"]: [r[0] for r in con.execute(
                "SELECT destino_id FROM paquete_destino WHERE paquete_id = ? ORDER BY rowid",
                (f["id"],))] for f in filas}
        # Los destinos se buscan con la conexión ya cerrada: una conexión dentro de otra esperaría.
        destinos = {pid: [Destino.buscar(i) for i in lista] for pid, lista in ids.items()}
        return [cls(f["nombre"], date.fromisoformat(f["fecha_salida"]),
                    date.fromisoformat(f["fecha_regreso"]), f["cupo_maximo"], destinos[f["id"]],
                    margen=f["margen"], id=f["id"], precio_por_persona=f["precio_por_persona"],
                    publicado=f["publicado"]) for f in filas]


class EstadoReserva(Enum):
    """Una reserva no se borra: queda vigente o anulada (S-01, S-08)."""
    VIGENTE = "VIGENTE"
    ANULADA = "ANULADA"


class Reserva:
    """tabla: reserva. R11 a R16. El total queda fijo al reservar y no se vuelve a calcular."""

    # r.id va con alias: sin él, fila["id"] sería el de la reserva y no el del cliente.
    SQL_DE_CLIENTE = ("SELECT r.id AS reserva_id, r.paquete_id, r.fecha_emision, r.personas,"
                      " r.total, r.estado, u.id, u.correo, u.hash_clave, u.rol, u.nombre, u.rut_cifrado, u.telefono_cifrado, u.bloqueado_hasta"
                      " FROM reserva r JOIN usuario u ON u.id = r.cliente_id"
                      " WHERE r.cliente_id = ? ORDER BY r.fecha_emision, r.id")
    SQL_DE_PAQUETE = ("SELECT r.id AS reserva_id, r.paquete_id, r.fecha_emision, r.personas,"
                      " r.total, r.estado, u.id, u.correo, u.hash_clave, u.rol, u.nombre, u.rut_cifrado, u.telefono_cifrado, u.bloqueado_hasta"
                      " FROM reserva r JOIN usuario u ON u.id = r.cliente_id"
                      " WHERE r.paquete_id = ? ORDER BY r.fecha_emision, r.id")

    def __init__(self, cliente: Cliente, paquete: Paquete, personas: int, total: int,
                 fecha_emision: date, estado: EstadoReserva = EstadoReserva.VIGENTE,
                 id: int | None = None):
        if not isinstance(cliente, Cliente) or not isinstance(paquete, Paquete):
            raise TypeError("Una reserva corresponde a un cliente y a un paquete (R12)")
        if not isinstance(estado, EstadoReserva):
            raise TypeError("El estado de la reserva no es válido")
        self.__id = id
        self.__cliente, self.__paquete = cliente, paquete
        self.__personas = entero(personas, "La cantidad de personas", 1, CUPO_MAXIMO, "R16")
        self.__total = entero(total, "El total", 1, PRECIO_MAXIMO * CUPO_MAXIMO, "R13")
        self.__fecha_emision = fecha(fecha_emision, "La fecha de emisión")
        self.__estado = estado

    def __str__(self) -> str:
        return (f"[{self.__id}] {self.__cliente.obtener_nombre()} <{self.__cliente.obtener_correo()}>"
                f" · paquete {self.__paquete.obtener_id()} · {self.__personas} persona(s) · "
                f"{pesos(self.__total)} · emitida el {self.__fecha_emision:%d-%m-%Y} · "
                f"{self.__estado.value.lower()}")

    def obtener_total(self) -> int:
        return self.__total

    @staticmethod
    def reservar(paquete: Paquete, personas: int, solicitante: Cliente,
                 hoy: date | None = None) -> "Reserva":
        """C: comprueba fecha (R15) y cupo (R14) y guarda, todo en una transacción BEGIN IMMEDIATE.

        conectar() toma el permiso de escritura antes de leer el cupo: una segunda reserva
        simultánea espera a que esta termine y después ve el cupo ya descontado. Así dos personas
        no pueden quedarse con el mismo último lugar (RNF-FIA-02, P-02).
        """
        autorizar(solicitante, "reservar")
        hoy = fecha(hoy or date.today(), "La fecha de hoy")
        personas = entero(personas, "La cantidad de personas", 1, CUPO_MAXIMO, "R16")
        with conectar() as con:
            fila = con.execute(
                "SELECT p.fecha_salida, p.publicado, p.precio_por_persona, p.cupo_maximo"
                " - COALESCE((SELECT SUM(personas) FROM reserva WHERE paquete_id = p.id"
                " AND estado = 'VIGENTE'), 0) AS disponible FROM paquete p WHERE p.id = ?",
                (paquete.obtener_id(),)).fetchone()
            if fila is None or not fila["publicado"]:
                raise ReglaNegocioError("R7", "Ese paquete no está publicado")
            # Se compara contra la base y no contra el objeto: la regla se cumple aunque el
            # paquete esté oculto de la oferta o el objeto esté viejo (RF-RES-06).
            if date.fromisoformat(fila["fecha_salida"]) <= hoy:
                raise ReglaNegocioError("R15", "No se puede reservar: la fecha de salida ya llegó")
            if personas > fila["disponible"]:
                raise ReglaNegocioError("R14", f"No hay cupo: quedan {fila['disponible']} lugares")
            # R13: se calcula una vez, y se valida antes de guardar (H-09).
            total = entero(fila["precio_por_persona"] * personas, "El total", 1,
                           PRECIO_MAXIMO * CUPO_MAXIMO, "R13")
            cur = con.execute("INSERT INTO reserva (cliente_id, paquete_id, fecha_emision,"
                              " personas, total) VALUES (?, ?, ?, ?, ?)",
                              (solicitante.obtener_id(), paquete.obtener_id(), hoy.isoformat(),
                               personas, total))
            registrar_evento(con, solicitante.obtener_id(), "reserva.crear",
                             f"reserva {cur.lastrowid}: paquete {paquete.obtener_id()}, {personas} personas")
        return Reserva(solicitante, paquete, personas, total, hoy, id=cur.lastrowid)

    def anular(self, solicitante: Cliente) -> None:
        """U: solo el titular, solo vigente y hasta el día anterior a la salida (S-01, R11)."""
        autorizar(solicitante, "reservar")
        if solicitante.obtener_id() != self.__cliente.obtener_id():
            raise PermissionError("Solo el titular puede anular su reserva")
        with conectar() as con:
            cur = con.execute(
                "UPDATE reserva SET estado = 'ANULADA' WHERE id = ? AND cliente_id = ?"
                " AND estado = 'VIGENTE' AND (SELECT fecha_salida FROM paquete"
                " WHERE id = reserva.paquete_id) > ?",
                (self.__id, solicitante.obtener_id(), date.today().isoformat()))
            if cur.rowcount == 1:
                registrar_evento(con, solicitante.obtener_id(), "reserva.anular", f"reserva {self.__id}")
        if cur.rowcount != 1:
            raise ReglaNegocioError("S-01", "Solo se anula una reserva vigente, antes del día de salida")
        self.__estado = EstadoReserva.ANULADA

    @staticmethod
    def listar_por_paquete(paquete: Paquete, solicitante: "Usuario") -> list["Reserva"]:
        """R: quién viaja en un paquete, con nombre y correo; nunca RUT ni teléfono (RF-RES-11, S-16)."""
        autorizar(solicitante, "ver_reservas")
        return Reserva._listar(Reserva.SQL_DE_PAQUETE, (paquete.obtener_id(),))

    @staticmethod
    def _listar(sql: str, parametros: tuple) -> list["Reserva"]:
        # sql es siempre una de las constantes SQL_ de esta clase; los datos van como parámetros.
        with conectar() as con:
            filas = con.execute(sql, parametros).fetchall()
        paquetes: dict[int, Paquete] = {}
        reservas = []
        for f in filas:
            if f["paquete_id"] not in paquetes:
                paquetes[f["paquete_id"]] = Paquete.buscar(f["paquete_id"])
            reservas.append(Reserva(_usuario_desde_fila(f), paquetes[f["paquete_id"]],
                                    f["personas"], f["total"], date.fromisoformat(f["fecha_emision"]),
                                    EstadoReserva(f["estado"]), id=f["reserva_id"]))
        return reservas
