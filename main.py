"""Viajes Aventura: menú de terminal.

Pantalla de inicio (iniciar sesión o registrarse) y un menú por sesión que muestra solo lo que el
rol puede hacer. No contiene ninguna sentencia SQL: todo el acceso a datos vive en viajes.py.

    python main.py
"""

import getpass                              # contraseñas sin eco en pantalla
import os                                   # umask: archivos nuevos solo para su dueño (H-15)
import re                                   # números con separador de miles (1.050.000)
import sqlite3                              # solo para reconocer sus errores, nunca para consultar
import time                                 # inactividad de la sesión (RF-SEG-09)
from datetime import date, datetime         # fechas como día-mes-año (RNF-USA-02)

from viajes import (MARGEN_PROPUESTO, Administrador, Cliente, Destino, Paquete,
                    ReglaNegocioError, Reserva, Usuario, crear_tablas, hay_usuarios, pesos,
                    validar_correo, validar_rut, validar_telefono)

# Techo de todo entero que se teclea: un número enorme no debe llegar a int() ni a la base.
MAXIMO_ENTERO = 10**9
INACTIVIDAD_MAXIMA = 10 * 60                # segundos sin actividad antes de cerrar la sesión

CREDENCIALES_INVALIDAS = ("   ! Correo o contraseña incorrectos, o la cuenta está bloqueada"
                          " por unos minutos.")
SESION_CADUCADA = "   ! La sesión se cerró por inactividad. Inicie sesión de nuevo."
# Deber de información (Ley 19.628 modificada por la Ley 21.719, art. 14 ter): para qué se piden los
# datos, cómo se protegen y cómo se ejercen los derechos (H-14).
AVISO_DATOS = (
    "   Responsable: Viajes Aventura, Valparaíso.\n"
    "   Datos: nombre, RUT, correo y teléfono. Finalidad: registrar sus reservas y contactarlo\n"
    "   por ellas; no se usan para nada más. Base legal: la ejecución de la reserva que usted\n"
    "   solicita. Destinatarios: solo los socios de la agencia; no se ceden a terceros.\n"
    "   Conservación: mientras su cuenta exista; las reservas, como respaldo de lo cobrado.\n"
    "   Protección: el RUT y el teléfono se guardan cifrados y nunca se muestran completos.\n"
    "   Derechos: acceso, rectificación, supresión, oposición, portabilidad y bloqueo; se\n"
    "   ejercen ante los socios de la agencia, que responden en 30 días corridos\n"
    "   (Ley 19.628 modificada por la Ley 21.719).")
NO_DISPONIBLE = "Ese paquete no está en la oferta"
INTERRUMPIDO = "\n   Interrumpido. Hasta luego."
PIDE_ID_DESTINO = "   Id del destino: "
PIDE_ID_PAQUETE = "   Id del paquete: "
PIDE_CORREO = "   Correo: "
PIDE_NOMBRE = "   Nombre: "
MI_CUENTA = "Mi cuenta"


class Cancelado(Exception):
    """El usuario escribió x en lugar del dato (RNF-USA-01). No hereda de ValueError a propósito:
    una lectura que reintenta ante un ValueError la confundiría con un dato mal escrito."""


class CerrarSesion(Exception):
    """El usuario pidió cerrar la sesión (RF-SEG-08)."""


class SesionCaducada(CerrarSesion):
    """Pasaron más de 10 minutos sin actividad, en el menú o dentro de una acción (RF-SEG-09)."""


# Plazo de la sesión abierta, en segundos de time.monotonic(). None: no hay sesión.
VENCE: float | None = None


def esperar(lectura, mensaje: str) -> str:
    """Toda espera de un dato pasa por aquí: si la sesión venció mientras esperaba, el dato no se
    usa. Antes solo se medía en el menú, y una pregunta abierta podía responderse horas después (H-11)."""
    global VENCE
    valor = lectura(mensaje)
    if VENCE is not None:
        if time.monotonic() > VENCE:
            raise SesionCaducada
        VENCE = time.monotonic() + INACTIVIDAD_MAXIMA
    return valor


def limpiar() -> None:
    # Secuencia ANSI: borra la pantalla sin abrir una shell ni buscar un programa en el PATH.
    print("\033[2J\033[H", end="")


# --- Entrada del usuario ---------------------------------------------------
# Toda lectura pasa por leer(): así «x» cancela en cualquier dato.

def leer(mensaje: str) -> str:
    valor = esperar(input, mensaje).strip()
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


# Un entero, con o sin separador de miles: 1050000 o 1.050.000, como la planilla. «2.5» no calza:
# antes se borraban todos los puntos y «2.5» personas se registraba como 25 (hallazgo 3).
ENTERO_CON_MILES = re.compile(r"\d{1,3}(?:\.\d{3})+", re.ASCII)


def pedir_entero(mensaje: str) -> int:
    while True:
        valor = leer(mensaje)
        if ENTERO_CON_MILES.fullmatch(valor):
            valor = valor.replace(".", "")
        # isdecimal y no isdigit: isdigit acepta caracteres como «²» que int() rechaza.
        if not valor.isdecimal():
            print("   ! Escriba un número entero, sin letras ni decimales.")
        elif len(valor) > 12 or int(valor) > MAXIMO_ENTERO:
            print(f"   ! Demasiado grande. El máximo es {MAXIMO_ENTERO:,}.".replace(",", "."))
        else:
            return int(valor)


def pedir_fecha(mensaje: str) -> date:
    while True:
        try:
            return datetime.strptime(leer(mensaje), "%d-%m-%Y").date()
        except ValueError:
            print("   ! Escriba la fecha como día-mes-año, por ejemplo 15-12-2026.")


def pedir_margen() -> int:
    """Enter deja el margen habitual de 20 % (RF-PAQ-11). Un margen mal escrito se vuelve a pedir,
    sin perder el resto del paquete ya ingresado."""
    while True:
        valor = leer(f"   Margen de operación en % (Enter = {MARGEN_PROPUESTO}): ")
        if not valor:
            return MARGEN_PROPUESTO
        if valor.isdecimal() and len(valor) <= 4:
            return int(valor)
        print("   ! El margen es un número entero de 0 a 1000, sin el signo %.")


def pedir_si_no(mensaje: str) -> bool:
    while True:
        valor = leer(mensaje + " (s/n): ").lower()
        if valor in ("s", "n"):
            return valor == "s"
        print("   ! Responda s o n.")


def pedir_clave(mensaje: str = "   Contraseña: ") -> str:
    clave = esperar(getpass.getpass, mensaje)
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


def pedir_paquete() -> Paquete:
    paquete = Paquete.buscar(pedir_entero(PIDE_ID_PAQUETE))
    if paquete is None:
        raise ValueError("No existe un paquete con ese id")
    return paquete


def pedir_destinos() -> list[Destino]:
    ids = leer("   Ids de los destinos, separados por coma (2 a 5): ").replace(" ", "").split(",")
    if not all(i.isdecimal() and len(i) < 10 for i in ids):
        raise ValueError("Escriba solo los números de los destinos, separados por coma")
    destinos = [Destino.buscar(int(i)) for i in ids]
    if None in destinos:
        raise ValueError("Uno de esos destinos no existe")
    return destinos


# --- Acciones sin sesión ---------------------------------------------------

def ver_oferta(_sesion: Usuario | None = None) -> None:
    """Los paquetes disponibles; se puede ver sin cuenta (S-09)."""
    paquetes = Paquete.listar_disponibles()
    print("\n   Paquetes disponibles")
    for paquete in paquetes:
        print(f"   {paquete}")
    if not paquetes:
        print("   (no hay paquetes disponibles)")


def registrarse() -> None:
    """Registro público: siempre crea un cliente (RF-SEG-12). Nada en pantalla permite elegir rol."""
    print("\n   Registro de cliente (escriba x para cancelar)")
    print(AVISO_DATOS)
    if not pedir_si_no("   ¿Acepta?"):
        raise Cancelado
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


# --- Acciones del administrador: paquetes y reservas -----------------------

def crear_paquete(sesion: Usuario) -> None:
    paquete = Paquete(pedir_texto(PIDE_NOMBRE), pedir_fecha("   Fecha de salida (dd-mm-aaaa): "),
                      pedir_fecha("   Fecha de regreso (dd-mm-aaaa): "),
                      pedir_entero("   Cupo máximo de personas: "), pedir_destinos(), pedir_margen())
    # RF-PAQ-04: el precio se muestra con el costo de cada destino antes de guardar.
    for destino in paquete.listar_destinos():
        print(f"     {destino}")
    print(f"   Precio por persona calculado: {pesos(paquete.calcular_precio())}")
    if not pedir_si_no("   ¿Guardar el paquete en borrador?"):
        raise Cancelado
    paquete.guardar(sesion)
    print(f"   Guardado en borrador: {paquete}")


def publicar_paquete(sesion: Usuario) -> None:
    paquete = pedir_paquete()
    print(f"   {paquete}")
    if not pedir_si_no("   ¿Publicarlo? El precio por persona queda fijo desde ahora (R7)"):
        raise Cancelado
    paquete.publicar(sesion)
    print(f"   Publicado: {paquete}")


def listar_paquetes(sesion: Usuario) -> None:
    paquetes = Paquete.listar_todos(sesion)
    print("\n   Todos los paquetes")
    for paquete in paquetes:
        print(f"   {paquete}")
    if not paquetes:
        print("   (sin paquetes)")


def editar_paquete(sesion: Usuario) -> None:
    """Solo en borrador (S-07): datos y, si se pide, los destinos."""
    paquete = pedir_paquete()
    print(f"   Actual: {paquete}")
    if paquete.estado() != "borrador":           # aviso temprano; el dominio lo vuelve a exigir
        raise ValueError("Solo se edita un paquete en borrador; uno publicado solo cambia su cupo")
    paquete.editar(pedir_texto(PIDE_NOMBRE), pedir_fecha("   Fecha de salida (dd-mm-aaaa): "),
                   pedir_fecha("   Fecha de regreso (dd-mm-aaaa): "), pedir_margen(), sesion)
    if pedir_si_no("   ¿Cambiar también los destinos?"):
        paquete.reemplazar_destinos(pedir_destinos(), sesion)
    print(f"   Guardado: {paquete}")


def cambiar_cupo(sesion: Usuario) -> None:
    paquete = pedir_paquete()
    print(f"   Actual: {paquete}")
    paquete.cambiar_cupo(pedir_entero("   Cupo máximo nuevo: "), sesion)
    print(f"   Guardado: {paquete}")


def eliminar_paquete(sesion: Usuario) -> None:
    paquete = pedir_paquete()
    print(f"   {paquete}")
    if not pedir_si_no("   ¿Eliminarlo?"):
        raise Cancelado
    paquete.eliminar(sesion)
    print("   Paquete eliminado.")


def reservas_de_paquete(sesion: Usuario) -> None:
    """RF-RES-11: nombre y correo de cada cliente; nunca RUT ni teléfono (S-16)."""
    paquete = pedir_paquete()
    reservas = Reserva.listar_por_paquete(paquete, sesion)
    print(f"\n   Reservas de: {paquete}")
    for reserva in reservas:
        print(f"   {reserva}")
    if not reservas:
        print("   (sin reservas)")


def respaldar(sesion: Administrador) -> None:
    ruta = sesion.respaldar_base()
    print(f"   Respaldo guardado en {ruta}.")
    print("   La clave de cifrado no va en el respaldo: respáldela aparte (ver README).")


def crear_socio(sesion: Administrador) -> None:
    nuevo = sesion.crear_administrador(pedir_texto("   Correo del socio: "), pedir_clave_nueva())
    print(f"   Cuenta de administrador creada para {nuevo.obtener_correo()}.")


# --- Acciones del cliente y de toda sesión ---------------------------------

def reservar(sesion: Cliente) -> None:
    ver_oferta()
    # «No existe» y «no está publicado» dan el mismo mensaje: un cliente no puede deducir los ids
    # de los paquetes en borrador (H-13). El dominio vuelve a revisar todo al reservar.
    paquete = Paquete.buscar(pedir_entero(PIDE_ID_PAQUETE))
    if paquete is None or not paquete.esta_disponible():
        raise ValueError(NO_DISPONIBLE)
    # RF-RES-10: advertir una segunda reserva en el mismo paquete (P-01, reservas duplicadas).
    if sesion.tiene_reserva_vigente(paquete) and not pedir_si_no(
            "   Ya tiene una reserva vigente en este paquete. ¿Reservar otra?"):
        raise Cancelado
    reserva = Reserva.reservar(paquete, pedir_entero("   Cantidad de personas: "), sesion)
    print(f"   Reserva confirmada por {pesos(reserva.obtener_total())}.")


def mis_reservas(sesion: Cliente) -> list[Reserva]:
    reservas = sesion.historial()
    print("\n   Mis reservas")
    for numero, reserva in enumerate(reservas, 1):
        print(f"   {numero:>2}) {reserva}")
    if not reservas:
        print("   (todavía no tiene reservas)")
    return reservas


def anular_reserva(sesion: Cliente) -> None:
    """Se elige por su número en la lista propia: no hay forma de nombrar una reserva ajena."""
    reservas = mis_reservas(sesion)
    if not reservas:
        return
    numero = pedir_entero("   Número de la reserva a anular: ")
    if not 1 <= numero <= len(reservas):
        raise ValueError("Ese número no está en la lista")
    reservas[numero - 1].anular(sesion)
    print("   Reserva anulada. Sus lugares vuelven al cupo del paquete.")


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
    ("Paquetes", "Listar todos los paquetes", "catalogo", listar_paquetes),
    ("Paquetes", "Crear un paquete", "catalogo", crear_paquete),
    ("Paquetes", "Publicar un paquete", "catalogo", publicar_paquete),
    ("Paquetes", "Editar un paquete en borrador", "catalogo", editar_paquete),
    ("Paquetes", "Cambiar el cupo de un paquete", "catalogo", cambiar_cupo),
    ("Paquetes", "Eliminar un paquete", "catalogo", eliminar_paquete),
    ("Paquetes", "Ver las reservas de un paquete", "ver_reservas", reservas_de_paquete),
    ("Cuentas", "Crear la cuenta de un socio", "cuentas", crear_socio),
    ("Cuentas", "Respaldar la base de datos", "respaldo", respaldar),
    ("Reservas", "Ver los paquetes disponibles", "reservar", ver_oferta),
    ("Reservas", "Reservar un paquete", "reservar", reservar),
    ("Reservas", "Mis reservas", "reservar", mis_reservas),
    ("Reservas", "Anular una reserva", "reservar", anular_reserva),
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
        esperar(input, "\n   Presione Enter para continuar...")
    except (KeyboardInterrupt, EOFError):
        return False
    return True


def usar_sesion(sesion: Usuario) -> bool:
    """El menú de una sesión. True: volver al inicio (cerró o caducó). False: salir del programa."""
    global VENCE
    opciones = opciones_de(sesion)
    VENCE = time.monotonic() + INACTIVIDAD_MAXIMA
    try:
        return recorrer_menu(sesion, opciones)
    except SesionCaducada:
        limpiar()                      # lo que quedó en pantalla no queda a la vista (H-11)
        print(SESION_CADUCADA)
        return True
    finally:
        VENCE = None


def recorrer_menu(sesion: Usuario, opciones: list[tuple]) -> bool:
    while True:
        mostrar_menu(sesion, opciones)
        try:
            eleccion = esperar(input, "\n   Opción: ").strip()
        except (KeyboardInterrupt, EOFError):
            return False
        resultado = ejecutar_opcion(eleccion, opciones, sesion)
        if resultado is not None:
            return resultado
        if not pausar():
            return False


def ejecutar_opcion(eleccion: str, opciones: list[tuple], sesion: Usuario) -> bool | None:
    """None: seguir en el menú. True: volver al inicio. False: salir del programa."""
    if eleccion == "0":
        return False
    # El largo va antes de int(): con más de 4.300 dígitos, int() lanza ValueError (H-12).
    if not (len(eleccion) <= 3 and eleccion.isdecimal() and 1 <= int(eleccion) <= len(opciones)):
        print("   ! Opción desconocida.")
        return None
    try:
        return None if atender(opciones[int(eleccion) - 1][3], sesion) else False
    except SesionCaducada:
        raise
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
        except PermissionError as error:       # otro equipo creó la primera cuenta (H-12)
            print(f"   ! {error}")
            return


def inicio() -> bool:
    """Pantalla sin sesión. False: salir del programa."""
    print("\n" + "=" * 66 + "\n   Viajes Aventura\n" + "=" * 66)
    print("   1. Iniciar sesión\n   2. Registrarme como cliente\n   3. Ver los paquetes disponibles"
          "\n   0. Salir")
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
    elif eleccion == "3":
        if not atender(ver_oferta, None):
            return False
    else:
        print("   ! Opción desconocida.")
    return True


def activar_ansi_en_windows() -> None:
    """La consola clásica de Windows muestra «←[2J» en vez de limpiar, salvo que se le pida
    interpretar las secuencias ANSI (Windows Terminal, macOS y Linux ya lo hacen)."""
    if os.name != "nt":
        return
    import ctypes                           # solo en Windows: API de la consola
    consola = ctypes.windll.kernel32
    salida = consola.GetStdHandle(-11)      # STD_OUTPUT_HANDLE
    modo = ctypes.c_uint32()
    if consola.GetConsoleMode(salida, ctypes.byref(modo)):   # falso si la salida no es una consola
        consola.SetConsoleMode(salida, modo.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING


def main() -> None:
    os.umask(0o077)       # la base, su diario y la clave nacen solo para su dueño (H-15)
    activar_ansi_en_windows()
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
    except Exception as error:
        # Último recurso: nunca una traza con rutas o datos (RNF-SEG-05, H-12).
        print(f"   ! Error inesperado ({type(error).__name__}). El programa se cierra.")


if __name__ == "__main__":
    main()
