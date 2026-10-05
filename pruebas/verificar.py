"""Verificación de Viajes Aventura: todas las pruebas, paso a paso y ordenadas por la rúbrica.

El producto es viajes.py (dominio y persistencia) y main.py (interfaz). Este archivo no forma parte
de él: solo lo observa. Si se borrara, el programa seguiría igual de seguro, porque cada control
(permisos, validaciones, cifrado, transacciones) vive en el producto. Aquí está la evidencia de que
esos controles funcionan, y de que una prueba se daría cuenta si alguien los rompiera.

Cada sección corre sobre una base y una clave temporales: nunca toca viajes.db ni la clave real.

    python pruebas/verificar.py              interfaz: elige qué sección correr
    python pruebas/verificar.py --todo       todas, sin preguntar (lo usa el workflow)
    python pruebas/verificar.py --rapido     todas menos las mutaciones (tardan unos minutos)
    python pruebas/verificar.py --solo menu  una sección: reglas, implementacion, credenciales,
                                             datos, seguridad, menu, uml o mutaciones

El índice de qué afirmación se comprueba dónde está en pruebas/README.md.
"""

import argparse
import ast
import builtins
import getpass
import io
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from contextlib import contextmanager, redirect_stdout
from datetime import date, datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from argon2 import PasswordHasher  # noqa: E402
from cryptography.fernet import Fernet, InvalidToken  # noqa: E402

import viajes as v  # noqa: E402
from viajes import (COSTO_MAXIMO, CUPO_MAXIMO, DESTINOS_MAXIMO, MARGEN_MAXIMO,  # noqa: E402
                    PRECIO_MAXIMO, Administrador, Cliente, Destino, Paquete, ReglaNegocioError,
                    Reserva, Usuario, autorizar, conectar, crear_tablas, descifrar, hay_usuarios,
                    validar_rut)

RUTA_CLAVE_REAL = v.RUTA_CLAVE            # la de este equipo; ninguna prueba la usa


# =====================================================================
# 0. CÓMO SE MUESTRA Y SE AÍSLA CADA PRUEBA
# =====================================================================

PASOS: dict[str, int] = {}                # indicador de la rúbrica -> afirmaciones comprobadas


def ok(indicador: str, afirmacion: str) -> None:
    """Se llama recién después de comprobar la afirmación: si algo falla, nunca se imprime."""
    PASOS[indicador] = PASOS.get(indicador, 0) + 1
    print(f"  {sum(PASOS.values()):>3}. OK  {indicador:<8} {afirmacion}")


def rechaza(error: type[Exception], accion, *args) -> Exception:
    try:
        accion(*args)
    except error as e:
        return e
    raise AssertionError(f"{getattr(accion, '__name__', accion)} no rechazó {args!r}")


def futuro(dias: int) -> date:
    return date.today() + timedelta(days=dias)


@contextmanager
def entorno_temporal(nombre: str):
    """Base y clave en una carpeta temporal; al salir, todo vuelve a ser como antes."""
    base_real, clave_real = v.RUTA_ACTIVA, v.RUTA_CLAVE
    variable_real = os.environ.pop(v.VARIABLE_CLAVE, None)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as carpeta:
        v.RUTA_CLAVE = Path(carpeta) / "clave.env"
        v.cifrador.cache_clear()
        v.usar_base(os.path.join(carpeta, f"{nombre}.db"))
        try:
            crear_tablas()
            yield Path(carpeta)
        finally:
            v.usar_base(base_real)
            v.RUTA_CLAVE = clave_real
            v.cifrador.cache_clear()
            if variable_real is not None:
                os.environ[v.VARIABLE_CLAVE] = variable_real


def primer_administrador() -> Administrador:
    return Administrador.crear_primero("admin@viajes.cl", "cumbre-nevada-9x")


# =====================================================================
# 1. REGLAS DEL NEGOCIO R1 A R17 (antes, la autoverificación de viajes.py)
# =====================================================================

def _verificar_clave_y_permisos() -> None:
    # S-12: la clave se crea en el primer uso, fuera de la base, con un nombre de variable fijo,
    # aunque ya exista el primer administrador (que no tiene datos cifrados).
    with conectar() as con:
        con.execute("INSERT INTO usuario (correo, hash_clave, rol) VALUES ('primero@x.cl',"
                    " '$argon2id$prueba', 'ADMINISTRADOR')")
    v.cifrador()
    assert v.RUTA_CLAVE.read_text(encoding="utf-8").startswith(f"{v.VARIABLE_CLAVE}=")
    with conectar() as con:
        con.execute("DELETE FROM usuario")
    # RNF-SEG-04: la base y la clave quedan solo para su dueño. Windows no tiene estos permisos.
    if os.name == "posix":
        for archivo in (v.RUTA_ACTIVA, v.RUTA_CLAVE):
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


CAROLINA = "carolina@correo.cl"            # correos de prueba de la autoverificación
PEDRO = "pedro@correo.cl"
ZONA_PRUEBA = "Norte Chico"
# Los RUT y teléfonos de las pruebas son ficticios: cumplen el dígito verificador para ejercitar la
# validación, pero no corresponden a ninguna persona del caso.


def _verificar_cuentas() -> None:
    # S-04: la primera cuenta es de administrador y solo puede crearse una vez.
    assert not hay_usuarios()
    admin = Administrador.crear_primero("ana@viajes.cl", "clave-larga-de-ana")
    _rechaza(PermissionError, Administrador.crear_primero, "otro@viajes.cl", "clave-larga-ajena")
    socio = admin.crear_administrador("matias@viajes.cl", "brisa-del-pacifico-7")
    assert socio.puede("catalogo") and not socio.puede("reservar")
    # Hallazgo 5: la cuenta creada por otro no trae sesión; la tendrá al iniciarla con su clave.
    assert admin.tiene_sesion() and not socio.tiene_sesion()
    _rechaza(PermissionError, Destino("Del socio", "Z", "d", 1, 1).guardar, socio)
    assert Usuario.autenticar("matias@viajes.cl", "brisa-del-pacifico-7").tiene_sesion()

    # RF-RES-01 a RF-RES-03 y RF-SEG-12: el registro público crea clientes y valida cada dato.
    carolina = Cliente.registrar("Carolina Díaz", "12.345.678-5", CAROLINA,
                                 "+56 9 1234 5678", "luna-sobre-el-salar")
    assert isinstance(carolina, Cliente) and carolina.puede("reservar")
    assert not carolina.puede("catalogo")
    _rechaza(PermissionError, autorizar, carolina, "cuentas")
    _rechaza(ReglaNegocioError, Cliente.registrar, "Otra", "11.111.111-1", "Carolina@Correo.cl",
             "912345678", "brisa-de-la-tarde", regla="R9")
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
    guardada, v.RUTA_CLAVE = v.RUTA_CLAVE, v.RUTA_CLAVE.with_name("perdida.env")
    v.cifrador.cache_clear()
    _rechaza(RuntimeError, v.cifrador)
    v.RUTA_CLAVE = guardada
    v.cifrador.cache_clear()

    # RF-SEG-10 y C4: enmascarado, y fuera de la representación del objeto.
    assert carolina.rut_enmascarado() == "12.***.***-5"
    assert carolina.telefono_enmascarado() == "+56 9 ******* 8"
    assert "12345678" not in repr(carolina) and "5678" not in repr(carolina)

    # RF-SEG-01 y RF-SEG-02: inicio de sesión; los tres fallos devuelven lo mismo.
    entrada = Usuario.autenticar("Carolina@correo.cl", "luna-sobre-el-salar")
    assert isinstance(entrada, Cliente) and entrada.rut_enmascarado() == "12.***.***-5"
    assert isinstance(Usuario.autenticar("ana@viajes.cl", "clave-larga-de-ana"), Administrador)
    assert Usuario.autenticar("nadie@correo.cl", "luna-sobre-el-salar") is None
    assert Usuario.autenticar(CAROLINA, "otra-clave") is None
    assert Usuario.autenticar("no es correo", "x") is None

    # RF-SEG-03: cinco fallos seguidos bloquean, aun con la contraseña correcta, y el bloqueo
    # está en la base (sobrevive a cerrar el programa). Al vencer, se puede entrar.
    for _ in range(4):
        Usuario.autenticar(CAROLINA, "otra-clave")   # 1 ya contó arriba: 5 en total
    assert Usuario.autenticar(CAROLINA, "luna-sobre-el-salar") is None
    with conectar() as con:
        con.execute("UPDATE usuario SET bloqueado_hasta = ? WHERE correo = ?",
                    ((datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(), CAROLINA))
    assert Usuario.autenticar(CAROLINA, "luna-sobre-el-salar") is not None

    # RF-SEG-11 y RF-RES-12.
    _rechaza(PermissionError, carolina.cambiar_clave, "clave-equivocada", "nueva-clave-larga")
    carolina.cambiar_clave("luna-sobre-el-salar", "nueva-clave-larga")
    assert Usuario.autenticar(CAROLINA, "nueva-clave-larga") is not None
    carolina.actualizar_contacto("Carolina Díaz R.", "987654321")
    releida = Usuario.autenticar(CAROLINA, "nueva-clave-larga")
    assert releida.obtener_nombre() == "Carolina Díaz R."
    assert releida.telefono_enmascarado() == "+56 9 ******* 1"

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
    elqui = Destino("Valle del Elqui", ZONA_PRUEBA, "Observación astronómica", 3, 120_000)
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
    elqui.editar("Valle del Elqui", ZONA_PRUEBA, "Observación astronómica y pisco", 3, admin)
    elqui.cambiar_costo(130_000, admin)
    assert Destino.buscar(id_elqui).obtener_costo_base() == 130_000

    # RF-SEG-05: un cliente no toca el catálogo, aunque llame directo al dominio; y un
    # administrador armado a mano, sin iniciar sesión, tampoco (hallazgo 5).
    _rechaza(PermissionError, elqui.cambiar_costo, 1, cliente)
    _rechaza(PermissionError, Destino("Nuevo", "Z", "d", 1, 1).guardar, cliente)
    _rechaza(PermissionError, Destino("Nuevo", "Z", "d", 1, 1).guardar,
             Administrador("intruso@viajes.cl", "clave-larga-ajena"))

    # Hallazgo 4: una edición que falla no deja el objeto a medias.
    antes = str(elqui)
    _rechaza(ValueError, elqui.editar, "Otro nombre", "", "d", 2, admin)
    assert str(elqui) == antes and str(Destino.buscar(id_elqui)) == antes

    # Respaldo (RNF-FIA-03): copia consistente, solo para su dueño, y solo para el administrador.
    copia = Path(admin.respaldar_base())
    otra = sqlite3.connect(copia)
    assert otra.execute("SELECT COUNT(*) FROM destino").fetchone()[0] == len(Destino.listar())
    otra.close()
    if os.name == "posix":
        assert os.stat(copia).st_mode & 0o777 == 0o600
    _rechaza(PermissionError, autorizar, cliente, "respaldo")

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
    # Hallazgo 20: escribir sobre un destino que ya no existe no se informa como guardado.
    _rechaza(ValueError, elqui.cambiar_costo, 1, admin)
    _rechaza(ValueError, elqui.reactivar, admin)
    # El paquete de apoyo se insertó por SQL con un solo destino, cosa que R3 prohíbe y que la
    # base no puede impedir (la regla abarca varias filas): se borra para no dejar un dato inválido.
    with conectar() as con:
        con.execute("DELETE FROM paquete WHERE id = 1")



def _verificar_paquetes_y_reservas() -> None:
    admin, carolina = _verificar_cuentas.cuentas
    pedro = Cliente.registrar("Pedro Soto", "11.111.111-1", PEDRO, "922223333",
                              "viento-en-la-pampa-1")
    salida, regreso = date.today() + timedelta(days=30), date.today() + timedelta(days=35)
    surire = Destino("Salar de Surire 2", "Altiplano", "Flamencos", 4, 310_000)
    elqui = Destino("Valle del Elqui 2", ZONA_PRUEBA, "Estrellas", 3, 120_000)
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
    assert not carolina.tiene_reserva_vigente(altiplano)
    reserva = Reserva.reservar(altiplano, 2, carolina)
    assert reserva.obtener_total() == 1_032_000
    assert carolina.tiene_reserva_vigente(altiplano) and not pedro.tiene_reserva_vigente(altiplano)
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

    con = sqlite3.connect(v.RUTA_ACTIVA, timeout=5, isolation_level=None)
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

    # Una reserva leída del historial (el camino del menú) conoce a su verdadero titular.
    vigente = next(r for r in pedro.historial() if r.obtener_total() == 6 * 516_000)
    _rechaza(PermissionError, vigente.anular, carolina)
    vigente.anular(pedro)

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



def _verificar_auditoria() -> None:
    admin, _ = _verificar_cuentas.cuentas
    with conectar() as con:
        filas = con.execute("SELECT usuario_id, accion, detalle FROM auditoria").fetchall()
    acciones = {f["accion"] for f in filas}
    esperadas = {"cuenta.crear", "sesion.inicio", "sesion.fallida", "sesion.bloqueo",
                 "sesion.rechazada_bloqueada", "sesion.correo_inexistente", "cuenta.cambiar_clave",
                 "cliente.contacto", "destino.crear", "destino.editar", "destino.costo",
                 "destino.eliminar",
                 "destino.no_disponible", "destino.reactivar", "paquete.crear", "paquete.editar",
                 "paquete.destinos", "paquete.publicar", "paquete.cupo", "paquete.eliminar",
                 "reserva.crear", "reserva.anular"}
    assert esperadas <= acciones, esperadas - acciones                     # H-02
    detalles = " ".join(f["detalle"] for f in filas)
    for dato in ("12345678", "@", "clave", "5678"):       # las contraseñas de prueba dicen “clave”
        assert dato not in detalles, dato                                  # sin datos personales
    # Lo eliminado queda con su nombre: el id solo ya no dice qué se borró.
    assert "destino" in detalles and "“Valle del Elqui”" in detalles
    # Una operación rechazada se deshace entera, con su registro: el registro no miente.
    antes = len(filas)
    _rechaza(ReglaNegocioError, Destino("Destino 0", "Z", "d", 1, 1).guardar, admin, regla="R1")
    with conectar() as con:
        assert con.execute("SELECT COUNT(*) FROM auditoria").fetchone()[0] == antes

    # H-10: una sesión vieja no cambia una contraseña que otra sesión ya cambió.
    sesion_a = Usuario.autenticar(CAROLINA, "nueva-clave-larga")
    sesion_b = Usuario.autenticar(CAROLINA, "nueva-clave-larga")
    _rechaza(ReglaNegocioError, sesion_a.cambiar_clave, "nueva-clave-larga", "nueva-clave-larga",
             regla="RF-SEG-11")
    sesion_a.cambiar_clave("nueva-clave-larga", "otra-clave-larga-1")
    _rechaza(PermissionError, sesion_b.cambiar_clave, "nueva-clave-larga", "tercera-clave-larga")
    assert Usuario.autenticar(CAROLINA, "otra-clave-larga-1") is not None

    # H-16 y H-14: contraseñas comunes o repetitivas, y el RUT 0.
    for clave in ("Contraseña123", "aaaaaaaaaaaa", "121212121212"):
        _rechaza(ReglaNegocioError, Cliente, "N", "12.345.678-5", "n@b.cl", "912345678", clave,
                 regla="RF-SEG-04")
    _rechaza(ValueError, validar_rut, "0.000.000-0")

    # H-09: el total más alto posible se guarda y se vuelve a leer (antes rompía el historial).
    caros = [Destino(f"Caro {i}", "Z", "d", 1, COSTO_MAXIMO) for i in range(DESTINOS_MAXIMO)]
    for d in caros:
        d.guardar(admin)
    lujo = Paquete("Lujo", date.today() + timedelta(days=9), date.today() + timedelta(days=10),
                   CUPO_MAXIMO, caros, MARGEN_MAXIMO)
    lujo.guardar(admin)
    lujo.publicar(admin)
    pedro = Usuario.autenticar(PEDRO, "viento-en-la-pampa-1")
    assert Reserva.reservar(lujo, CUPO_MAXIMO, pedro).obtener_total() == PRECIO_MAXIMO * CUPO_MAXIMO
    assert max(r.obtener_total() for r in pedro.historial()) == PRECIO_MAXIMO * CUPO_MAXIMO

    # H-04 y H-05: un RUT alterado en la base no impide entrar ni listar; solo falla al mostrarlo.
    with conectar() as con:
        con.execute("UPDATE usuario SET rut_cifrado = 'alterado' WHERE correo = ?", (PEDRO,))
    pedro = Usuario.autenticar(PEDRO, "viento-en-la-pampa-1")
    assert pedro is not None and len(Reserva.listar_por_paquete(lujo, admin)) == 1
    _rechaza(ValueError, pedro.rut_enmascarado)


def seccion_reglas() -> None:
    with entorno_temporal("reglas"):
        for indicador, descripcion, prueba in (
            ("I.19", "la clave de cifrado se crea en el primer uso, fuera de la base, en 0600 (S-12)",
             _verificar_clave_y_permisos),
            ("G.18", "cuentas: primer administrador, registro, Argon2id, cifrado, enmascarado, inicio de"
                     " sesión, bloqueo y permisos (R9, R10, RF-SEG-01 a 13)", _verificar_cuentas),
            ("G.15", "destinos: nombre único sin tildes, costo positivo, edición sin estados a medias,"
                     " eliminar o dejar no disponible, respaldo (R1, R2, R8)", _verificar_destinos),
            ("G.14", "paquetes y reservas: 2 a 5 destinos, precio fijo al publicar, cupo, fecha, total"
                     " y dos reservas simultáneas (R3 a R7, R11 a R16, RNF-FIA-02)",
             _verificar_paquetes_y_reservas),
            ("I.20", "registro de auditoría, contraseñas comunes, RUT 0, total máximo y RUT alterado"
                     " (H-02, H-04, H-05, H-09, H-10, H-14, H-16)", _verificar_auditoria),
        ):
            prueba()
            ok(indicador, descripcion)


# =====================================================================
# 2 A 4. IMPLEMENTACIÓN, CREDENCIALES Y DATOS PERSONALES (G.13 A I.19): una afirmación por
# indicador de la rúbrica que se puede verificar en el código
# =====================================================================

# --- 4.1.4.G.13: el código respeta el UML y los cuatro principios -------------

def g13() -> None:
    rechaza(TypeError, v.Usuario, "x@y.cl", "clave-larga-xyz")
    ok("G.13", "abstracción: Usuario es abstracta y no se puede instanciar")
    assert issubclass(v.Cliente, v.Usuario) and issubclass(v.Administrador, v.Usuario)
    ok("G.13", "herencia: Cliente y Administrador heredan la autenticación de Usuario")
    cliente = v.Cliente("Ana", "12.345.678-5", "ana@c.cl", "912345678", "clave-larga-ana")
    admin = v.Administrador("adm@c.cl", "clave-larga-adm")
    assert [s.puede("catalogo") for s in (cliente, admin)] == [False, True]
    assert [s.puede("reservar") for s in (cliente, admin)] == [True, False]
    ok("G.13", "polimorfismo: puede() responde distinto en cada rol, con la misma llamada")
    for nombre in ("rut", "telefono", "nombre", "correo", "hash_clave", "id"):
        assert not hasattr(cliente, nombre), nombre
    ok("G.13", "encapsulamiento: todo atributo es privado; el RUT solo sale con rut_enmascarado()")


# --- 4.1.4.G.14: persistencia robusta, eficiente y completa --------------------

def g14(admin: v.Administrador) -> None:
    with v.conectar() as con:
        tablas = {f[0] for f in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        indices = {f[0] for f in con.execute("SELECT name FROM sqlite_master WHERE type = 'index'"
                                             " AND name LIKE 'ix_%'")}
        fk = con.execute("PRAGMA foreign_keys").fetchone()[0]
    assert {"usuario", "destino", "paquete", "paquete_destino", "reserva"} <= tablas and fk == 1
    ok("G.14", "5 tablas en sqlite3 con claves foráneas activadas")
    assert len(indices) == 3
    ok("G.14", "índices en las claves foráneas que consultan el historial y el cupo")
    destino = v.Destino("Persistente", "Zona", "d", 2, 50_000)
    id_destino = destino.guardar(admin)
    otra = sqlite3.connect(v.RUTA_ACTIVA)              # otra conexión: lo guardado está en disco
    assert otra.execute("SELECT costo_base FROM destino WHERE id = ?", (id_destino,)).fetchone() == (50_000,)
    otra.close()
    ok("G.14", "lo guardado se lee desde otra conexión: queda en disco, no en memoria")
    with v.conectar() as con:
        casos = {
            "R2 costo 0": "INSERT INTO destino (nombre, nombre_normalizado, zona, descripcion,"
                          " duracion_dias, costo_base, fecha_costo) VALUES ('a', 'a', 'z', 'd', 1, 0, 'x')",
            "R1 nombre repetido": "INSERT INTO destino (nombre, nombre_normalizado, zona, descripcion,"
                                  " duracion_dias, costo_base, fecha_costo) VALUES"
                                  " ('PERSISTENTE', 'persistente', 'z', 'd', 1, 1, 'x')",
            "R5 regreso antes": "INSERT INTO paquete (nombre, fecha_salida, fecha_regreso, cupo_maximo,"
                                " margen) VALUES ('p', '2030-01-05', '2030-01-01', 5, 20)",
            "R6 margen negativo": "INSERT INTO paquete (nombre, fecha_salida, fecha_regreso, cupo_maximo,"
                                  " margen) VALUES ('p', '2030-01-01', '2030-01-05', 5, -1)",
            "R10 clave en claro": "INSERT INTO usuario (correo, hash_clave, rol) VALUES"
                                  " ('z@z.cl', 'clave', 'ADMINISTRADOR')",
            "R16 cero personas": "INSERT INTO reserva (cliente_id, paquete_id, fecha_emision, personas,"
                                 " total) VALUES (1, 1, '2030-01-01', 0, 1)",
        }
        for sql in casos.values():
            rechaza(sqlite3.IntegrityError, con.execute, sql)
    ok("G.14", f"la base rechaza por sí misma {len(casos)} datos inválidos ({', '.join(casos)})")


# --- 4.1.4.G.15: CRUD completo y operativo -------------------------------------

def g15(admin: v.Administrador) -> None:
    a = v.Destino("Valle del Elqui", "Norte Chico", "Estrellas", 3, 120_000)
    b = v.Destino("Salar de Surire", "Altiplano", "Flamencos", 4, 310_000)
    c = v.Destino("Sin paquete", "Zona", "d", 1, 1_000)
    for d in (a, b, c):
        d.guardar(admin)
    a.editar("Valle del Elqui", "Norte Chico", "Observación astronómica", 3, admin)
    a.cambiar_costo(130_000, admin)
    assert v.Destino.buscar(a.obtener_id()).obtener_costo_base() == 130_000
    assert c.eliminar(admin) is True and v.Destino.buscar(c.obtener_id()) is None
    ok("G.15", "Destino: crear, leer (listar y buscar), actualizar (editar y costo) y eliminar")

    paquete = v.Paquete("Altiplano", futuro(30), futuro(35), 12, [a, b])
    paquete.guardar(admin)
    paquete.editar("Altiplano y estrellas", futuro(30), futuro(35), 20, admin)
    paquete.publicar(admin)
    paquete.cambiar_cupo(10, admin)
    assert v.Paquete.buscar(paquete.obtener_id()).cupo_disponible() == 10
    borrador = v.Paquete("Borrador", futuro(40), futuro(42), 5, [a, b])
    borrador.guardar(admin)
    borrador.eliminar(admin)
    assert v.Paquete.buscar(borrador.obtener_id()) is None
    ok("G.15", "Paquete: crear, leer (oferta, todos y buscar), actualizar (editar, publicar, cupo) y eliminar")

    cliente = v.Cliente.registrar("Carolina Díaz", "12.345.678-5", "carolina@c.cl", "912345678",
                                  "luna-sobre-el-salar")
    cliente.actualizar_contacto("Carolina Díaz R.", "987654321")
    assert v.Usuario.autenticar("carolina@c.cl", "luna-sobre-el-salar").obtener_nombre() == "Carolina Díaz R."
    ok("G.15", "Cliente: crear (registro), leer (inicio de sesión) y actualizar su contacto")

    reserva = v.Reserva.reservar(paquete, 2, cliente)
    assert len(cliente.historial()) == 1 and len(v.Reserva.listar_por_paquete(paquete, admin)) == 1
    cliente.historial()[0].anular(cliente)
    assert v.Paquete.buscar(paquete.obtener_id()).cupo_disponible() == 10 and reserva.obtener_total() > 0
    ok("G.15", "Reserva: crear, leer (historial y por paquete) y anular; no se borra, es historial (S-01)")
    rechaza(v.ReglaNegocioError, paquete.eliminar, admin)
    ok("G.15", "un paquete con reservas no se elimina (RF-PAQ-09), ni siquiera si están anuladas")


# --- 4.1.5.G.17: autenticación con una librería oficial especializada ----------

def g17() -> None:
    with v.conectar() as con:
        hashes = [f[0] for f in con.execute("SELECT hash_clave FROM usuario")]
    assert hashes and all(h.startswith("$argon2id$v=19$m=65536,t=4,p=4$") for h in hashes)
    ok("G.17", f"argon2-cffi {version('argon2-cffi')} (PyPI): toda contraseña es un Argon2id con sal propia")
    assert len({h.split("$")[4] for h in hashes}) == len(hashes)
    ok("G.17", "ninguna sal se repite entre cuentas")
    clave = "una-clave-de-prueba"
    h = v.HASHER.hash(clave)
    inicio = time.perf_counter()
    v.HASHER.verify(h, clave)
    duracion = time.perf_counter() - inicio
    # El piso de 0,1 s depende del equipo (un servidor de GitHub tardó 48 ms): lo que se garantiza
    # es el costo fijado en el hash, 64 MiB de memoria y 4 pasadas. El techo de 1 s sí se exige.
    assert "m=65536,t=4" in h and duracion <= 1.0, duracion
    ok("G.17", f"verificar una contraseña tarda {duracion * 1000:.0f} ms en este equipo, con 64 MiB y 4"
               " pasadas (RNF-REN-02: 0,1 a 1 s en el equipo de la oficina)")


# --- 4.1.5.G.18: validación rigurosa de credenciales en todos los escenarios ---

PEDRO_C, NADIE = "pedro@c.cl", "nadie@c.cl"


def g18() -> None:
    cuenta = v.Cliente.registrar("Pedro", "11.111.111-1", PEDRO_C, "922223333", "viento-en-la-pampa-1")
    assert isinstance(v.Usuario.autenticar("PEDRO@c.cl", "viento-en-la-pampa-1"), v.Cliente)
    ok("G.18", "credenciales correctas: entra, sin importar mayúsculas en el correo")
    assert v.Usuario.autenticar(PEDRO_C, "clave-equivocada") is None
    assert v.Usuario.autenticar(NADIE, "viento-en-la-pampa-1") is None
    assert v.Usuario.autenticar("no es correo", "") is None and v.Usuario.autenticar("", "") is None
    ok("G.18", "contraseña errónea, correo inexistente, formato inválido o vacío: la misma respuesta")

    def demora(correo: str) -> float:
        inicio = time.perf_counter()
        for _ in range(3):
            v.Usuario.autenticar(correo, "otra-clave-x")
        return time.perf_counter() - inicio

    v.Usuario.autenticar(NADIE, "x")                 # el hash señuelo se calcula una vez
    existe, no_existe = demora(PEDRO_C), demora(NADIE)
    assert 0.5 < existe / no_existe < 2, (existe, no_existe)
    ok("G.18", f"el correo inexistente tarda lo mismo que uno existente ({no_existe / 3 * 1000:.0f} ms"
               f" contra {existe / 3 * 1000:.0f} ms): no revela qué correos hay")
    with v.conectar() as con:
        con.execute("UPDATE usuario SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE correo = ?", (PEDRO_C,))
    for _ in range(5):
        v.Usuario.autenticar(PEDRO_C, "clave-equivocada")
    assert v.Usuario.autenticar(PEDRO_C, "viento-en-la-pampa-1") is None
    otra = sqlite3.connect(v.RUTA_ACTIVA)
    hasta = otra.execute("SELECT bloqueado_hasta FROM usuario WHERE correo = ?", (PEDRO_C,)).fetchone()[0]
    otra.close()
    assert datetime.fromisoformat(hasta) > datetime.now(timezone.utc) + timedelta(minutes=4)
    ok("G.18", "5 fallos seguidos bloquean 5 minutos, aun con la contraseña correcta, y el bloqueo"
               " queda en la base")
    for clave, motivo in (("a" * 11, "11 caracteres"), ("Pedro2@c.cl", "igual al correo")):
        rechaza(v.ReglaNegocioError, v.Cliente, "P", "11.111.111-1", "pedro2@c.cl", "922223333", clave)
    ok("G.18", "política de contraseña: se rechaza con 11 caracteres o si es igual al correo")
    # Teléfono sin secuencias propias (982736150): así cada caso cae en su regla y no en otra.
    for correo, nombre, clave, motivo in (
            ("ana@c.cl", "Ana", "viaje-al-sur-1234", "secuencias"),
            ("ana@c.cl", "Ana", "viaje-al-sur-DCBA", "secuencias"),
            ("juan.perez@c.cl", "Ana", "mi-ruta-perez-sur", "partes de su correo"),
            ("ana@c.cl", "José Díaz", "ruta-de-diaz-sur", "su nombre"),       # sin tilde, igual
            ("ana@c.cl", "Ana", "llamar-al-7361-hoy", "su teléfono")):
        e = rechaza(v.ReglaNegocioError, v.Cliente, nombre, "11.111.111-1", correo, "982736150", clave)
        assert e.obtener_regla() == "RF-SEG-04" and motivo in str(e), (clave, str(e))
    v.Cliente("José Díaz", "11.111.111-1", "juan.perez@c.cl", "982736150", "luna-sobre-el-salar")
    ok("G.18", "política de contraseña: sin secuencias (1234, dcba) ni partes del correo, del nombre"
               " o del teléfono; sin exigir mayúsculas ni símbolos (RF-SEG-04)")
    rechaza(PermissionError, cuenta.cambiar_clave, "clave-equivocada", "otra-clave-larga")
    ok("G.18", "cambiar la contraseña exige la actual")
    debil = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash("viento-en-la-pampa-1")
    with v.conectar() as con:
        con.execute("UPDATE usuario SET hash_clave = ?, bloqueado_hasta = NULL WHERE correo = ?",
                    (debil, PEDRO_C))
    assert v.Usuario.autenticar(PEDRO_C, "viento-en-la-pampa-1") is not None
    with v.conectar() as con:
        nuevo = con.execute("SELECT hash_clave FROM usuario WHERE correo = ?", (PEDRO_C,)).fetchone()[0]
    assert "m=65536,t=4,p=4" in nuevo
    ok("G.18", "un hash con parámetros viejos se rehace al entrar (check_needs_rehash)")
    sesion = v.Usuario.autenticar(PEDRO_C, "viento-en-la-pampa-1")
    e = rechaza(v.ReglaNegocioError, sesion.cambiar_clave, "viento-en-la-pampa-1", "ruta-sur-922223333")
    assert e.obtener_regla() == "RF-SEG-04"
    ok("G.18", "la misma política rige al cambiar la contraseña: la nueva no puede traer el teléfono")


def g18_endurecido() -> None:
    """Los riesgos que la auditoría había dejado como aceptados, cerrados y comprobados."""
    admin = v.Usuario.autenticar("admin@viajes.cl", "cumbre-nevada-9x")
    admin.crear_administrador("socio@viajes.cl", "rio-baker-turquesa")
    rita = v.Cliente.registrar("Rita", "11.111.111-1", "rita@c.cl", "933334444", "glaciar-grey-azul")
    for _ in range(5):
        rechaza(PermissionError, rita.cambiar_clave, "clave-equivocada", "otra-clave-larga-1")
    assert v.Usuario.autenticar("rita@c.cl", "glaciar-grey-azul") is None
    ok("G.18", "al cambiar la contraseña, la actual equivocada cuenta como intento: 5 errores bloquean la"
               " cuenta (H-10)")

    def bloquear(correo: str) -> int:
        """Cinco fallos; devuelve los minutos del bloqueo y lo da por vencido para seguir probando."""
        for _ in range(5):
            v.Usuario.autenticar(correo, "clave-equivocada")
        with v.conectar() as con:
            hasta = con.execute("SELECT bloqueado_hasta FROM usuario WHERE correo = ?", (correo,)).fetchone()[0]
            con.execute("UPDATE usuario SET bloqueado_hasta = NULL WHERE correo = ?", (correo,))
        return round((datetime.fromisoformat(hasta) - datetime.now(timezone.utc)) / timedelta(minutes=1))

    assert [bloquear("socio@viajes.cl") for _ in range(4)] == [5, 15, 60, 60]
    assert v.Usuario.autenticar("socio@viajes.cl", "rio-baker-turquesa") is not None
    assert bloquear("socio@viajes.cl") == 5
    ok("G.18", "bloqueo progresivo: 5, 15 y 60 minutos mientras siga fallando; un acierto vuelve a 5 (H-17)")

    una, otra = (v.Usuario.autenticar("socio@viajes.cl", "rio-baker-turquesa") for _ in range(2))
    una.cambiar_clave("rio-baker-turquesa", "rio-baker-esmeralda")
    assert una.tiene_sesion() and not otra.tiene_sesion()
    rechaza(PermissionError, v.Destino("Sesión vieja", "Zona", "d", 1, 1000).guardar, otra)
    ok("G.18", "cambiar la contraseña invalida las otras sesiones abiertas de esa cuenta")

    abierta = v.Usuario.autenticar("socio@viajes.cl", "rio-baker-esmeralda")
    admin.desactivar_cuenta("socio@viajes.cl")
    assert v.Usuario.autenticar("socio@viajes.cl", "rio-baker-esmeralda") is None
    assert not abierta.tiene_sesion()
    rechaza(PermissionError, v.Destino("Cuenta cerrada", "Zona", "d", 1, 1000).guardar, abierta)
    rechaza(PermissionError, abierta.cambiar_clave, "rio-baker-esmeralda", "otra-clave-larga-2")
    rechaza(v.ReglaNegocioError, admin.desactivar_cuenta, "admin@viajes.cl")
    rechaza(PermissionError, v.Administrador.desactivar_cuenta, rita, "admin@viajes.cl")
    ok("G.18", "una cuenta desactivada no entra (mismo mensaje), pierde sus sesiones abiertas y no cambia"
               " su contraseña; nadie desactiva la propia, y un cliente no desactiva a nadie (RF-SEG-14)")

    for _ in range(v.Cliente.REPETIDOS_MAXIMO):
        rechaza(v.ReglaNegocioError, v.Cliente.registrar, "Otra", "11.111.111-1", "rita@c.cl",
                "933334444", "brisa-de-la-tarde")
    pausa = rechaza(v.ReglaNegocioError, v.Cliente.registrar, "Nueva", "11.111.111-1", "nueva@c.cl",
                    "933334444", "brisa-de-la-tarde")
    assert pausa.obtener_regla() == "RF-SEG-17"
    ok("G.18", f"tras {v.Cliente.REPETIDOS_MAXIMO} correos ya registrados en 10 minutos, el registro"
               " público se pausa: no sirve para averiguar qué correos existen (RF-SEG-17, H-06)")


# --- 4.1.5.I.19: confidencialidad e integridad de los datos personales --------

def i19(admin: v.Administrador, paquete: v.Paquete, cliente: v.Cliente) -> None:
    with v.conectar() as con:
        filas = con.execute("SELECT rut_cifrado, telefono_cifrado FROM usuario WHERE rol = 'CLIENTE'").fetchall()
    volcado = "\n".join(con_iterdump())
    assert filas and "12345678" not in volcado and "987654321" not in volcado and "9876" not in volcado
    ok("I.19", "confidencialidad: en el archivo de la base no aparece ningún RUT ni teléfono legible")
    token = filas[0][0]
    alterado = token[:-6] + ("A" if token[-6] != "A" else "B") + token[-5:]
    rechaza(ValueError, v.descifrar, alterado)
    ok("I.19", "integridad: un byte alterado del dato cifrado da error, nunca un RUT falso (Fernet)")
    if os.name == "posix":
        assert os.stat(v.RUTA_ACTIVA).st_mode & 0o777 == 0o600
        assert os.stat(v.RUTA_CLAVE).st_mode & 0o777 == 0o600
        ok("I.19", "la base y la clave quedan con permisos 0600, solo para su dueño")
    assert ".env" in (RAIZ / ".gitignore").read_text() and "*.db" in (RAIZ / ".gitignore").read_text()
    assert RAIZ not in RUTA_CLAVE_REAL.parents
    ok("I.19", "la clave vive fuera del proyecto (carpeta del usuario) y la base no viaja al repositorio")
    assert cliente.rut_enmascarado() == "12.***.***-5" and cliente.telefono_enmascarado() == "+56 9 ******* 1"
    assert all("12345678" not in str(r) for r in v.Reserva.listar_por_paquete(paquete, admin))
    assert "12345678" not in repr(cliente)
    ok("I.19", "RUT y teléfono solo enmascarados: en pantalla, en listados y en la representación del objeto")
    # El correo: primer y último carácter, siempre los mismos asteriscos (no delatan el largo).
    assert v.enmascarar_correo("juan9@gmail.com") == "j*******9@g****.com"
    assert v.enmascarar_correo("carolina@c.cl") == "c*******a@c****.cl"
    assert v.enmascarar_correo("jo@mail.uc.cl") == "j*******@m****.cl"
    ok("I.19", "el correo también sale enmascarado en “ver mis datos” y en la cabecera del menú (RF-SEG-10)")
    e = rechaza(ValueError, v.Cliente, "P", "12.345.678-6", "x@c.cl", "912345678", "clave-larga-xx")
    assert "12.345.678" not in str(e) and "12345678" not in str(e)
    ok("I.19", "los mensajes de error nombran el campo, nunca el RUT ni el teléfono ingresados")


def i19_rotacion(admin: v.Administrador, cliente: v.Cliente) -> None:
    """RF-SEG-15: la clave se cambia sin perder ningún dato, y la vieja deja de servir."""
    def rut_guardado() -> str:
        with v.conectar() as con:
            return con.execute("SELECT rut_cifrado FROM usuario WHERE id = ?", (cliente.obtener_id(),)).fetchone()[0]

    antes, clave_vieja = rut_guardado(), v._leer_clave(v.RUTA_CLAVE)
    cantidad, anterior = v.rotar_clave_de_datos(admin)
    despues = rut_guardado()
    assert cantidad == 1 and despues != antes
    assert v.Usuario.autenticar("carolina@c.cl", "luna-sobre-el-salar").rut_enmascarado() == "12.***.***-5"
    rechaza(InvalidToken, Fernet(clave_vieja.encode()).decrypt, despues.encode())
    archivo = v.RUTA_CLAVE.with_name(anterior)
    assert archivo.exists() and (os.name != "posix" or archivo.stat().st_mode & 0o777 == 0o600)
    rechaza(PermissionError, v.rotar_clave_de_datos, cliente)
    os.environ[v.VARIABLE_CLAVE] = v._leer_clave(v.RUTA_CLAVE)
    try:
        rechaza(RuntimeError, v.rotar_clave_de_datos, admin)
    finally:
        os.environ.pop(v.VARIABLE_CLAVE, None)
    ok("I.19", "rotar la clave: todos los RUT y teléfonos quedan con la nueva, la vieja ya no los lee y se"
               " archiva en 0600 para los respaldos anteriores; solo un socio puede hacerlo (RF-SEG-15)")


def con_iterdump() -> list[str]:
    con = sqlite3.connect(v.RUTA_ACTIVA)
    try:
        return list(con.iterdump())
    finally:
        con.close()


# --- RNF-REN-01: diez veces el volumen de una temporada ------------------------

def rendimiento(admin: v.Administrador) -> None:
    clientes = [v.Cliente.registrar(f"Cliente {i}", "11.111.111-1", f"c{i}@vol.cl", "912345678",
                                    "clave-larga-vol") for i in range(20)]
    destinos = [v.Destino(f"Destino de volumen {i}", "Zona", "d", 2, 10_000 + i) for i in range(180)]
    for d in destinos:
        d.guardar(admin)
    paquetes = []
    for i in range(120):
        p = v.Paquete(f"Paquete {i}", futuro(10 + i), futuro(15 + i), 100, destinos[i:i + 3])
        p.guardar(admin)
        p.publicar(admin)
        paquetes.append(p)
    for i in range(2140):
        v.Reserva.reservar(paquetes[i % 120], 1, clientes[i % 20])
    inicio = time.perf_counter()
    oferta = v.Paquete.listar_disponibles()
    t_oferta = time.perf_counter() - inicio
    inicio = time.perf_counter()
    historial = clientes[0].historial()
    t_historial = time.perf_counter() - inicio
    assert len(oferta) >= 120 and len(historial) == 107 and t_oferta < 1 and t_historial < 1
    ok("RNF-REN", f"con 2.140 reservas, 180 destinos y 120 paquetes: oferta en {t_oferta:.2f} s e"
                  f" historial en {t_historial:.2f} s (menos de 1 s)")




def seccion_implementacion() -> None:
    with entorno_temporal("implementacion"):
        admin = primer_administrador()
        g13()
        g14(admin)
        g15(admin)
        rendimiento(admin)


def seccion_credenciales() -> None:
    with entorno_temporal("credenciales"):
        primer_administrador()
        v.Cliente.registrar("Sal Uno", "11.111.111-1", "sal1@c.cl", "911111111", "clave-larga-uno")
        v.Cliente.registrar("Sal Dos", "22.222.222-2", "sal2@c.cl", "922222222", "clave-larga-dos")
        g17()
        g18()
        g18_endurecido()


def escenario_cliente(admin: v.Administrador) -> tuple[v.Paquete, v.Cliente]:
    """Un paquete publicado y una clienta con RUT, teléfono actualizado y una reserva."""
    a = v.Destino("Valle del Elqui", "Norte Chico", "Estrellas", 3, 120_000)
    b = v.Destino("Salar de Surire", "Altiplano", "Flamencos", 4, 310_000)
    for d in (a, b):
        d.guardar(admin)
    paquete = v.Paquete("Altiplano", futuro(30), futuro(35), 12, [a, b])
    paquete.guardar(admin)
    paquete.publicar(admin)
    cliente = v.Cliente.registrar("Carolina Díaz", "12.345.678-5", "carolina@c.cl", "912345678",
                                  "luna-sobre-el-salar")
    cliente.actualizar_contacto("Carolina Díaz R.", "987654321")
    v.Reserva.reservar(paquete, 2, cliente)
    return paquete, cliente


def seccion_datos() -> None:
    with entorno_temporal("datos"):
        admin = primer_administrador()
        paquete, cliente = escenario_cliente(admin)
        i19(admin, paquete, cliente)
        i19_rotacion(admin, cliente)


# =====================================================================
# 5. SEGURIDAD: EVALUACIÓN Y MEJORAS (I.20)
# =====================================================================

def demostracion(admin: v.Administrador) -> None:
    """El modo demostración (RNF-USA-04) carga sus datos en una base temporal y deja intactas la
    base, la clave y la variable de entorno reales, aunque la variable esté definida."""
    import main as menu
    base, clave = v.RUTA_ACTIVA, v.RUTA_CLAVE
    antes = (len(v.Destino.listar()), len(v.Paquete.listar_todos(admin)))
    os.environ[v.VARIABLE_CLAVE] = "marca-de-la-variable-real"
    entrada, salida = builtins.input, io.StringIO()
    builtins.input = lambda _mensaje="": "0"              # sale de la demostración apenas entra
    try:
        with redirect_stdout(salida):
            volver = menu.modo_demostracion()
        restaurada = os.environ.get(v.VARIABLE_CLAVE) == "marca-de-la-variable-real"
    finally:
        builtins.input = entrada
        os.environ.pop(v.VARIABLE_CLAVE, None)
        v.cifrador.cache_clear()
    assert volver and "Datos de ejemplo cargados: 5 destinos" in salida.getvalue()
    assert v.RUTA_ACTIVA == base and v.RUTA_CLAVE == clave and restaurada
    assert (len(v.Destino.listar()), len(v.Paquete.listar_todos(admin))) == antes
    ok("I.20", "modo demostración: datos de ejemplo en una base temporal; la base, la clave y la"
       " variable reales quedan intactas")


def es_literal(nodo: ast.expr) -> bool:
    """Un texto fijo, una constante con nombre, o la elección entre dos de ellos."""
    if isinstance(nodo, ast.IfExp):
        return es_literal(nodo.body) and es_literal(nodo.orelse)
    return isinstance(nodo, (ast.Constant, ast.Name, ast.Attribute))


def sql_armado(nodo: ast.AST) -> bool:
    """Un execute() que recibe texto armado, o una constante SQL_..., ESQUEMA o sql que lo es."""
    if isinstance(nodo, ast.Call) and getattr(nodo.func, "attr", "") in ("execute", "executescript",
                                                                         "executemany"):
        return bool(nodo.args) and not es_literal(nodo.args[0])
    if isinstance(nodo, ast.Assign):
        nombres = [t.id for t in nodo.targets if isinstance(t, ast.Name)]
        return any(n.upper().startswith("SQL") or n == "ESQUEMA" for n in nombres) and not es_literal(nodo.value)
    return False


def revisar_producto_con_ast() -> tuple[list[str], dict[str, int]]:
    """Lee el producto sin ejecutarlo: dónde hay SQL armado con texto y cuántos assert tiene."""
    armadas, asserts = [], {}
    for archivo in ("viajes.py", "main.py"):
        arbol = ast.parse((RAIZ / archivo).read_text(encoding="utf-8"))
        asserts[archivo] = sum(isinstance(n, ast.Assert) for n in ast.walk(arbol))
        armadas += [f"{archivo}:{n.lineno}" for n in ast.walk(arbol) if sql_armado(n)]
    return armadas, asserts


def i20(admin: v.Administrador) -> None:
    """La seguridad comprobada desde afuera: permisos, SQL, registro, dependencias y workflow."""
    rechaza(PermissionError, v.Destino("Sin sesión", "Zona", "d", 1, 1000).guardar,
            v.Administrador("x@y.cl", "clave-larga-xyz"))
    ok("I.20", "un Administrador armado sin iniciar sesión no tiene ningún permiso (hallazgo 5)")

    armadas, asserts = revisar_producto_con_ast()
    assert not armadas, f"SQL armado con texto en {armadas}"
    ok("I.20", "ninguna consulta SQL se arma pegando textos: todas son literales con parámetros ?"
               " (RNF-SEG-03, revisado con ast en todo el producto)")
    assert asserts == {"viajes.py": 0, "main.py": 0}, asserts
    ok("I.20", "el producto no usa assert: ninguna regla depende de algo que python -O desactiva (bandit B101)")

    visible = v.Cliente.registrar("Rut Visible", "12.345.678-5", "visible@c.cl", "987654321", "clave-larga-vis")
    for _ in range(5):
        v.Usuario.autenticar("visible@c.cl", "clave-equivocada")
    with v.conectar() as con:
        registro = " ".join(f[0] for f in con.execute("SELECT accion || ' ' || detalle FROM auditoria"))
    for dato in ("12345678", "12.345.678", "987654321", "visible@c.cl", "clave-larga-vis"):
        assert dato not in registro, dato
    ok("I.20", "el registro de auditoría no guarda RUT, teléfono, correo ni contraseña (H-02)")
    acciones = [evento[2] for evento in v.consultar_auditoria(admin, 50)]
    assert "sesion.bloqueo" in acciones and "cuenta.crear" in acciones and v.contar_bloqueos(admin) == 1
    rechaza(PermissionError, v.consultar_auditoria, visible)
    ok("I.20", "el socio lee el registro de auditoría y ve los bloqueos de las últimas 24 horas; un cliente"
               " no puede (RF-SEG-16)")

    requisitos = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
    bloques = [b for b in re.split(r"\n(?=[A-Za-z0-9_.-]+==)", requisitos) if re.match(r"[A-Za-z0-9_.-]+==", b)]
    flujo = (RAIZ / ".github" / "workflows" / "pruebas.yml").read_text(encoding="utf-8")
    acciones_ci = re.findall(r"uses: \S+@(\S+)", flujo)
    assert bloques and all("--hash=sha256:" in b for b in bloques)
    assert "contents: read" in flujo and acciones_ci and all(re.fullmatch(r"[0-9a-f]{40}", a) for a in acciones_ci)
    ok("I.20", f"{len(bloques)} dependencias con versión exacta y hash; las acciones del workflow fijadas por"
               " hash y su token de solo lectura (cadena de suministro)")


def seccion_seguridad() -> None:
    with entorno_temporal("seguridad"):
        admin = primer_administrador()
        demostracion(admin)
        i20(admin)


# =====================================================================
# 6. RECORRIDO DEL MENÚ REAL (G.15): genera docs/SALIDA_TERMINAL.md
# =====================================================================

ENTER = ""
ANA = "ana@viajes.cl"
SURIRE, FLAMENCOS = "Salar de Surire", "Flamencos y termas"
SALIDA = (date.today() + timedelta(days=30)).strftime("%d-%m-%Y")
REGRESO = (date.today() + timedelta(days=35)).strftime("%d-%m-%Y")
# Cada línea: lo que se teclea. Las contraseñas van por getpass y en la salida se ven como ••••.
# Menú del administrador: 1-6 destinos, 7-13 paquetes, 14 crear socio, 15 desactivar cuenta,
# 16 respaldo, 17 rotar la clave, 18 registro de auditoría, 19 contraseña, 20 cerrar sesión.
# Menú del cliente: 1-4 reservas, 5-6 mis datos, 7 contraseña, 8 cerrar sesión.
GUION = [
    # Modo demostración (RNF-USA-04): base temporal con datos de ejemplo. El socio edita un destino
    # y publica el borrador eligiéndolos de la lista; la clienta reserva por sobre el cupo (R14).
    "2",
    "1", "3", "1", "Valle del Elqui", "Norte Chico", "Observación astronómica", "3", ENTER,
    "9", "3", "s", ENTER,
    "20",
    "2", "2", "2", "2", ENTER,
    "8",
    "0",
    # Entrar al sistema. Primer uso (S-04): la base real no tiene cuentas.
    "1",
    ANA, "clave-larga-de-ana", "clave-larga-de-ana",
    # Inicio de sesión del administrador: catálogo de destinos.
    "1", ANA, "clave-larga-de-ana",
    "2", "Valle del Elqui", "Norte Chico", "Observación astronómica y pisco", "3", "120.000", ENTER,
    "2", "valle del  elqui", "Norte", "Repetido a propósito (R1)", "2", "1", ENTER,
    "2", SURIRE, "Altiplano", FLAMENCOS, "4", "0", ENTER,
    "2", SURIRE, "Altiplano", FLAMENCOS, "4", "310.000", ENTER,
    "4", "1", "130.000", ENTER,
    "1", "n", ENTER,
    "5", "2", "s", ENTER,
    "1", "s", ENTER,
    "2", SURIRE, "Altiplano", FLAMENCOS, "4", "310.000", ENTER,
    # Paquetes: uno con un solo destino (R3), uno válido, publicarlo y bajar el cupo.
    "8", "Solo uno", SALIDA, REGRESO, "12", "1", ENTER, ENTER,
    "8", "Altiplano y estrellas", SALIDA, REGRESO, "12", "2,1", ENTER, "s", ENTER,
    "9", "1", "s", ENTER,
    "10", "1", ENTER,
    "11", "1", "10", ENTER,
    "7", ENTER,
    # Cuentas, cancelación y opción inexistente.
    "14", "matias@viajes.cl", "s", "brisa-del-pacifico-7", "brisa-del-pacifico-7", ENTER,
    "2", "Torres del Paine", "x", ENTER,
    "99", ENTER,
    "9" * 5000, ENTER,                 # H-12: int() con más de 4.300 dígitos ya no rompe el menú
    "16", ENTER,                       # respaldo de la base (RNF-FIA-03)
    "15", "matias@viajes.cl", "s", ENTER,   # el socio deja la agencia: su cuenta se desactiva (RF-SEG-14)
    "20",
    # La cuenta desactivada ya no entra, con el mismo mensaje que una contraseña errónea.
    "1", "matias@viajes.cl", "brisa-del-pacifico-7",
    # Registro público de un cliente: el RUT con el dígito verificador malo se rechaza al
    # escribirlo, y se vuelve a pedir; una contraseña corta, con una secuencia o con su correo la
    # rechaza el dominio (RF-SEG-04).
    "2", "s", "Carolina Díaz", "12.345.678-6", "12.345.678-5", CAROLINA, "9 1234 5678",
    "corta", "corta",
    "2", "s", "Carolina Díaz", "12.345.678-5", CAROLINA, "9 1234 5678",
    "viaje-al-sur-1234", "viaje-al-sur-1234",
    "2", "s", "Carolina Díaz", "12.345.678-5", CAROLINA, "9 1234 5678",
    "clave-de-carolina", "clave-de-carolina",
    "2", "s", "Carolina Díaz", "12.345.678-5", CAROLINA, "9 1234 5678",
    "luna-sobre-el-salar", "luna-sobre-el-salar",
    # Contraseña errónea y correo inexistente: el mismo mensaje (RF-SEG-02).
    "1", CAROLINA, "clave-equivocada",
    "1", "nadie@correo.cl", "clave-equivocada",
    # Sesión de cliente: oferta, reserva, segunda reserva advertida, sobre el cupo, anulación.
    "1", CAROLINA, "luna-sobre-el-salar",
    "1", ENTER,
    "2", "99", ENTER,                  # H-13: un id inexistente recibe el mismo mensaje
    "2", "1", "2.5", "2", ENTER,       # “2.5” personas se rechaza, no se lee como 25
    "2", "1", "n", ENTER,
    "2", "1", "s", "20", ENTER,
    "3", ENTER,
    "2", "1", "s", "1", ENTER,
    "4", "2", "s", ENTER,
    "5", ENTER,
    "6", "Carolina Díaz Rojas", "987654321", ENTER,
    "8",
    # El administrador ve quién viaja: nombre y correo, sin RUT ni teléfono (RF-RES-11).
    "1", ANA, "clave-larga-de-ana",
    "13", "1", ENTER,
    "17", "s", ENTER,                  # rotar la clave de cifrado (RF-SEG-15)
    "18", ENTER,                       # registro de auditoría (RF-SEG-16)
    "20",
    # Sin sesión también se ve la oferta (S-09).
    "3",
    "0",
]

# Lo que la sesión tiene que mostrar: si falta algo, el guion se desalineó con el menú.
ESPERADO = [
    "Cuenta desactivada. Sus reservas y el registro de auditoría se conservan.",
    "Clave cambiada: 1 cliente(s) cifrados de nuevo.",
    "Registro de auditoría: los últimos 30 eventos (hora UTC)",
    "cuenta.desactivar",
    "clave.rotar",
    "MODO DEMOSTRACIÓN · base temporal, se borra al salir",
    "Datos de ejemplo cargados: 5 destinos",
    "Guardado: [1] Valle del Elqui",
    "Publicado: [3] Sur austral",
    "No hay cupo: quedan 1 lugares",
    "Base de prueba borrada. La base real no se tocó.",
    "Iniciar sesión (socios y clientes)",
    "Destinos disponibles:",
    "Ya existe un destino con ese nombre",
    "El costo base debe estar entre 1 y 100.000.000",
    "Eliminado del catálogo.",
    "Un paquete combina entre 2 y 5 destinos",
    "Precio por persona calculado: $528.000",
    "Guardado en borrador:",
    "Publicado: [1] Altiplano y estrellas",
    "Solo se edita un paquete en borrador",
    "cupo 10 de 10 · publicado",
    "Cuenta de administrador creada para matias@viajes.cl.",
    "Acción cancelada. No se guardó nada.",
    "Sesión cerrada.",
    "El RUT no es válido: revise el dígito verificador",
    "La contraseña debe tener entre 12 y 128 caracteres",
    "Cuenta creada para carolina@correo.cl.",
    "Ley 21.719",
    "Ese paquete no está en la oferta",
    "sin letras ni decimales",
    "Respaldo guardado en",
    "Base legal: la ejecución de la reserva",
    "c*******a@c****.cl (cliente)",         # el correo, enmascarado también en la cabecera
    "Correo:   c*******a@c****.cl",
    "Reserva confirmada por $1.056.000.",
    "Ya tiene una reserva vigente en este paquete",
    "No hay cupo: quedan 8 lugares",
    "Reserva confirmada por $528.000.",
    "Reserva anulada.",
    "RUT:      12.***.***-5",
    "Teléfono: +56 9 ******* 1",
    "(escriba x y Enter para cancelar)",
    "La contraseña no puede tener secuencias como 1234 o abcd",
    "La contraseña no puede contener partes de su correo",
    "¿Crear una cuenta de administrador para matias@viajes.cl?",
    "¿Anular la reserva 2? No se puede deshacer",
    "1) [1] Carolina Díaz <c*******a@c****.cl>",
    "Carolina Díaz Rojas <carolina@correo.cl>",
    "· anulada",
]


def ejecutar(guion: list[str] = GUION, esperado: list[str] = ESPERADO) -> str:
    pendientes = list(guion)
    salida = io.StringIO()

    def teclear(mensaje: str = "", oculto: bool = False) -> str:
        if not pendientes:
            raise EOFError("el guion se acabó antes que la sesión")
        valor = pendientes.pop(0)
        visible = "••••" if oculto and valor else valor
        if len(visible) > 60:
            visible = f"{visible[:12]}… ({len(visible)} caracteres)"
        print(f"{mensaje}{visible}")
        return valor

    originales = builtins.input, getpass.getpass
    builtins.input = lambda mensaje="": teclear(mensaje)
    getpass.getpass = lambda mensaje="Password: ", stream=None: teclear(mensaje, oculto=True)
    # Sin variable de entorno: la clave se crea como en una instalación nueva, en la carpeta temporal.
    os.environ.pop(v.VARIABLE_CLAVE, None)
    clave_original = v.RUTA_CLAVE
    try:
        with tempfile.TemporaryDirectory() as carpeta, redirect_stdout(salida):
            v.RUTA_CLAVE = Path(carpeta) / ".env"
            v.cifrador.cache_clear()
            v.usar_base(os.path.join(carpeta, "sesion.db"))
            import main
            main.main()
    finally:
        builtins.input, getpass.getpass = originales
        v.RUTA_CLAVE = clave_original
        v.cifrador.cache_clear()
    texto = condensar(salida.getvalue())
    assert "Traceback" not in texto, "la sesión mostró un Traceback"
    assert not pendientes, f"quedaron {len(pendientes)} respuestas sin usar: {pendientes[:3]}"
    faltan = [e for e in esperado if e not in texto]
    assert not faltan, f"la sesión no mostró: {faltan}"
    return texto


class RelojQueSalta:
    """time.monotonic falso: devuelve los instantes dados, y después repite el último."""

    def __init__(self, instantes: list[float]):
        self.__instantes = list(instantes)

    def monotonic(self) -> float:
        return self.__instantes.pop(0) if len(self.__instantes) > 1 else self.__instantes[0]


def probar_inactividad() -> str:
    """RF-SEG-09: tras más de 10 minutos ante el menú, la opción elegida no se ejecuta."""
    guion = ["1", ANA, "clave-larga-de-ana", "clave-larga-de-ana",    # entrar al sistema y primer uso
             "1", ANA, "clave-larga-de-ana",
             "14",                    # crear un socio: no debe llegar a pedir el correo
             "0"]
    texto = con_reloj(RelojQueSalta([0, 11 * 60]), guion)
    assert "Correo del socio" not in texto, "la sesión caducada ejecutó la opción"
    # H-11: también dentro de una acción. Se elige “crear socio” a tiempo, pero el correo llega
    # 11 minutos después: la cuenta no se crea.
    guion = ["1", ANA, "clave-larga-de-ana", "clave-larga-de-ana",    # entrar al sistema y primer uso
             "1", ANA, "clave-larga-de-ana",
             "14", "intruso@viajes.cl",
             "0"]
    dentro = con_reloj(RelojQueSalta([0, 10, 10, 11 * 60 + 20]), guion)
    assert "Cuenta de administrador creada" not in dentro, "la acción vencida se completó"
    return texto + "\n[inactividad dentro de una acción]\n" + dentro


def con_reloj(reloj: RelojQueSalta, guion: list[str]) -> str:
    import main
    original = main.time
    main.time = reloj
    try:
        return ejecutar(guion, ["La sesión se cerró por inactividad"])
    finally:
        main.time = original


def condensar(texto: str) -> str:
    """Cada menú se muestra completo la primera vez; las siguientes, como una línea. Las contraseñas
    que el modo demostración genera al azar se reemplazan, para que la evidencia no cambie sola."""
    vistos, partes = set(), texto.split("\033[2J\033[H")
    for i, parte in enumerate(partes[1:], 1):
        encabezado, _, resto = parte.partition("·  0. Salir\n" + "=" * 66 + "\n")
        titulo = next((l for l in encabezado.splitlines() if "Viajes Aventura ·" in l), "")
        if titulo in vistos:
            partes[i] = f"[pantalla limpia · menú de {titulo.split('·')[1].strip()}]\n" + resto
        else:
            vistos.add(titulo)
            partes[i] = "[pantalla limpia]\n" + parte
    texto = "".join(partes)
    return re.sub(r"^(\s+(?:socio|cliente)\s+\S+@demo\.cl\s+)\S+$", r"\1<generada al azar>", texto,
                  flags=re.M)


def seccion_menu() -> None:
    sesion = ejecutar()
    # RF-SEG-02 y RF-SEG-14: contraseña errónea, correo inexistente y cuenta desactivada, igual.
    assert sesion.count("Correo o contraseña incorrectos") == 3
    ok("G.15", f"el menú real, con los dos roles y el modo demostración: {len(ESPERADO)} resultados"
               " esperados, ninguna traza y todas las respuestas del guion usadas")
    caducada = probar_inactividad()
    ok("G.18", "la sesión caduca tras 10 minutos sin uso, en el menú y dentro de una acción (RF-SEG-09)")
    destino = RAIZ / "docs" / "SALIDA_TERMINAL.md"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text("# Sesión real del menú\n\nGenerada por `pruebas/verificar.py` (sección “menu”)"
                       " sobre una base temporal, con datos ficticios (ningún nombre, RUT ni teléfono"
                       " corresponde a una persona). Las contraseñas se teclearon sin eco y aquí se ven"
                       " como ••••; las del modo demostración se generan al azar en cada ejecución."
                       "\n\n```text\n" + sesion + "```\n\n## Sesión que caduca por inactividad"
                       " (RF-SEG-09)\n\nEl reloj se adelanta 11 minutos mientras el menú espera.\n\n"
                       "```text\n" + caducada + "```\n", encoding="utf-8")
    ok("G.15", f"evidencia guardada en {destino.relative_to(RAIZ).as_posix()}"
               f" ({sesion.count(chr(10))} líneas)")


# =====================================================================
# 7. DIAGRAMA DE CLASES CONTRA CÓDIGO (G.13, I.8)
# =====================================================================
# Lee clases.puml y viajes.py con ast, sin ejecutar nada. Para cada clase del diagrama comprueba que
# exista y herede de lo que el diagrama dice; cada atributo privado; cada método con sus parámetros
# en orden y sus marcas {static} o {abstract}; y que el código no tenga métodos públicos que el
# diagrama no dibuja. No se dibujan, por convención: el constructor, los métodos especiales y los
# auxiliares con guion bajo.

def snake(nombre: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", nombre).lower()


# --- Diagrama ----------------------------------------------------------------

def leer_miembro(clase: dict, linea: str) -> None:
    """Una línea del cuerpo de una clase: atributo (“- correo: str”) o método (“+ puede(...)”)."""
    if clase["tipo"] == "enum":
        clase["atributos"].add(linea)                       # valores de la enumeración
        return
    static, abstract = "{static}" in linea, "{abstract}" in linea
    sin_marcas = re.sub(r"\{(static|abstract)\} ", "", linea)
    protegido, firma = sin_marcas[0] == "#", sin_marcas[2:]
    nombre, abre, resto = firma.partition("(")
    if not abre:
        clase["atributos"].add(snake(nombre.split(":")[0].strip()))
        return
    lista = resto.rpartition(")")[0]
    params = tuple(snake(p.split(":")[0].strip()) for p in lista.split(",") if p.strip())
    # “#” protegido en el diagrama = un guion bajo en Python
    clase["metodos"][("_" if protegido else "") + snake(nombre)] = (params, static, abstract)


def leer_relacion(clases: dict, linea: str) -> None:
    """“A <|-- B” es herencia; cualquier otra flecha entre dos clases, una asociación."""
    partes = re.sub(r'"[^"]*"', " ", linea).split()        # sin las multiplicidades
    if len(partes) < 3 or partes[2] not in clases:
        return
    a, flecha, b = partes[:3]
    if "-" not in flecha or "hidden" in flecha:
        return
    if flecha.startswith("<|"):
        clases[b]["padre"] = a                              # el padre puede ser Exception
    elif a in clases:
        clases[a]["asociadas"] |= {snake(b), snake(b) + "s"}
        clases[b]["asociadas"] |= {snake(a), snake(a) + "s"}


def leer_diagrama(texto: str) -> dict:
    clases, actual, relaciones = {}, None, []
    for linea in (l.strip() for l in texto.splitlines()):
        if m := re.match(r"(abstract class|class|enum) (\w+) \{$", linea):
            actual = clases[m.group(2)] = {"tipo": m.group(1), "padre": None, "atributos": set(),
                                           "metodos": {}, "asociadas": set()}
        elif linea == "}":
            actual = None
        elif actual is not None and linea:
            leer_miembro(actual, linea)
        elif actual is None:
            relaciones.append(linea)
    for linea in relaciones:                                 # después: ya están todas las clases
        leer_relacion(clases, linea)
    return clases


# --- Código ------------------------------------------------------------------

def leer_metodo(funcion: ast.FunctionDef) -> tuple:
    decoradores = {getattr(d, "id", getattr(d, "attr", "")) for d in funcion.decorator_list}
    params = tuple(a.arg for a in funcion.args.args + funcion.args.kwonlyargs
                   if a.arg not in ("self", "cls"))
    return params, bool(decoradores & {"staticmethod", "classmethod"}), "abstractmethod" in decoradores


def atributos_asignados(nodo: ast.ClassDef) -> tuple[set, set]:
    """(privados, públicos) asignados como self.x. self.__x llega al árbol sin el mangling."""
    privados, publicos = set(), set()
    for sub in ast.walk(nodo):
        if not (isinstance(sub, ast.Attribute) and isinstance(sub.ctx, ast.Store)
                and isinstance(sub.value, ast.Name) and sub.value.id == "self"):
            continue
        if sub.attr.startswith("__"):
            privados.add(sub.attr[2:])
        elif not sub.attr.startswith("_"):
            publicos.add(sub.attr)
    return privados, publicos


def leer_codigo(texto: str) -> dict:
    clases = {}
    for nodo in (n for n in ast.parse(texto).body if isinstance(n, ast.ClassDef)):
        metodos = {f.name: leer_metodo(f) for f in nodo.body if isinstance(f, ast.FunctionDef)}
        valores = {t.id for a in nodo.body if isinstance(a, ast.Assign)
                   for t in a.targets if isinstance(t, ast.Name)}
        privados, publicos = atributos_asignados(nodo)
        clases[nodo.name] = {"padres": [getattr(b, "id", getattr(b, "attr", "")) for b in nodo.bases],
                             "metodos": metodos, "atributos": privados, "publicos": publicos,
                             "valores": valores}
    return clases


# --- Comparación -------------------------------------------------------------

def comparar_metodos(clase: str, d: dict, c: dict) -> list[str]:
    difs = []
    for nombre, (params, static, abstract) in d["metodos"].items():
        if nombre not in c["metodos"]:
            difs.append(f"{clase}: falta el método {nombre}()")
            continue
        cp, cs, ca = c["metodos"][nombre]
        if cp != params:
            difs.append(f"{clase}.{nombre}: parámetros {params} en el diagrama, {cp} en el código")
        if cs != static:
            difs.append(f"{clase}.{nombre}: {'' if static else 'no '}es de clase en el diagrama")
        if ca != abstract:
            difs.append(f"{clase}.{nombre}: {'' if abstract else 'no '}es abstracto en el diagrama")
    publicos = {m for m in c["metodos"] if not m.startswith("_")}
    difs += [f"{clase}: método público {m}() que el diagrama no dibuja"
             for m in sorted(publicos - set(d["metodos"]))]
    return difs


def comparar_atributos(clase: str, d: dict, c: dict) -> list[str]:
    return ([f"{clase}: falta el atributo privado {a}" for a in sorted(d["atributos"] - c["atributos"])]
            + [f"{clase}: atributo público {a}; el modelo los declara privados"
               for a in sorted(c["publicos"])]
            + [f"{clase}: atributo privado {a} que el diagrama no dibuja"
               for a in sorted(c["atributos"] - d["atributos"] - d["asociadas"])])


def comparar(diagrama: dict, codigo: dict) -> list[str]:
    difs = []
    for clase, d in diagrama.items():
        c = codigo.get(clase)
        if c is None:
            difs.append(f"{clase}: está en el diagrama y no en el código")
            continue
        if d["padre"] and d["padre"] not in c["padres"]:
            difs.append(f"{clase}: el diagrama dice que hereda de {d['padre']}, el código de {c['padres']}")
        if d["tipo"] == "enum":
            difs += [f"{clase}: falta el valor {v}" for v in sorted(d["atributos"] - c["valores"])]
        else:
            difs += comparar_atributos(clase, d, c) + comparar_metodos(clase, d, c)
    return difs


def seccion_uml() -> None:
    diagrama = leer_diagrama((RAIZ / "diagramas" / "clases.puml").read_text(encoding="utf-8"))
    codigo = leer_codigo((RAIZ / "viajes.py").read_text(encoding="utf-8"))
    difs = comparar(diagrama, codigo)
    for d in difs:
        print(f"       DIFERENCIA {d}")
    miembros = sum(len(d["atributos"]) + len(d["metodos"]) for d in diagrama.values())
    assert not difs, f"{len(difs)} diferencias entre el diagrama y el código"
    ok("G.13", f"el código implementa el diagrama: {len(diagrama)} clases, {miembros} miembros,"
               " 0 diferencias")


# =====================================================================
# 8. PRUEBAS DE MUTACIÓN (I.20): cada regla rota a propósito debe ser detectada
# =====================================================================
# Cada mutación cambia un fragmento exacto del producto en una copia temporal y corre las secciones
# indicadas. Si ninguna falla, la regla está desprotegida. Así, “cada corrección tiene una prueba que
# la vigila” es una afirmación que cualquiera puede repetir.

VIAJES, MENU = "viajes.py", "main.py"

# (regla, archivo, fragmento original, fragmento roto, secciones que deben detectarlo)
MUTACIONES = [
    # Reglas del negocio
    ("R1 nombre sin normalizar tildes", VIAJES,
     "if not unicodedata.combining(c))", "if True)", ["reglas"]),
    ("R8 borra el destino aunque esté en un paquete", VIAJES,
     'if en_paquete:\n                con.execute("UPDATE', 'if False:\n                con.execute("UPDATE', ["reglas"]),
    ("R7 publicar no fija el precio", VIAJES,
     'cur = con.execute("UPDATE paquete SET publicado = 1, precio_por_persona = ?"',
     'cur = con.execute("UPDATE paquete SET publicado = 1, precio_por_persona = ? * 0 + NULL"', ["reglas"]),
    ("R6 precio con float", VIAJES,
     "return (suma * (100 + self.__margen) + 50) // 100",
     "return int(suma * (1 + self.__margen / 100) * 0.999)", ["reglas"]),
    ("R14 las anuladas descuentan cupo", VIAJES,
     "WHERE paquete_id = ? AND estado = 'VIGENTE'\", (self.__id,)).fetchone()[0]",
     "WHERE paquete_id = ?\", (self.__id,)).fetchone()[0]", ["reglas"]),
    ("R15 se reserva el mismo día de salida", VIAJES,
     'if date.fromisoformat(fila["fecha_salida"]) <= hoy:',
     'if date.fromisoformat(fila["fecha_salida"]) < hoy:', ["reglas"]),
    ("RNF-FIA-02 sin BEGIN IMMEDIATE", VIAJES,
     '        con.execute("BEGIN IMMEDIATE")\n        try:\n            yield con',
     '        con.execute("BEGIN")\n        try:\n            yield con', ["reglas"]),
    ("H-09 techo antiguo del total", VIAJES,
     'self.__total = entero(total, "El total", 1, PRECIO_MAXIMO * CUPO_MAXIMO, "R13")',
     'self.__total = entero(total, "El total", 1, COSTO_MAXIMO * CUPO_MAXIMO, "R13")', ["reglas"]),
    ("RF-PAQ-09 borra un paquete con reservas", VIAJES,
     '"DELETE FROM paquete WHERE id = ? AND NOT EXISTS"\n                              " (SELECT 1 FROM reserva WHERE paquete_id = ?)", (self.__id, self.__id)',
     '"DELETE FROM reserva WHERE paquete_id = ?", (self.__id,))\n'
     '            cur = con.execute("DELETE FROM paquete WHERE id = ?", (self.__id,)', ["reglas"]),
    # Cuentas, autenticación y permisos
    ("RF-SEG-03 bloqueo tras 6 fallos", VIAJES, "MAX_INTENTOS = 5", "MAX_INTENTOS = 6", ["reglas"]),
    ("RF-SEG-05 el cliente puede tocar el catálogo", VIAJES,
     'return accion == "reservar"', "return True", ["reglas"]),
    ("Hallazgo 5 permiso sin sesión iniciada", VIAJES,
     "if (not isinstance(solicitante, Usuario) or not solicitante.tiene_sesion()",
     "if (not isinstance(solicitante, Usuario)", ["reglas"]),
    # La sesión se revisa antes de cambiar la contraseña; el “AND hash_clave = ?” del UPDATE queda como
    # defensa ante la carrera entre las dos (la mutación de la revisión sí se detecta).
    ("H-10 una sesión que ya no vale cambia la contraseña", VIAJES,
     'if not self.tiene_sesion():\n            raise PermissionError("La contraseña cambió en otra sesión',
     'if False:\n            raise PermissionError("La contraseña cambió en otra sesión', ["credenciales"]),
    ("H-10 la contraseña actual equivocada no cuenta como intento", VIAJES,
     "if not self.__intentar(actual, al_acertar=None):", "if not self.__verificar(actual):", ["credenciales"]),
    ("H-17 bloqueo fijo, no progresivo", VIAJES,
     "BLOQUEOS = (timedelta(minutes=5), timedelta(minutes=15), timedelta(minutes=60))",
     "BLOQUEOS = (timedelta(minutes=5), timedelta(minutes=5), timedelta(minutes=5))", ["credenciales"]),
    ("Sesión vieja sigue valiendo tras cambiar la contraseña", VIAJES,
     'fila["activa"] == 1 and fila["hash_clave"] == self.__hash_clave', 'fila["activa"] == 1', ["credenciales"]),
    ("RF-SEG-14 una cuenta desactivada entra", VIAJES, 'if not fila["activa"]:', "if False:", ["credenciales"]),
    ("RF-SEG-17 el registro no se pausa", VIAJES, "if repetidos >= Cliente.REPETIDOS_MAXIMO:", "if False:",
     ["credenciales"]),
    ("RF-SEG-15 rotar la clave sin volver a cifrar", VIAJES,
     'rut = rotador.rotate(fila["rut_cifrado"].encode()).decode()', 'rut = fila["rut_cifrado"]', ["datos"]),
    ("RF-SEG-16 cualquiera lee el registro de auditoría", VIAJES,
     '    autorizar(solicitante, "auditoria")\n    limite = entero(', '    limite = entero(', ["seguridad"]),
    ("RNF-SEG-03 una consulta armada pegando textos", VIAJES,
     'SQL_CREDENCIAL = "SELECT hash_clave, activa FROM usuario WHERE id = ?"',
     'SQL_CREDENCIAL = "SELECT hash_clave, activa FROM usuario WHERE id = " + "?"', ["seguridad"]),
    ("H-16 sin lista de contraseñas comunes", VIAJES,
     "if clave.casefold() in CLAVES_COMUNES or len(set(clave)) < CLAVE_DISTINTOS:", "if False:", ["reglas"]),
    ("RF-SEG-04 acepta secuencias como 1234", VIAJES,
     "if tiene_secuencia(clave):\n            raise", "if False:\n            raise", ["credenciales"]),
    ("RF-SEG-04 acepta partes del correo", VIAJES,
     "if any(p in normalizar(clave) for p in partes_propias(self.__correo",
     "if False and any(p in normalizar(clave) for p in partes_propias(self.__correo", ["credenciales"]),
    ("RF-SEG-04 acepta el nombre o el teléfono", VIAJES,
     "        if any(p in normalizar(clave) for p in propias):", "        if False:", ["credenciales"]),
    ("H-17 bloqueo con hora local", VIAJES,
     "        ahora = datetime.now(timezone.utc)\n        with conectar() as con:\n            hasta",
     "        ahora = datetime.now()\n        with conectar() as con:\n            hasta", ["reglas"]),
    # Datos personales y cifrado
    ("H-14 acepta el RUT 0", VIAJES, "if int(cuerpo) == 0:", "if False:", ["reglas"]),
    ("H-04/05 descifrar al leer de la base", VIAJES,
     'return Cliente(fila["nombre"], fila["rut_cifrado"], fila["correo"],\n'
     '                       fila["telefono_cifrado"], cifrado=True, **cuenta)',
     'return Cliente(fila["nombre"], descifrar(fila["rut_cifrado"]), fila["correo"],\n'
     '                       descifrar(fila["telefono_cifrado"]), **cuenta)', ["reglas"]),
    ("K-05 la clave exige “sin usuarios”", VIAJES,
     'con.execute("SELECT 1 FROM usuario WHERE rut_cifrado IS NOT NULL LIMIT 1"',
     'con.execute("SELECT 1 FROM usuario LIMIT 1"', ["reglas", "menu"]),
    ("RF-SEG-10 el teléfono muestra los cuatro últimos dígitos", VIAJES,
     'return f"+56 {telefono[0]} ******* {telefono[-1]}"', 'return f"+56 {telefono[0]} **** {telefono[-4:]}"',
     ["datos"]),
    ("RF-SEG-10 el correo completo en “ver mis datos”", MENU,
     "Correo:   {enmascarar_correo(sesion.obtener_correo())}", "Correo:   {sesion.obtener_correo()}", ["menu"]),
    ("H-01 clave dentro del proyecto", VIAJES,
     'RUTA_CLAVE = Path.home() / ".config" / "viajes-aventura" / "clave.env"',
     'RUTA_CLAVE = Path(__file__).with_name(".env")', ["datos"]),
    # Persistencia y consistencia
    ("K-04 historial con el id equivocado", VIAJES,
     'SQL_DE_CLIENTE = ("SELECT r.id AS reserva_id', 'SQL_DE_CLIENTE = ("SELECT r.id, r.id AS reserva_id', ["reglas"]),
    ("H-02 reserva sin registro de auditoría", VIAJES,
     '            registrar_evento(con, solicitante.obtener_id(), "reserva.crear",',
     '            (lambda *a: None)(con, solicitante.obtener_id(), "reserva.crear",', ["reglas"]),
    ("RF-SEG-16 el registro no dice qué destino se eliminó", VIAJES,
     'f"destino {self.__id} “{self.__nombre}”"', 'f"destino {self.__id}"', ["reglas"]),
    ("Hallazgo 4 editar deja el objeto a medias", VIAJES,
     '        autorizar(solicitante, "catalogo")\n        datos = self.__validar_datos(nombre, zona, descripcion, duracion_dias)',
     '        autorizar(solicitante, "catalogo")\n        self.__nombre = nombre\n'
     '        datos = self.__validar_datos(nombre, zona, descripcion, duracion_dias)', ["reglas"]),
    ("Hallazgo 20 escritura sin revisar rowcount", VIAJES,
     "    if cur.rowcount != 1:\n        raise ValueError(f\"El {que} ya no existe",
     "    if False:\n        raise ValueError(f\"El {que} ya no existe", ["reglas"]),
    # Menú
    ("Hallazgo 3 “2.5” personas se lee como 25", MENU,
     "        valor = leer(mensaje)\n        if ENTERO_CON_MILES.fullmatch(valor):",
     "        valor = leer(mensaje).replace(\".\", \"\")\n        if ENTERO_CON_MILES.fullmatch(valor):", ["menu"]),
    ("H-11 plazo de inactividad solo en el menú", MENU,
     "        if time.monotonic() > VENCE:\n            raise SesionCaducada",
     "        if False:\n            raise SesionCaducada", ["menu"]),
    ("H-12 int() sin límite de largo", MENU,
     "if not (len(eleccion) <= 3 and eleccion.isdecimal()", "if not (eleccion.isdecimal()", ["menu"]),
    ("RNF-USA-01 anular una reserva sin confirmar", MENU,
     '    if not pedir_si_no(f"   ¿Anular la reserva {numero}? No se puede deshacer"):\n        raise Cancelado\n', "", ["menu"]),
    ("RNF-USA-01 crear un socio sin confirmar", MENU,
     '    if not pedir_si_no(f"   ¿Crear una cuenta de administrador para {correo}? Tendrá todos los"\n'
     '                       " permisos de un socio"):\n        raise Cancelado\n', "", ["menu"]),
    ("RNF-USA-01 sin el aviso de cómo cancelar", MENU,
     "        AVISAR_CANCELAR = False\n        print(AVISO_CANCELAR)", "        AVISAR_CANCELAR = False",
     ["menu"]),
    ("RNF-USA-04 la demostración escribe en la base real", MENU,
     'viajes.usar_base(os.path.join(carpeta, "demostracion.db"))', "pass", ["seguridad"]),
    ("H-13 mensajes distintos para “no existe” y “no publicado”", MENU,
     "    if paquete is None or not paquete.esta_disponible():\n        raise ValueError(NO_DISPONIBLE)",
     "    if paquete is None:\n        raise ValueError('No existe')", ["menu"]),
]


def mutacion_detectada(nombre: str, archivo: str, original: str, roto: str, secciones: list[str]) -> bool:
    """True si al menos una de las secciones falla con la mutación puesta."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as carpeta:
        copia = Path(carpeta)
        for parte in ("viajes.py", "main.py", "pruebas", "diagramas", ".gitignore", "requirements.txt",
                      ".github"):
            origen = RAIZ / parte
            if origen.exists():
                (shutil.copytree if origen.is_dir() else shutil.copy)(origen, copia / parte)
        texto = (copia / archivo).read_text(encoding="utf-8")
        if texto.count(original) != 1:
            raise AssertionError(f"“{nombre}”: el fragmento original ya no está en {archivo}")
        (copia / archivo).write_text(texto.replace(original, roto), encoding="utf-8")
        for seccion in secciones:
            r = subprocess.run([sys.executable, "pruebas/verificar.py", "--solo", seccion], cwd=copia,
                               capture_output=True, text=True, timeout=600)
            if r.returncode != 0:
                return True
    return False


def seccion_mutaciones() -> None:
    vivas = []
    for nombre, archivo, original, roto, secciones in MUTACIONES:
        detectada = mutacion_detectada(nombre, archivo, original, roto, secciones)
        print(f"       {'detectada' if detectada else 'VIVA     '}  {nombre}")
        if not detectada:
            vivas.append(nombre)
    assert not vivas, f"mutaciones que ninguna prueba detecta: {vivas}"
    ok("I.20", f"{len(MUTACIONES)} de {len(MUTACIONES)} reglas rotas a propósito: todas detectadas")


# =====================================================================
# 9. INTERFAZ
# =====================================================================

SECCIONES = [
    ("reglas", "Reglas del negocio R1 a R17", "G.14, G.15", seccion_reglas),
    ("implementacion", "POO, persistencia y CRUD", "G.13, G.14, G.15", seccion_implementacion),
    ("credenciales", "Autenticación y credenciales", "G.17, G.18", seccion_credenciales),
    ("datos", "Datos personales: confidencialidad e integridad", "I.19", seccion_datos),
    ("seguridad", "Seguridad: evaluación y mejoras", "I.20", seccion_seguridad),
    ("menu", "Recorrido del menú real (genera la evidencia)", "G.15", seccion_menu),
    ("uml", "Diagrama de clases contra código", "G.13, I.8", seccion_uml),
    ("mutaciones", "Pruebas de mutación (tardan unos minutos)", "I.20", seccion_mutaciones),
]


def lugar_del_fallo(error: BaseException) -> str:
    """La línea de este archivo donde falló la afirmación, para ir directo a ella."""
    marcos = [m for m in traceback.extract_tb(error.__traceback__) if m.filename == __file__]
    return f"verificar.py:{marcos[-1].lineno}" if marcos else ""


def correr(claves: list[str]) -> bool:
    PASOS.clear()
    resultados = []
    for clave, titulo, indicadores, funcion in SECCIONES:
        if clave not in claves:
            continue
        print(f"\n== {titulo} ({indicadores}) " + "=" * max(3, 60 - len(titulo) - len(indicadores)))
        inicio = time.perf_counter()
        try:
            funcion()
            resultados.append((titulo, "OK", time.perf_counter() - inicio))
        except Exception as error:                    # se informa y se sigue con la siguiente
            print(f"  FALLA  {type(error).__name__}: {error}  [{lugar_del_fallo(error)}]")
            resultados.append((titulo, "FALLA", time.perf_counter() - inicio))
    print("\n== Resumen " + "=" * 58)
    for titulo, estado, segundos in resultados:
        print(f"  {estado:<6} {titulo:<50} {segundos:6.1f} s")
    print("  Afirmaciones por indicador: "
          + " · ".join(f"{k} {n}" for k, n in sorted(PASOS.items())))
    todo_bien = all(estado == "OK" for _, estado, _ in resultados)
    print(f"  {sum(PASOS.values())} afirmaciones comprobadas; "
          + ("ninguna falla." if todo_bien else "HAY FALLAS."))
    return todo_bien


def interfaz() -> None:
    while True:
        print("\n" + "=" * 70 + "\n   VERIFICACIÓN · Viajes Aventura\n" + "=" * 70)
        for numero, (_, titulo, indicadores, _) in enumerate(SECCIONES, 1):
            print(f"   {numero}. {titulo:<50} ({indicadores})")
        print(f"   {len(SECCIONES) + 1}. Todo\n   0. Salir")
        try:
            eleccion = input("\n   Opción: ").strip()
        except (KeyboardInterrupt, EOFError):
            return
        if eleccion == "0":
            return
        if eleccion == str(len(SECCIONES) + 1):
            correr([s[0] for s in SECCIONES])
        elif eleccion.isdecimal() and 1 <= int(eleccion) <= len(SECCIONES):
            correr([SECCIONES[int(eleccion) - 1][0]])
        else:
            print("   ! Opción desconocida.")
            continue
        try:
            input("\n   Presione Enter para volver...")
        except (KeyboardInterrupt, EOFError):
            return


def main() -> None:
    opciones = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    grupo = opciones.add_mutually_exclusive_group()
    grupo.add_argument("--todo", action="store_true", help="todas las secciones")
    grupo.add_argument("--rapido", action="store_true", help="todas menos las mutaciones")
    grupo.add_argument("--solo", choices=[s[0] for s in SECCIONES], help="una sección")
    args = opciones.parse_args()
    if args.solo:
        sys.exit(0 if correr([args.solo]) else 1)
    if args.todo or args.rapido:
        claves = [s[0] for s in SECCIONES if not (args.rapido and s[0] == "mutaciones")]
        sys.exit(0 if correr(claves) else 1)
    interfaz()


if __name__ == "__main__":
    main()
