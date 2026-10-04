"""Fig. · BPMN 2.0 del proceso «Armar y publicar paquete» (TO-BE), carriles Administrador y Sistema.

La primera compuerta junta las validaciones del paquete (R3, R5, R6 y R8) y, si falla, devuelve al
administrador a corregir: es el único ciclo del proceso. La segunda es la decisión de publicar, el
momento en que el precio deja de cambiar (R7): la causa de los 4 paquetes cobrados a otro precio. Al
publicar, el sistema vuelve a comprobar que la salida no haya llegado y que los destinos sigan disponibles.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from svgkit import SVG
from bpmn import pool, evento, tarea, compuerta, flujo, TH, GD, R_EV, TW

g = SVG(470, 512)
XC, XS, XR = 101, 290, 414
pool(g, 4, 4, 462, 504, "Viajes Aventura · Armar y publicar paquete (TO-BE)", [("Administrador", 150), ("Sistema", 292)])

Y = {"ini": 44, "a1": 90, "s1": 138, "g1": 190, "s2": 244, "s3": 290, "a2": 336, "g2": 388, "fin": 430,
     "g3": 420, "pub": 474}
evento(g, XC, Y["ini"], "Temporada\npor armar", lado="der")
tarea(g, XC, Y["a1"], "Ingresar nombre, fechas,\ncupo, margen y destinos")
tarea(g, XS, Y["s1"], "Validar los datos\ny los destinos")
compuerta(g, XS, Y["g1"], "¿2 a 5 destinos disponibles,\nfechas, cupo y margen\nválidos? (R3, R5, R6, R8)")
tarea(g, XR, Y["g1"], "Informar qué\ndato falla", w=86)
tarea(g, XS, Y["s2"], "Calcular el precio por persona\n(suma de costos más margen)")
tarea(g, XS, Y["s3"], "Guardar el paquete\nen borrador")
tarea(g, XC, Y["a2"], "Revisar el precio\ncalculado")
compuerta(g, XC, Y["g2"], "¿Publicar\nahora?")
compuerta(g, XS, Y["g3"], "¿La salida todavía no llega\ny sus destinos siguen\ndisponibles? (R15, R8)")
tarea(g, XR, Y["g3"], "Informar por qué\nno se publica", w=86)
evento(g, XR, Y["g3"] + 44, "Sigue en borrador", fin=True)
tarea(g, XS, Y["pub"], "Fijar el precio y\npublicar (R7)")
evento(g, XC, Y["fin"] + 6, "Queda en\nborrador", fin=True, lado="der")
evento(g, XS - TW / 2 - 32, Y["pub"], "Paquete publicado", fin=True)

h = TH / 2
flujo(g, [(XC, Y["ini"] + R_EV), (XC, Y["a1"] - h)])
flujo(g, [(XC, Y["a1"] + h), (XC, Y["s1"]), (XS - TW / 2, Y["s1"])])
flujo(g, [(XS, Y["s1"] + h), (XS, Y["g1"] - GD)])
flujo(g, [(XS + GD, Y["g1"]), (XR - 43, Y["g1"])], "no", (XS + GD + 3, Y["g1"] - 4))
flujo(g, [(XR, Y["g1"] - h), (XR, Y["a1"] - 22), (XC + 30, Y["a1"] - 22), (XC + 30, Y["a1"] - h)])  # vuelve a corregir
flujo(g, [(XS, Y["g1"] + GD), (XS, Y["s2"] - h)], "sí", (XS + 4, Y["g1"] + GD + 11))
flujo(g, [(XS, Y["s2"] + h), (XS, Y["s3"] - h)])
flujo(g, [(XS, Y["s3"] + h), (XS, Y["s3"] + 24), (XC, Y["s3"] + 24), (XC, Y["a2"] - h)])
flujo(g, [(XC, Y["a2"] + h), (XC, Y["g2"] - GD)])
flujo(g, [(XC + GD, Y["g2"]), (XS, Y["g2"]), (XS, Y["g3"] - GD)], "sí", (XC + GD + 3, Y["g2"] - 4))
flujo(g, [(XS + GD, Y["g3"]), (XR - 43, Y["g3"])], "no", (XS + GD + 3, Y["g3"] - 4))
flujo(g, [(XR, Y["g3"] + TH / 2), (XR, Y["g3"] + 44 - R_EV)])
flujo(g, [(XS, Y["g3"] + GD), (XS, Y["pub"] - TH / 2)], "sí", (XS + 4, Y["g3"] + GD + 11))
flujo(g, [(XC, Y["g2"] + GD), (XC, Y["fin"] + 6 - R_EV)], "no", (XC + 4, Y["g2"] + GD + 11))
flujo(g, [(XS - TW / 2, Y["pub"]), (XS - TW / 2 - 32 + R_EV, Y["pub"])])

g.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "04_bpmn_paquete.svg"))
