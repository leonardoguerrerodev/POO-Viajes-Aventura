# Privacidad: conservación de los datos e incidentes de seguridad

Viajes Aventura es responsable de los datos personales de sus clientes (Ley 19.628, modificada por la
Ley 21.719, que rige desde el 1 de diciembre de 2026). El sistema cifra el RUT y el teléfono, registra
cada acción y deja desactivar cuentas y rotar la clave. Pero dos deberes de la ley no son funciones de
un programa: **cuánto tiempo se guardan los datos** y **qué hacer si se filtran**. Esta página los
deja escritos como procedimiento de la agencia.

Las citas son del texto oficial de la Ley 21.719 (LeyChile, idNorma 1209272, consultado el 5 de octubre
de 2026).

## 1. Conservación de los datos

> «Los datos personales pueden ser conservados sólo por el período de tiempo que sea necesario para
> cumplir con los fines del tratamiento, luego de lo cual deben ser suprimidos o anonimizados, sin
> perjuicio de las excepciones que establezca la ley.» (art. 3, letra c, principio de proporcionalidad)

| Dato | Para qué se guarda | Hasta cuándo |
|---|---|---|
| Nombre, RUT, correo y teléfono del cliente | Registrar sus reservas y contactarlo por ellas | Mientras tenga reservas vigentes o futuras, y después mientras la ley tributaria exija respaldar lo cobrado |
| Reservas (fecha, personas, total) | Respaldo de lo cobrado | Lo que exija la ley tributaria |
| Cuenta de un socio | Saber quién hizo cada cambio | Mientras sea socio; al irse, la cuenta se **desactiva** desde el menú (no se borra, para no perder quién hizo qué) |
| Registro de auditoría | Detectar accesos indebidos y responder un incidente | No guarda RUT, teléfono, correo ni contraseñas, así que no tiene datos personales que suprimir |
| Respaldos de la base | Recuperar las reservas si falla el equipo | Se conservan los últimos 12; los más antiguos se borran junto con la clave anterior que los lee |

**Revisión anual:** una vez al año, un socio revisa las cuentas de clientes sin reservas en los últimos
24 meses. Si ya no hay obligación de respaldo, las desactiva desde el menú, y atiende la supresión de
sus datos según el punto 3.

## 2. Si los datos se filtran o se alteran (art. 14 sexies)

> «El responsable deberá reportar a la Agencia, por los medios más expeditos posibles y sin dilaciones
> indebidas, las vulneraciones a las medidas de seguridad que ocasionen la destrucción, filtración,
> pérdida o alteración accidental o ilícita de los datos personales que trate o la comunicación o
> acceso no autorizados a dichos datos, cuando exista un riesgo razonable para los derechos y
> libertades de los titulares.»

**Qué cuenta como incidente:**
- se pierde o roban el equipo de la oficina, o un respaldo de la base;
- la clave de cifrado sale del equipo, por ejemplo por un correo o una copia;
- el registro de auditoría muestra accesos que ningún socio reconoce, o bloqueos repetidos de una
  cuenta (el menú del socio lo avisa al entrar);
- un dato cifrado no se puede leer porque fue alterado (el sistema lo informa).

**Qué hacer, en orden:**
1. **Contener:**
   - cambiar la contraseña de la cuenta afectada, o desactivarla;
   - si la clave pudo salir, **rotarla** desde el menú («Rotar la clave de cifrado»): los datos copiados
     quedan ilegibles para quien no tenga la clave anterior.
2. **Evaluar:**
   - con el registro de auditoría («Ver el registro de auditoría»), establecer qué pasó, desde cuándo y
     qué cuentas y datos estuvieron expuestos;
   - el RUT y el teléfono van cifrados. Si solo salió la base, sin la clave, esos datos no son legibles.
3. **Reportar a la Agencia de Protección de Datos Personales** sin dilaciones indebidas, si existe un
   riesgo razonable para los clientes.
4. **Avisar a los clientes** cuando la ley lo exige. La agencia no guarda datos personales sensibles
   (art. 2 g) ni de menores de catorce años, pero sí guarda los **totales cobrados**. Con un criterio
   prudente, se tratan como datos relativos a obligaciones comerciales: si están entre los afectados, se avisa a cada
   cliente «en un lenguaje claro y sencillo, singularizando los datos afectados, las posibles
   consecuencias de las vulneraciones de seguridad y las medidas de solución o resguardo adoptadas».
5. **Registrarlo**, aunque no haya que reportarlo, en la tabla de abajo.

**Registro de incidentes.** La ley pide registrar «la naturaleza de las vulneraciones sufridas, sus
efectos, las categorías de datos y el número aproximado de titulares afectados y las medidas adoptadas
para gestionarlas y precaver incidentes futuros». Se lleva fuera del sistema, en un documento de la
agencia, con estas columnas:

| Fecha | Qué ocurrió | Efectos | Categorías de datos | Titulares afectados (aprox.) | Medidas adoptadas | ¿Reportado a la Agencia y a los titulares? |
|---|---|---|---|---|---|---|

## 3. Derechos de los clientes

El aviso que el cliente acepta al registrarse indica sus seis derechos:
- acceso;
- rectificación;
- supresión;
- oposición;
- portabilidad;
- bloqueo.

Se ejercen ante los socios, que responden en 30 días corridos.
- **Acceso y rectificación:** el cliente ve sus datos («Ver mis datos») y corrige su nombre y su teléfono
  desde el menú.
- **Supresión:** la atiende un socio a mano mientras no exista la opción en el sistema (Won't W-08, con
  la condición de construirla antes de que rija la Ley 21.719). La cuenta se desactiva desde el menú.
  La supresión de los datos personales la hace un socio a mano, y las reservas se conservan como
  respaldo de lo cobrado.
