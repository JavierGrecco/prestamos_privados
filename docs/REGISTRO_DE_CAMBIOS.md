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
- **Seguridad de la interfaz:** los componentes compartidos escapan tablas, notas, badges y estados vacíos, con regresiones contra texto malicioso. Ver [PR #162](https://github.com/JavierGrecco/prestamos_privados/pull/162).
- **Segunda capa de seguridad:** se escaparon identificadores visibles del préstamo y se agregó una prueba para el historial de decisiones. Ver [PR #164](https://github.com/JavierGrecco/prestamos_privados/pull/164).
- **Renderer heredado:** también se protegió `ui/ss.py`, una pantalla antigua que no está conectada al punto de entrada actual, y se agregó una regresión específica. Ver [PR #165](https://github.com/JavierGrecco/prestamos_privados/pull/165).
- **Control automático de HTML:** se agregó una prueba estática que revisa llamadas a `render_html()` y a `st.markdown(..., unsafe_allow_html=True)` para detectar campos de texto sensibles insertados sin escape. También se escapó el número de préstamo en el encabezado de pagos. Ver [PR #167](https://github.com/JavierGrecco/prestamos_privados/pull/167).
- **Migraciones explícitas:** la inspección de schema dejó de crear el historial al consultar la versión; la UI inicializa bases vacías, pero bloquea upgrades silenciosos sobre bases existentes. `python -m scripts.migrar_base` ofrece modo de inspección y, al actualizar, exige generar un backup verificado antes de ejecutar los cambios. El issue [#160](https://github.com/JavierGrecco/prestamos_privados/issues/160) sigue abierto para hardening de recuperación y casos históricos sin versión.
- **Concurrencia SQLite:** `BaseDatos` ahora protege la transacción exterior con `threading.RLock` y serializa los accesos SQL sobre una instancia compartida; se añade una prueba que fuerza una falla concurrente y verifica que el rollback de una operación no borre el cambio de otra. La validación E2E de pagos y dos sesiones sigue pendiente en [#159](https://github.com/JavierGrecco/prestamos_privados/issues/159); detalles en [Concurrencia de SQLite](CONCURRENCIA_SQLITE.md).

Los cuatro PR pasaron los tests en Python 3.11–3.14, auditoría de dependencias y CodeQL antes de integrarse.

### Seguridad de interfaz: varias tandas integradas, auditoría completa pendiente

Los [PR #162](https://github.com/JavierGrecco/prestamos_privados/pull/162), [#164](https://github.com/JavierGrecco/prestamos_privados/pull/164), [#165](https://github.com/JavierGrecco/prestamos_privados/pull/165) y [#167](https://github.com/JavierGrecco/prestamos_privados/pull/167) ya están integrados. Las mejoras incluyen:

- Las tablas escapan encabezados y celdas de texto por defecto.
- Los mensajes contextuales y los estados vacíos escapan los textos que muestran.
- Los tipos visuales de notas y badges se limitan a valores conocidos.
- Varias pantallas escapan nombres, notas, referencias y datos históricos antes de insertarlos en HTML.
- Se agregaron pruebas para etiquetas, atributos y texto malicioso.
- Se incorporó una comprobación estática para campos sensibles conocidos; ayuda a detectar regresiones, pero no entiende todos los aliases ni todas las formas posibles de construir HTML.

**Esto no cierra todavía la auditoría de la interfaz.** La función que renderiza plantillas HTML conserva su propósito y no sanea automáticamente todo el HTML que recibe. La revisión manual y la cobertura actual están descritas en [Auditoría de HTML en la interfaz](AUDITORIA_HTML_UI.md). La prevención automática inicial ya existe en `tests/test_ui_html_escape_contract.py`, pero su lista de campos es deliberadamente acotada. Sigue pendiente ampliar la detección y completar la validación de extremo a extremo. El issue [#158 — Seguridad de la interfaz](https://github.com/JavierGrecco/prestamos_privados/issues/158) permanecerá abierto hasta cumplir esos puntos.

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
