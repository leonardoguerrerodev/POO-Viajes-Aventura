# Entrega · Evaluación Sumativa 4 · Viajes Aventura

Programación Orientada a Objeto Seguro (TI3021) · Leonardo Guerrero · individual · 5 de octubre de 2026

Esta página dice dónde está la evidencia de cada indicador de la rúbrica. "Informe" es el informe técnico
en PDF entregado en el AAI, con una copia en [`docs/Informe_Tecnico.pdf`](docs/Informe_Tecnico.pdf); las rutas son
archivos de este repositorio.

**Para probar el programa sin ingresar datos:** instalar según el [README](README.md), activar el
entorno virtual (`source .venv/bin/activate`, o `.venv\Scripts\Activate.ps1` en Windows) y correr
`python main.py` → **2. Modo demostración**. Trae datos de ejemplo y cuentas de prueba de los dos roles,
en una base temporal que no toca nada real.

**Para comprobar cada afirmación:** `python pruebas/verificar.py`, con el entorno virtual activado. Corre las pruebas paso a paso, por
indicador de la rúbrica, y [`pruebas/README.md`](pruebas/README.md) dice qué prueba cada una y dónde
está el control en el código. Corren solas en cada envío al repositorio ([sello “Pruebas”](README.md)).

## Evidencia por indicador

| Indicador | Qué pide | Dónde está |
|---|---|---|
| **4.1.1.G.1** | Requerimientos funcionales y no funcionales | Informe §2.2 (50 RF en cuatro grupos) y §2.3 (18 RNF por característica ISO/IEC 25010) |
| **4.1.1.G.2** | Clasificación y priorización | Informe §2.4: MoSCoW con criterio escrito por letra, conteo y dependencias; 8 Won't |
| **4.1.1.G.3** | Redacción estructurada | Informe §2.2 (forma “El sistema debe…”, origen y dependencia) y §2.5 (criterio de aceptación “dado… cuando… entonces…” de cada RF) |
| **4.1.1.I.4** | Requerimientos que responden al problema | Informe §1.1 (15 consecuencias del caso con su cifra), §1.3 (16 supuestos), §2.1 (las 17 reglas traducidas) y §2.6 (matriz problema → requerimiento) |
| **4.1.2.G.5** | BPMN | Informe §3.2 · [`diagramas/03_bpmn_reserva.svg`](diagramas/03_bpmn_reserva.svg) · [`diagramas/04_bpmn_paquete.svg`](diagramas/04_bpmn_paquete.svg) · [`diagramas/05_bpmn_anulacion.svg`](diagramas/05_bpmn_anulacion.svg) |
| **4.1.2.G.6** | Casos de uso | Informe §3.1 (13 casos, 2 actores, fichas) · [`diagramas/02_casos_uso.svg`](diagramas/02_casos_uso.svg) |
| **4.1.2.G.7** | Diagrama de clases UML | Informe §3.3 · [`diagramas/clases.puml`](diagramas/clases.puml) (la fuente) · [`diagramas/01_clases.svg`](diagramas/01_clases.svg) |
| **4.1.2.I.8** | Trazabilidad requerimientos ↔ modelos | Informe §7 (matriz con los 68 requerimientos, RF y RNF: caso de uso → BPMN → clase y método → prueba) · [`pruebas/verificar.py`](pruebas/verificar.py), sección “uml” (diagrama contra código: 0 diferencias) |
| **4.1.3.G.9** | Roles | Informe §4.1 |
| **4.1.3.G.10** | Product Backlog | Informe §4.2 (30 historias en épicas, con RF de origen, prioridad y puntos) |
| **4.1.3.G.11** | Sprint Backlog | Informe §4.3 (sprints con objetivo, historias, horas estimadas y reales, tablero de cuatro columnas, revisión, retrospectiva y tareas con su hora real) |
| **4.1.3.I.12** | Tiempos y entregables | Informe §4.4 · [historial de commits](https://github.com/leonardoguerrerodev/POO-Viajes-Aventura/commits/main), con la historia de usuario en cada mensaje |
| **4.1.4.G.13** | Fiel al UML y a los cuatro principios | Informe §5.2 · [`pruebas/verificar.py`](pruebas/verificar.py), secciones “implementacion” (los cuatro principios) y “uml” |
| **4.1.4.G.14** | Persistencia | Informe §5.3 · `ESQUEMA` en [`viajes.py`](viajes.py) · [`pruebas/verificar.py`](pruebas/verificar.py), secciones “reglas” e “implementacion” |
| **4.1.4.G.15** | CRUD operativo | `python main.py` → **2. Modo demostración** ([README §2](README.md#2-primer-uso)) · Informe §5.4 (matriz entidad × operación) · [`pruebas/verificar.py`](pruebas/verificar.py), secciones “implementacion” y “menu” · [`docs/SALIDA_TERMINAL.md`](docs/SALIDA_TERMINAL.md) (sesión real con los dos roles) |
| **4.1.4.I.16** | Uso crítico de la IA | Informe §6 · [`docs/ANALISIS_IA.md`](docs/ANALISIS_IA.md) (93 contribuciones de cinco fuentes: 30 adoptadas, 40 modificadas, [23 descartadas](docs/ANALISIS_IA.md#descartados-23)) · [`docs/ia/`](docs/ia/) (respuestas íntegras) |
| **4.1.5.G.17** | Autenticación con librerías oficiales | Informe §5.6 · [`pruebas/verificar.py`](pruebas/verificar.py), sección “credenciales” (argon2-cffi, Argon2id) |
| **4.1.5.G.18** | Validación de credenciales | Informe §5.7 (escenario → respuesta → prueba) · [`pruebas/verificar.py`](pruebas/verificar.py), sección “credenciales” (bloqueo progresivo, sesiones invalidadas, cuentas desactivadas, pausa del registro) |
| **4.1.5.I.19** | Protección de datos sensibles | Informe §5.8 · [`pruebas/verificar.py`](pruebas/verificar.py), sección “datos” (Fernet: confidencialidad, integridad y rotación de la clave) · [`docs/PRIVACIDAD.md`](docs/PRIVACIDAD.md) (conservación e incidentes, art. 14 sexies) |
| **4.1.5.I.20** | Evaluación de la seguridad con IA | Informe §5.9 · [`docs/AUDITORIA.md`](docs/AUDITORIA.md) (17 hallazgos de la IA en cinco partes con su decisión, auditoría final, cierre de los riesgos declarados, OWASP Top 10:2025) · [`pruebas/verificar.py`](pruebas/verificar.py), secciones “seguridad” y “mutaciones” (45 de 45 reglas rotas a propósito, todas detectadas) · [`docs/ia/auditoria_seguridad_ia.md`](docs/ia/auditoria_seguridad_ia.md) |

## Calidad continua

- [Workflow “Pruebas”](https://github.com/leonardoguerrerodev/POO-Viajes-Aventura/actions/workflows/pruebas.yml):
  cada sección de [`pruebas/verificar.py`](pruebas/verificar.py) en Windows, macOS y Linux con Python 3.12 y 3.14, más las
  mutaciones, en cada envío.
- [SonarCloud](https://sonarcloud.io/summary/new_code?id=leonardoguerrerodev_POO-Viajes-Aventura):
  Quality Gate aprobado, sin observaciones abiertas.
- bandit sobre el producto ([`viajes.py`](viajes.py), [`main.py`](main.py)): 0 observaciones. pip-audit: 0 vulnerabilidades.
