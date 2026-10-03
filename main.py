"""Viajes Aventura: menú de terminal.

Pantalla de inicio (iniciar sesión o registrarse) y un menú por sesión que muestra solo lo que el
rol puede hacer. No contiene ninguna sentencia SQL: todo el acceso a datos vive en viajes.py.

    python main.py
"""

import getpass                              # contraseñas sin eco en pantalla
import sqlite3                              # solo para reconocer sus errores, nunca para consultar
import time                                 # inactividad de la sesión (RF-SEG-09)

from viajes import (Administrador, Cliente, Destino, ReglaNegocioError, Usuario,
                    crear_tablas, hay_usuarios, validar_correo, validar_rut, validar_telefono)

# Techo de todo entero que se teclea: un número enorme no debe llegar a int() ni a la base.
MAXIMO_ENTERO = 10**9
INACTIVIDAD_MAXIMA = 10 * 60                # segundos sin actividad antes de cerrar la sesión

CREDENCIALES_INVALIDAS = ("   ! Correo o contraseña incorrectos, o la cuenta está bloqueada"
                          " por unos minutos.")
SESION_CADUCADA = "   ! La sesión se cerró por inactividad. Inicie sesión de nuevo."
INTERRUMPIDO = "\n   Interrumpido. Hasta luego."
PIDE_ID_DESTINO = "   Id del destino: "
PIDE_CORREO = "   Correo: "
PIDE_NOMBRE = "   Nombre: "
MI_CUENTA = "Mi cuenta"


class Cancelado(Exception):
    """El usuario escribió x en lugar del dato (RNF-USA-01). No hereda de ValueError a propósito:
    una lectura que reintenta ante un ValueError la confundiría con un dato mal escrito."""


class CerrarSesion(Exception):
    """El usuario pidió cerrar la sesión (RF-SEG-08)."""


def limpiar() -> None:
    # Secuencia ANSI: borra la pantalla sin abrir una shell ni buscar un programa en el PATH.
    print("\033[2J\033[H", end="")


# --- Entrada del usuario ---------------------------------------------------
# Toda lectura pasa por leer(): así «x» cancela en cualquier dato.

def leer(mensaje: str) -> str:
    valor = input(mensaje).strip()
    if valor.lower() == "x":
        raise Cancelado
    return valor


def pedir_texto(mensaje: str) -> str:
    while True:
        valor = leer(mensaje)
        if valor:
            return valor
        print("   ! No puede quedar vacío.")


def pedir_valido(mensaje: str, validar) -> str:
    """Primera capa de validación: avisa apenas se escribe el dato. El dominio vuelve a validarlo."""
    while True:
        valor = pedir_texto(mensaje)
        try:
            validar(valor)
            return valor
        except (ValueError, TypeError) as error:
            print(f"   ! {error}")


def pedir_entero(mensaje: str) -> int:
    while True:
        valor = leer(mensaje).replace(".", "")       # acepta 1.050.000, como la planilla
        # isdecimal y no isdigit: isdigit acepta caracteres como «²» que int() rechaza.
        if not valor.isdecimal():
            print("   ! Escriba un número entero, sin letras.")
        elif len(valor) > 12 or int(valor) > MAXIMO_ENTERO:
            print(f"   ! Demasiado grande. El máximo es {MAXIMO_ENTERO:,}.".replace(",", "."))
        else:
            return int(valor)


def pedir_si_no(mensaje: str) -> bool:
    while True:
        valor = leer(mensaje + " (s/n): ").lower()
        if valor in ("s", "n"):
            return valor == "s"
        print("   ! Responda s o n.")


def pedir_clave(mensaje: str = "   Contraseña: ") -> str:
    clave = getpass.getpass(mensaje)
    if clave.strip().lower() == "x":
        raise Cancelado
    return clave


def pedir_clave_nueva() -> str:
    """Dos veces y sin eco. La política (12 o más, distinta del correo) la valida Usuario."""
    while True:
        clave = pedir_clave("   Contraseña nueva (12 caracteres o más): ")
        if clave == pedir_clave("   Repita la contraseña: "):
            return clave
        print("   ! Las contraseñas no coinciden.")


def pedir_destino() -> Destino:
    destino = Destino.buscar(pedir_entero(PIDE_ID_DESTINO))
    if destino is None:
        raise ValueError("No existe un destino con ese id")
    return destino


# --- Acciones sin sesión ---------------------------------------------------

def registrarse() -> None:
    """Registro público: siempre crea un cliente (RF-SEG-12). Nada en pantalla permite elegir rol."""
    print("\n   Registro de cliente (escriba x para cancelar)")
    cliente = Cliente.registrar(pedir_texto("   Nombre completo: "),
                                pedir_valido("   RUT (12.345.678-5): ", validar_rut),
                                pedir_valido(PIDE_CORREO, validar_correo),
                                pedir_valido("   Teléfono (9 1234 5678): ", validar_telefono),
                                pedir_clave_nueva())
    print(f"   Cuenta creada para {cliente.obtener_correo()}. Ya puede iniciar sesión.")


def iniciar_sesion() -> Usuario | None:
    print("\n   Inicio de sesión (escriba x para cancelar)")
    try:
        usuario = Usuario.autenticar(pedir_texto(PIDE_CORREO), pedir_clave())
    except Cancelado:
        print("   Acción cancelada.")
        return None
    except (ValueError, RuntimeError) as error:
        # Un dato personal ilegible o la clave de cifrado ausente: el mensaje no trae datos.
        print(f"   ! {error}")
        return None
    if usuario is None:
        print(CREDENCIALES_INVALIDAS)        # mismo mensaje para los tres fallos (RF-SEG-02)
    return usuario


# --- Acciones del administrador: destinos ----------------------------------

def listar_destinos(_sesion: Usuario) -> None:
    solo = pedir_si_no("   ¿Solo los disponibles?")
    destinos = Destino.listar(solo_disponibles=solo)
    print("\n   Catálogo de destinos" + (" disponibles" if solo else ""))
    for destino in destinos:
        print(f"   {destino}")
    if not destinos:
        print("   (sin destinos)")


def registrar_destino(sesion: Usuario) -> None:
    destino = Destino(pedir_texto(PIDE_NOMBRE), pedir_texto("   Zona: "),
                      pedir_texto("   Descripción: "), pedir_entero("   Duración en días: "),
                      pedir_entero("   Costo base por persona ($): "))
    destino.guardar(sesion)
    print(f"   Registrado: {destino}")


def editar_destino(sesion: Usuario) -> None:
    destino = pedir_destino()
    print(f"   Actual: {destino}")
    destino.editar(pedir_texto(PIDE_NOMBRE), pedir_texto("   Zona: "),
                   pedir_texto("   Descripción: "), pedir_entero("   Duración en días: "), sesion)
    print(f"   Guardado: {destino}")


def cambiar_costo(sesion: Usuario) -> None:
    destino = pedir_destino()
    print(f"   Actual: {destino}")
    destino.cambiar_costo(pedir_entero("   Costo base nuevo ($): "), sesion)
    print(f"   Guardado: {destino}")


def eliminar_destino(sesion: Usuario) -> None:
    destino = pedir_destino()
    print(f"   {destino}")
    if not pedir_si_no("   ¿Eliminarlo?"):
        raise Cancelado
    if destino.eliminar(sesion):
        print("   Eliminado del catálogo.")
    else:
        # R8: el destino está en un paquete; se conserva para no cambiar lo que ya se vendió.
        print("   Está en al menos un paquete: quedó «no disponible» y no se ofrecerá en"
              " paquetes nuevos.")


def reactivar_destino(sesion: Usuario) -> None:
    destino = pedir_destino()
    destino.reactivar(sesion)
    print(f"   Disponible otra vez: {destino}")


def crear_socio(sesion: Administrador) -> None:
    nuevo = sesion.crear_administrador(pedir_texto("   Correo del socio: "), pedir_clave_nueva())
    print(f"   Cuenta de administrador creada para {nuevo.obtener_correo()}.")


# --- Acciones del cliente y de toda sesión ---------------------------------

def mis_datos(sesion: Cliente) -> None:
    # RUT y teléfono solo enmascarados, incluso para su dueño (RF-SEG-10, S-16).
    print(f"   Nombre:   {sesion.obtener_nombre()}\n   Correo:   {sesion.obtener_correo()}\n"
          f"   RUT:      {sesion.rut_enmascarado()}\n   Teléfono: {sesion.telefono_enmascarado()}")


def actualizar_contacto(sesion: Cliente) -> None:
    sesion.actualizar_contacto(pedir_texto(PIDE_NOMBRE),
                               pedir_valido("   Teléfono: ", validar_telefono))
    print("   Datos actualizados.")
    mis_datos(sesion)


def cambiar_clave(sesion: Usuario) -> None:
    sesion.cambiar_clave(pedir_clave("   Contraseña actual: "), pedir_clave_nueva())
    print("   Contraseña cambiada.")


def cerrar_sesion(_sesion: Usuario) -> None:
    raise CerrarSesion


# Cada opción: (sección, texto, acción que exige o None, función). El menú de una sesión es la
# lista filtrada con puede(): el mismo código arma el menú de los dos roles (polimorfismo).
OPCIONES = [
    ("Destinos", "Listar el catálogo", "catalogo", listar_destinos),
    ("Destinos", "Registrar un destino", "catalogo", registrar_destino),
    ("Destinos", "Editar un destino", "catalogo", editar_destino),
    ("Destinos", "Cambiar el costo de un destino", "catalogo", cambiar_costo),
    ("Destinos", "Eliminar un destino", "catalogo", eliminar_destino),
    ("Destinos", "Volver a ofrecer un destino", "catalogo", reactivar_destino),
    ("Cuentas", "Crear la cuenta de un socio", "cuentas", crear_socio),
    (MI_CUENTA, "Ver mis datos", "reservar", mis_datos),
    (MI_CUENTA, "Actualizar nombre y teléfono", "reservar", actualizar_contacto),
    (MI_CUENTA, "Cambiar mi contraseña", None, cambiar_clave),
    (MI_CUENTA, "Cerrar sesión", None, cerrar_sesion),
]


def opciones_de(sesion: Usuario) -> list[tuple]:
    """Solo lo que este rol puede hacer (RNF-USA-03). El dominio vuelve a revisarlo al escribir."""
    return [o for o in OPCIONES if o[2] is None or sesion.puede(o[2])]


def mostrar_menu(sesion: Usuario, opciones: list[tuple]) -> None:
    limpiar()
    rol = "administrador" if sesion.puede("catalogo") else "cliente"
    print("=" * 66 + f"\n   Viajes Aventura · {sesion.obtener_correo()} ({rol})\n" + "=" * 66)
    seccion = None
    for numero, (nombre_seccion, etiqueta, _accion, _funcion) in enumerate(opciones, 1):
        if nombre_seccion != seccion:
            seccion = nombre_seccion
            print(f"\n   {seccion.upper()}")
        print(f"   {numero:>2}. {etiqueta}")
    print("\n   Escriba «x» para cancelar la acción en curso  ·  0. Salir\n" + "=" * 66)


# --- Ejecución y errores ---------------------------------------------------

def atender(funcion, sesion: Usuario | None) -> bool:
    """Ejecuta una acción y traduce cada error a un mensaje para el usuario. False: salir.

    Ningún mensaje muestra trazas, rutas ni datos personales (RNF-SEG-05).
    """
    try:
        funcion(sesion) if sesion is not None else funcion()
    except Cancelado:
        print("   Acción cancelada. No se guardó nada.")
    except ReglaNegocioError as error:
        print(f"   ! {error}")                          # el mensaje de la regla es para el usuario
    except (PermissionError, ValueError, TypeError) as error:
        print(f"   ! {error}")
    except sqlite3.OperationalError:
        print("   ! La base de datos está ocupada o no se pudo abrir. Intente de nuevo.")
    except sqlite3.Error:
        print("   ! La base rechazó la operación. No se guardó nada.")
    except (KeyboardInterrupt, EOFError):
        return False
    except CerrarSesion:
        raise
    except Exception as error:
        # Solo el tipo: el texto de un error desconocido puede traer rutas, consultas o datos.
        print(f"   ! Error inesperado ({type(error).__name__}). La acción no se completó.")
    return True


def pausar() -> bool:
    try:
        input("\n   Presione Enter para continuar...")
    except (KeyboardInterrupt, EOFError):
        return False
    return True


def usar_sesion(sesion: Usuario) -> bool:
    """El menú de una sesión. True: volver al inicio (cerró o caducó). False: salir del programa."""
    opciones = opciones_de(sesion)
    ultima = time.monotonic()
    while True:
        mostrar_menu(sesion, opciones)
        try:
            eleccion = input("\n   Opción: ").strip()
        except (KeyboardInterrupt, EOFError):
            return False
        # La espera ante el menú también cuenta como inactividad (RF-SEG-09).
        if time.monotonic() - ultima > INACTIVIDAD_MAXIMA:
            print(SESION_CADUCADA)
            return True
        resultado = ejecutar_opcion(eleccion, opciones, sesion)
        if resultado is not None:
            return resultado
        if not pausar():
            return False
        ultima = time.monotonic()


def ejecutar_opcion(eleccion: str, opciones: list[tuple], sesion: Usuario) -> bool | None:
    """None: seguir en el menú. True: volver al inicio. False: salir del programa."""
    if eleccion == "0":
        return False
    if not (eleccion.isdecimal() and 1 <= int(eleccion) <= len(opciones)):
        print("   ! Opción desconocida.")
        return None
    try:
        return None if atender(opciones[int(eleccion) - 1][3], sesion) else False
    except CerrarSesion:
        print("   Sesión cerrada.")
        return True


def alta_inicial() -> None:
    """Primer uso (S-04): sin cuentas en la base, se crea la del primer administrador."""
    print("\n   Primer uso: cree la cuenta del primer administrador.")
    while True:
        try:
            admin = Administrador.crear_primero(pedir_texto(PIDE_CORREO), pedir_clave_nueva())
            print(f"   Cuenta creada para {admin.obtener_correo()}. Ahora inicie sesión.")
            return
        except (ReglaNegocioError, ValueError, TypeError) as error:
            print(f"   ! {error}")


def inicio() -> bool:
    """Pantalla sin sesión. False: salir del programa."""
    print("\n" + "=" * 66 + "\n   Viajes Aventura\n" + "=" * 66)
    print("   1. Iniciar sesión\n   2. Registrarme como cliente\n   0. Salir")
    try:
        eleccion = input("\n   Opción: ").strip()
    except (KeyboardInterrupt, EOFError):
        return False
    if eleccion == "0":
        return False
    if eleccion == "1":
        sesion = iniciar_sesion()
        if sesion is not None:
            return usar_sesion(sesion)
    elif eleccion == "2":
        if not atender(registrarse, None):
            return False
    else:
        print("   ! Opción desconocida.")
    return True


def main() -> None:
    try:
        crear_tablas()
        if not hay_usuarios():
            alta_inicial()
        seguir = True
        while seguir:
            seguir = inicio()
        print("   Hasta luego.")
    except sqlite3.Error:
        print("   ! No se pudo abrir la base de datos. El programa se cierra.")
    except (Cancelado, KeyboardInterrupt, EOFError):
        print(INTERRUMPIDO)


if __name__ == "__main__":
    main()
