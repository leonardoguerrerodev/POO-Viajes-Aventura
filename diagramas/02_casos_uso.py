"""Fig. · Diagrama de casos de uso, con coordenadas fijas (svgkit), como el del informe 4+1.

Disposición según Scott Ambler, *The Elements of UML 2.0 Style*: actor primario arriba a la izquierda y
todos los actores fuera del límite del sistema; casos de uso apilados en el orden en que ocurren;
asociaciones sin punta de flecha. Dos actores, como pide la guía del curso (Cliente y Administrador):
el actor es un rol, no una persona. La gestión de cada entidad es un solo caso («Gestionar destinos»),
no una elipse por operación CRUD. Cada caso que exige sesión la incluye con su propia flecha.
Cada caso lleva los RF que cumple; la tabla de la sección 2.1 repite esa asignación y trazabilidad.py
comprueba que todo RF funcional esté en algún caso de uso.
"""
import os
import sys

from PIL import ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from svgkit import SVG, AMARILLO, GRIS, BORDE

FUENTE = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 100)
g = SVG(484, 452)
RX, RY = 68, 20
XL, XR, XC = 140, 330, 235          # columna del cliente, del administrador y bus de «include»
Y = [118, 168, 218, 268, 318, 368]  # filas, en el orden en que ocurren


def cu(cx, cy, titulo, reqs, rx=RX, fill=GRIS):
    g.ellipse(cx, cy, rx, RY, fill=fill)
    lineas, rl = titulo.split("\n"), reqs.split("\n")
    n = len(lineas) + len(rl)
    y0 = cy - (n - 1) * 4.8 + 3
    for i, l in enumerate(lineas):
        assert FUENTE.getlength(l) * 8.3 / 100 < 2 * rx - 14, f"no cabe: {l}"
        g.text(cx, y0 + i * 9.6, l, 8.3, bold=True)
    for i, l in enumerate(rl):
        g.text(cx, y0 + (len(lineas) + i) * 9.6, l, 7.2)


# límite del sistema
g.rect(64, 14, 344, 430, fill="#ffffff")
g.text(236, 29, "Sistema de Viajes Aventura", 9, bold=True)

# arriba al centro, el caso que incluyen todos los que exigen sesión
YS = 62
cu(XC, YS, "CU-02 Iniciar sesión", "RF-SEG-01 a 03 · 05 · 08 · 09", rx=72)

# columna del cliente (orden temporal: registrarse, mirar, reservar, revisar)
cu(XL, Y[0], "CU-01 Registrarse", "RF-RES-01 a 03\nRF-SEG-04 · 12 · 13")
cu(XL, Y[1], "CU-03 Consultar paquetes", "RF-PAQ-06 · 07")
cu(XL, Y[2], "CU-04 Reservar paquete", "RF-RES-04 a 07 · 10", fill=AMARILLO)
cu(XL, Y[3], "CU-05 Ver mis reservas", "RF-RES-08 · RF-SEG-10")
cu(XL, Y[4], "CU-06 Anular reserva", "RF-RES-09")
cu(XL, Y[5], "CU-07 Actualizar mis datos", "RF-RES-12")
# columna del administrador
cu(XR, Y[0], "CU-09 Gestionar destinos", "RF-DES-01 a 10")
cu(XR, Y[1], "CU-10 Gestionar paquetes", "RF-PAQ-01 a 04 · 08 a 11")
cu(XR, Y[2], "CU-11 Publicar paquete", "RF-PAQ-05", fill=AMARILLO)
cu(XR, Y[3], "CU-12 Ver reservas\nde un paquete", "RF-RES-11 · RF-SEG-10")
cu(XR, Y[4], "CU-13 Crear\nadministrador", "RF-SEG-06 · 07")
# abajo al centro, el caso de los dos actores
YC = 418
cu(XC, YC, "CU-08 Cambiar contraseña", "RF-SEG-11 · 04", rx=72)

# «include» Iniciar sesión: una dependencia por caso, cada una con su punta (UML 2.5.1). Cada
# flecha sube por su propio carril y entra al borde inferior de CU-02; el carril de un caso más
# abajo queda más cerca del centro, para que ninguna vertical cruce una horizontal.
def borde_inferior(x):
    """Punto del borde inferior de la elipse de CU-02 sobre la vertical x."""
    return YS + 20 * (1 - ((x - XC) / 72) ** 2) ** 0.5


# Entre las dos columnas hay 54 pt (de x = 208 a 262): nueve carriles separados por 6 pt.
carriles = [(XL + RX, Y[2], XC - 25), (XL + RX, Y[3], XC - 19), (XL + RX, Y[5], XC - 13),
            (XR - RX, Y[0], XC + 25), (XR - RX, Y[1], XC + 19), (XR - RX, Y[2], XC + 13),
            (XR - RX, Y[3], XC + 7), (XR - RX, Y[4], XC + 1)]
for x0, y0, xc in carriles:
    g.path([(x0, y0), (xc, y0), (xc, borde_inferior(xc))], dash=True, end="vee")
XU = XC - 7                                     # CU-08 sube desde abajo por su propio carril
g.path([(XU, YC - 20 * (1 - ((XU - XC) / 72) ** 2) ** 0.5), (XU, borde_inferior(XU))], dash=True, end="vee")
g.text(XC - 36, YS + RY + 13, "«include»", 7.5, anchor="end", halo=True)

# «extend»: anular es opcional dentro de ver mis reservas (la flecha va al caso base)
g.path([(XL, Y[4] - RY), (XL, Y[3] + RY)], dash=True, end="vee")
g.text(XL + 4, (Y[3] + Y[4]) / 2 + 3, "«extend»", 7.5, anchor="start", halo=True)

# Cliente: arriba a la izquierda, con un bus ortogonal hacia sus casos
g.actor(30, 60, "Cliente")
BL = 50
g.path([(38, 80), (BL, 80)])
g.path([(BL, 80), (BL, YC)])
for k in (0, 1, 2, 3, 5):
    g.path([(BL, Y[k]), (XL - RX, Y[k])])
    g.circle(BL, Y[k], 1.4, fill=BORDE)
g.path([(BL, YC), (XC - 72, YC)])

# Administrador: a la derecha, mismo criterio
g.actor(456, 60, "Administrador", size=8.5)
BR = 422
g.path([(448, 80), (BR, 80)])
g.path([(BR, 80), (BR, YC)])
for k in (0, 1, 2, 3, 4):
    g.path([(BR, Y[k]), (XR + RX, Y[k])])
    g.circle(BR, Y[k], 1.4, fill=BORDE)
g.path([(BR, YC), (XC + 72, YC)])

g.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "02_casos_uso.svg"))
