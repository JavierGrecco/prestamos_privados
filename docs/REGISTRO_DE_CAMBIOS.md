# Registro de cambios y continuidad

Este documento ayuda a entender el proyecto sin tener que reconstruir la historia leyendo todos los commits. Resume los cambios relevantes, cómo se validan y qué queda pendiente.

**Última actualización:** 8 de octubre de 2026.

Para ver el estado actual de cada frente, consultar también el [Estado del proyecto](ESTADO_DEL_PROYECTO.md), el [Roadmap](ROADMAP.md) y los issues enlazados. El issue o PR es la referencia viva para su trabajo específico.

## Novedades del 8 de octubre de 2026

### Cambios integrados

- **J18.2 — Política de pago trazable:** cada pago conserva la versión de política aplicada; la migración v016 asocia los pagos históricos cuando existe evidencia suficiente. La documentación se sincronizó en el [PR #153](https://github.com/JavierGrecco/prestamos_privados/pull/153).
- **Seguridad de CI:** el permiso para publicar resultados de CodeQL quedó limitado a ese job y la auditoría de dependencias incluye el manifiesto de desarrollo. Ver [PR #154](https://github.com/JavierGrecco/prestamos_privados/pull/154).
- **Criterios financieros y migraciones:** el proyecto distingue las divergencias identificadas de una equivalencia financiera demostrada; también aclara que la prueba H4 actual cubre v009 → v010, no toda la historia hasta v016. Ver [PR #155](https://github.com/JavierGrecco/prestamos_privados/pull/155).
- **Dependencias:** la instalación de ejecución se separó de las herramientas de pruebas y se alinearon los manifiestos e instrucciones. Ver [PR #161](https://github.com/JavierGrecco/prestamos_privados/pull/161).

### Trabajo de seguridad de interfaz en curso

El [PR #162](https://github.com/JavierGrecco/prestamos_privados/pull/162) añade una primera barrera frente a la inserción de texto como HTML:

- Las tablas escapan encabezados y celdas de texto por defecto.
- Los mensajes contextuales y los estados vacíos escapan los textos que muestran.
- Los tipos visuales de notas y badges se limitan a valores conocidos.
- Varias pantallas escapan nombres, notas, referencias y datos históricos antes de insertarlos en HTML.
- Se agregaron pruebas para etiquetas, atributos y texto malicioso.

**Esto no cierra todavía la auditoría de la interfaz.** La función que renderiza plantillas HTML conserva su propósito y no sanea automáticamente todo el HTML que recibe. Quedan usos directos por revisar y deben sumarse regresiones para ellos. El trabajo sigue abierto en [#158 — Seguridad de la interfaz](https://github.com/JavierGrecco/prestamos_privados/issues/158). Los checks del PR enlazado son la referencia para saber si su última revisión está validada.

## Pendientes prioritarios

1. **Elegir y documentar la regla financiera de salida:** resolver las diferencias de interés post-vencimiento y la distribución interés/capital después de pagos parciales. [Issue #145](https://github.com/JavierGrecco/prestamos_privados/issues/145).
2. **Ejecutar un canary controlado:** solo sobre una base autorizada, con backup verificable, readiness, revisión humana y rollback preparado. No activar V3 automáticamente. [Issue #74](https://github.com/JavierGrecco/prestamos_privados/issues/74).
3. **Completar la auditoría de HTML dinámico:** seguir desde los componentes compartidos al resto de las pantallas y cubrir cada límite de confianza. [Issue #158](https://github.com/JavierGrecco/prestamos_privados/issues/158).
4. **Aislar las sesiones de SQLite:** probar la aplicación con dos sesiones simultáneas y evitar que compartan una misma transacción. [Issue #159](https://github.com/JavierGrecco/prestamos_privados/issues/159).
5. **Controlar las actualizaciones de la base:** separar la migración de bases existentes del arranque normal de la UI. [Issue #160](https://github.com/JavierGrecco/prestamos_privados/issues/160).
6. **Ampliar las pruebas de migraciones:** comprobar actualizaciones representativas hasta v016 sin reescribir hechos económicos. [Issue #156](https://github.com/JavierGrecco/prestamos_privados/issues/156).
7. **Proteger la rama principal:** configurar PR obligatorio y checks requeridos en GitHub. [Issue #157](https://github.com/JavierGrecco/prestamos_privados/issues/157).
8. **Preparar la autenticación real:** integrar un proveedor de identidad si se habilita un despliegue multiusuario. [Issue #137](https://github.com/JavierGrecco/prestamos_privados/issues/137).

## Cómo mantenemos este registro

Cada tanda de trabajo debe explicar, en lenguaje cotidiano:

- qué problema encontramos y a quién puede afectar;
- qué cambió realmente;
- qué pruebas o verificaciones lo respaldan;
- qué no se cambió y por qué;
- qué falta, quién o qué lo bloquea y cuál es el criterio para darlo por terminado.

Un PR abierto no se registra como integrado. Un check pendiente no se describe como verde. Una decisión financiera u operativa que requiere autorización humana no se da por resuelta mediante código o documentación.
