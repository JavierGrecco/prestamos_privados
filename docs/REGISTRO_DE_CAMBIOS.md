# Registro de cambios y continuidad

Este documento ayuda a entender el proyecto sin tener que reconstruir la historia leyendo todos los commits. Resume los cambios relevantes, cómo se validan y qué queda pendiente.

**Última actualización:** 9 de octubre de 2026.

Para ver el estado actual de cada frente, consultar también el [Estado del proyecto](ESTADO_DEL_PROYECTO.md), el [Roadmap](ROADMAP.md) y los issues enlazados. El issue o PR es la referencia viva para su trabajo específico.

## Novedades del 9 de octubre de 2026

### Frontera de HTML confiable más estricta — issue #158

Se eliminó la fábrica pública que permitía etiquetar un string arbitrario como fragmento HTML confiable. El constructor ahora requiere un token interno; las pantallas quedan cubiertas por una prueba estática que impide importar o invocar el mecanismo de construcción. Los badges siguen disponibles: escapan el texto y validan la variante CSS antes de generar el marcado. Se agregaron regresiones para el rechazo de construcción directa.

Esta entrega reduce la posibilidad de que una pantalla futura convierta por accidente una nota, un nombre o una referencia en HTML ejecutable. No cierra el issue #158: sigue pendiente ampliar el análisis estático de interpolaciones, revisar aliases/atributos y validar los flujos E2E de las superficies de HTML. La suite, CodeQL y la auditoría de dependencias deben pasar en CI antes de integrar.

### Rendimiento objetivo como requisito central del autopréstamo — issue #202

El usuario aclaró que la meta no es solo recuperar capital o conservar su valor de referencia: el plan debe recuperar capital, conservar poder de compra y sumar un rendimiento positivo como si el dinero hubiera permanecido invertido. La UI del modo USD requiere ahora un benchmark identificable y una tasa anual USD positiva, usa TEA como opción inicial y muestra el costo/rendimiento objetivo total junto con XIRR. El 0% queda como comparación analítica, no como el escenario principal. En un autopréstamo se reporta como costo de oportunidad/rendimiento interno, no como ganancia externa consolidada. La cotización proyectada continúa siendo un supuesto y el modo no crea contratos ni pagos. La tasa y la etiqueta del benchmark se cargan manualmente; el [issue #204](https://github.com/JavierGrecco/prestamos_privados/issues/204) sigue el trabajo para comparar contra una inversión identificable con costos, reinversión y datos históricos cuando estén disponibles.

### UI del plan interno en unidad USD — PR #200

El [issue #199](https://github.com/JavierGrecco/prestamos_privados/issues/199) continúa el [simulador USD de dominio integrado en PR #198](https://github.com/JavierGrecco/prestamos_privados/pull/198). El modo ARS nominal permanece como predeterminado. El modo USD convierte el capital inicial con una cotización fechada y muestra capital, cuotas, intereses y saldos en USD; la equivalencia ARS es opcional y usa una trayectoria proyectada cuota por cuota. Sin esa hipótesis, el total ARS queda sin calcular. La pantalla continúa siendo analítica, no registra operaciones y no presenta USD como contrato legal habilitado. La suite de CI debe validar el E2E de ambos modos antes de integrar.


### Rendimiento objetivo como requisito central del autopréstamo — issue #202

El usuario aclaró que la meta no es solo recuperar capital o conservar su valor de referencia: el plan debe recuperar capital, conservar poder de compra y sumar un rendimiento positivo como si el dinero hubiera permanecido invertido. La UI del modo USD requiere ahora un benchmark identificable y una tasa anual USD positiva, usa TEA como opción inicial y muestra el costo/rendimiento objetivo total junto con XIRR. El 0% queda como comparación analítica, no como el escenario principal. En un autopréstamo se reporta como costo de oportunidad/rendimiento interno, no como ganancia externa consolidada. La cotización proyectada continúa siendo un supuesto y el modo no crea contratos ni pagos.

### Comparación de valor final frente al benchmark — issue #206

El simulador calcula dos valores al último vencimiento: cuánto habría valido el capital original si siguiera invertido con el benchmark, y cuánto valdrían las cuotas recuperadas si cada una se reinvirtiera desde su fecha de vencimiento hasta ese mismo final. La diferencia muestra si el plan completo queda por debajo o por encima de la alternativa, manteniendo todo en USD de referencia. La comparación es una hipótesis de reinversión con una tasa manual; no representa aún el retorno histórico de un instrumento específico ni incluye sus costos/impuestos.

### Rendimiento reinvertido durante la carencia — issue #204

La simulación USD separa ahora dos conceptos: el crecimiento contrafactual del capital si permaneciera invertido durante la carencia (con reinversión del rendimiento por período) y el interés simple contractual que el escenario incluye en sus cuotas. En el modo de autopréstamo, el valor futuro del benchmark se convierte en la base interna a reponer; ese crecimiento no se guarda como cláusula legal ni como interés contractual. En el modo de préstamo entre personas, la tasa contractual USD queda separada de la tasa del benchmark; la diferencia respecto del benchmark se muestra como brecha informativa, sin sumarla automáticamente a la deuda. Las pruebas cubren TEA compuesta frente a interés simple diferido y la UI mantiene separadas ambas rutas.

### Autopréstamo y cobertura cambiaria — diseño documentado (issue #194)

Se documenta el caso de uso de compra al contado con reposición del capital, distinguiendo objetivo nominal, conservación en una unidad USD y ganancia. El documento separa el plan interno de reposición del préstamo real entre personas, exige registrar una cotización base y una referencia por cada pago, y propone gatillos como alertas de presupuesto, no como cambios automáticos de contrato. Incluye alternativas ARS nominal, USD, USD referenciado y UVA/CER, más referencias normativas oficiales vigentes consultadas el 09/10/2026. La implementación y la habilitación de condiciones contractuales sensibles siguen pendientes.


### Amortización por fechas explícitas — integrada por PR #190

El [issue #189](https://github.com/JavierGrecco/prestamos_privados/issues/189) registró la brecha entre la convención guardada y el generador mensual que utiliza el alta. El [PR #190](https://github.com/JavierGrecco/prestamos_privados/pull/190) integró una API aditiva para calendarios explícitos. Mantiene igualdad exacta con el motor legado cuando el calendario MENSUAL coincide y calcula factores por fechas para ACTUAL/365, ACTUAL/360, ACTUAL/ACTUAL y 30E/360 Eurobond, con excepción del vencimiento final en febrero. La ruta usa TNA proporcional y TEA compuesta con Decimal y cubre amortización francesa y alemana. El servicio de alta todavía no utiliza esta API.

Este cambio aún no modifica el servicio de alta, no recalcula préstamos históricos y no hace operativa la carencia. La suite completa y la revisión de seguridad del HEAD final deben pasar antes de proponer la integración.

### Integración de convenciones temporales en el simulador de carencia — PR #191

El [issue #186](https://github.com/JavierGrecco/prestamos_privados/issues/186) continúa con el [PR #191](https://github.com/JavierGrecco/prestamos_privados/pull/191). El simulador utiliza ahora la misma API de amortización por fechas que el dominio para las cuotas posteriores, y el cálculo de interés simple durante la carencia reutiliza los factores temporales TNA/TEA. La UI permite elegir MENSUAL, ACTUAL/365, ACTUAL/360, ACTUAL/ACTUAL y 30E/360 Eurobond.

Es una mejora de análisis, no una operación real: el alta actual no se modifica, los préstamos existentes no se recalculan y ningún interés diferido se convierte automáticamente en capital. La matriz de CI y la revisión de seguridad del PR #191 están en curso.

### Carencia inicial y primera cuota diferida — simulador integrado; operación real pendiente

El [issue #186](https://github.com/JavierGrecco/prestamos_privados/issues/186)
define el alcance financiero y legal del caso. El [PR #187](https://github.com/JavierGrecco/prestamos_privados/pull/187)
agrega cálculo simple de devengamiento, simulación comparativa y una pantalla
accesible desde **Análisis e informes → Simular carencia**.

La pantalla compara interés no cobrado, pago de intereses durante la carencia,
interés simple diferido a la primera cuota, distribución del interés simple sin
capitalización y capitalización solo como análisis. Muestra fechas, cuotas,
total del deudor, componentes de interés y rendimiento anualizado del prestamista
a partir de flujos fechados. No crea ni modifica préstamos.

**Límites explícitos:** el cálculo integral usa convención mensual porque el
generador regular de amortización aún no soporta de manera homogénea todas las
convenciones de días reales. Capitalización con TEA queda deshabilitada hasta
definir una semántica contractual consistente. La persistencia de contratos con
carencia, imputación de pagos, mora y validación E2E operativa siguen pendientes.
El PR continúa en borrador mientras se corrige y confirma CI del simulador.

Consulta el [diseño financiero de carencia inicial](DISENO_CARENCIA_INICIAL.md)
para la decisión de producto, ejemplos, riesgos y etapas siguientes.



### D0 — Plan de evolución UX e identidad polifuncional (integrada)

El [PR #180](https://github.com/JavierGrecco/prestamos_privados/pull/180) integró el [plan de evolución](PLAN_EVOLUCION_UX_POLIFUNCIONALIDAD.md) y su enlace en el índice documental. La issue coordinadora es [#173](https://github.com/JavierGrecco/prestamos_privados/issues/173). Las entregas D1–D6 cuentan con issues, alcance y criterios de aceptación. El PR pasó CI para Python 3.11–3.14, auditoría de dependencias y CodeQL.

### D1 — Arranque recuperable y selección explícita de persona (integrada)

El [PR #181](https://github.com/JavierGrecco/prestamos_privados/pull/181) resolvió la primera barrera de uso con una base sin personas:
- conserva el tema oscuro como predeterminado, conforme a la preferencia de producto;
- deja de seleccionar automáticamente a Javier o a la primera persona disponible;
- permite ir a Personas desde el estado vacío solo cuando la cuenta tiene capacidad de operar;
- presenta una orientación cuando falta seleccionar persona y una pantalla requiere ese contexto;
- agrega pruebas AppTest para inicio sin persona, selección explícita y permisos de LECTURA.

El PR pasó CI para Python 3.11–3.14, CodeQL y auditoría de dependencias. La issue [#174](https://github.com/JavierGrecco/prestamos_privados/issues/174) quedó cerrada.

### D2 — Personas polifuncionales, vínculo de cuenta y garantías (integrada)

El [PR #182](https://github.com/JavierGrecco/prestamos_privados/pull/182) se integró por squash en el commit `4fdbc67`; el issue [#175](https://github.com/JavierGrecco/prestamos_privados/issues/175) quedó cerrado.

- La migración v019 agrega el vínculo opcional entre una cuenta local y una persona financiera. Las cuentas históricas siguen sin vincular hasta que una persona administradora lo decide; la vinculación no concede capacidades.
- La migración v020 agrega garantías relacionadas con un préstamo, con alcance, tope opcional, estado y motivo/fecha de cierre.
- Las personas pueden acumular roles financieros `DEUDOR`, `INVERSOR` y `GARANTE`; el rol financiero `ADMIN` queda como legado y no concede privilegios de acceso.
- Las garantías se auditan y mantienen fuera de los cálculos de deuda, intereses, mora, pagos y ledger.
- `Mi espacio` consulta la persona vinculada a la cuenta y no toma una persona arbitraria del selector global.

**Validación real:** [tests en Python 3.11–3.14](https://github.com/JavierGrecco/prestamos_privados/actions/runs/37885777659) y [CodeQL + auditoría de dependencias](https://github.com/JavierGrecco/prestamos_privados/actions/runs/37885777657) finalizaron correctamente antes de integrar.

### D3 — Catálogo único y navegación agrupada por permisos (integrada)

El [PR #183](https://github.com/JavierGrecco/prestamos_privados/pull/183) integró D3 y cerró el issue [#176](https://github.com/JavierGrecco/prestamos_privados/issues/176). El commit de integración es [e788fde](https://github.com/JavierGrecco/prestamos_privados/commit/e788fdeffea028754aafe7d9e854ac9bbc7819f4).

- `ui/navegacion.py` define el catálogo central con grupo, capacidad, contexto y nivel de cada pantalla.
- La navegación ya no es una fila horizontal interminable: se agrupa en el sidebar y destaca la ruta activa.
- Detalle financiero se abre desde el préstamo, no como acceso global.
- Administrar el sistema y cambiar el modo efectivo de Motor V3 son capacidades distintas.
- La auditoría global queda reservada a ADMIN por defecto.
- Los tests de Python 3.11–3.14, CodeQL y auditoría de dependencias pasaron sobre la rama antes de integrar.
- D4 continúa siendo responsable de la inspección visual completa y el ajuste fino de CSS.

### D4 — Rediseño visual de prioridad oscura (integrada por PR #184)

El [PR #184](https://github.com/JavierGrecco/prestamos_privados/pull/184) se
integró por squash en `776ce15`. Conserva oscuro como tema predeterminado,
hace coherentes los widgets nativos con el tema elegido, ordena la navegación y
recupera el selector de tema en la configuración inicial y el login. Incluye
regresiones para temas, cuenta existente y bootstrap del primer ADMIN.

**Validación automatizada:** tests Python 3.11–3.14, CodeQL y auditoría de
dependencias pasaron antes de la integración. **Pendiente:** revisión visual
manual de dark, tamaños de ventana, teclado y widgets en un navegador real.

### D5 — Instalación local reproducible (implementación integrada por PR #185; validación manual pendiente)

**Issue:** [#178](https://github.com/JavierGrecco/prestamos_privados/issues/178)  
**PR de implementación:** [#185](https://github.com/JavierGrecco/prestamos_privados/pull/185)

Se agregan dos ayudantes multiplataforma: `scripts/preparar_entorno.py`
prepara `.venv` e instala los manifiestos declarados sin tocar SQLite;
`scripts/iniciar_local.py` exige el intérprete virtual de este checkout, una
ruta explícita de base y una inspección del schema antes de lanzar Streamlit.
Una base nueva se inicializa; una base existente con migraciones pendientes no
se actualiza sin una autorización explícita y un backup verificado.

La guía `docs/INSTALACION_LOCAL.md` separa PowerShell, CMD y macOS/Linux, explica
la diferencia entre cuenta de acceso y persona financiera y detalla qué hacer
si aparece el asistente de ADMIN en una base donde se esperaba una cuenta.

**Validación automatizada:** la revisión de código pasó tests en Python
3.11–3.14 ([tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/37889991491)),
CodeQL y auditoría de dependencias
([seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/37889991509)),
y el smoke de instalación ejecutó el preparador y las regresiones en Ubuntu,
Windows y macOS ([smoke](https://github.com/JavierGrecco/prestamos_privados/actions/runs/37889991644)).
La suite, CodeQL, auditoría y smoke multiplataforma también finalizaron correctamente sobre el HEAD documental `ee5403a`; ese commit no altera código ejecutable. **Pendiente manual:** inspección de UI,
primer acceso y reinicio en un navegador/entorno real. El lock exacto de
dependencias también queda como mejora separada porque los manifiestos usan
rangos de versiones.

## Novedades del 8 de octubre de 2026

### En desarrollo — rama `feature/usuarios-locales-admin`

- **Cuentas locales de acceso (v017):** ya integradas y verificadas. La aplicación tiene cuentas separadas de las personas del negocio, inicio de sesión con hash scrypt, bootstrap de ADMIN, roles `ADMIN/OPERADOR/LECTURA`, administración auditada, bloqueo temporal por intentos fallidos y recuperación offline de ADMIN. Pasaron los tests en Python 3.11–3.14, auditoría de dependencias y CodeQL.
- **Revocación de sesiones locales (v018, PR en preparación):** agrega una revisión por cuenta para invalidar sesiones existentes después de cambiar contraseña, rol o estado. El esquema no modifica préstamos, pagos ni movimientos financieros; la prueba de actualización v017→v018 conserva las cuentas existentes.
- **Fuera de alcance actual:** registro público, verificación de correo, recuperación por email y proveedor OIDC/SSO permanecen pendientes de N4. La ejecución local no debe exponerse a Internet.

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
