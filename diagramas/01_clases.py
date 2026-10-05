"""Fig. · Diagrama de clases completo, con coordenadas fijas (svgkit), para una página ancha.

Los miembros y las relaciones se leen de clases.puml, que sigue siendo la única fuente del modelo
(y la que pruebas/verificar.py compara contra el código). Este script solo decide dónde va
cada caja: las relaciones dibujadas se comprueban contra las del .puml y, si no coinciden, falla.
Unidad = 1 pt impreso. Las firmas largas se envuelven en la misma caja («envolver antes que ensanchar»).
"""
import os
import re
import sys

from PIL import ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from svgkit import SVG, GRIS, AMARILLO, BORDE

AQUI = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(AQUI, "clases.puml"), encoding="utf-8").read()
FUENTE = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 100)
F, LH, W = 7.5, 9.3, 180          # letra de los miembros, interlineado y ancho de cada caja


def ancho(s, size=F):
    return FUENTE.getlength(s) * size / 100


# --- lectura del modelo -------------------------------------------------------------------------
CLASES = {}
actual = None                    # clase abierta; se lee línea por línea (una regex sobre todo el archivo es superlineal)
for linea in (l.strip() for l in SRC.splitlines()):
    if m := re.match(r"(abstract class|class|enum) (\w+) \{$", linea):
        tipo, nombre = m.groups()
        attrs, mets = [], []
        actual = CLASES[nombre] = (tipo, attrs, mets)
    elif linea == "}":
        actual = None
    elif actual and linea:
        estatico, abstracto = "{static}" in linea, "{abstract}" in linea
        texto = re.sub(r"\{(static|abstract)\} ", "", linea)
        texto = re.sub(r"^([-+#]) ", r"\1", texto)
        (mets if "(" in texto else attrs).append((texto, estatico, abstracto))

RELS = set()
for a, ma, flecha, mb, b in re.findall(r'^(\w+) (?:"([^"]+)" )?(\S+) (?:"([^"]+)" )?(\w+)', SRC, re.M):
    if "-" in flecha and "hidden" not in flecha and a in CLASES and b in CLASES:
        RELS.add((a, b))


def envolver(texto, w=W):
    """Parte una firma en renglones que caben en la caja, cortando después de una coma."""
    if ancho(texto) <= w - 10:
        return [texto]
    partes, renglones, actual = re.split(r"(?<=,) ", texto), [], ""
    for p in partes:
        prueba = f"{actual} {p}" if actual else p
        if actual and ancho(("    " if renglones else "") + prueba) > w - 10:
            renglones.append(actual)
            actual = p
        else:
            actual = prueba
    return renglones + [actual]


# --- dibujo ---------------------------------------------------------------------------------------
ALTO = 630
g = SVG(556, ALTO)
CAJAS = {}


def clase(nombre, x, y, fill=GRIS, w=W):
    tipo, attrs, mets = CLASES[nombre]
    abstracta, enum = tipo == "abstract class", tipo == "enum"
    cab = 16 + (9 if (abstracta or enum) else 0)
    filas_a = [(t, False, False, False) for t, _, _ in attrs]
    filas_m = []
    for t, est, abst in mets:
        for i, r in enumerate(envolver(t, w)):
            filas_m.append((r, est, abst, i > 0))
    ha = len(filas_a) * LH + 5
    hm = 0 if enum else len(filas_m) * LH + 5
    h = cab + ha + hm
    g.rect(x, y, w, h, fill=fill)
    if enum:
        g.text(x + w / 2, y + 10, "«enumeration»", 7, italic=True)
    g.text(x + w / 2, y + cab - 5, nombre, 8.5, bold=True, italic=abstracta)
    if abstracta:
        g.text(x + w / 2, y + 10, "{abstract}", 7, italic=True)
    g.path([(x, y + cab), (x + w, y + cab)], sw=0.7)
    for i, (t, *_rest) in enumerate(filas_a):
        g.text(x + 5, y + cab + 9.5 + i * LH, t, F, anchor="start")
    if not enum:
        g.path([(x, y + cab + ha), (x + w, y + cab + ha)], sw=0.7)
        for i, (t, est, abst, cont) in enumerate(filas_m):
            g.text(x + (13 if cont else 5), y + cab + ha + 9.5 + i * LH, t, F, anchor="start",
                   italic=abst, underline=est)
    CAJAS[nombre] = (x, y, w, h)
    return y + h


def paquete(x, y, w, h, nombre, fill="none"):
    tw = ancho(nombre, 7.8) + 12
    g.rect(x, y, tw, 12, fill="#eeeeee", sw=0.8)
    g.text(x + 5, y + 9, nombre, 7.8, anchor="start", bold=True)
    g.rect(x, y + 12, w, h - 12, fill=fill, sw=0.8)


def etiqueta(x, y, t, anchor="start", size=7.2):
    g.text(x, y, t, size, anchor=anchor, halo=True)


def sentido(x, y, hacia):
    """Triangulito negro que indica el sentido de lectura del nombre de la asociación."""
    d = {"der": f"M{x},{y-3} l5,3 l-5,3 Z", "abajo": f"M{x-3},{y} h6 l-3,5 Z",
         "arriba": f"M{x-3},{y+5} h6 l-3,-5 Z"}[hacia]
    g.el.append(f'<path d="{d}" fill="{BORDE}"/>')


# dos columnas: Cuentas y Reservas (izquierda), Catálogo (derecha)
XA, WA = 16, 244          # el margen izquierdo deja pasar la línea de la generalización
XC, WC = 296, 250

# Cuentas y acceso: Usuario, y debajo sus dos especializaciones
yu = clase("Usuario", XA, 24, w=WA)
ya = clase("Administrador", XA, yu + 30, w=WA)
yc = clase("Cliente", XA, ya + 16, w=WA)
paquete(4, 4, 262, yc + 10 - 4, "Cuentas y acceso")
xt = XA + WA / 2
yt = yu + 18                                           # tronco común de la generalización
g.path([(xt, CAJAS["Administrador"][1]), (xt, yu)], end="tri")
ym = CAJAS["Cliente"][1] + 30
g.path([(XA, ym), (9, ym), (9, yt), (xt, yt)])

# Reservas: Reserva a la derecha (para llegar derecho a Paquete) y su enumeración a la izquierda
yr0 = yc + 56
paquete(4, yr0 - 22, 262, ALTO - (yr0 - 22) - 4, "Reservas", fill="#fffdf3")
XR, WR = 90, 170
yr = clase("Reserva", XR, yr0, fill=AMARILLO, w=WR)
clase("EstadoReserva", XA, yr0 + 30, w=66)

# Catálogo: Destino arriba, Paquete abajo (así Paquete queda a la altura de Reserva)
n0 = len(g.el)
yd = clase("Destino", XC, 24, w=WC)
yp0 = yd + 46
yp = clase("Paquete", XC, yp0, fill=AMARILLO, w=WC)
n1 = len(g.el)
paquete(XC - 6, 4, 262, yp + 10 - 4, "Catálogo")
marco = g.el[n1:]                # el marco se dibuja al final porque su alto depende de Paquete,
del g.el[n1:]                    # pero va debajo de las cajas
g.el[n0:n0] = marco

# ReglaNegocioError, fuera de los módulos porque la lanzan todos, y su generalización desde Exception
yx0 = yp + 34
yx = clase("ReglaNegocioError", XC, yx0, w=130)
XE, WE = XC + 176, 74
g.rect(XE, yx0, WE, 25, fill="#ffffff")
g.text(XE + WE / 2, yx0 + 10, "«Python»", 7, italic=True)
g.text(XE + WE / 2, yx0 + 20, "Exception", 8.5, bold=True)
g.path([(XC + 130, yx0 + 12.5), (XE, yx0 + 12.5)], end="tri")

# Paquete 0..* ◇— 2..5 Destino «combina»: el rombo va en el todo (Paquete)
xg = XC + WC / 2
g.el.append(f'<path d="M{xg},{yp0} l4,-6 l-4,-6 l-4,6 Z" fill="#fff" stroke="{BORDE}" stroke-width="0.8"/>')
g.path([(xg, yp0 - 12), (xg, yd)])
etiqueta(xg + 6, yp0 - 4, "0..*"); etiqueta(xg + 6, yd + 10, "2..5")
etiqueta(xg - 10, (yd + yp0) / 2 + 3, "combina", "end"); sentido(xg - 6, (yd + yp0) / 2 - 7, "arriba")

# Cliente 1 — 0..* Reserva «realiza»: vertical, cruza el borde entre paquetes
xl = XR + WR / 2
g.path([(xl, yc), (xl, yr0)])
etiqueta(xl + 5, yc + 10, "1"); etiqueta(xl - 5, yr0 - 3, "0..*", "end")
etiqueta(xl - 6, yc + 24, "realiza", "end"); sentido(xl - 4, yc + 18, "abajo")

# Reserva 0..* — 1 Paquete «sobre»
yl = yr0 + 40
g.path([(XR + WR, yl), (XC, yl)])
etiqueta(XR + WR + 4, yl - 4, "0..*"); etiqueta(XC - 4, yl - 4, "1", "end")
etiqueta((XR + WR + XC) / 2 - 4, yl + 11, "sobre", "middle"); sentido((XR + WR + XC) / 2 + 10, yl + 8, "der")

DIBUJADAS = {("Usuario", "Cliente"), ("Usuario", "Administrador"), ("Cliente", "Reserva"),
             ("Paquete", "Destino"), ("Reserva", "Paquete")}
assert RELS == DIBUJADAS, f"el .puml y el dibujo no tienen las mismas relaciones: {RELS ^ DIBUJADAS}"

g.save(os.path.join(AQUI, "01_clases.svg"))
print("01_clases.svg:", {k: (round(v[1]), round(v[1] + v[3])) for k, v in CAJAS.items()})
