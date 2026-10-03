"""Compara el diagrama de clases (diagramas/clases.puml) con el código (viajes.py).

Para cada clase del diagrama comprueba, leyendo el código con `ast` (sin ejecutarlo):
  - que la clase exista y herede de lo que el diagrama dice;
  - cada atributo: un `self.__nombre` privado asignado en la clase;
  - cada método: mismo nombre (camelCase en el diagrama, snake_case en el código), mismos
    parámetros y en el mismo orden, y la marca {static} o {abstract} cuando la tiene;
  - que el código no tenga métodos públicos que el diagrama no dibuja.
Un atributo con el nombre de una clase asociada (paquete, destinos) es el extremo de una asociación
del diagrama, y se acepta solo si esa asociación existe.
No se dibujan, por convención: el constructor, los métodos especiales de Python (__str__,
__repr__) y los auxiliares que empiezan con guion bajo (lectura de filas, INSERT común).

    python herramientas/uml_vs_codigo.py      -> «0 diferencias» o la lista, con código de salida 1
"""

import ast
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def snake(nombre: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", nombre).lower()


def leer_diagrama(texto: str) -> dict:
    """{clase: {"tipo", "padre", "atributos": {...}, "metodos": {nombre: (params, static, abstract)}}}"""
    clases, actual = {}, None
    for linea in (l.strip() for l in texto.splitlines()):
        if m := re.match(r"(abstract class|class|enum) (\w+) \{$", linea):
            actual = clases[m.group(2)] = {"tipo": m.group(1), "padre": None,
                                           "atributos": set(), "metodos": {}}
        elif linea == "}":
            actual = None
        elif actual is not None and linea and actual["tipo"] != "enum":
            static, abstract = "{static}" in linea, "{abstract}" in linea
            sin_marcas = re.sub(r"\{(static|abstract)\} ", "", linea)
            protegido, firma = sin_marcas[0] == "#", sin_marcas[2:]
            if m := re.match(r"(\w+)\((.*)\)", firma):
                params = tuple(snake(p.split(":")[0].strip()) for p in m.group(2).split(",")
                               if p.strip())
                # «#» protegido en el diagrama = un guion bajo en Python
                nombre = ("_" if protegido else "") + snake(m.group(1))
                actual["metodos"][nombre] = (params, static, abstract)
            else:
                actual["atributos"].add(snake(firma.split(":")[0].strip()))
        elif actual is not None and linea:
            actual["atributos"].add(linea)              # valores de la enumeración
        if m := re.match(r"(\w+) <\|-+\w*-* (\w+)$", linea):
            if m.group(2) in clases:
                clases[m.group(2)]["padre"] = m.group(1)
    # las generalizaciones pueden estar después de las clases
    for padre, hija in re.findall(r"^(\w+) <\|-+\w*-* (\w+)$", texto, re.M):
        if hija in clases:
            clases[hija]["padre"] = padre
    # asociaciones y agregaciones: cada extremo puede ser un atributo de la otra clase
    for a, flecha, b in re.findall(r'^(\w+) (?:"[^"]+" )?(\S+) (?:"[^"]+" )?(\w+)', texto, re.M):
        if "<|" not in flecha and "hidden" not in flecha and a in clases and b in clases:
            clases[a].setdefault("asociadas", set()).update({snake(b), snake(b) + "s"})
            clases[b].setdefault("asociadas", set()).update({snake(a), snake(a) + "s"})
    return clases


def leer_codigo(texto: str) -> dict:
    clases = {}
    for nodo in ast.parse(texto).body:
        if not isinstance(nodo, ast.ClassDef):
            continue
        metodos, atributos, valores, publicos = {}, set(), set(), set()
        for hijo in nodo.body:
            if isinstance(hijo, ast.FunctionDef):
                decoradores = {getattr(d, "id", getattr(d, "attr", "")) for d in hijo.decorator_list}
                params = tuple(a.arg for a in hijo.args.args + hijo.args.kwonlyargs
                               if a.arg not in ("self", "cls"))
                static = bool(decoradores & {"staticmethod", "classmethod"})
                metodos[hijo.name] = (params, static, "abstractmethod" in decoradores)
            elif isinstance(hijo, ast.Assign):
                valores |= {t.id for t in hijo.targets if isinstance(t, ast.Name)}
        for sub in ast.walk(nodo):
            # self.__x se guarda mangled como atributo «__x» en el árbol: se toma tal cual.
            if (isinstance(sub, ast.Attribute) and isinstance(sub.ctx, ast.Store)
                    and isinstance(sub.value, ast.Name) and sub.value.id == "self"):
                if sub.attr.startswith("__"):
                    atributos.add(sub.attr[2:])
                elif not sub.attr.startswith("_"):
                    publicos.add(sub.attr)          # rompe el encapsulamiento del modelo
        padres = [getattr(b, "id", getattr(b, "attr", "")) for b in nodo.bases]
        clases[nodo.name] = {"padres": padres, "metodos": metodos, "atributos": atributos,
                             "valores": valores, "publicos": publicos}
    return clases


def comparar(diagrama: dict, codigo: dict) -> list[str]:
    difs = []
    for clase, d in diagrama.items():
        c = codigo.get(clase)
        if c is None:
            difs.append(f"{clase}: está en el diagrama y no en el código")
            continue
        if d["padre"] and d["padre"] not in c["padres"]:
            difs.append(f"{clase}: el diagrama dice que hereda de {d['padre']}, el código de {c['padres']}")
        if d["tipo"] == "enum":
            faltan = d["atributos"] - c["valores"]
            difs += [f"{clase}: falta el valor {v}" for v in sorted(faltan)]
            continue
        difs += [f"{clase}: falta el atributo privado {a}" for a in sorted(d["atributos"] - c["atributos"])]
        difs += [f"{clase}: atributo público {a}; el modelo los declara privados"
                 for a in sorted(c["publicos"])]
        difs += [f"{clase}: atributo privado {a} que el diagrama no dibuja"
                 for a in sorted(c["atributos"] - d["atributos"] - d.get("asociadas", set()))]
        for nombre, (params, static, abstract) in d["metodos"].items():
            if nombre not in c["metodos"]:
                difs.append(f"{clase}: falta el método {nombre}()")
                continue
            cp, cs, ca = c["metodos"][nombre]
            if cp != params:
                difs.append(f"{clase}.{nombre}: parámetros {params} en el diagrama, {cp} en el código")
            if cs != static:
                difs.append(f"{clase}.{nombre}: {'' if static else 'no '}es de clase en el diagrama")
            if ca != abstract:
                difs.append(f"{clase}.{nombre}: {'' if abstract else 'no '}es abstracto en el diagrama")
        publicos = {m for m in c["metodos"] if not m.startswith("_")}
        difs += [f"{clase}: método público {m}() que el diagrama no dibuja"
                 for m in sorted(publicos - set(d["metodos"]))]
    return difs


if __name__ == "__main__":
    diagrama = leer_diagrama((RAIZ / "diagramas" / "clases.puml").read_text(encoding="utf-8"))
    codigo = leer_codigo((RAIZ / "viajes.py").read_text(encoding="utf-8"))
    difs = comparar(diagrama, codigo)
    miembros = sum(len(d["atributos"]) + len(d["metodos"]) for d in diagrama.values())
    for d in difs:
        print(f"  ✘ {d}")
    print(f"{len(diagrama)} clases y {miembros} miembros comparados: {len(difs)} diferencias")
    sys.exit(1 if difs else 0)
