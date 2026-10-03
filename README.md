# Viajes Aventura

[![Pruebas](https://github.com/leonardoguerrerodev/POO-Viajes-Aventura/actions/workflows/pruebas.yml/badge.svg)](https://github.com/leonardoguerrerodev/POO-Viajes-Aventura/actions/workflows/pruebas.yml)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=leonardoguerrerodev_POO-Viajes-Aventura&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=leonardoguerrerodev_POO-Viajes-Aventura)

Sistema de gestión de destinos, paquetes turísticos y reservas para la agencia Viajes Aventura
(Valparaíso). Aplicación de terminal en Python con persistencia en `sqlite3`, autenticación con
contraseñas protegidas y cifrado de los datos personales del cliente.

Evaluación Sumativa 4 de Programación Orientada a Objeto Seguro (TI3021), INACAP Valparaíso.

**Para el corrector:** [`ENTREGA.md`](ENTREGA.md) enlaza la evidencia de cada indicador de la rúbrica.

## Instalar y ejecutar

Requiere Python 3.12 o superior, en Windows, macOS o Linux. No necesita un servidor de base de datos.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS y Linux: source .venv/bin/activate
pip install --only-binary :all: --require-hashes -r requirements.txt
python main.py
```

La primera vez la base está vacía y el sistema pide crear la cuenta del primer administrador: no hay
contraseñas escritas en el código. Después, cualquier persona puede registrarse como cliente desde la
pantalla de inicio.

- La base queda en `viajes.db`, junto al código, con permisos solo para su dueño.
- La clave que cifra el RUT y el teléfono se crea con el primer cliente en
  `~/.config/viajes-aventura/clave.env`, fuera del proyecto. **Respáldela aparte:** sin ella, los
  RUT y teléfonos guardados no se pueden leer.

## Verificar

```bash
python viajes.py                     # autoverificación de las reglas R1 a R17: imprime OK
python herramientas/driver.py        # recorre el menú con los dos roles y guarda docs/SALIDA_TERMINAL.md
python herramientas/uml_vs_codigo.py # el diagrama de clases contra el código: 0 diferencias
python pruebas/prueba_rubrica.py     # una afirmación verificable por indicador de la rúbrica
```

Las cuatro corren en cada envío al repositorio, en Windows, macOS y Linux con Python 3.12 y 3.14
(sello «Pruebas» de arriba). Ninguna toca `viajes.db` ni la clave real: trabajan sobre archivos
temporales.

## Estructura

| Ruta | Contenido |
|---|---|
| `viajes.py` | Dominio: las clases del diagrama, su persistencia (todo el SQL) y la autoverificación |
| `main.py` | Menú de terminal, sin SQL |
| `diagramas/` | Diagrama de clases (`clases.puml`, la fuente), casos de uso y BPMN, con sus generadores |
| `herramientas/` | Driver del menú y comparador del diagrama con el código |
| `pruebas/` | Prueba por indicador de la rúbrica |
| `docs/` | Auditoría de seguridad, análisis del uso de IA, sesión real del menú, transcripciones de la IA e informe técnico |
