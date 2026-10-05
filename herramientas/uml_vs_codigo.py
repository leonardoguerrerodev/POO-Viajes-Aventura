"""Compara el diagrama de clases (diagramas/clases.puml) con el código (viajes.py).

Para cada clase del diagrama comprueba, leyendo el código con `ast` (sin ejecutarlo):
  - que la clase exista y herede de lo que el diagrama dice;
  - cada atributo: un `self.__nombre` privado asignado en la clase, y ningún atributo público;
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


# --- Diagrama ----------------------------------------------------------------

def leer_miembro(clase: dict, linea: str) -> None:
    """Una línea del cuerpo de una clase: atributo («- correo: str») o método («+ puede(...)»)."""
    if clase["tipo"] == "enum":
        clase["atributos"].add(linea)                       # valores de la enumeración
        return
    static, abstract = "{static}" in linea, "{abstract}" in linea
    sin_marcas = re.sub(r"\{(static|abstract)\} ", "", linea)
    protegido, firma = sin_marcas[0] == "#", sin_marcas[2:]
    nombre, abre, resto = firma.partition("(")
    if not abre:
        clase["atributos"].add(snake(nombre.split(":")[0].strip()))
        return
    lista = resto.rpartition(")")[0]
    params = tuple(snake(p.split(":")[0].strip()) for p in lista.split(",") if p.strip())
    # «#» protegido en el diagrama = un guion bajo en Python
    clase["metodos"][("_" if protegido else "") + snake(nombre)] = (params, static, abstract)


def leer_relacion(clases: dict, linea: str) -> None:
    """«A <|-- B» es herencia; cualquier otra flecha entre dos clases, una asociación."""
    partes = re.sub(r'"[^"]*"', " ", linea).split()        # sin las multiplicidades
    if len(partes) < 3 or partes[2] not in clases:
        return
    a, flecha, b = partes[:3]
    if "-" not in flecha or "hidden" in flecha:
        return
    if flecha.startswith("<|"):
        clases[b]["padre"] = a                              # el padre puede ser Exception
    elif a in clases:
        clases[a]["asociadas"] |= {snake(b), snake(b) + "s"}
        clases[b]["asociadas"] |= {snake(a), snake(a) + "s"}


def leer_diagrama(texto: str) -> dict:
    clases, actual, relaciones = {}, None, []
    for linea in (l.strip() for l in texto.splitlines()):
        if m := re.match(r"(abstract class|class|enum) (\w+) \{$", linea):
            actual = clases[m.group(2)] = {"tipo": m.group(1), "padre": None, "atributos": set(),
                                           "metodos": {}, "asociadas": set()}
        elif linea == "}":
            actual = None
        elif actual is not None and linea:
            leer_miembro(actual, linea)
        elif actual is None:
            relaciones.append(linea)
    for linea in relaciones:                                 # después: ya están todas las clases
        leer_relacion(clases, linea)
    return clases


# --- Código ------------------------------------------------------------------

def leer_metodo(funcion: ast.FunctionDef) -> tuple:
    decoradores = {getattr(d, "id", getattr(d, "attr", "")) for d in funcion.decorator_list}
    params = tuple(a.arg for a in funcion.args.args + funcion.args.kwonlyargs
                   if a.arg not in ("self", "cls"))
    return params, bool(decoradores & {"staticmethod", "classmethod"}), "abstractmethod" in decoradores


def atributos_asignados(nodo: ast.ClassDef) -> tuple[set, set]:
    """(privados, públicos) asignados como self.x. self.__x llega al árbol sin el mangling."""
    privados, publicos = set(), set()
    for sub in ast.walk(nodo):
        if not (isinstance(sub, ast.Attribute) and isinstance(sub.ctx, ast.Store)
                and isinstance(sub.value, ast.Name) and sub.value.id == "self"):
            continue
        if sub.attr.startswith("__"):
            privados.add(sub.attr[2:])
        elif not sub.attr.startswith("_"):
            publicos.add(sub.attr)
    return privados, publicos


def leer_codigo(texto: str) -> dict:
    clases = {}
    for nodo in (n for n in ast.parse(texto).body if isinstance(n, ast.ClassDef)):
        metodos = {f.name: leer_metodo(f) for f in nodo.body if isinstance(f, ast.FunctionDef)}
        valores = {t.id for a in nodo.body if isinstance(a, ast.Assign)
                   for t in a.targets if isinstance(t, ast.Name)}
        privados, publicos = atributos_asignados(nodo)
        clases[nodo.name] = {"padres": [getattr(b, "id", getattr(b, "attr", "")) for b in nodo.bases],
                             "metodos": metodos, "atributos": privados, "publicos": publicos,
                             "valores": valores}
    return clases


# --- Comparación -------------------------------------------------------------

def comparar_metodos(clase: str, d: dict, c: dict) -> list[str]:
    difs = []
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


def comparar_atributos(clase: str, d: dict, c: dict) -> list[str]:
    return ([f"{clase}: falta el atributo privado {a}" for a in sorted(d["atributos"] - c["atributos"])]
            + [f"{clase}: atributo público {a}; el modelo los declara privados"
               for a in sorted(c["publicos"])]
            + [f"{clase}: atributo privado {a} que el diagrama no dibuja"
               for a in sorted(c["atributos"] - d["atributos"] - d["asociadas"])])


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
            difs += [f"{clase}: falta el valor {v}" for v in sorted(d["atributos"] - c["valores"])]
        else:
            difs += comparar_atributos(clase, d, c) + comparar_metodos(clase, d, c)
    return difs


if __name__ == "__main__":
    diagrama = leer_diagrama((RAIZ / "diagramas" / "clases.puml").read_text(encoding="utf-8"))
    codigo = leer_codigo((RAIZ / "viajes.py").read_text(encoding="utf-8"))
    difs = comparar(diagrama, codigo)
    miembros = sum(len(d["atributos"]) + len(d["metodos"]) for d in diagrama.values())
    for d in difs:
        print(f"  DIFERENCIA {d}")
    print(f"{len(diagrama)} clases y {miembros} miembros comparados: {len(difs)} diferencias")
    sys.exit(1 if difs else 0)
