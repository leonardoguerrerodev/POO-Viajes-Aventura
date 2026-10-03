"""Primitivas BPMN 2.0 (ISO/IEC 19510) sobre svgkit: pool con carriles, eventos, tareas y compuertas.

Carriles verticales (el flujo baja), como la actividad del informe 4+1: en horizontal, once elementos no
caben en el ancho de una carta con letra legible. La norma admite pools en las dos orientaciones.
- evento de inicio: círculo de borde fino · evento de fin: círculo de borde grueso
- tarea: rectángulo redondeado · compuerta exclusiva: rombo con una X
- flujo de secuencia: línea continua con punta rellena
"""
from svgkit import SVG, GRIS, AMARILLO, BORDE

R_EV, TW, TH, GD = 9, 112, 30, 17   # radio de evento, ancho y alto de tarea, semidiagonal de la compuerta


def pool(g, x, y, w, h, titulo, carriles):
    """carriles: lista de (nombre, ancho). Banda del pool a la izquierda, encabezado de cada carril arriba."""
    g.rect(x, y, w, h, fill="#ffffff", sw=0.9)
    g.rect(x, y, 20, h, fill="#eeeeee", sw=0.9)
    g.el.append(f'<text transform="translate({x + 13},{y + h / 2}) rotate(-90)" font-family="Liberation Sans" '
                f'font-size="8.5" font-weight="bold" text-anchor="middle">{titulo}</text>')
    cx = x + 20
    for nombre, ancho in carriles:
        g.rect(cx, y, ancho, h, fill="none", sw=0.8)
        g.rect(cx, y, ancho, 18, fill="#f3f3f3", sw=0.8)
        g.text(cx + ancho / 2, y + 12.5, nombre, 8.5, bold=True)
        cx += ancho


def evento(g, cx, cy, etiqueta, fin=False, lado="abajo"):
    sw = 2.6 if fin else 1.0
    g.el.append(f'<circle cx="{cx}" cy="{cy}" r="{R_EV}" fill="#fff" stroke="{BORDE}" stroke-width="{sw}"/>')
    if lado == "abajo":
        g.text(cx, cy + R_EV + 10, etiqueta, 7.3)
    elif lado == "der":
        g.text(cx + R_EV + 4, cy + 3 - etiqueta.count("\n") * 4.4, etiqueta, 7.3, anchor="start")
    else:
        g.text(cx - R_EV - 4, cy + 3, etiqueta, 7.3, anchor="end")


def tarea(g, cx, cy, texto, w=TW, fill=GRIS):
    g.rect(cx - w / 2, cy - TH / 2, w, TH, fill=fill, rx=6)
    g.ctext(cx, cy, texto, 7.8)


def compuerta(g, cx, cy, pregunta, lado="izq"):
    d = GD
    g.el.append(f'<path d="M{cx},{cy-d} L{cx+d},{cy} L{cx},{cy+d} L{cx-d},{cy} Z" fill="{AMARILLO}" stroke="{BORDE}" stroke-width="0.9"/>')
    k = 5.5
    g.el.append(f'<path d="M{cx-k},{cy-k} L{cx+k},{cy+k} M{cx+k},{cy-k} L{cx-k},{cy+k}" stroke="{BORDE}" stroke-width="1.6"/>')
    lineas = pregunta.split("\n")
    y0 = cy - (len(lineas) - 1) * 4.5 + 3
    x = cx - d - 5 if lado == "izq" else cx + d + 5
    for i, l in enumerate(lineas):
        g.text(x, y0 + i * 9, l, 7.5, anchor="end" if lado == "izq" else "start", italic=True)


def flujo(g, pts, etiqueta=None, en=None):
    """Flujo de secuencia ortogonal con punta rellena; etiqueta («sí», «no») junto al punto en."""
    g.path(pts, end="fill", sw=0.9)
    if etiqueta:
        g.text(en[0], en[1], etiqueta, 7.5, anchor="start", italic=True, halo=True)
