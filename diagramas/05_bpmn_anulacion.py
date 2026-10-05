"""Fig. · BPMN 2.0 del proceso “Anular una reserva” (TO-BE), carriles Cliente y Sistema.

El vacío que el propio caso nombra (“qué ocurre cuando un cliente desiste”), resuelto por el supuesto
S-01: la reserva no se borra, queda anulada, y sus personas vuelven al cupo. La compuerta reúne las tres
condiciones que el sistema comprueba en la misma sentencia que anula: es del cliente (R11), está vigente
y su salida no ha llegado.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from svgkit import SVG
from bpmn import pool, evento, tarea, compuerta, flujo, TH, GD, R_EV, TW

g = SVG(470, 330)
XC, XS, XR = 101, 290, 414
pool(g, 4, 4, 462, 322, "Viajes Aventura · Anular una reserva (TO-BE)", [("Cliente", 150), ("Sistema", 292)])

Y = {"ini": 44, "c1": 88, "s1": 134, "c2": 180, "g1": 230, "s2": 280}
evento(g, XC, Y["ini"], "Desiste del viaje", lado="der")
tarea(g, XC, Y["c1"], "Ver mis reservas")
tarea(g, XS, Y["s1"], "Mostrar las reservas propias,\nnumeradas")
tarea(g, XC, Y["c2"], "Elegir la reserva\na anular")
compuerta(g, XS, Y["g1"], "¿Es suya, está vigente\ny su salida no llegó?\n(R11, S-01)")
tarea(g, XR, Y["g1"], "Informar por qué\nno se anula", w=86)
evento(g, XR, Y["g1"] + 44, "No se anula", fin=True)
tarea(g, XS, Y["s2"], "Marcarla anulada; sus personas\nvuelven al cupo (en una transacción)", w=160)
evento(g, XC, Y["s2"], "Reserva anulada", fin=True)

h = TH / 2
flujo(g, [(XC, Y["ini"] + R_EV), (XC, Y["c1"] - h)])
flujo(g, [(XC, Y["c1"] + h), (XC, Y["s1"]), (XS - TW / 2, Y["s1"])])
flujo(g, [(XS, Y["s1"] + h), (XS, Y["s1"] + 26), (XC, Y["s1"] + 26), (XC, Y["c2"] - h)])
flujo(g, [(XC, Y["c2"] + h), (XC, Y["g1"] - 30), (XS, Y["g1"] - 30), (XS, Y["g1"] - GD)])
flujo(g, [(XS + GD, Y["g1"]), (XR - 43, Y["g1"])], "no")
flujo(g, [(XR, Y["g1"] + h), (XR, Y["g1"] + 44 - R_EV)])
flujo(g, [(XS, Y["g1"] + GD), (XS, Y["s2"] - h)], "sí")
flujo(g, [(XS - 80, Y["s2"]), (XC + R_EV, Y["s2"])])

g.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "05_bpmn_anulacion.svg"))
