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
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from cryptography.fernet import Fernet  # noqa: E402

import viajes  # noqa: E402

ENTER = ""
# Cada línea: lo que se teclea. Las contraseñas van por getpass y en la salida se ven como ••••.
GUION = [
    # Primer uso (S-04): la base no tiene cuentas.
    "ana@viajes.cl", "clave-larga-de-ana", "clave-larga-de-ana",
    # Inicio de sesión del administrador.
    "1", "ana@viajes.cl", "clave-larga-de-ana",
    "2", "Valle del Elqui", "Norte Chico", "Observación astronómica y pisco", "3", "120.000", ENTER,
    "2", "valle del  elqui", "Norte", "Repetido a propósito (R1)", "2", "1", ENTER,
    "2", "Salar de Surire", "Altiplano", "Flamencos y termas", "4", "0", ENTER,
    "2", "Salar de Surire", "Altiplano", "Flamencos y termas", "4", "310.000", ENTER,
    "4", "1", "130.000", ENTER,
    "1", "n", ENTER,
    "5", "2", "s", ENTER,
    "1", "s", ENTER,
    "7", "matias@viajes.cl", "clave-larga-de-matias", "clave-larga-de-matias", ENTER,
    "2", "Torres del Paine", "x", ENTER,
    "11", ENTER,
    "9",
    # Registro público de un cliente: el RUT con el dígito verificador malo se rechaza al
    # escribirlo, y se vuelve a pedir; una contraseña corta la rechaza el dominio.
    "2", "Carolina Díaz", "12.345.678-6", "12.345.678-5", "carolina@correo.cl", "9 1234 5678",
    "corta", "corta",
    "2", "Carolina Díaz", "12.345.678-5", "carolina@correo.cl", "9 1234 5678",
    "clave-de-carolina", "clave-de-carolina",
    # Contraseña errónea y correo inexistente: el mismo mensaje (RF-SEG-02).
    "1", "carolina@correo.cl", "clave-equivocada",
    "1", "nadie@correo.cl", "clave-equivocada",
    # Sesión de cliente: solo ve «Mi cuenta» (RNF-USA-03).
    "1", "carolina@correo.cl", "clave-de-carolina",
    "1", ENTER,
    "2", "Carolina Díaz Rojas", "987654321", ENTER,
    "4",
    "0",
]

# Lo que la sesión tiene que mostrar: si falta algo, el guion se desalineó con el menú.
ESPERADO = [
    "Ya existe un destino con ese nombre",
    "El costo base debe estar entre 1 y 100.000.000",
    "Eliminado del catálogo.",
    "Cuenta de administrador creada para matias@viajes.cl.",
    "Acción cancelada. No se guardó nada.",
    "Sesión cerrada.",
    "El RUT no es válido: revise el dígito verificador",
    "La contraseña debe tener entre 12 y 128 caracteres",
    "Cuenta creada para carolina@correo.cl.",
    "carolina@correo.cl (cliente)",
    "RUT:      12.***.***-5",
    "Teléfono: +56 9 **** 4321",
]


def ejecutar() -> str:
    pendientes = list(GUION)
    salida = io.StringIO()

    def teclear(mensaje: str = "", oculto: bool = False) -> str:
        if not pendientes:
            raise EOFError("el guion se acabó antes que la sesión")
        valor = pendientes.pop(0)
        print(f"{mensaje}{'••••' if oculto and valor else valor}")
        return valor

    originales = builtins.input, getpass.getpass
    builtins.input = lambda mensaje="": teclear(mensaje)
    getpass.getpass = lambda mensaje="Password: ", stream=None: teclear(mensaje, oculto=True)
    os.environ[viajes.VARIABLE_CLAVE] = Fernet.generate_key().decode()
    viajes.cifrador.cache_clear()
    try:
        with tempfile.TemporaryDirectory() as carpeta, redirect_stdout(salida):
            viajes.usar_base(os.path.join(carpeta, "sesion.db"))
            import main
            main.main()
    finally:
        builtins.input, getpass.getpass = originales
    texto = condensar(salida.getvalue())
    assert "Traceback" not in texto, "la sesión mostró un Traceback"
    assert not pendientes, f"quedaron {len(pendientes)} respuestas sin usar: {pendientes[:3]}"
    faltan = [e for e in ESPERADO if e not in texto]
    assert not faltan, f"la sesión no mostró: {faltan}"
    assert texto.count("Correo o contraseña incorrectos") == 2
    return texto


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
    destino = RAIZ / "docs" / "SALIDA_TERMINAL.md"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text("# Sesión real del menú\n\nGenerada por `herramientas/driver.py` sobre una "
                       "base temporal. Las contraseñas se teclearon sin eco y aquí se ven como ••••."
                       "\n\n```text\n" + sesion + "```\n", encoding="utf-8")
    print(f"OK: {destino.relative_to(RAIZ)} ({sesion.count(chr(10))} líneas)")
