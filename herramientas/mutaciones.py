"""Pruebas de mutación: rompe a propósito una regla por vez y comprueba que alguna prueba lo detecta.

Cada mutación cambia un fragmento exacto del código en una copia temporal del proyecto y corre las
pruebas indicadas. Si ninguna falla, la regla está desprotegida y el script termina con código 1.
Así, «cada corrección tiene una prueba que la vigila» es una afirmación que cualquiera puede repetir.

    python herramientas/mutaciones.py
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
VIAJES, MENU = "viajes.py", "main.py"
AV, DR, PR = VIAJES, "herramientas/driver.py", "pruebas/prueba_rubrica.py"

# (regla, archivo, fragmento original, fragmento roto, pruebas que deben detectarlo)
MUTACIONES = [
    # Reglas del negocio
    ("R1 nombre sin normalizar tildes", VIAJES,
     "if not unicodedata.combining(c))", "if True)", [AV]),
    ("R8 borra el destino aunque esté en un paquete", VIAJES,
     'if en_paquete:\n                con.execute("UPDATE', 'if False:\n                con.execute("UPDATE', [AV]),
    ("R7 publicar no fija el precio", VIAJES,
     'cur = con.execute("UPDATE paquete SET publicado = 1, precio_por_persona = ?"',
     'cur = con.execute("UPDATE paquete SET publicado = 1, precio_por_persona = ? * 0 + NULL"', [AV]),
    ("R6 precio con float", VIAJES,
     "return (suma * (100 + self.__margen) + 50) // 100",
     "return int(suma * (1 + self.__margen / 100) * 0.999)", [AV]),
    ("R14 las anuladas descuentan cupo", VIAJES,
     "WHERE paquete_id = ? AND estado = 'VIGENTE'\", (self.__id,)).fetchone()[0]",
     "WHERE paquete_id = ?\", (self.__id,)).fetchone()[0]", [AV]),
    ("R15 se reserva el mismo día de salida", VIAJES,
     'if date.fromisoformat(fila["fecha_salida"]) <= hoy:',
     'if date.fromisoformat(fila["fecha_salida"]) < hoy:', [AV]),
    ("RNF-FIA-02 sin BEGIN IMMEDIATE", VIAJES,
     '        con.execute("BEGIN IMMEDIATE")\n        try:\n            yield con',
     '        con.execute("BEGIN")\n        try:\n            yield con', [AV]),
    ("H-09 techo antiguo del total", VIAJES,
     'self.__total = entero(total, "El total", 1, PRECIO_MAXIMO * CUPO_MAXIMO, "R13")',
     'self.__total = entero(total, "El total", 1, COSTO_MAXIMO * CUPO_MAXIMO, "R13")', [AV]),
    ("RF-PAQ-09 borra un paquete con reservas", VIAJES,
     '"DELETE FROM paquete WHERE id = ? AND NOT EXISTS"\n                              " (SELECT 1 FROM reserva WHERE paquete_id = ?)", (self.__id, self.__id)',
     '"DELETE FROM reserva WHERE paquete_id = ?", (self.__id,))\n'
     '            cur = con.execute("DELETE FROM paquete WHERE id = ?", (self.__id,)', [AV]),
    # Cuentas, autenticación y permisos
    ("RF-SEG-03 bloqueo tras 6 fallos", VIAJES, "MAX_INTENTOS = 5", "MAX_INTENTOS = 6", [AV]),
    ("RF-SEG-05 el cliente puede tocar el catálogo", VIAJES,
     'return accion == "reservar"', "return True", [AV]),
    ("Hallazgo 5 permiso sin sesión iniciada", VIAJES,
     "if (not isinstance(solicitante, Usuario) or not solicitante.tiene_sesion()",
     "if (not isinstance(solicitante, Usuario)", [AV]),
    ("H-10 cambiar la clave sin comparar el hash", VIAJES,
     '"UPDATE usuario SET hash_clave = ? WHERE id = ? AND hash_clave = ?",\n'
     '                              (nuevo_hash, self.__id, self.__hash_clave)',
     '"UPDATE usuario SET hash_clave = ? WHERE id = ?",\n                              (nuevo_hash, self.__id)', [AV]),
    ("H-16 sin lista de contraseñas comunes", VIAJES,
     "if clave.casefold() in CLAVES_COMUNES or len(set(clave)) < CLAVE_DISTINTOS:", "if False:", [AV]),
    ("H-17 bloqueo con hora local", VIAJES,
     "        ahora = datetime.now(timezone.utc)\n        with conectar() as con:\n            hasta",
     "        ahora = datetime.now()\n        with conectar() as con:\n            hasta", [AV]),
    # Datos personales y cifrado
    ("H-14 acepta el RUT 0", VIAJES, "if int(cuerpo) == 0:", "if False:", [AV]),
    ("H-04/05 descifrar al leer de la base", VIAJES,
     'return Cliente(fila["nombre"], fila["rut_cifrado"], fila["correo"],\n'
     '                       fila["telefono_cifrado"], cifrado=True, **cuenta)',
     'return Cliente(fila["nombre"], descifrar(fila["rut_cifrado"]), fila["correo"],\n'
     '                       descifrar(fila["telefono_cifrado"]), **cuenta)', [AV]),
    ("K-05 la clave exige «sin usuarios»", VIAJES,
     'con.execute("SELECT 1 FROM usuario WHERE rut_cifrado IS NOT NULL LIMIT 1"',
     'con.execute("SELECT 1 FROM usuario LIMIT 1"', [AV, DR]),
    ("H-01 clave dentro del proyecto", VIAJES,
     'RUTA_CLAVE = Path.home() / ".config" / "viajes-aventura" / "clave.env"',
     'RUTA_CLAVE = Path(__file__).with_name(".env")', [PR]),
    # Persistencia y consistencia
    ("K-04 historial con el id equivocado", VIAJES,
     'SQL_DE_CLIENTE = ("SELECT r.id AS reserva_id', 'SQL_DE_CLIENTE = ("SELECT r.id, r.id AS reserva_id', [AV]),
    ("H-02 reserva sin registro de auditoría", VIAJES,
     '            registrar_evento(con, solicitante.obtener_id(), "reserva.crear",',
     '            (lambda *a: None)(con, solicitante.obtener_id(), "reserva.crear",', [AV]),
    ("Hallazgo 4 editar deja el objeto a medias", VIAJES,
     '        autorizar(solicitante, "catalogo")\n        datos = self.__validar_datos(nombre, zona, descripcion, duracion_dias)',
     '        autorizar(solicitante, "catalogo")\n        self.__nombre = nombre\n'
     '        datos = self.__validar_datos(nombre, zona, descripcion, duracion_dias)', [AV]),
    ("Hallazgo 20 escritura sin revisar rowcount", VIAJES,
     "    if cur.rowcount != 1:\n        raise ValueError(f\"El {que} ya no existe",
     "    if False:\n        raise ValueError(f\"El {que} ya no existe", [AV]),
    # Menú
    ("Hallazgo 3 «2.5» personas se lee como 25", MENU,
     "        valor = leer(mensaje)\n        if ENTERO_CON_MILES.fullmatch(valor):",
     "        valor = leer(mensaje).replace(\".\", \"\")\n        if ENTERO_CON_MILES.fullmatch(valor):", [DR]),
    ("H-11 plazo de inactividad solo en el menú", MENU,
     "        if time.monotonic() > VENCE:\n            raise SesionCaducada",
     "        if False:\n            raise SesionCaducada", [DR]),
    ("H-12 int() sin límite de largo", MENU,
     "if not (len(eleccion) <= 3 and eleccion.isdecimal()", "if not (eleccion.isdecimal()", [DR]),
    ("RNF-USA-04 la demostración escribe en la base real", MENU,
     'viajes.usar_base(os.path.join(carpeta, "demostracion.db"))', "pass", [PR]),
    ("H-13 mensajes distintos para «no existe» y «no publicado»", MENU,
     "    if paquete is None or not paquete.esta_disponible():\n        raise ValueError(NO_DISPONIBLE)",
     "    if paquete is None:\n        raise ValueError('No existe')", [DR]),
]


def probar(nombre: str, archivo: str, original: str, roto: str, pruebas: list[str]) -> bool:
    """True si al menos una de las pruebas falla con la mutación puesta."""
    with tempfile.TemporaryDirectory() as carpeta:
        copia = Path(carpeta)
        for parte in (VIAJES, MENU, "herramientas", "pruebas", "diagramas", ".gitignore"):
            origen = RAIZ / parte
            (shutil.copytree if origen.is_dir() else shutil.copy)(origen, copia / parte)
        texto = (copia / archivo).read_text(encoding="utf-8")
        if texto.count(original) != 1:
            raise SystemExit(f"«{nombre}»: el fragmento original ya no está en {archivo}; actualice la mutación")
        (copia / archivo).write_text(texto.replace(original, roto), encoding="utf-8")
        for prueba in pruebas:
            r = subprocess.run([sys.executable, prueba], cwd=copia, capture_output=True, text=True,
                               timeout=300)
            if r.returncode != 0:
                return True
    return False


if __name__ == "__main__":
    vivas = []
    for nombre, archivo, original, roto, pruebas in MUTACIONES:
        detectada = probar(nombre, archivo, original, roto, pruebas)
        print(f"  {'detectada' if detectada else 'VIVA     '} {nombre}")
        if not detectada:
            vivas.append(nombre)
    print(f"{len(MUTACIONES) - len(vivas)} de {len(MUTACIONES)} mutaciones detectadas")
    sys.exit(1 if vivas else 0)
