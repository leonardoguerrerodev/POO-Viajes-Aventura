"""Una prueba por indicador de la rúbrica que se puede verificar en el código.

Cada bloque imprime «✔ <indicador> <afirmación>» solo si la afirmación se cumple; si una falla, la
prueba se detiene con AssertionError y el workflow queda en rojo. Trabaja sobre una base y una clave
temporales: no toca viajes.db ni .env.

    python pruebas/prueba_rubrica.py
"""

import os
import sqlite3
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "herramientas"))

from argon2 import PasswordHasher  # noqa: E402

import uml_vs_codigo  # noqa: E402
import viajes as v  # noqa: E402

TOTAL = 0


def ok(indicador: str, afirmacion: str) -> None:
    global TOTAL
    TOTAL += 1
    print(f"  ✔ {indicador:<7} {afirmacion}")


def rechaza(error: type[Exception], accion, *args) -> Exception:
    try:
        accion(*args)
    except error as e:
        return e
    raise AssertionError(f"{getattr(accion, '__name__', accion)} no rechazó {args!r}")


def futuro(dias: int) -> date:
    return date.today() + timedelta(days=dias)


# --- 4.1.4.G.13: el código respeta el UML y los cuatro principios -------------

def g13() -> None:
    diagrama = uml_vs_codigo.leer_diagrama((RAIZ / "diagramas/clases.puml").read_text(encoding="utf-8"))
    codigo = uml_vs_codigo.leer_codigo((RAIZ / "viajes.py").read_text(encoding="utf-8"))
    difs = uml_vs_codigo.comparar(diagrama, codigo)
    miembros = sum(len(d["atributos"]) + len(d["metodos"]) for d in diagrama.values())
    assert not difs, difs
    ok("G.13", f"el código implementa el diagrama: {len(diagrama)} clases, {miembros} miembros, 0 diferencias")
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
                                  "clave-de-carolina")
    cliente.actualizar_contacto("Carolina Díaz R.", "987654321")
    assert v.Usuario.autenticar("carolina@c.cl", "clave-de-carolina").obtener_nombre() == "Carolina Díaz R."
    ok("G.15", "Cliente: crear (registro), leer (inicio de sesión) y actualizar su contacto")

    reserva = v.Reserva.reservar(paquete, 2, cliente)
    assert len(cliente.historial()) == 1 and len(v.Reserva.listar_por_paquete(paquete, admin)) == 1
    cliente.historial()[0].anular(cliente)
    assert v.Paquete.buscar(paquete.obtener_id()).cupo_disponible() == 10 and reserva.obtener_total() > 0
    ok("G.15", "Reserva: crear, leer (historial y por paquete) y anular; no se borra, es historial (S-01)")
    rechaza(v.ReglaNegocioError, paquete.eliminar, admin)
    ok("G.15", "un paquete con reservas no se elimina (RF-PAQ-09), ni siquiera si están anuladas")
    g15.datos = (paquete, cliente)


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
    assert 0.05 <= duracion <= 1.0, duracion
    ok("G.17", f"verificar una contraseña tarda {duracion * 1000:.0f} ms (RNF-REN-02 pide 0,1 a 1 s"
               " en el equipo de la oficina)")


# --- 4.1.5.G.18: validación rigurosa de credenciales en todos los escenarios ---

def g18() -> None:
    cuenta = v.Cliente.registrar("Pedro", "11.111.111-1", "pedro@c.cl", "922223333", "clave-de-pedro-1")
    assert isinstance(v.Usuario.autenticar("PEDRO@c.cl", "clave-de-pedro-1"), v.Cliente)
    ok("G.18", "credenciales correctas: entra, sin importar mayúsculas en el correo")
    assert v.Usuario.autenticar("pedro@c.cl", "clave-equivocada") is None
    assert v.Usuario.autenticar("nadie@c.cl", "clave-de-pedro-1") is None
    assert v.Usuario.autenticar("no es correo", "") is None and v.Usuario.autenticar("", None) is None
    ok("G.18", "contraseña errónea, correo inexistente, formato inválido o vacío: la misma respuesta")

    def demora(correo: str) -> float:
        inicio = time.perf_counter()
        for _ in range(3):
            v.Usuario.autenticar(correo, "otra-clave-x")
        return time.perf_counter() - inicio

    v.Usuario.autenticar("nadie@c.cl", "x")                 # el hash señuelo se calcula una vez
    existe, no_existe = demora("pedro@c.cl"), demora("nadie@c.cl")
    assert 0.5 < existe / no_existe < 2, (existe, no_existe)
    ok("G.18", f"el correo inexistente tarda lo mismo que uno existente ({no_existe / 3 * 1000:.0f} ms"
               f" contra {existe / 3 * 1000:.0f} ms): no revela qué correos hay")
    with v.conectar() as con:
        con.execute("UPDATE usuario SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE correo = 'pedro@c.cl'")
    for _ in range(5):
        v.Usuario.autenticar("pedro@c.cl", "clave-equivocada")
    assert v.Usuario.autenticar("pedro@c.cl", "clave-de-pedro-1") is None
    otra = sqlite3.connect(v.RUTA_ACTIVA)
    hasta = otra.execute("SELECT bloqueado_hasta FROM usuario WHERE correo = 'pedro@c.cl'").fetchone()[0]
    otra.close()
    assert datetime.fromisoformat(hasta) > datetime.now(timezone.utc) + timedelta(minutes=4)
    ok("G.18", "5 fallos seguidos bloquean 5 minutos, aun con la contraseña correcta, y el bloqueo"
               " queda en la base")
    for clave, motivo in (("a" * 11, "11 caracteres"), ("Pedro2@c.cl", "igual al correo")):
        rechaza(v.ReglaNegocioError, v.Cliente, "P", "11.111.111-1", "pedro2@c.cl", "922223333", clave)
    ok("G.18", "política de contraseña: se rechaza con 11 caracteres o si es igual al correo")
    rechaza(PermissionError, cuenta.cambiar_clave, "clave-equivocada", "otra-clave-larga")
    ok("G.18", "cambiar la contraseña exige la actual")
    debil = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash("clave-de-pedro-1")
    with v.conectar() as con:
        con.execute("UPDATE usuario SET hash_clave = ?, bloqueado_hasta = NULL WHERE correo = 'pedro@c.cl'",
                    (debil,))
    assert v.Usuario.autenticar("pedro@c.cl", "clave-de-pedro-1") is not None
    with v.conectar() as con:
        nuevo = con.execute("SELECT hash_clave FROM usuario WHERE correo = 'pedro@c.cl'").fetchone()[0]
    assert "m=65536,t=4,p=4" in nuevo
    ok("G.18", "un hash con parámetros viejos se rehace al entrar (check_needs_rehash)")


# --- 4.1.5.I.19: confidencialidad e integridad de los datos personales --------

def i19() -> None:
    paquete, cliente = g15.datos
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
    ok("I.19", "la clave (.env) y la base (*.db) no viajan al repositorio")
    assert cliente.rut_enmascarado() == "12.***.***-5" and cliente.telefono_enmascarado() == "+56 9 **** 4321"
    assert all("12345678" not in str(r) for r in v.Reserva.listar_por_paquete(paquete, g15.admin))
    assert "12345678" not in repr(cliente)
    ok("I.19", "RUT y teléfono solo enmascarados: en pantalla, en listados y en la representación del objeto")
    e = rechaza(ValueError, v.Cliente, "P", "12.345.678-6", "x@c.cl", "912345678", "clave-larga-xx")
    assert "12.345.678" not in str(e) and "12345678" not in str(e)
    ok("I.19", "los mensajes de error nombran el campo, nunca el RUT ni el teléfono ingresados")


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


def main() -> None:
    print("Autoverificación del dominio (reglas R1 a R17):")
    v.autoverificar()
    os.environ.pop(v.VARIABLE_CLAVE, None)      # la clave se crea en la carpeta temporal
    with tempfile.TemporaryDirectory() as carpeta:
        original = v.RUTA_CLAVE
        v.RUTA_CLAVE = Path(carpeta) / ".env"
        v.cifrador.cache_clear()
        try:
            v.usar_base(os.path.join(carpeta, "rubrica.db"))
            v.crear_tablas()
            admin = v.Administrador.crear_primero("admin@viajes.cl", "clave-larga-admin")
            g15.admin = admin
            print("\nPrueba por indicador:")
            g13()
            g14(admin)
            g15(admin)
            g17()
            g18()
            i19()
            rendimiento(admin)
        finally:
            v.RUTA_CLAVE = original
            v.cifrador.cache_clear()
    print(f"\n{TOTAL} afirmaciones verificadas, 0 fallos")


if __name__ == "__main__":
    main()
