"""Viajes Aventura: destinos, paquetes turísticos y reservas.

Implementación en Python del diagrama de clases del informe (diagramas/clases.puml). El archivo
contiene, en este orden:

    1. Validaciones y autorización compartidas
    2. Esquema y conexión a la base de datos (sqlite3, biblioteca estándar)
    3. Las clases del diagrama, cada una con su persistencia (CRUD)
    4. Autoverificación

Uso:
    python viajes.py   -> autoverificación sobre una base temporal (imprime OK)
    python main.py     -> menú de la aplicación

Un solo archivo para el dominio y otro para el menú: es la estructura que pidió el docente en la
Unidad 2 (no modularizar clase por clase).
"""

import os                                   # permisos 0600 de la base y lectura del entorno
import re                                   # patrones de correo, RUT y teléfono
import secrets                              # contraseña aleatoria del hash señuelo
import sqlite3                              # la base de datos: un archivo, sin servidor
import tempfile                             # base temporal para la autoverificación
import threading                            # prueba de dos reservas simultáneas (RNF-FIA-02)
import unicodedata                          # quita tildes al comparar nombres de destinos (RF-DES-02)
from abc import ABC, abstractmethod         # Usuario es abstracta: no existe «solo un usuario»
from contextlib import contextmanager       # `with conectar()`: abre y siempre cierra la conexión
from datetime import date, datetime, timedelta  # fechas, y el bloqueo temporal del inicio de sesión
from enum import Enum                       # estado de la reserva: un valor mal escrito falla al crearse
from functools import lru_cache             # la clave de cifrado se lee una sola vez
from pathlib import Path                    # ubica la base y la clave junto a este archivo

from argon2 import PasswordHasher           # Argon2id, librería especializada de PyPI (G.17)
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.fernet import Fernet, InvalidToken  # cifrado autenticado: AES + HMAC (I.19)

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

# Correo: lineal, sin retroceso exponencial (regla 11 de EcoTech). RUT con o sin puntos y guion.
PATRON_CORREO = re.compile(r"[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+")
PATRON_RUT = re.compile(r"(\d{1,2})\.?(\d{3})\.?(\d{3})-?([\dkK])", re.ASCII)
PATRON_TELEFONO = re.compile(r"(?:\+?56)?([2-9]\d{8})", re.ASCII)
SEPARADORES = re.compile(r"[\s()\-.]")

CLAVE_MINIMA, CLAVE_MAXIMA = 12, 128          # RF-SEG-04; el tope evita hashear textos enormes

# Argon2id con time_cost=4 y 64 MiB: unos 130 ms por verificación, dentro de lo que pide
# RNF-REN-02 (entre 0,1 y 1 segundo). Con los valores por omisión medía 98 ms.
HASHER = PasswordHasher(time_cost=4)

# La clave que cifra RUT y teléfono vive fuera del código y de la base (S-12): en el entorno
# o en un archivo .env junto a este archivo, con permisos 0600.
RUTA_CLAVE = Path(__file__).with_name(".env")
VARIABLE_CLAVE = "VIAJES_CLAVE_DATOS"
CAMPO_NOMBRE = "El nombre"

# Acciones que un rol puede tener. Un texto fuera de este conjunto es un error de
# programación y se rechaza: así un permiso mal escrito no se convierte en un «no» silencioso.
ACCIONES = frozenset({"catalogo", "ver_reservas", "cuentas", "reservar"})


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


@lru_cache(maxsize=1)
def cifrador() -> Fernet:
    """Fernet con la clave del entorno o del archivo .env; la crea en el primer uso (S-12)."""
    clave = os.environ.get(VARIABLE_CLAVE)
    if not clave and RUTA_CLAVE.exists():
        for linea in RUTA_CLAVE.read_text(encoding="utf-8").splitlines():
            nombre, _, valor = linea.partition("=")
            if nombre.strip() == VARIABLE_CLAVE:
                clave = valor.strip()
    if not clave:
        if hay_usuarios():
            # Sin la clave, los RUT ya guardados son ilegibles: crear otra los perdería para siempre.
            raise RuntimeError("Falta la clave de cifrado de los datos personales (.env)")
        clave = Fernet.generate_key().decode()
        # O_EXCL: si dos procesos la crean a la vez, uno falla en vez de pisar la clave del otro.
        fd = os.open(RUTA_CLAVE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as archivo:
            archivo.write(f"{VARIABLE_CLAVE}={clave}\n")
    return Fernet(clave.encode())


def cifrar(valor: str) -> str:
    return cifrador().encrypt(valor.encode()).decode()


def descifrar(token: str) -> str:
    """Un dato alterado o cifrado con otra clave da error, nunca un dato falso (RNF-SEG-02)."""
    try:
        return cifrador().decrypt(token.encode()).decode()
    except InvalidToken:
        raise ValueError("Un dato personal no se pudo leer: la clave no corresponde "
                         "o el dato fue alterado") from None


def autorizar(solicitante: "Usuario", accion: str) -> None:
    """El permiso se revisa en el dominio, no solo en el menú (RF-SEG-05, decisión 6 del modelo)."""
    if accion not in ACCIONES:
        raise ValueError(f"Acción desconocida: {accion!r}")
    # Usuario se define más abajo; la función se llama recién en tiempo de ejecución.
    if not isinstance(solicitante, Usuario) or not solicitante.puede(accion):
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
    """Abre una conexión, la deja en una transacción y siempre la cierra.

    `with con:` confirma al salir sin error y deshace si hubo una excepción: ninguna operación
    queda guardada a medias.
    """
    con = sqlite3.connect(RUTA_ACTIVA, timeout=5)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")     # sqlite las trae apagadas por omisión
    try:
        with con:
            yield con
    finally:
        con.close()


def crear_tablas() -> None:
    with conectar() as con:
        con.executescript(ESQUEMA)
    try:
        os.chmod(RUTA_ACTIVA, 0o600)            # sqlite crea el archivo en 0644 (RNF-SEG-04)
    except OSError:
        print("   ! No se pudieron restringir los permisos de la base de datos.")


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
    COLUMNAS = ("id, correo, hash_clave, rol, nombre, rut_cifrado, telefono_cifrado,"
                " bloqueado_hasta")
    MAX_INTENTOS = 5
    BLOQUEO = timedelta(minutes=5)
    _senuelo: str | None = None         # hash que se verifica cuando el correo no existe

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

    def obtener_id(self) -> int | None:
        return self.__id

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

    def __verificar(self, clave: str) -> bool:
        try:
            return HASHER.verify(self.__hash_clave, clave)
        except (VerificationError, InvalidHashError):
            return False

    def cambiar_clave(self, actual: str, nueva: str) -> None:
        """RF-SEG-11: exige la contraseña actual antes de aceptar la nueva."""
        if not self.__verificar(actual):
            raise PermissionError("La contraseña actual no es correcta")
        self._validar_clave(nueva)
        self.__hash_clave = HASHER.hash(nueva)
        with conectar() as con:
            con.execute("UPDATE usuario SET hash_clave = ? WHERE id = ?",
                        (self.__hash_clave, self.__id))

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
                fila = con.execute(f"SELECT {cls.COLUMNAS} FROM usuario WHERE correo = ?",
                                   (correo,)).fetchone()
        if fila is None:
            cls.__senuelo(clave)
            return None
        usuario = _usuario_desde_fila(fila)
        return usuario if usuario.__intentar(clave) else None

    @classmethod
    def __senuelo(cls, clave: str) -> None:
        """Verifica la clave contra un hash al azar: el correo inexistente tarda lo mismo."""
        if cls._senuelo is None:
            Usuario._senuelo = HASHER.hash(secrets.token_urlsafe(16))
        try:
            HASHER.verify(cls._senuelo, clave if isinstance(clave, str) else "")
        except VerificationError:
            pass

    def __intentar(self, clave: str) -> bool:
        """Un intento de inicio de sesión sobre esta cuenta: True si entra. Registra el resultado."""
        ahora = datetime.now()
        bloqueada = self.__bloqueado_hasta is not None and ahora < self.__bloqueado_hasta
        correcta = isinstance(clave, str) and self.__verificar(clave)   # siempre: misma demora
        if bloqueada:
            return False
        with conectar() as con:
            if correcta:
                # Si los parámetros de Argon2 subieron desde que se creó el hash, se rehace ahora,
                # que es el único momento en que se tiene la contraseña en claro.
                if HASHER.check_needs_rehash(self.__hash_clave):
                    self.__hash_clave = HASHER.hash(clave)
                con.execute("UPDATE usuario SET intentos_fallidos = 0, bloqueado_hasta = NULL,"
                            " hash_clave = ? WHERE id = ?", (self.__hash_clave, self.__id))
            else:
                # Una sola sentencia: dos sesiones que fallan a la vez no pierden un intento.
                # SQLite evalúa cada CASE con los valores anteriores a la actualización.
                con.execute(
                    "UPDATE usuario SET"
                    " bloqueado_hasta = CASE WHEN intentos_fallidos + 1 >= ? THEN ?"
                    "                   ELSE bloqueado_hasta END,"
                    " intentos_fallidos = CASE WHEN intentos_fallidos + 1 >= ? THEN 0"
                    "                     ELSE intentos_fallidos + 1 END"
                    " WHERE id = ?",
                    (self.MAX_INTENTOS, (ahora + self.BLOQUEO).isoformat(), self.MAX_INTENTOS,
                     self.__id))
        return correcta

    def _insertar(self, rol: str, datos_cliente: tuple[str, str, str] | None = None,
                  solo_si_vacia: bool = False) -> bool:
        """C: INSERT de la cuenta. Las dos subclases lo comparten; no está en el diagrama porque
        es la persistencia común, como los métodos de CRUD."""
        nombre, rut, telefono = datos_cliente or (None, None, None)
        # Sin sesión, la primera cuenta solo entra si la tabla está vacía: la comprobación y la
        # escritura son una sola sentencia, sin carrera entre las dos (S-04).
        condicion = " WHERE NOT EXISTS (SELECT 1 FROM usuario)" if solo_si_vacia else ""
        try:
            with conectar() as con:
                cur = con.execute(
                    "INSERT INTO usuario (correo, hash_clave, rol, nombre, rut_cifrado,"
                    " telefono_cifrado) SELECT ?, ?, ?, ?, ?, ?" + condicion,
                    (self.__correo, self.__hash_clave, rol, nombre,
                     rut and cifrar(rut), telefono and cifrar(telefono)))
        except sqlite3.IntegrityError:
            raise ReglaNegocioError("R9", "Ese correo ya tiene una cuenta") from None
        if cur.rowcount != 1:
            return False
        self.__id = cur.lastrowid
        return True


class Cliente(Usuario):
    """Usuario con datos personales. RUT y teléfono se guardan cifrados y se muestran enmascarados."""

    def __init__(self, nombre: str, rut: str, correo: str, telefono: str,
                 clave: str | None = None, **cuenta):
        # Los datos se validan antes que la contraseña: el hash es lo caro, y no vale la pena
        # calcularlo para un registro que se va a rechazar.
        self.__nombre = texto(nombre, CAMPO_NOMBRE, 80)
        self.__rut = validar_rut(rut)
        self.__telefono = validar_telefono(telefono)
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
        cuerpo, dv = self.__rut.split("-")
        return f"{cuerpo[:-6]}.***.***-{dv}"

    def telefono_enmascarado(self) -> str:
        """+56 9 **** 1234 (RF-SEG-10)."""
        return f"+56 {self.__telefono[0]} **** {self.__telefono[-4:]}"

    @staticmethod
    def registrar(nombre: str, rut: str, correo: str, telefono: str, clave: str) -> "Cliente":
        """Registro público: siempre crea un cliente, nunca un administrador (RF-SEG-12)."""
        cliente = Cliente(nombre, rut, correo, telefono, clave)
        cliente._insertar("CLIENTE", (cliente.__nombre, cliente.__rut, cliente.__telefono))
        return cliente

    def historial(self) -> list["Reserva"]:
        """R: todas las reservas propias, pasadas, vigentes y anuladas; nunca las de otro (R11)."""
        return Reserva._listar("r.cliente_id = ?", (self.obtener_id(),))

    def actualizar_contacto(self, nombre: str, telefono: str) -> None:
        """U: nombre y teléfono propios (RF-RES-12). El RUT y el correo no cambian."""
        nombre, telefono = texto(nombre, CAMPO_NOMBRE, 80), validar_telefono(telefono)
        with conectar() as con:
            con.execute("UPDATE usuario SET nombre = ?, telefono_cifrado = ? WHERE id = ?",
                        (nombre, cifrar(telefono), self.obtener_id()))
        self.__nombre, self.__telefono = nombre, telefono


class Administrador(Usuario):
    """Socio de la agencia: mantiene el catálogo, arma los paquetes y crea cuentas de socios."""

    def puede(self, accion: str) -> bool:
        return accion in ("catalogo", "ver_reservas", "cuentas")

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
        nuevo._insertar("ADMINISTRADOR")
        return nuevo


def _usuario_desde_fila(fila: sqlite3.Row) -> Usuario:
    """La subclase que corresponde al rol guardado, con sus datos personales descifrados."""
    hasta = fila["bloqueado_hasta"]
    cuenta = {"id": fila["id"], "hash_clave": fila["hash_clave"],
              "bloqueado_hasta": datetime.fromisoformat(hasta) if hasta else None}
    if fila["rol"] == "CLIENTE":
        return Cliente(fila["nombre"], descifrar(fila["rut_cifrado"]), fila["correo"],
                       descifrar(fila["telefono_cifrado"]), **cuenta)
    return Administrador(fila["correo"], **cuenta)


class Destino:
    """tabla: destino. R1, R2 y R8."""

    COLUMNAS = ("id, nombre, zona, descripcion, duracion_dias, costo_base, disponible,"
                " fecha_costo")

    def __init__(self, nombre: str, zona: str, descripcion: str, duracion_dias: int,
                 costo_base: int, id: int | None = None, disponible: bool = True,
                 fecha_costo: date | None = None):
        # El constructor valida todo: un Destino inválido no llega a existir, se cree desde el
        # menú, desde una prueba o desde la base (tercera capa de validación, después del menú
        # y antes del CHECK).
        self.__id = id
        self.__fijar_datos(nombre, zona, descripcion, duracion_dias)
        self.__costo_base = entero(costo_base, "El costo base", 1, COSTO_MAXIMO, "R2")
        self.__disponible = bool(disponible)
        self.__fecha_costo = fecha_costo or date.today()

    def __fijar_datos(self, nombre, zona, descripcion, duracion_dias) -> None:
        self.__nombre = texto(nombre, CAMPO_NOMBRE, 80)
        self.__zona = texto(zona, "La zona", 80)
        self.__descripcion = texto(descripcion, "La descripción", 500)
        self.__duracion_dias = entero(duracion_dias, "La duración en días", 1,
                                      DURACION_MAXIMA, "R1")

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
        except sqlite3.IntegrityError:
            raise ReglaNegocioError("R1", "Ya existe un destino con ese nombre") from None
        self.__id = cur.lastrowid
        return self.__id

    def editar(self, nombre: str, zona: str, descripcion: str, duracion_dias: int,
               solicitante: "Usuario") -> None:
        """U: los datos descriptivos, con las mismas validaciones del registro (RF-DES-04)."""
        autorizar(solicitante, "catalogo")
        anterior = (self.__nombre, self.__zona, self.__descripcion, self.__duracion_dias)
        self.__fijar_datos(nombre, zona, descripcion, duracion_dias)
        try:
            with conectar() as con:
                con.execute(
                    "UPDATE destino SET nombre = ?, nombre_normalizado = ?, zona = ?,"
                    " descripcion = ?, duracion_dias = ? WHERE id = ?",
                    (self.__nombre, normalizar(self.__nombre), self.__zona, self.__descripcion,
                     self.__duracion_dias, self.__id))
        except sqlite3.IntegrityError:
            # El objeto vuelve a sus datos anteriores: memoria y base siguen diciendo lo mismo.
            self.__nombre, self.__zona, self.__descripcion, self.__duracion_dias = anterior
            raise ReglaNegocioError("R1", "Ya existe un destino con ese nombre") from None

    def cambiar_costo(self, costo_base: int, solicitante: "Usuario") -> None:
        """U: el costo, con la fecha del cambio (RF-DES-05). Los paquetes publicados no cambian (R7)."""
        autorizar(solicitante, "catalogo")
        self.__costo_base = entero(costo_base, "El costo base", 1, COSTO_MAXIMO, "R2")
        self.__fecha_costo = date.today()
        with conectar() as con:
            con.execute("UPDATE destino SET costo_base = ?, fecha_costo = ? WHERE id = ?",
                        (self.__costo_base, self.__fecha_costo.isoformat(), self.__id))

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
        self.__disponible = False
        return en_paquete is None

    def reactivar(self, solicitante: "Usuario") -> None:
        """U: vuelve a ofrecer un destino no disponible (RF-DES-09)."""
        autorizar(solicitante, "catalogo")
        with conectar() as con:
            con.execute("UPDATE destino SET disponible = 1 WHERE id = ?", (self.__id,))
        self.__disponible = True

    @classmethod
    def listar(cls, solo_disponibles: bool = False) -> list["Destino"]:
        """R: todo el catálogo, o solo lo que se puede ofrecer (RF-DES-08, RF-DES-10)."""
        filtro = " WHERE disponible = 1" if solo_disponibles else ""
        with conectar() as con:
            filas = con.execute(f"SELECT {cls.COLUMNAS} FROM destino{filtro} ORDER BY nombre"
                                ).fetchall()
        return [cls._desde_fila(f) for f in filas]

    @classmethod
    def buscar(cls, id: int) -> "Destino | None":
        with conectar() as con:
            fila = con.execute(f"SELECT {cls.COLUMNAS} FROM destino WHERE id = ?",
                               (id,)).fetchone()
        return cls._desde_fila(fila) if fila else None

    @classmethod
    def _desde_fila(cls, fila: sqlite3.Row) -> "Destino":
        return cls(fila["nombre"], fila["zona"], fila["descripcion"], fila["duracion_dias"],
                   fila["costo_base"], id=fila["id"], disponible=fila["disponible"],
                   fecha_costo=date.fromisoformat(fila["fecha_costo"]))


class Paquete:
    """tabla: paquete, y paquete_destino para la agregación con Destino. R3 a R8 y R14."""

    COLUMNAS = ("id, nombre, fecha_salida, fecha_regreso, cupo_maximo, margen,"
                " precio_por_persona, publicado")

    def __init__(self, nombre: str, fecha_salida: date, fecha_regreso: date, cupo_maximo: int,
                 destinos: list[Destino], margen: int = MARGEN_PROPUESTO, id: int | None = None,
                 precio_por_persona: int | None = None, publicado: bool = False):
        self.__id = id
        self.__fijar_datos(nombre, fecha_salida, fecha_regreso, margen)
        self.__cupo_maximo = entero(cupo_maximo, "El cupo máximo", 1, CUPO_MAXIMO, "R5")
        # Un paquete nuevo solo combina destinos disponibles (R8); uno guardado conserva los que
        # tenía aunque después hayan quedado no disponibles (S-15).
        self.__destinos = self.__validar_destinos(destinos, exigir_disponibles=id is None)
        self.__precio_por_persona = precio_por_persona
        self.__publicado = bool(publicado)

    def __fijar_datos(self, nombre, fecha_salida, fecha_regreso, margen) -> None:
        self.__nombre = texto(nombre, CAMPO_NOMBRE, 80)
        self.__fecha_salida = fecha(fecha_salida, "La fecha de salida")
        self.__fecha_regreso = fecha(fecha_regreso, "La fecha de regreso")
        if self.__fecha_regreso <= self.__fecha_salida:
            raise ReglaNegocioError("R5", "La fecha de regreso debe ser posterior a la de salida")
        self.__margen = entero(margen, "El margen (%)", 0, MARGEN_MAXIMO, "R6")

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
        self.__id = cur.lastrowid
        return self.__id

    def __exigir_disponibles_en_base(self, con: sqlite3.Connection) -> None:
        """R8 contra la base, dentro de la transacción: el objeto en memoria puede estar viejo."""
        ids = [d.obtener_id() for d in self.__destinos]
        disponibles = con.execute(
            f"SELECT COUNT(*) FROM destino WHERE disponible = 1 AND id IN ({','.join('?' * len(ids))})",
            ids).fetchone()[0]                  # solo signos «?»: el SQL no lleva datos del usuario
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
        self.__fijar_datos(nombre, fecha_salida, fecha_regreso, margen)
        with conectar() as con:
            con.execute("UPDATE paquete SET nombre = ?, fecha_salida = ?, fecha_regreso = ?,"
                        " margen = ? WHERE id = ? AND publicado = 0",
                        (self.__nombre, self.__fecha_salida.isoformat(),
                         self.__fecha_regreso.isoformat(), self.__margen, self.__id))

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
        if cur.rowcount != 1:
            raise ReglaNegocioError("R14", "El cupo no puede quedar bajo las personas ya reservadas")
        self.__cupo_maximo = cupo

    def eliminar(self, solicitante: "Usuario") -> None:
        """D: solo sin reservas, ni siquiera anuladas: son historial (RF-PAQ-09, R11)."""
        autorizar(solicitante, "catalogo")
        with conectar() as con:
            cur = con.execute("DELETE FROM paquete WHERE id = ? AND NOT EXISTS"
                              " (SELECT 1 FROM reserva WHERE paquete_id = ?)", (self.__id, self.__id))
        if cur.rowcount != 1:
            raise ReglaNegocioError("RF-PAQ-09", "Un paquete con reservas no se elimina")

    @classmethod
    def listar_disponibles(cls, hoy: date | None = None) -> list["Paquete"]:
        """R: la oferta (RF-PAQ-06, RF-PAQ-07). Sin sesión también se puede ver (S-09)."""
        hoy = hoy or date.today()
        return [p for p in cls._listar("publicado = 1 AND fecha_salida > ?", (hoy.isoformat(),))
                if p.esta_disponible(hoy)]

    @classmethod
    def listar_todos(cls, solicitante: "Usuario") -> list["Paquete"]:
        """R: todos, con su estado, para el administrador (RF-PAQ-10)."""
        autorizar(solicitante, "catalogo")
        return cls._listar("1 = 1", ())

    @classmethod
    def buscar(cls, id: int) -> "Paquete | None":
        encontrados = cls._listar("id = ?", (id,))
        return encontrados[0] if encontrados else None

    @classmethod
    def _listar(cls, condicion: str, parametros: tuple) -> list["Paquete"]:
        # condicion es siempre un texto fijo de esta clase; los datos van como parámetros.
        with conectar() as con:
            filas = con.execute(f"SELECT {cls.COLUMNAS} FROM paquete WHERE {condicion}"
                                " ORDER BY fecha_salida, id", parametros).fetchall()
            destinos = {}
            for fila in filas:
                ids = [r[0] for r in con.execute(
                    "SELECT destino_id FROM paquete_destino WHERE paquete_id = ? ORDER BY rowid",
                    (fila["id"],))]
                destinos[fila["id"]] = [Destino.buscar(i) for i in ids]
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
        self.__total = entero(total, "El total", 1, COSTO_MAXIMO * CUPO_MAXIMO, "R13")
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

        IMMEDIATE toma el permiso de escritura antes de leer el cupo: una segunda reserva
        simultánea espera a que esta termine y después ve el cupo ya descontado. Así dos personas
        no pueden quedarse con el mismo último lugar (RNF-FIA-02, P-02).
        """
        autorizar(solicitante, "reservar")
        hoy = fecha(hoy or date.today(), "La fecha de hoy")
        personas = entero(personas, "La cantidad de personas", 1, CUPO_MAXIMO, "R16")
        with conectar() as con:
            con.execute("BEGIN IMMEDIATE")
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
            total = fila["precio_por_persona"] * personas          # R13: se calcula una vez
            cur = con.execute("INSERT INTO reserva (cliente_id, paquete_id, fecha_emision,"
                              " personas, total) VALUES (?, ?, ?, ?, ?)",
                              (solicitante.obtener_id(), paquete.obtener_id(), hoy.isoformat(),
                               personas, total))
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
        if cur.rowcount != 1:
            raise ReglaNegocioError("S-01", "Solo se anula una reserva vigente, antes del día de salida")
        self.__estado = EstadoReserva.ANULADA

    @staticmethod
    def listar_por_paquete(paquete: Paquete, solicitante: "Usuario") -> list["Reserva"]:
        """R: quién viaja en un paquete, con nombre y correo; nunca RUT ni teléfono (RF-RES-11, S-16)."""
        autorizar(solicitante, "ver_reservas")
        return Reserva._listar("r.paquete_id = ?", (paquete.obtener_id(),))

    @staticmethod
    def _listar(condicion: str, parametros: tuple) -> list["Reserva"]:
        # condicion es siempre un texto fijo de esta clase; los datos van como parámetros.
        with conectar() as con:
            filas = con.execute(
                f"SELECT r.id, r.paquete_id, r.fecha_emision, r.personas, r.total, r.estado,"
                f" {', '.join('u.' + c.strip() for c in Usuario.COLUMNAS.split(','))}"
                f" FROM reserva r JOIN usuario u ON u.id = r.cliente_id WHERE {condicion}"
                f" ORDER BY r.fecha_emision, r.id", parametros).fetchall()
        paquetes: dict[int, Paquete] = {}
        reservas = []
        for f in filas:
            if f["paquete_id"] not in paquetes:
                paquetes[f["paquete_id"]] = Paquete.buscar(f["paquete_id"])
            reservas.append(Reserva(_usuario_desde_fila(f), paquetes[f["paquete_id"]],
                                    f["personas"], f["total"], date.fromisoformat(f["fecha_emision"]),
                                    EstadoReserva(f["estado"]), id=f[0]))
        return reservas


# =====================================================================
# 4. AUTOVERIFICACIÓN
# =====================================================================


def autoverificar() -> None:
    """Recorre las reglas sobre una base temporal y falla con AssertionError si alguna se rompe."""
    global RUTA_CLAVE
    original = RUTA_CLAVE
    os.environ.pop(VARIABLE_CLAVE, None)            # la clave se crea en la carpeta temporal,
    with tempfile.TemporaryDirectory() as carpeta:  # nunca en el .env real
        RUTA_CLAVE = Path(carpeta) / ".env"
        cifrador.cache_clear()
        try:
            usar_base(os.path.join(carpeta, "prueba.db"))
            crear_tablas()
            _verificar_clave_y_permisos(carpeta)
            _verificar_cuentas()
            _verificar_destinos()
            _verificar_paquetes_y_reservas()
        finally:
            RUTA_CLAVE = original
            cifrador.cache_clear()
    print("OK")


def _verificar_clave_y_permisos(carpeta: str) -> None:
    # S-12: la clave se crea en el primer uso, fuera de la base, con un nombre de variable fijo.
    cifrador()
    assert RUTA_CLAVE.read_text(encoding="utf-8").startswith(f"{VARIABLE_CLAVE}=")
    # RNF-SEG-04: la base y la clave quedan solo para su dueño. Windows no tiene estos permisos.
    if os.name == "posix":
        for archivo in (RUTA_ACTIVA, RUTA_CLAVE):
            assert os.stat(archivo).st_mode & 0o777 == 0o600, archivo


def _rechaza(error: type[Exception], accion, *args, regla: str | None = None) -> None:
    """Comprueba que la acción falla con ese error (y esa regla, si se indica)."""
    try:
        accion(*args)
    except error as e:
        if regla is not None:
            assert e.obtener_regla() == regla, (e.obtener_regla(), regla)
        return
    raise AssertionError(f"{getattr(accion, '__name__', accion)} no rechazó {args!r}")


CAROLINA = "carolina@correo.cl"            # correo de prueba de la autoverificación


def _verificar_cuentas() -> None:
    # S-04: la primera cuenta es de administrador y solo puede crearse una vez.
    assert not hay_usuarios()
    admin = Administrador.crear_primero("ana@viajes.cl", "clave-larga-de-ana")
    _rechaza(PermissionError, Administrador.crear_primero, "otro@viajes.cl", "clave-larga-otro")
    socio = admin.crear_administrador("matias@viajes.cl", "clave-larga-matias")
    assert socio.puede("catalogo") and not socio.puede("reservar")

    # RF-RES-01 a RF-RES-03 y RF-SEG-12: el registro público crea clientes y valida cada dato.
    carolina = Cliente.registrar("Carolina Díaz", "12.345.678-5", CAROLINA,
                                 "+56 9 1234 5678", "clave-de-carolina")
    assert isinstance(carolina, Cliente) and carolina.puede("reservar")
    assert not carolina.puede("catalogo")
    _rechaza(PermissionError, autorizar, carolina, "cuentas")
    _rechaza(ReglaNegocioError, Cliente.registrar, "Otra", "11.111.111-1", "Carolina@Correo.cl",
             "912345678", "otra-clave-larga", regla="R9")
    for rut, correo, fono in (("12.345.678-6", "a@b.cl", "912345678"),
                              ("12.345.678-5", "sin-arroba.cl", "912345678"),
                              ("12.345.678-5", "a@b.cl", "9123abc78")):
        try:
            Cliente("Nombre", rut, correo, fono, "clave-larga-valida")
            raise AssertionError("aceptó un dato inválido")
        except ValueError as e:
            assert "12.345.678" not in str(e) and "9123" not in str(e)   # RF-SEG-13
    assert validar_rut("6.574.256-K") == "6574256-K"         # dígito K

    # RF-SEG-04: 12 caracteres o más, y distinta del correo.
    _rechaza(ReglaNegocioError, Cliente, "N", "12.345.678-5", "n@b.cl", "912345678", "a" * 11,
             regla="RF-SEG-04")
    _rechaza(ReglaNegocioError, Cliente, "N", "12.345.678-5", "nombre.largo@b.cl", "912345678",
             "Nombre.Largo@b.cl", regla="RF-SEG-04")

    # R10, R17 y RNF-SEG-02: en la base no hay contraseña, RUT ni teléfono legibles,
    # y un dato cifrado alterado da error, no un dato falso.
    with conectar() as con:
        fila = con.execute("SELECT hash_clave, rut_cifrado, telefono_cifrado FROM usuario"
                           " WHERE correo = ?", (CAROLINA,)).fetchone()
    assert fila["hash_clave"].startswith("$argon2id$")
    assert "12345678" not in fila["rut_cifrado"] and "5678" not in fila["telefono_cifrado"]
    alterado = fila["rut_cifrado"][:-6] + ("A" if fila["rut_cifrado"][-6] != "A" else "B") \
        + fila["rut_cifrado"][-5:]
    _rechaza(ValueError, descifrar, alterado)

    # S-12: si la clave se pierde con datos ya cifrados, no se crea otra (los dejaría ilegibles).
    respaldo = RUTA_CLAVE.read_bytes()
    RUTA_CLAVE.unlink()
    cifrador.cache_clear()
    _rechaza(RuntimeError, cifrador)
    RUTA_CLAVE.write_bytes(respaldo)
    cifrador.cache_clear()

    # RF-SEG-10 y C4: enmascarado, y fuera de la representación del objeto.
    assert carolina.rut_enmascarado() == "12.***.***-5"
    assert carolina.telefono_enmascarado() == "+56 9 **** 5678"
    assert "12345678" not in repr(carolina) and "5678" not in repr(carolina)

    # RF-SEG-01 y RF-SEG-02: inicio de sesión; los tres fallos devuelven lo mismo.
    entrada = Usuario.autenticar("Carolina@correo.cl", "clave-de-carolina")
    assert isinstance(entrada, Cliente) and entrada.rut_enmascarado() == "12.***.***-5"
    assert isinstance(Usuario.autenticar("ana@viajes.cl", "clave-larga-de-ana"), Administrador)
    assert Usuario.autenticar("nadie@correo.cl", "clave-de-carolina") is None
    assert Usuario.autenticar(CAROLINA, "otra-clave") is None
    assert Usuario.autenticar("no es correo", "x") is None

    # RF-SEG-03: cinco fallos seguidos bloquean, aun con la contraseña correcta, y el bloqueo
    # está en la base (sobrevive a cerrar el programa). Al vencer, se puede entrar.
    for _ in range(4):
        Usuario.autenticar(CAROLINA, "otra-clave")   # 1 ya contó arriba: 5 en total
    assert Usuario.autenticar(CAROLINA, "clave-de-carolina") is None
    with conectar() as con:
        con.execute("UPDATE usuario SET bloqueado_hasta = ? WHERE correo = ?",
                    ((datetime.now() - timedelta(seconds=1)).isoformat(), CAROLINA))
    assert Usuario.autenticar(CAROLINA, "clave-de-carolina") is not None

    # RF-SEG-11 y RF-RES-12.
    _rechaza(PermissionError, carolina.cambiar_clave, "clave-equivocada", "nueva-clave-larga")
    carolina.cambiar_clave("clave-de-carolina", "nueva-clave-larga")
    assert Usuario.autenticar(CAROLINA, "nueva-clave-larga") is not None
    carolina.actualizar_contacto("Carolina Díaz R.", "987654321")
    releida = Usuario.autenticar(CAROLINA, "nueva-clave-larga")
    assert releida.obtener_nombre() == "Carolina Díaz R."
    assert releida.telefono_enmascarado() == "+56 9 **** 4321"

    # La base rechaza por sí misma una contraseña en claro y un cliente sin RUT.
    with conectar() as con:
        for sql in ("INSERT INTO usuario (correo, hash_clave, rol) VALUES ('z@z.cl', 'clave', 'ADMINISTRADOR')",
                    "INSERT INTO usuario (correo, hash_clave, rol, nombre) VALUES"
                    " ('y@z.cl', '$argon2id$x', 'CLIENTE', 'Sin RUT')"):
            _rechaza(sqlite3.IntegrityError, con.execute, sql)
    _verificar_cuentas.cuentas = (admin, carolina)


def _verificar_destinos() -> None:
    admin, cliente = _verificar_cuentas.cuentas

    # R1 y RF-DES-02: el nombre no se repite, aunque cambien mayúsculas, tildes o espacios.
    elqui = Destino("Valle del Elqui", "Norte Chico", "Observación astronómica", 3, 120_000)
    id_elqui = elqui.guardar(admin)
    for repetido in ("valle del  elqui", "Valle del Elquí"):
        _rechaza(ReglaNegocioError, Destino(repetido, "Norte", "x", 1, 1).guardar, admin, regla="R1")

    # R2 y R1: costo mayor que cero y duración de al menos un día, en el dominio y en la base.
    _rechaza(ReglaNegocioError, Destino, "Otro", "Zona", "x", 1, 0, regla="R2")
    _rechaza(ReglaNegocioError, Destino, "Otro", "Zona", "x", 1, -1, regla="R2")
    _rechaza(ReglaNegocioError, Destino, "Otro", "Zona", "x", 0, 1, regla="R1")
    _rechaza(TypeError, Destino, "Otro", "Zona", "x", True, 1)     # bool no es un entero válido
    with conectar() as con:
        for costo, dias in ((0, 1), (1, 0)):
            _rechaza(sqlite3.IntegrityError, con.execute,
                     "INSERT INTO destino (nombre, nombre_normalizado, zona, descripcion,"
                     " duracion_dias, costo_base, fecha_costo) VALUES ('a', 'a', 'z', 'd', ?, ?, 'x')",
                     (dias, costo))

    # RF-DES-04 y RF-DES-05: editar y cambiar el costo, que registra la fecha.
    elqui.cambiar_costo(130_000, admin)
    assert Destino.buscar(id_elqui).obtener_costo_base() == 130_000

    # RF-SEG-05: un cliente no toca el catálogo, aunque llame directo al dominio.
    _rechaza(PermissionError, elqui.cambiar_costo, 1, cliente)
    _rechaza(PermissionError, Destino("Nuevo", "Z", "d", 1, 1).guardar, cliente)

    # R8: sin paquetes se elimina; dentro de un paquete queda no disponible.
    surire = Destino("Salar de Surire", "Altiplano", "Flamencos", 4, 310_000)
    surire.guardar(admin)
    with conectar() as con:
        con.execute("INSERT INTO paquete (id, nombre, fecha_salida, fecha_regreso,"
                    " cupo_maximo, margen) VALUES (1, 'P', '2026-12-01', '2026-12-05', 10, 20)")
        con.execute("INSERT INTO paquete_destino VALUES (1, ?)", (surire.obtener_id(),))
    assert surire.eliminar(admin) is False and not surire.esta_disponible()
    assert [d.obtener_costo_base() for d in Destino.listar(solo_disponibles=True)] == [130_000]
    surire.reactivar(admin)
    assert len(Destino.listar(solo_disponibles=True)) == 2
    assert elqui.eliminar(admin) is True and Destino.buscar(id_elqui) is None
    # El paquete de apoyo se insertó por SQL con un solo destino, cosa que R3 prohíbe y que la
    # base no puede impedir (la regla abarca varias filas): se borra para no dejar un dato inválido.
    with conectar() as con:
        con.execute("DELETE FROM paquete WHERE id = 1")



def _verificar_paquetes_y_reservas() -> None:
    admin, carolina = _verificar_cuentas.cuentas
    pedro = Cliente.registrar("Pedro Soto", "11.111.111-1", "pedro@correo.cl", "922223333",
                              "clave-de-pedro-1")
    salida, regreso = date.today() + timedelta(days=30), date.today() + timedelta(days=35)
    surire = Destino("Salar de Surire 2", "Altiplano", "Flamencos", 4, 310_000)
    elqui = Destino("Valle del Elqui 2", "Norte Chico", "Estrellas", 3, 120_000)
    otros = [Destino(f"Destino {i}", "Zona", "d", 1, 10_000) for i in range(4)]
    for d in (surire, elqui, *otros):
        d.guardar(admin)

    # RF-PAQ-02 (R3, R8): uno o seis destinos, uno repetido o uno no disponible.
    for destinos in ([surire], [surire, elqui, *otros], [surire, surire]):
        _rechaza(ReglaNegocioError, Paquete, "P", salida, regreso, 10, destinos, regla="R3")
    otros[3].eliminar(admin)                        # sin paquetes: se elimina
    otros[2].eliminar(admin)
    no_disponible = otros[1]
    with conectar() as con:
        con.execute("UPDATE destino SET disponible = 0 WHERE id = ?", (no_disponible.obtener_id(),))
    no_disponible = Destino.buscar(no_disponible.obtener_id())
    _rechaza(ReglaNegocioError, Paquete, "P", salida, regreso, 10, [surire, no_disponible], regla="R8")

    # RF-PAQ-03 (R5, R6): regreso no posterior, cupo 0 y margen negativo.
    _rechaza(ReglaNegocioError, Paquete, "P", salida, salida, 10, [surire, elqui], regla="R5")
    _rechaza(ReglaNegocioError, Paquete, "P", salida, regreso, 0, [surire, elqui], regla="R5")
    _rechaza(ReglaNegocioError, Paquete, "P", salida, regreso, 10, [surire, elqui], -5, regla="R6")
    _rechaza(TypeError, Paquete, "P", datetime.now(), regreso, 10, [surire, elqui])

    # RF-PAQ-01, RF-PAQ-04 y RF-PAQ-11: borrador con 20 % por omisión; 310.000 + 120.000 = 516.000.
    altiplano = Paquete("Altiplano y estrellas", salida, regreso, 12, [surire, elqui])
    altiplano.guardar(admin)
    assert altiplano.calcular_precio() == 516_000 and altiplano.estado() == "borrador"
    otro = Paquete("Otro con Surire", salida, regreso, 5, [surire, otros[0]])   # R4
    otro.guardar(admin)
    _rechaza(PermissionError, Paquete("Del cliente", salida, regreso, 5, [elqui, otros[0]]).guardar,
             carolina)

    # S-07 y RF-PAQ-08: el borrador se edita completo.
    altiplano.editar("Altiplano y estrellas", salida, regreso, 20, admin)
    altiplano.reemplazar_destinos([surire, elqui], admin)
    _rechaza(ReglaNegocioError, Reserva.reservar, altiplano, 1, carolina, regla="R7")   # sin publicar

    # RF-PAQ-05 (R7): publicado, el precio no cambia aunque cambie un costo; el borrador sí.
    altiplano.publicar(admin)
    elqui.cambiar_costo(150_000, admin)
    assert Paquete.buscar(altiplano.obtener_id()).calcular_precio() == 552_000      # costo nuevo
    assert "516.000" in str(Paquete.buscar(altiplano.obtener_id()))                 # precio fijo
    assert Paquete.buscar(otro.obtener_id()).calcular_precio() == (310_000 + 10_000) * 120 // 100
    _rechaza(ReglaNegocioError, altiplano.editar, "X", salida, regreso, 20, admin, regla="R7")
    _rechaza(ReglaNegocioError, altiplano.publicar, admin, regla="R7")

    # RF-RES-04, RF-RES-07 (R13) y R16: total fijo = precio publicado × personas.
    _rechaza(PermissionError, Reserva.reservar, altiplano, 1, admin)
    _rechaza(ReglaNegocioError, Reserva.reservar, altiplano, 0, carolina, regla="R16")
    reserva = Reserva.reservar(altiplano, 2, carolina)
    assert reserva.obtener_total() == 1_032_000
    elqui.cambiar_costo(200_000, admin)
    assert carolina.historial()[0].obtener_total() == 1_032_000

    # RF-PAQ-06 y R14: cupo 12, vigentes por 10 y una anulada por 2: quedan 2.
    Reserva.reservar(altiplano, 2, carolina)
    Reserva.reservar(altiplano, 6, pedro)
    anulada = Reserva.reservar(altiplano, 2, pedro)
    _rechaza(PermissionError, anulada.anular, carolina)                 # R11: solo el titular
    anulada.anular(pedro)                                               # RF-RES-09, S-01
    _rechaza(ReglaNegocioError, anulada.anular, pedro, regla="S-01")
    assert Paquete.buscar(altiplano.obtener_id()).cupo_disponible() == 2
    try:
        Reserva.reservar(altiplano, 3, carolina)
        raise AssertionError("aceptó una reserva sobre el cupo")
    except ReglaNegocioError as e:
        assert e.obtener_regla() == "R14" and "quedan 2" in str(e)        # RF-RES-05

    # RF-PAQ-08: un publicado solo cambia el cupo, y nunca bajo lo reservado (10).
    _rechaza(ReglaNegocioError, altiplano.cambiar_cupo, 9, admin, regla="R14")
    altiplano.cambiar_cupo(11, admin)

    # RNF-FIA-02: dos reservas simultáneas por el último lugar; solo una se guarda.
    resultado = {}

    def reservar_en_paralelo():
        try:
            Reserva.reservar(altiplano, 1, pedro)
            resultado["otra"] = "guardada"
        except ReglaNegocioError as e:
            resultado["otra"] = e.obtener_regla()

    con = sqlite3.connect(RUTA_ACTIVA, timeout=5, isolation_level=None)
    con.execute("BEGIN IMMEDIATE")                      # esta sesión toma el último lugar primero
    hilo = threading.Thread(target=reservar_en_paralelo)
    hilo.start()
    hilo.join(0.3)
    assert hilo.is_alive(), "la segunda reserva no esperó a la primera"
    con.execute("INSERT INTO reserva (cliente_id, paquete_id, fecha_emision, personas, total)"
                " VALUES (?, ?, ?, 1, 516000)",
                (carolina.obtener_id(), altiplano.obtener_id(), date.today().isoformat()))
    con.execute("COMMIT")
    con.close()
    hilo.join()
    assert resultado["otra"] == "R14", resultado
    assert Paquete.buscar(altiplano.obtener_id()).cupo_disponible() == 0

    # RF-PAQ-07, RF-RES-06 (R15) y S-02: el día de salida ya no se ofrece ni se reserva,
    # pero el paquete sigue en el listado del administrador, como vencido.
    altiplano.cambiar_cupo(15, admin)
    ofertas = Paquete.listar_disponibles()
    assert [p.obtener_id() for p in ofertas] == [altiplano.obtener_id()]
    assert Paquete.listar_disponibles(hoy=salida) == []
    _rechaza(ReglaNegocioError, Reserva.reservar, altiplano, 1, carolina, salida, regla="R15")
    assert Paquete.buscar(altiplano.obtener_id()).estado(salida) == "vencido"
    assert len(Paquete.listar_todos(admin)) == 2
    _rechaza(PermissionError, Paquete.listar_todos, carolina)

    # RF-RES-08 (R11): cada cliente ve todas las suyas, incluida la anulada, y ninguna ajena.
    assert len(carolina.historial()) == 3 and len(pedro.historial()) == 2
    assert {r.obtener_total() for r in pedro.historial()} == {6 * 516_000, 2 * 516_000}

    # RF-RES-11 y S-16: el administrador ve nombre y correo, nunca RUT ni teléfono.
    lista = Reserva.listar_por_paquete(altiplano, admin)
    assert len(lista) == 5 and all("12.345" not in str(r) and "2222" not in str(r) for r in lista)
    _rechaza(PermissionError, Reserva.listar_por_paquete, altiplano, carolina)

    # RF-PAQ-09: con reservas no se elimina; sin reservas, sí (y se llevan sus destinos).
    _rechaza(ReglaNegocioError, altiplano.eliminar, admin, regla="RF-PAQ-09")
    otro.eliminar(admin)
    assert Paquete.buscar(otro.obtener_id()) is None

    # R8 con paquetes: Surire está en un paquete, así que queda no disponible y el paquete lo
    # conserva (S-15); un paquete nuevo ya no puede usarlo, ni en memoria ni en la base.
    assert surire.eliminar(admin) is False
    assert surire.obtener_id() in [d.obtener_id() for d in
                                   Paquete.buscar(altiplano.obtener_id()).listar_destinos()]
    _rechaza(ReglaNegocioError, Paquete("Nuevo", salida, regreso, 5, [elqui, otros[0]])
             .reemplazar_destinos, [surire, elqui], admin, regla="R8")

    # La base rechaza por sí misma lo que violan R3, R5, R13 y R16 (RNF-FIA-01).
    with conectar() as con:
        for sql, datos in (
                ("INSERT INTO paquete (nombre, fecha_salida, fecha_regreso, cupo_maximo, margen)"
                 " VALUES ('x', '2030-01-05', '2030-01-01', 5, 20)", ()),                    # R5
                ("INSERT INTO paquete_destino VALUES (?, ?)",
                 (altiplano.obtener_id(), elqui.obtener_id())),                            # R3
                ("INSERT INTO reserva (cliente_id, paquete_id, fecha_emision, personas, total)"
                 " VALUES (?, ?, '2030-01-01', 0, 1)", (pedro.obtener_id(), altiplano.obtener_id())),
                ("INSERT INTO reserva (cliente_id, paquete_id, fecha_emision, personas, total,"
                 " estado) VALUES (?, ?, '2030-01-01', 1, 1, 'PAGADA')",
                 (pedro.obtener_id(), altiplano.obtener_id()))):
            _rechaza(sqlite3.IntegrityError, con.execute, sql, datos)


if __name__ == "__main__":
    autoverificar()
