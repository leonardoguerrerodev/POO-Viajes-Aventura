# Entrega · Evaluación Sumativa 4 · Viajes Aventura

Programación Orientada a Objeto Seguro (TI3021) · Leonardo Guerrero · individual · 5 de octubre de 2026

Esta página dice dónde está la evidencia de cada indicador de la rúbrica. «Informe» es el informe técnico
en PDF entregado en el AAI; las rutas son archivos de este repositorio.

**Para comprobarlo todo en un minuto:** instalar según el [README](README.md) y correr
`python pruebas/prueba_rubrica.py`. Imprime una línea por cada afirmación verificable, agrupadas por
indicador, y falla si alguna no se cumple. Corre sola en cada envío al repositorio ([sello «Pruebas»](README.md)).

## Evidencia por indicador

| Indicador | Qué pide | Dónde está |
|---|---|---|
| **4.1.1.G.1** | Requerimientos funcionales y no funcionales | Informe §2.2 (46 RF en cuatro grupos) y §2.3 (16 RNF por característica ISO/IEC 25010) |
| **4.1.1.G.2** | Clasificación y priorización | Informe §2.4: MoSCoW con criterio escrito por letra, conteo y dependencias; 8 Won't |
| **4.1.1.G.3** | Redacción estructurada | Informe §2.2 (forma «El sistema debe…», origen y dependencia) y §2.5 (criterio de aceptación «dado… cuando… entonces…» de cada Must) |
| **4.1.1.I.4** | Requerimientos que responden al problema | Informe §1.1 (15 consecuencias del caso con su cifra), §1.3 (16 supuestos), §2.1 (las 17 reglas traducidas) y §2.6 (matriz problema → requerimiento) |
| **4.1.2.G.5** | BPMN | Informe §3.2 · [`diagramas/03_bpmn_reserva.svg`](diagramas/03_bpmn_reserva.svg) · [`diagramas/04_bpmn_paquete.svg`](diagramas/04_bpmn_paquete.svg) |
| **4.1.2.G.6** | Casos de uso | Informe §3.1 (13 casos, 2 actores, fichas) · [`diagramas/02_casos_uso.svg`](diagramas/02_casos_uso.svg) |
| **4.1.2.G.7** | Diagrama de clases UML | Informe §3.3 · [`diagramas/clases.puml`](diagramas/clases.puml) (la fuente) · [`diagramas/01_clases.svg`](diagramas/01_clases.svg) |
| **4.1.2.I.8** | Trazabilidad requerimientos ↔ modelos | Informe §7 (matriz RF → caso de uso → BPMN → clase y método → prueba) · [`herramientas/uml_vs_codigo.py`](herramientas/uml_vs_codigo.py) (0 diferencias) |
| **4.1.3.G.9** | Roles | Informe §4.1 |
| **4.1.3.G.10** | Product Backlog | Informe §4.2 (26 historias en épicas, con RF de origen, prioridad y puntos) |
| **4.1.3.G.11** | Sprint Backlog | Informe §4.3 (sprints con objetivo, historias, horas estimadas y reales, tablero, revisión y retrospectiva) |
| **4.1.3.I.12** | Tiempos y entregables | Informe §4.4 · [historial de commits](https://github.com/leonardoguerrerodev/POO-Viajes-Aventura/commits/main): ramas `feature/…` con la historia de usuario en cada mensaje |
| **4.1.4.G.13** | Fiel al UML y a los cuatro principios | Informe §5.2 · `prueba_rubrica.py` G.13 · [`herramientas/uml_vs_codigo.py`](herramientas/uml_vs_codigo.py) |
| **4.1.4.G.14** | Persistencia | Informe §5.3 · `ESQUEMA` en [`viajes.py`](viajes.py) · `prueba_rubrica.py` G.14 |
| **4.1.4.G.15** | CRUD operativo | Informe §5.4 (matriz entidad × operación) · `prueba_rubrica.py` G.15 · [`docs/SALIDA_TERMINAL.md`](docs/SALIDA_TERMINAL.md) (sesión real con los dos roles) |
| **4.1.4.I.16** | Uso crítico de la IA | Informe §6 · [`docs/ANALISIS_IA.md`](docs/ANALISIS_IA.md) (63 contribuciones: 10 adoptadas, 36 modificadas, [17 descartadas](docs/ANALISIS_IA.md#descartados-17)) · [`docs/ia/`](docs/ia/) (respuestas íntegras) |
| **4.1.5.G.17** | Autenticación con librerías oficiales | Informe §5.6 · `prueba_rubrica.py` G.17 (argon2-cffi, Argon2id) |
| **4.1.5.G.18** | Validación de credenciales | Informe §5.7 (escenario → respuesta → prueba) · `prueba_rubrica.py` G.18 |
| **4.1.5.I.19** | Protección de datos sensibles | Informe §5.8 · `prueba_rubrica.py` I.19 (Fernet: confidencialidad e integridad) |
| **4.1.5.I.20** | Evaluación de la seguridad con IA | Informe §5.9 · [`docs/AUDITORIA.md`](docs/AUDITORIA.md) (17 hallazgos con su decisión, OWASP Top 10:2025, 12 de 12 mutaciones detectadas) · [`docs/ia/auditoria_seguridad_ia.md`](docs/ia/auditoria_seguridad_ia.md) |

## Calidad continua

- [Workflow «Pruebas»](https://github.com/leonardoguerrerodev/POO-Viajes-Aventura/actions/workflows/pruebas.yml):
  Windows, macOS y Linux con Python 3.12 y 3.14, en cada envío.
- [SonarCloud](https://sonarcloud.io/summary/new_code?id=leonardoguerrerodev_POO-Viajes-Aventura):
  Quality Gate aprobado, sin observaciones abiertas.
