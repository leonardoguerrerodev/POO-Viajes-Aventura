"""Recorre el menú real con respuestas fijas y guarda la sesión en docs/SALIDA_TERMINAL.md.

Reemplaza input() y getpass() por un guion, usa una base y una clave temporales, y falla si
la sesión muestra un Traceback o si el guion no se consume completo. Es la evidencia de que el
menú funciona de punta a punta con los dos roles.

    python herramientas/driver.py
"""

import builtins
import getpass
import io
import os
import sys
import tempfile
from contextlib import redirect_stdout
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import viajes  # noqa: E402

ENTER = ""
CAROLINA = "carolina@correo.cl"
ANA = "ana@viajes.cl"
SURIRE, FLAMENCOS = "Salar de Surire", "Flamencos y termas"
SALIDA = (date.today() + timedelta(days=30)).strftime("%d-%m-%Y")
REGRESO = (date.today() + timedelta(days=35)).strftime("%d-%m-%Y")
# Cada línea: lo que se teclea. Las contraseñas van por getpass y en la salida se ven como ••••.
# Menú del administrador: 1-6 destinos, 7-13 paquetes, 14 crear socio, 15 respaldo, 16 contraseña,
# 17 cerrar sesión.
# Menú del cliente: 1-4 reservas, 5-6 mis datos, 7 contraseña, 8 cerrar sesión.
GUION = [
    # Modo demostración (RNF-USA-04): base temporal con datos de ejemplo. El socio edita un destino
    # y publica el borrador eligiéndolos de la lista; la clienta reserva por sobre el cupo (R14).
    "2",
    "1", "3", "1", "Valle del Elqui", "Norte Chico", "Observación astronómica", "3", ENTER,
    "9", "3", "s", ENTER,
    "17",
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
    "14", "matias@viajes.cl", "clave-larga-de-matias", "clave-larga-de-matias", ENTER,
    "2", "Torres del Paine", "x", ENTER,
    "99", ENTER,
    "9" * 5000, ENTER,                 # H-12: int() con más de 4.300 dígitos ya no rompe el menú
    "15", ENTER,                       # respaldo de la base (RNF-FIA-03)
    "17",
    # Registro público de un cliente: el RUT con el dígito verificador malo se rechaza al
    # escribirlo, y se vuelve a pedir; una contraseña corta la rechaza el dominio.
    "2", "s", "Carolina Díaz", "12.345.678-6", "12.345.678-5", CAROLINA, "9 1234 5678",
    "corta", "corta",
    "2", "s", "Carolina Díaz", "12.345.678-5", CAROLINA, "9 1234 5678",
    "clave-de-carolina", "clave-de-carolina",
    # Contraseña errónea y correo inexistente: el mismo mensaje (RF-SEG-02).
    "1", CAROLINA, "clave-equivocada",
    "1", "nadie@correo.cl", "clave-equivocada",
    # Sesión de cliente: oferta, reserva, segunda reserva advertida, sobre el cupo, anulación.
    "1", CAROLINA, "clave-de-carolina",
    "1", ENTER,
    "2", "99", ENTER,                  # H-13: un id inexistente recibe el mismo mensaje
    "2", "1", "2.5", "2", ENTER,       # «2.5» personas se rechaza, no se lee como 25
    "2", "1", "n", ENTER,
    "2", "1", "s", "20", ENTER,
    "3", ENTER,
    "2", "1", "s", "1", ENTER,
    "4", "2", ENTER,
    "5", ENTER,
    "6", "Carolina Díaz Rojas", "987654321", ENTER,
    "8",
    # El administrador ve quién viaja: nombre y correo, sin RUT ni teléfono (RF-RES-11).
    "1", ANA, "clave-larga-de-ana",
    "13", "1", ENTER,
    "17",
    # Sin sesión también se ve la oferta (S-09).
    "3",
    "0",
]

# Lo que la sesión tiene que mostrar: si falta algo, el guion se desalineó con el menú.
ESPERADO = [
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
    "carolina@correo.cl (cliente)",
    "Reserva confirmada por $1.056.000.",
    "Ya tiene una reserva vigente en este paquete",
    "No hay cupo: quedan 8 lugares",
    "Reserva confirmada por $528.000.",
    "Reserva anulada.",
    "RUT:      12.***.***-5",
    "Teléfono: +56 9 **** 4321",
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
    os.environ.pop(viajes.VARIABLE_CLAVE, None)
    clave_original = viajes.RUTA_CLAVE
    try:
        with tempfile.TemporaryDirectory() as carpeta, redirect_stdout(salida):
            viajes.RUTA_CLAVE = Path(carpeta) / ".env"
            viajes.cifrador.cache_clear()
            viajes.usar_base(os.path.join(carpeta, "sesion.db"))
            import main
            main.main()
    finally:
        builtins.input, getpass.getpass = originales
        viajes.RUTA_CLAVE = clave_original
        viajes.cifrador.cache_clear()
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
    # H-11: también dentro de una acción. Se elige «crear socio» a tiempo, pero el correo llega
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
    """Cada menú se muestra completo la primera vez; las siguientes, como una línea."""
    vistos, partes = set(), texto.split("\033[2J\033[H")
    for i, parte in enumerate(partes[1:], 1):
        encabezado, _, resto = parte.partition("·  0. Salir\n" + "=" * 66 + "\n")
        titulo = next((l for l in encabezado.splitlines() if "Viajes Aventura ·" in l), "")
        if titulo in vistos:
            partes[i] = f"[pantalla limpia · menú de {titulo.split('·')[1].strip()}]\n" + resto
        else:
            vistos.add(titulo)
            partes[i] = "[pantalla limpia]\n" + parte
    return "".join(partes)


if __name__ == "__main__":
    sesion = ejecutar()
    assert sesion.count("Correo o contraseña incorrectos") == 2     # RF-SEG-02
    caducada = probar_inactividad()
    destino = RAIZ / "docs" / "SALIDA_TERMINAL.md"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text("# Sesión real del menú\n\nGenerada por `herramientas/driver.py` sobre una "
                       "base temporal, con datos ficticios (ningún nombre, RUT ni teléfono corresponde a una persona). "
                       "Las contraseñas se teclearon sin eco y aquí se ven como ••••."
                       "\n\n```text\n" + sesion + "```\n\n## Sesión que caduca por inactividad"
                       " (RF-SEG-09)\n\nEl reloj se adelanta 11 minutos mientras el menú espera.\n\n"
                       "```text\n" + caducada + "```\n", encoding="utf-8")
    print(f"OK: {destino.relative_to(RAIZ)} ({sesion.count(chr(10))} líneas)")
