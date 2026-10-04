"""Fig. · BPMN 2.0 del proceso «Reservar paquete» (TO-BE), carriles Cliente y Sistema.

Las dos compuertas son las dos fallas de la temporada que el caso separa en su «pista»: la fecha de
salida vencida (R15, 3 reservas) se compara contra la fecha del día, y el cupo (R14, 6 reservas) contra
un dato que el sistema lleva. Cada camino termina en su propio evento de fin. El cálculo del total advierte si el cliente ya tiene
una reserva vigente en ese paquete (RF-RES-10), y el cliente puede no confirmar.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from svgkit import SVG
from bpmn import pool, evento, tarea, compuerta, flujo, TH, GD, R_EV

g = SVG(470, 556)
XC, XS, XR = 101, 290, 414          # centro del carril Cliente, columna principal y columna de rechazos del Sistema
pool(g, 4, 4, 462, 548, "Viajes Aventura · Reservar paquete (TO-BE)", [("Cliente", 150), ("Sistema", 292)])

Y = {"ini": 44, "c1": 88, "s1": 134, "c2": 180, "s2": 226, "c3": 272, "g1": 322, "g2": 414, "s3": 474, "s4": 522}
evento(g, XC, Y["ini"], "Quiere viajar", lado="der")
tarea(g, XC, Y["c1"], "Iniciar sesión")
tarea(g, XS, Y["s1"], "Mostrar paquetes disponibles\ncon precio y cupo")
tarea(g, XC, Y["c2"], "Elegir paquete e\nindicar personas")
tarea(g, XS, Y["s2"], "Calcular el total y advertir si ya\ntiene una reserva vigente (RF-RES-10)", w=150)
tarea(g, XC, Y["c3"], "Revisar el total\ny confirmar")
compuerta(g, XC, Y["g1"], "¿Confirma?")
evento(g, XC, Y["g1"] + 52, "Reserva no realizada", fin=True)
compuerta(g, XS, Y["g1"], "¿La fecha de salida\nya llegó? (R15)")
tarea(g, XR, Y["g1"], "Informar fecha\nvencida", w=86)
evento(g, XR, Y["g1"] + 40, "Reserva rechazada", fin=True)
compuerta(g, XS, Y["g2"], "¿Las personas superan\nel cupo disponible? (R14)")
tarea(g, XR, Y["g2"], "Informar los\ncupos que quedan", w=86)
evento(g, XR, Y["g2"] + 40, "Reserva rechazada", fin=True)
tarea(g, XS, Y["s3"], "Guardar la reserva con su\ntotal fijo, en una transacción")
tarea(g, XS, Y["s4"], "Mostrar el comprobante")
evento(g, XC, Y["s4"], "Reserva registrada", fin=True)

h = TH / 2
flujo(g, [(XC, Y["ini"] + R_EV), (XC, Y["c1"] - h)])
flujo(g, [(XC, Y["c1"] + h), (XC, Y["s1"]), (XS - 56, Y["s1"])])
flujo(g, [(XS, Y["s1"] + h), (XS, Y["s1"] + 26), (XC, Y["s1"] + 26), (XC, Y["c2"] - h)])
flujo(g, [(XC, Y["c2"] + h), (XC, Y["s2"]), (XS - 75, Y["s2"])])
flujo(g, [(XS, Y["s2"] + h), (XS, Y["s2"] + 26), (XC, Y["s2"] + 26), (XC, Y["c3"] - h)])
flujo(g, [(XC, Y["c3"] + h), (XC, Y["g1"] - GD)])
# el cliente puede no confirmar (por ejemplo, tras la advertencia de reserva duplicada)
# entra por arriba a la compuerta de R15, para no cruzar su pregunta
flujo(g, [(XC + GD, Y["g1"]), (XC + 44, Y["g1"]), (XC + 44, Y["g1"] - 32), (XS, Y["g1"] - 32), (XS, Y["g1"] - GD)], "sí", (XC + GD + 3, Y["g1"] - 4))
flujo(g, [(XC, Y["g1"] + GD), (XC, Y["g1"] + 52 - R_EV)], "no", (XC + 4, Y["g1"] + GD + 11))
# R15
flujo(g, [(XS + GD, Y["g1"]), (XR - 43, Y["g1"])], "sí", (XS + GD + 3, Y["g1"] - 4))
flujo(g, [(XR, Y["g1"] + h), (XR, Y["g1"] + 40 - R_EV)])
flujo(g, [(XS, Y["g1"] + GD), (XS, Y["g2"] - GD)], "no", (XS + 4, Y["g1"] + GD + 11))
# R14
flujo(g, [(XS + GD, Y["g2"]), (XR - 43, Y["g2"])], "sí", (XS + GD + 3, Y["g2"] - 4))
flujo(g, [(XR, Y["g2"] + h), (XR, Y["g2"] + 40 - R_EV)])
flujo(g, [(XS, Y["g2"] + GD), (XS, Y["s3"] - h)], "no", (XS + 4, Y["g2"] + GD + 11))
flujo(g, [(XS, Y["s3"] + h), (XS, Y["s4"] - h)])
flujo(g, [(XS - 56, Y["s4"]), (XC + R_EV, Y["s4"])])

g.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "03_bpmn_reserva.svg"))
