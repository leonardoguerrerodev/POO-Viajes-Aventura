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
import sqlite3                              # la base de datos: un archivo, sin servidor
import tempfile                             # base temporal para la autoverificación
import unicodedata                          # quita tildes al comparar nombres de destinos (RF-DES-02)
from contextlib import contextmanager       # `with conectar()`: abre y siempre cierra la conexión
from datetime import date                   # fecha del último cambio de costo (RF-DES-05)
from pathlib import Path                    # ubica la base junto a este archivo

# =====================================================================
# 1. VALIDACIONES Y AUTORIZACIÓN COMPARTIDAS
# =====================================================================

# Todo entero que llega del usuario tiene techo: sin techo, un número de 25 dígitos
# termina en OverflowError al guardarlo (regla 8 de EcoTech).
COSTO_MAXIMO = 100_000_000
DURACION_MAXIMA = 365

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


def normalizar(nombre: str) -> str:
    """Forma comparable de un nombre: sin tildes, sin mayúsculas y con un solo espacio entre palabras.

    «Valle del  Elquí» y «valle del elqui» dan lo mismo (RF-DES-02). La IA propuso mayúsculas y
    espacios; las tildes se agregaron porque el criterio de aceptación las exige.
    """
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", nombre)
                         if not unicodedata.combining(c))
    return " ".join(sin_tildes.casefold().split())


def autorizar(solicitante: "Usuario", accion: str) -> None:
    """El permiso se revisa en el dominio, no solo en el menú (RF-SEG-05, decisión 6 del modelo)."""
    if accion not in ACCIONES:
        raise ValueError(f"Acción desconocida: {accion!r}")
    # La importación circular no existe: Usuario se define más abajo en este mismo archivo
    # y esta función se llama recién en tiempo de ejecución.
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
        self.__nombre = texto(nombre, "El nombre", 80)
        self.__zona = texto(zona, "La zona", 80)
        self.__descripcion = texto(descripcion, "La descripción", 500)
        self.__duracion_dias = entero(duracion_dias, "La duración en días", 1,
                                      DURACION_MAXIMA, "R1")

    def __str__(self) -> str:
        estado = "disponible" if self.__disponible else "no disponible"
        costo = f"{self.__costo_base:,}".replace(",", ".")       # RNF-USA-02
        return (f"[{self.__id}] {self.__nombre} · {self.__zona} · {self.__duracion_dias} días · "
                f"${costo} (costo al {self.__fecha_costo:%d-%m-%Y}) · {estado}")

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


# =====================================================================
# 4. AUTOVERIFICACIÓN
# =====================================================================


def autoverificar() -> None:
    """Recorre las reglas sobre una base temporal y falla con AssertionError si alguna se rompe."""
    with tempfile.TemporaryDirectory() as carpeta:
        usar_base(os.path.join(carpeta, "prueba.db"))
        crear_tablas()
        admin = Usuario({"catalogo"})

        # R1 y RF-DES-02: el nombre no se repite, aunque cambien mayúsculas, tildes o espacios.
        elqui = Destino("Valle del Elqui", "Norte Chico", "Observación astronómica", 3, 120_000)
        id_elqui = elqui.guardar(admin)
        for repetido in ("valle del  elqui", "Valle del Elquí"):
            try:
                Destino(repetido, "Norte", "x", 1, 1).guardar(admin)
                raise AssertionError("aceptó un nombre repetido")
            except ReglaNegocioError as e:
                assert e.obtener_regla() == "R1"

        # R2 y R1: costo mayor que cero y duración de al menos un día, en el dominio y en la base.
        for costo, dias in ((0, 1), (-1, 1), (1, 0)):
            try:
                Destino("Otro", "Zona", "x", dias, costo)
                raise AssertionError("aceptó costo o duración inválidos")
            except ReglaNegocioError:
                pass
        try:
            Destino("Otro", "Zona", "x", True, 1)                 # bool no es un entero válido
            raise AssertionError("aceptó un bool como duración")
        except TypeError:
            pass
        with conectar() as con:
            for sql in ("INSERT INTO destino (nombre, nombre_normalizado, zona, descripcion,"
                        " duracion_dias, costo_base, fecha_costo) VALUES ('a','a','z','d',1,0,'x')",
                        "INSERT INTO destino (nombre, nombre_normalizado, zona, descripcion,"
                        " duracion_dias, costo_base, fecha_costo) VALUES ('b','b','z','d',0,1,'x')"):
                try:
                    con.execute(sql)
                    raise AssertionError("la base aceptó un destino inválido")
                except sqlite3.IntegrityError:
                    pass

        # RF-DES-04 y RF-DES-05: editar y cambiar el costo, que registra la fecha.
        elqui.cambiar_costo(130_000, admin)
        assert Destino.buscar(id_elqui).obtener_costo_base() == 130_000

        # RF-SEG-05: sin el permiso, el dominio rechaza aunque el menú no exista.
        try:
            elqui.cambiar_costo(1, Usuario(set()))
            raise AssertionError("cambió el costo sin permiso")
        except PermissionError:
            pass

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
    print("OK")


class Usuario:
    """Provisional, con un conjunto fijo de permisos.

    ponytail: existe solo hasta el incremento de cuentas (HU-01 a HU-05), que trae el Usuario
    abstracto del modelo con Cliente y Administrador; entonces se reemplaza entero.
    """

    def __init__(self, acciones: set[str]):
        self.__acciones = acciones

    def puede(self, accion: str) -> bool:
        return accion in self.__acciones


if __name__ == "__main__":
    autoverificar()
