"""Primitivas mínimas para dibujar diagramas UML en SVG con coordenadas fijas.

Unidad = 1 pt en la página impresa (el SVG se inserta con el mismo ancho en pt),
así el tamaño de letra declarado es el que se imprime. Solo líneas ortogonales.
"""
from xml.sax.saxutils import escape

FONT = "Liberation Sans"
GRIS, BORDE, AMARILLO = "#f5f5f5", "#333333", "#fff6d6"
BOLA, SOCKET = 4, 7   # radio de la interfaz provista y del semicírculo requerido


class SVG:
    def __init__(self, w, h):
        self.w, self.h, self.el = w, h, []

    # --- texto -------------------------------------------------------------
    def text(self, x, y, s, size=9, anchor="middle", bold=False, italic=False, fill="#000", halo=False, underline=False):
        """Texto multilínea ('\n'); y es la línea base de la primera línea."""
        lines = s.split("\n")
        attrs = (f'font-family="{FONT}" font-size="{size}" text-anchor="{anchor}" fill="{fill}"'
                 + (' font-weight="bold"' if bold else '') + (' font-style="italic"' if italic else '')
                 + (' text-decoration="underline"' if underline else '')
                 + (' style="paint-order:stroke" stroke="#fff" stroke-width="2.6" stroke-linejoin="round"' if halo else ''))
        tsp = "".join(f'<tspan x="{x}" dy="{0 if i == 0 else size * 1.2}">{escape(l)}</tspan>'
                      for i, l in enumerate(lines))
        self.el.append(f'<text x="{x}" y="{y}" {attrs}>{tsp}</text>')

    def ctext(self, cx, cy, s, size=9, **k):
        """Texto centrado vertical y horizontalmente en (cx, cy)."""
        n = len(s.split("\n"))
        self.text(cx, cy - (n - 1) * size * 0.6 + size * 0.35, s, size, **k)

    # --- figuras -----------------------------------------------------------
    def rect(self, x, y, w, h, fill=GRIS, rx=0, dash=False, stroke=BORDE, sw=0.8):
        d = ' stroke-dasharray="4 3"' if dash else ''
        self.el.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def ellipse(self, cx, cy, rx, ry, fill=GRIS):
        self.el.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{BORDE}" stroke-width="0.8"/>')

    def circle(self, cx, cy, r, fill="#fff"):
        self.el.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{BORDE}" stroke-width="0.9"/>')

    def node3d(self, x, y, w, h, d=6, fill="#ffffff"):
        """Nodo UML (caja tridimensional)."""
        self.el.append(f'<path d="M{x},{y} l{d},{-d} h{w} v{h} l{-d},{d}" fill="#e9e9e9" stroke="{BORDE}" stroke-width="0.8"/>')
        self.el.append(f'<path d="M{x+w},{y} l{d},{-d}" stroke="{BORDE}" stroke-width="0.8" fill="none"/>')
        self.rect(x, y, w, h, fill=fill)

    def actor(self, cx, top, name, size=9, stereo=None):
        """Figura de palo UML con su nombre debajo."""
        s = BORDE
        self.circle(cx, top + 5, 5)
        self.el.append(f'<path d="M{cx},{top+10} v12 M{cx-9},{top+14} h18 M{cx},{top+22} l-7,10 M{cx},{top+22} l7,10" stroke="{s}" stroke-width="0.9" fill="none"/>')
        y = top + 43
        if stereo:
            self.text(cx, top - 4, stereo, size - 1, italic=True)
        self.text(cx, y, name, size)

    # --- líneas ------------------------------------------------------------
    def path(self, pts, dash=False, end=None, start=None, sw=0.8):
        """Polilínea ortogonal por los puntos dados.
        end/start: 'vee' (abierta), 'tri' (hueca), 'fill' (rellena), 'socket' (el último punto
        es el centro de la bola de la interfaz: la línea se detiene en el semicírculo que la abraza)."""
        pts = list(pts)
        if end == "socket":
            (x0, y0), (x1, y1) = pts[-2], pts[-1]
            dx, dy = (x1 > x0) - (x1 < x0), (y1 > y0) - (y1 < y0)
            r = SOCKET
            pts[-1] = (x1 - dx * r, y1 - dy * r)
            px, py = -dy, dx
            p1, p2 = (x1 - dx * 0 - px * r, y1 - py * r), (x1 + px * r, y1 + py * r)
            # arco centrado en la bola, abombado hacia la línea que llega
            sweep = 0 if (dx, dy) in ((1, 0), (0, -1)) else 1
            if (dx, dy) in ((0, 1),): sweep = 0
            if (dx, dy) in ((-1, 0),): sweep = 0
            self.el.append(f'<path d="M{p1[0]},{p1[1]} A{r},{r} 0 0 {sweep} {p2[0]},{p2[1]}" fill="none" stroke="{BORDE}" stroke-width="0.9"/>')
            end = None
        d = "M" + " L".join(f"{x},{y}" for x, y in pts)
        da = ' stroke-dasharray="4 3"' if dash else ''
        self.el.append(f'<path d="{d}" fill="none" stroke="{BORDE}" stroke-width="{sw}"{da}/>')
        if end:
            self._head(pts[-2], pts[-1], end)
        if start:
            self._head(pts[1], pts[0], start)

    def _head(self, a, b, kind):
        (x0, y0), (x1, y1) = a, b
        dx, dy = (x1 > x0) - (x1 < x0), (y1 > y0) - (y1 < y0)  # dirección ortogonal
        px, py = -dy, dx
        L, W = (6, 2.8) if kind == "fill" else (7, 3.5)
        bx, by = x1 - dx * L, y1 - dy * L
        if kind == "vee":
            self.el.append(f'<path d="M{bx+px*W},{by+py*W} L{x1},{y1} L{bx-px*W},{by-py*W}" fill="none" stroke="{BORDE}" stroke-width="0.9"/>')
        elif kind == "diamond":   # composición: rombo relleno en el extremo del todo
            mx, my = x1 - dx * 6, y1 - dy * 6
            ex, ey = x1 - dx * 12, y1 - dy * 12
            self.el.append(f'<path d="M{x1},{y1} L{mx+px*4},{my+py*4} L{ex},{ey} L{mx-px*4},{my-py*4} Z" fill="{BORDE}" stroke="{BORDE}" stroke-width="0.8"/>')
        elif kind in ("tri", "fill"):
            f = "#fff" if kind == "tri" else BORDE
            self.el.append(f'<path d="M{bx+px*W},{by+py*W} L{x1},{y1} L{bx-px*W},{by-py*W} Z" fill="{f}" stroke="{BORDE}" stroke-width="0.9"/>')

    def save(self, path):
        with open(path, "w") as f:
            f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}pt" height="{self.h}pt" '
                    f'viewBox="0 0 {self.w} {self.h}">\n<rect width="100%" height="100%" fill="#fff"/>\n'
                    + "\n".join(self.el) + "\n</svg>\n")
