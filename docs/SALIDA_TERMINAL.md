# Sesión real del menú

Generada por `herramientas/driver.py` sobre una base temporal, con datos ficticios (ningún nombre, RUT ni teléfono corresponde a una persona). Las contraseñas se teclearon sin eco y aquí se ven como ••••.

```text

   Primer uso: cree la cuenta del primer administrador.
   Correo: ana@viajes.cl
   Contraseña nueva (12 caracteres o más): ••••
   Repita la contraseña: ••••
   Cuenta creada para ana@viajes.cl. Ahora inicie sesión.

==================================================================
   Viajes Aventura
==================================================================
   1. Iniciar sesión
   2. Registrarme como cliente
   3. Ver los paquetes disponibles
   0. Salir

   Opción: 1

   Inicio de sesión (escriba x para cancelar)
   Correo: ana@viajes.cl
   Contraseña: ••••
[pantalla limpia]
==================================================================
   Viajes Aventura · ana@viajes.cl (administrador)
==================================================================

   DESTINOS
    1. Listar el catálogo
    2. Registrar un destino
    3. Editar un destino
    4. Cambiar el costo de un destino
    5. Eliminar un destino
    6. Volver a ofrecer un destino

   PAQUETES
    7. Listar todos los paquetes
    8. Crear un paquete
    9. Publicar un paquete
   10. Editar un paquete en borrador
   11. Cambiar el cupo de un paquete
   12. Eliminar un paquete
   13. Ver las reservas de un paquete

   CUENTAS
   14. Crear la cuenta de un socio
   15. Respaldar la base de datos

   MI CUENTA
   16. Cambiar mi contraseña
   17. Cerrar sesión

   Escriba «x» para cancelar la acción en curso  ·  0. Salir
==================================================================

   Opción: 2
   Nombre: Valle del Elqui
   Zona: Norte Chico
   Descripción: Observación astronómica y pisco
   Duración en días: 3
   Costo base por persona ($): 120.000
   Registrado: [1] Valle del Elqui · Norte Chico · 3 días · $120.000 (costo al 03-10-2026) · disponible

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 2
   Nombre: valle del  elqui
   Zona: Norte
   Descripción: Repetido a propósito (R1)
   Duración en días: 2
   Costo base por persona ($): 1
   ! Ya existe un destino con ese nombre

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 2
   Nombre: Salar de Surire
   Zona: Altiplano
   Descripción: Flamencos y termas
   Duración en días: 4
   Costo base por persona ($): 0
   ! El costo base debe estar entre 1 y 100.000.000

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 2
   Nombre: Salar de Surire
   Zona: Altiplano
   Descripción: Flamencos y termas
   Duración en días: 4
   Costo base por persona ($): 310.000
   Registrado: [2] Salar de Surire · Altiplano · 4 días · $310.000 (costo al 03-10-2026) · disponible

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 4
   Id del destino: 1
   Actual: [1] Valle del Elqui · Norte Chico · 3 días · $120.000 (costo al 03-10-2026) · disponible
   Costo base nuevo ($): 130.000
   Guardado: [1] Valle del Elqui · Norte Chico · 3 días · $130.000 (costo al 03-10-2026) · disponible

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 1
   ¿Solo los disponibles? (s/n): n

   Catálogo de destinos
   [2] Salar de Surire · Altiplano · 4 días · $310.000 (costo al 03-10-2026) · disponible
   [1] Valle del Elqui · Norte Chico · 3 días · $130.000 (costo al 03-10-2026) · disponible

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 5
   Id del destino: 2
   [2] Salar de Surire · Altiplano · 4 días · $310.000 (costo al 03-10-2026) · disponible
   ¿Eliminarlo? (s/n): s
   Eliminado del catálogo.

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 1
   ¿Solo los disponibles? (s/n): s

   Catálogo de destinos disponibles
   [1] Valle del Elqui · Norte Chico · 3 días · $130.000 (costo al 03-10-2026) · disponible

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 2
   Nombre: Salar de Surire
   Zona: Altiplano
   Descripción: Flamencos y termas
   Duración en días: 4
   Costo base por persona ($): 310.000
   Registrado: [2] Salar de Surire · Altiplano · 4 días · $310.000 (costo al 03-10-2026) · disponible

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 8
   Nombre: Solo uno
   Fecha de salida (dd-mm-aaaa): 02-11-2026
   Fecha de regreso (dd-mm-aaaa): 07-11-2026
   Cupo máximo de personas: 12
   Ids de los destinos, separados por coma (2 a 5): 1
   Margen de operación en % (Enter = 20): 
   ! Un paquete combina entre 2 y 5 destinos

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 8
   Nombre: Altiplano y estrellas
   Fecha de salida (dd-mm-aaaa): 02-11-2026
   Fecha de regreso (dd-mm-aaaa): 07-11-2026
   Cupo máximo de personas: 12
   Ids de los destinos, separados por coma (2 a 5): 2,1
   Margen de operación en % (Enter = 20): 
     [2] Salar de Surire · Altiplano · 4 días · $310.000 (costo al 03-10-2026) · disponible
     [1] Valle del Elqui · Norte Chico · 3 días · $130.000 (costo al 03-10-2026) · disponible
   Precio por persona calculado: $528.000
   ¿Guardar el paquete en borrador? (s/n): s
   Guardado en borrador: [1] Altiplano y estrellas · 02-11-2026 a 07-11-2026 · Salar de Surire, Valle del Elqui · $528.000 por persona · cupo 12 de 12 · borrador

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 9
   Id del paquete: 1
   [1] Altiplano y estrellas · 02-11-2026 a 07-11-2026 · Salar de Surire, Valle del Elqui · $528.000 por persona · cupo 12 de 12 · borrador
   ¿Publicarlo? El precio por persona queda fijo desde ahora (R7) (s/n): s
   Publicado: [1] Altiplano y estrellas · 02-11-2026 a 07-11-2026 · Salar de Surire, Valle del Elqui · $528.000 por persona · cupo 12 de 12 · publicado

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 10
   Id del paquete: 1
   Actual: [1] Altiplano y estrellas · 02-11-2026 a 07-11-2026 · Salar de Surire, Valle del Elqui · $528.000 por persona · cupo 12 de 12 · publicado
   ! Solo se edita un paquete en borrador; uno publicado solo cambia su cupo

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 11
   Id del paquete: 1
   Actual: [1] Altiplano y estrellas · 02-11-2026 a 07-11-2026 · Salar de Surire, Valle del Elqui · $528.000 por persona · cupo 12 de 12 · publicado
   Cupo máximo nuevo: 10
   Guardado: [1] Altiplano y estrellas · 02-11-2026 a 07-11-2026 · Salar de Surire, Valle del Elqui · $528.000 por persona · cupo 10 de 10 · publicado

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 7

   Todos los paquetes
   [1] Altiplano y estrellas · 02-11-2026 a 07-11-2026 · Salar de Surire, Valle del Elqui · $528.000 por persona · cupo 10 de 10 · publicado

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 14
   Correo del socio: matias@viajes.cl
   Contraseña nueva (12 caracteres o más): ••••
   Repita la contraseña: ••••
   Cuenta de administrador creada para matias@viajes.cl.

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 2
   Nombre: Torres del Paine
   Zona: x
   Acción cancelada. No se guardó nada.

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 99
   ! Opción desconocida.

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 999999999999… (5000 caracteres)
   ! Opción desconocida.

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 15
   Respaldo guardado en /tmp/tmpagl3embd/respaldos/viajes_20261004_010234_497434.db.
   La clave de cifrado no va en el respaldo: respáldela aparte (ver README).

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 17
   Sesión cerrada.

==================================================================
   Viajes Aventura
==================================================================
   1. Iniciar sesión
   2. Registrarme como cliente
   3. Ver los paquetes disponibles
   0. Salir

   Opción: 2

   Registro de cliente (escriba x para cancelar)
   Responsable: Viajes Aventura, Valparaíso.
   Datos: nombre, RUT, correo y teléfono. Finalidad: registrar sus reservas y contactarlo
   por ellas; no se usan para nada más. Base legal: la ejecución de la reserva que usted
   solicita. Destinatarios: solo los socios de la agencia; no se ceden a terceros.
   Conservación: mientras su cuenta exista; las reservas, como respaldo de lo cobrado.
   Protección: el RUT y el teléfono se guardan cifrados y nunca se muestran completos.
   Derechos: acceso, rectificación, supresión, oposición, portabilidad y bloqueo; se
   ejercen ante los socios de la agencia, que responden en 30 días corridos
   (Ley 19.628 modificada por la Ley 21.719).
   ¿Acepta? (s/n): s
   Nombre completo: Carolina Díaz
   RUT (12.345.678-5): 12.345.678-6
   ! El RUT no es válido: revise el dígito verificador
   RUT (12.345.678-5): 12.345.678-5
   Correo: carolina@correo.cl
   Teléfono (9 1234 5678): 9 1234 5678
   Contraseña nueva (12 caracteres o más): ••••
   Repita la contraseña: ••••
   ! La contraseña debe tener entre 12 y 128 caracteres

==================================================================
   Viajes Aventura
==================================================================
   1. Iniciar sesión
   2. Registrarme como cliente
   3. Ver los paquetes disponibles
   0. Salir

   Opción: 2

   Registro de cliente (escriba x para cancelar)
   Responsable: Viajes Aventura, Valparaíso.
   Datos: nombre, RUT, correo y teléfono. Finalidad: registrar sus reservas y contactarlo
   por ellas; no se usan para nada más. Base legal: la ejecución de la reserva que usted
   solicita. Destinatarios: solo los socios de la agencia; no se ceden a terceros.
   Conservación: mientras su cuenta exista; las reservas, como respaldo de lo cobrado.
   Protección: el RUT y el teléfono se guardan cifrados y nunca se muestran completos.
   Derechos: acceso, rectificación, supresión, oposición, portabilidad y bloqueo; se
   ejercen ante los socios de la agencia, que responden en 30 días corridos
   (Ley 19.628 modificada por la Ley 21.719).
   ¿Acepta? (s/n): s
   Nombre completo: Carolina Díaz
   RUT (12.345.678-5): 12.345.678-5
   Correo: carolina@correo.cl
   Teléfono (9 1234 5678): 9 1234 5678
   Contraseña nueva (12 caracteres o más): ••••
   Repita la contraseña: ••••
   Cuenta creada para carolina@correo.cl. Ya puede iniciar sesión.

==================================================================
   Viajes Aventura
==================================================================
   1. Iniciar sesión
   2. Registrarme como cliente
   3. Ver los paquetes disponibles
   0. Salir

   Opción: 1

   Inicio de sesión (escriba x para cancelar)
   Correo: carolina@correo.cl
   Contraseña: ••••
   ! Correo o contraseña incorrectos, o la cuenta está bloqueada por unos minutos.

==================================================================
   Viajes Aventura
==================================================================
   1. Iniciar sesión
   2. Registrarme como cliente
   3. Ver los paquetes disponibles
   0. Salir

   Opción: 1

   Inicio de sesión (escriba x para cancelar)
   Correo: nadie@correo.cl
   Contraseña: ••••
   ! Correo o contraseña incorrectos, o la cuenta está bloqueada por unos minutos.

==================================================================
   Viajes Aventura
==================================================================
   1. Iniciar sesión
   2. Registrarme como cliente
   3. Ver los paquetes disponibles
   0. Salir

   Opción: 1

   Inicio de sesión (escriba x para cancelar)
   Correo: carolina@correo.cl
   Contraseña: ••••
[pantalla limpia]
==================================================================
   Viajes Aventura · carolina@correo.cl (cliente)
==================================================================

   RESERVAS
    1. Ver los paquetes disponibles
    2. Reservar un paquete
    3. Mis reservas
    4. Anular una reserva

   MI CUENTA
    5. Ver mis datos
    6. Actualizar nombre y teléfono
    7. Cambiar mi contraseña
    8. Cerrar sesión

   Escriba «x» para cancelar la acción en curso  ·  0. Salir
==================================================================

   Opción: 1

   Paquetes disponibles
   [1] Altiplano y estrellas · 02-11-2026 a 07-11-2026 · Salar de Surire, Valle del Elqui · $528.000 por persona · cupo 10 de 10 · publicado

   Presione Enter para continuar...
[pantalla limpia · menú de carolina@correo.cl (cliente)]

   Opción: 2

   Paquetes disponibles
   [1] Altiplano y estrellas · 02-11-2026 a 07-11-2026 · Salar de Surire, Valle del Elqui · $528.000 por persona · cupo 10 de 10 · publicado
   Id del paquete: 99
   ! Ese paquete no está en la oferta

   Presione Enter para continuar...
[pantalla limpia · menú de carolina@correo.cl (cliente)]

   Opción: 2

   Paquetes disponibles
   [1] Altiplano y estrellas · 02-11-2026 a 07-11-2026 · Salar de Surire, Valle del Elqui · $528.000 por persona · cupo 10 de 10 · publicado
   Id del paquete: 1
   Cantidad de personas: 2.5
   ! Escriba un número entero, sin letras ni decimales.
   Cantidad de personas: 2
   Reserva confirmada por $1.056.000.

   Presione Enter para continuar...
[pantalla limpia · menú de carolina@correo.cl (cliente)]

   Opción: 2

   Paquetes disponibles
   [1] Altiplano y estrellas · 02-11-2026 a 07-11-2026 · Salar de Surire, Valle del Elqui · $528.000 por persona · cupo 8 de 10 · publicado
   Id del paquete: 1
   Ya tiene una reserva vigente en este paquete. ¿Reservar otra? (s/n): n
   Acción cancelada. No se guardó nada.

   Presione Enter para continuar...
[pantalla limpia · menú de carolina@correo.cl (cliente)]

   Opción: 2

   Paquetes disponibles
   [1] Altiplano y estrellas · 02-11-2026 a 07-11-2026 · Salar de Surire, Valle del Elqui · $528.000 por persona · cupo 8 de 10 · publicado
   Id del paquete: 1
   Ya tiene una reserva vigente en este paquete. ¿Reservar otra? (s/n): s
   Cantidad de personas: 20
   ! No hay cupo: quedan 8 lugares

   Presione Enter para continuar...
[pantalla limpia · menú de carolina@correo.cl (cliente)]

   Opción: 3

   Mis reservas
    1) [1] Carolina Díaz <carolina@correo.cl> · paquete 1 · 2 persona(s) · $1.056.000 · emitida el 03-10-2026 · vigente

   Presione Enter para continuar...
[pantalla limpia · menú de carolina@correo.cl (cliente)]

   Opción: 2

   Paquetes disponibles
   [1] Altiplano y estrellas · 02-11-2026 a 07-11-2026 · Salar de Surire, Valle del Elqui · $528.000 por persona · cupo 8 de 10 · publicado
   Id del paquete: 1
   Ya tiene una reserva vigente en este paquete. ¿Reservar otra? (s/n): s
   Cantidad de personas: 1
   Reserva confirmada por $528.000.

   Presione Enter para continuar...
[pantalla limpia · menú de carolina@correo.cl (cliente)]

   Opción: 4

   Mis reservas
    1) [1] Carolina Díaz <carolina@correo.cl> · paquete 1 · 2 persona(s) · $1.056.000 · emitida el 03-10-2026 · vigente
    2) [2] Carolina Díaz <carolina@correo.cl> · paquete 1 · 1 persona(s) · $528.000 · emitida el 03-10-2026 · vigente
   Número de la reserva a anular: 2
   Reserva anulada. Sus lugares vuelven al cupo del paquete.

   Presione Enter para continuar...
[pantalla limpia · menú de carolina@correo.cl (cliente)]

   Opción: 5
   Nombre:   Carolina Díaz
   Correo:   carolina@correo.cl
   RUT:      12.***.***-5
   Teléfono: +56 9 **** 5678

   Presione Enter para continuar...
[pantalla limpia · menú de carolina@correo.cl (cliente)]

   Opción: 6
   Nombre: Carolina Díaz Rojas
   Teléfono: 987654321
   Datos actualizados.
   Nombre:   Carolina Díaz Rojas
   Correo:   carolina@correo.cl
   RUT:      12.***.***-5
   Teléfono: +56 9 **** 4321

   Presione Enter para continuar...
[pantalla limpia · menú de carolina@correo.cl (cliente)]

   Opción: 8
   Sesión cerrada.

==================================================================
   Viajes Aventura
==================================================================
   1. Iniciar sesión
   2. Registrarme como cliente
   3. Ver los paquetes disponibles
   0. Salir

   Opción: 1

   Inicio de sesión (escriba x para cancelar)
   Correo: ana@viajes.cl
   Contraseña: ••••
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 13
   Id del paquete: 1

   Reservas de: [1] Altiplano y estrellas · 02-11-2026 a 07-11-2026 · Salar de Surire, Valle del Elqui · $528.000 por persona · cupo 8 de 10 · publicado
   [1] Carolina Díaz Rojas <carolina@correo.cl> · paquete 1 · 2 persona(s) · $1.056.000 · emitida el 03-10-2026 · vigente
   [2] Carolina Díaz Rojas <carolina@correo.cl> · paquete 1 · 1 persona(s) · $528.000 · emitida el 03-10-2026 · anulada

   Presione Enter para continuar...
[pantalla limpia · menú de ana@viajes.cl (administrador)]

   Opción: 17
   Sesión cerrada.

==================================================================
   Viajes Aventura
==================================================================
   1. Iniciar sesión
   2. Registrarme como cliente
   3. Ver los paquetes disponibles
   0. Salir

   Opción: 3

   Paquetes disponibles
   [1] Altiplano y estrellas · 02-11-2026 a 07-11-2026 · Salar de Surire, Valle del Elqui · $528.000 por persona · cupo 8 de 10 · publicado

==================================================================
   Viajes Aventura
==================================================================
   1. Iniciar sesión
   2. Registrarme como cliente
   3. Ver los paquetes disponibles
   0. Salir

   Opción: 0
   Hasta luego.
```

## Sesión que caduca por inactividad (RF-SEG-09)

El reloj se adelanta 11 minutos mientras el menú espera.

```text

   Primer uso: cree la cuenta del primer administrador.
   Correo: ana@viajes.cl
   Contraseña nueva (12 caracteres o más): ••••
   Repita la contraseña: ••••
   Cuenta creada para ana@viajes.cl. Ahora inicie sesión.

==================================================================
   Viajes Aventura
==================================================================
   1. Iniciar sesión
   2. Registrarme como cliente
   3. Ver los paquetes disponibles
   0. Salir

   Opción: 1

   Inicio de sesión (escriba x para cancelar)
   Correo: ana@viajes.cl
   Contraseña: ••••
[pantalla limpia]
==================================================================
   Viajes Aventura · ana@viajes.cl (administrador)
==================================================================

   DESTINOS
    1. Listar el catálogo
    2. Registrar un destino
    3. Editar un destino
    4. Cambiar el costo de un destino
    5. Eliminar un destino
    6. Volver a ofrecer un destino

   PAQUETES
    7. Listar todos los paquetes
    8. Crear un paquete
    9. Publicar un paquete
   10. Editar un paquete en borrador
   11. Cambiar el cupo de un paquete
   12. Eliminar un paquete
   13. Ver las reservas de un paquete

   CUENTAS
   14. Crear la cuenta de un socio
   15. Respaldar la base de datos

   MI CUENTA
   16. Cambiar mi contraseña
   17. Cerrar sesión

   Escriba «x» para cancelar la acción en curso  ·  0. Salir
==================================================================

   Opción: 14
[pantalla limpia]
   ! La sesión se cerró por inactividad. Inicie sesión de nuevo.

==================================================================
   Viajes Aventura
==================================================================
   1. Iniciar sesión
   2. Registrarme como cliente
   3. Ver los paquetes disponibles
   0. Salir

   Opción: 0
   Hasta luego.

[inactividad dentro de una acción]

   Primer uso: cree la cuenta del primer administrador.
   Correo: ana@viajes.cl
   Contraseña nueva (12 caracteres o más): ••••
   Repita la contraseña: ••••
   Cuenta creada para ana@viajes.cl. Ahora inicie sesión.

==================================================================
   Viajes Aventura
==================================================================
   1. Iniciar sesión
   2. Registrarme como cliente
   3. Ver los paquetes disponibles
   0. Salir

   Opción: 1

   Inicio de sesión (escriba x para cancelar)
   Correo: ana@viajes.cl
   Contraseña: ••••
[pantalla limpia]
==================================================================
   Viajes Aventura · ana@viajes.cl (administrador)
==================================================================

   DESTINOS
    1. Listar el catálogo
    2. Registrar un destino
    3. Editar un destino
    4. Cambiar el costo de un destino
    5. Eliminar un destino
    6. Volver a ofrecer un destino

   PAQUETES
    7. Listar todos los paquetes
    8. Crear un paquete
    9. Publicar un paquete
   10. Editar un paquete en borrador
   11. Cambiar el cupo de un paquete
   12. Eliminar un paquete
   13. Ver las reservas de un paquete

   CUENTAS
   14. Crear la cuenta de un socio
   15. Respaldar la base de datos

   MI CUENTA
   16. Cambiar mi contraseña
   17. Cerrar sesión

   Escriba «x» para cancelar la acción en curso  ·  0. Salir
==================================================================

   Opción: 14
   Correo del socio: intruso@viajes.cl
[pantalla limpia]
   ! La sesión se cerró por inactividad. Inicie sesión de nuevo.

==================================================================
   Viajes Aventura
==================================================================
   1. Iniciar sesión
   2. Registrarme como cliente
   3. Ver los paquetes disponibles
   0. Salir

   Opción: 0
   Hasta luego.
```
