# Registro de cambios y continuidad

Este documento ayuda a entender el proyecto sin tener que reconstruir la historia leyendo todos los commits. Resume los cambios relevantes, cómo se validan y qué queda pendiente.

**Última actualización:** 10 de octubre de 2026.

Para ver el estado actual de cada frente, consultar también el [Estado del proyecto](ESTADO_DEL_PROYECTO.md), el [Roadmap](ROADMAP.md) y los issues enlazados. El issue o PR es la referencia viva para su trabajo específico.

La hoja de ruta para finalizar la experiencia local está centralizada en [ROADMAP_MVP_LOCAL.md](ROADMAP_MVP_LOCAL.md), con fases, dependencias y criterios de aceptación. El seguimiento coordinador es [issue #223](https://github.com/JavierGrecco/prestamos_privados/issues/223).

## Novedades del 10 de octubre de 2026

### Roadmap profesional para la entrega local

Se creó una hoja de ruta operativa con lenguaje de producto, estado de cada frente, dependencias entre fases, alcance explícito del MVP, criterios de salida y forma de trabajo para cada PR. La prioridad es cerrar préstamos privados y autocrédito/reposición desde la UI local; nube y conexión automática a mercados permanecen fuera del camino crítico. El plan queda coordinado por el issue #223.

### Guardar y consultar análisis de reposición USD — PR #225

El simulador permite guardar un análisis desde la UI local y volver a consultarlo. La migración v022 agrega la tabla de snapshots con creación registrada y bloqueos de actualización/eliminación; el repositorio serializa importes con `Decimal`, conserva supuestos y resultados en JSON determinista y calcula un SHA-256 para comprobar integridad. La UI permite seleccionar análisis guardados, consultar el calendario y revisar supuestos/sensibilidad. La acción de guardar exige capacidad `OPERAR`.

La entrega es deliberadamente un **snapshot inmutable de análisis**: no es aún un plan editable ni registra contrato, desembolso o pagos. La siguiente tarea de la fase 2 es agrupar versiones bajo una identidad de plan con ciclo de vida, manteniendo separadas las obligaciones reales y el rendimiento hipotético. CI de PR #225 aprobado en Python 3.11–3.14, CodeQL y auditoría de dependencias.

### Planes de reposición con identidad y versiones — PR #227

Se agrega la migración v023 con una entidad de plan y su historial de versiones. Los snapshots v022 existentes se convierten en planes con versión inicial, vinculados al registro de origen para conservar continuidad. La UI permite crear un plan, guardar una nueva versión consecutiva, consultar versiones anteriores y cerrar el plan sin borrar el historial. Tanto los planes como sus versiones están protegidos por triggers; cada versión contiene su SHA-256 y los valores financieros se serializan sin `float`.

La entrega conserva un límite deliberado: el plan es una herramienta de planificación financiera, no un préstamo legal ni un registro de desembolsos, aportes, cobros o ganancias realizadas. El siguiente paso es la aceptación manual y el seguimiento de cuánto capital se repuso, cómo se conserva poder de compra y cómo se compara el rendimiento realizado con el objetivo, sin contabilizar proyecciones como resultados reales. PR #227 validado en Python 3.11–3.14 y con controles de seguridad aprobados.

### Registro de aportes y avance de reposición — PR #229

La migración v024 incorpora un libro de aportes asociado a un plan interno activo. Cada registro conserva fecha, importe ARS, cotización declarada, naturaleza (observada o supuesto), fuente/referencia, equivalente USD de referencia, autor y SHA-256. Los aportes no se editan ni se borran; el modelo de correcciones debe conservar la traza y queda para una etapa posterior.

La UI permite registrar aportes desde el plan, consultar el historial y comparar el equivalente USD de referencia acumulado contra las cuotas programadas ya vencidas de la versión seleccionada. La comparación no revalúa aportes anteriores al tipo de cambio de hoy ni prueba que se hayan comprado dólares. Tampoco registra pagos de préstamos o rendimiento de inversiones: el equivalente USD es una referencia, no un resultado realizado. Se validan importes/cotizaciones positivos, precisión, fuente para cotizaciones observadas y rechazo de fechas futuras. CI de PR #229 aprobado en Python 3.11–3.14, CodeQL y auditoría de dependencias.

### Flujos de inversión, valuaciones y rendimiento reportado — PR #232

La migración v025 agrega libros inmutables separados para movimientos y valuaciones de inversión. Los movimientos distinguen aportes a la inversión, rescates, distribuciones y costos/impuestos pagados fuera de la cartera. Cada fila guarda fecha, moneda, importe original, cotización declarada para convertir ARS/USD, fuente/referencia, autor y SHA-256. Las valuaciones mantienen snapshots históricos y permiten registrar un valor cero si la cartera queda totalmente deteriorada.

La UI muestra aportes a inversión, cobros/rescates, costos externos, última valuación y resultado total en USD de referencia. Calcula XIRR anualizada solo cuando hay un aporte a inversión, existe una valuación igual o posterior al último movimiento y el solver encuentra un resultado; en caso contrario, indica qué falta o por qué no pudo calcularse. El valor de mercado final de los activos abiertos es una valuación no realizada, no una ganancia cobrada. Para evitar doble conteo, los costos externos se deben registrar solo si se pagaron fuera de la cartera y no están descontados de la valuación ingresada.

Todos los flujos/valuaciones son datos declarados por el usuario: no hay descarga ni conciliación automática con broker, cotizaciones o comprobantes. Esto no modifica pagos contractuales Legacy/V3. CI de PR #232 aprobado en Python 3.11–3.14, CodeQL y auditoría de dependencias.

### Importación de índice histórico de retorno total — etapa B inicial de issue #204

El modo USD permite descargar una plantilla CSV e importar observaciones fechadas de un índice de retorno total con nivel, moneda, tipo de índice (bruto/neto), fuente y referencia por fila. Se exige UTF-8, separador punto y coma, valores `Decimal`, fechas ISO estrictamente crecientes, moneda homogénea, tipo de índice homogéneo, fuente declarada y al menos 30 días entre la primera y la última observación. Se limita el archivo a 2 MB y 5.000 filas.

El resumen muestra retorno acumulado, CAGR observado con base 365 días, caída máxima desde un pico histórico y el mayor hueco de fechas de toda la serie, con inicio y fin de ese hueco. La serie permanece en sesión y puede inspeccionarse junto con sus referencias. Solo si el índice está clasificado como `BRUTO_TOTAL_RETURN`, la moneda es USD, el nombre/clase coincide con el benchmark seleccionado, el rendimiento anualizado está dentro del rango admitido, hay **al menos 365 días de historia y 12 observaciones**, y ningún intervalo entre observaciones supera **45 días**, la UI habilita una casilla explícita para usar el CAGR pasado como **hipótesis de rendimiento bruto base**; después se aplican los costos, el impuesto estimado y el margen de escenarios. Las series cortas o con huecos mayores siguen disponibles para análisis y backtest si las fechas operativas están cubiertas, pero no se permite usar ese CAGR como tasa base. La exportación de sensibilidad incluye también el mayor hueco y sus fechas para auditoría. Una serie `NETO_TOTAL_RETURN` se puede analizar, pero no se puede reutilizar como rendimiento bruto para evitar doble descuento de costos/impuestos. El CAGR nunca se aplica automáticamente ni se presenta como pronóstico.

Si se importa un índice total-return ya calculado, la aplicación conserva la clasificación y la metodología declaradas por el proveedor, pero no verifica de forma independiente su autenticidad. No descarga datos de mercado y no implementa todavía un modelo específico de bonos, cupón corrido, rendimiento al vencimiento ni acciones corporativas.

### Derivar índice total-return desde precio no ajustado + distribuciones — etapa B

Se añade una segunda vía de carga con plantilla CSV: fecha, precio de cierre **no ajustado**, distribución en efectivo por unidad, moneda, clasificación bruto/neto, fuente y referencia. El precio debe declararse como `PRECIO_NO_AJUSTADO`; la importación rechaza otras bases para evitar sumar una distribución a un precio que ya podría incorporarla. La primera observación debe tener distribución cero porque no existe un intervalo previo dentro de la serie para reinvertirla.

Para cada intervalo calcula `TRI_t = TRI_(t-1) × (P_t + D_t) / P_(t-1)`, normalizando la serie a 100. La distribución declarada se reinvierte al cierre de su fecha. Se mantiene `Decimal`, el orden estricto de fechas, la moneda única, la clasificación homogénea bruto/neto, la fuente y referencias. Los precios y distribuciones originales permanecen en la sesión y se muestran junto al índice derivado; el método de construcción viaja también en el CSV de sensibilidad y en el CSV del backtest.

Esta fórmula es una aproximación de retorno total con distribuciones por unidad, no un feed verificado ni una liquidación fiscal. El usuario debe confirmar que los precios realmente son no ajustados y que las distribuciones corresponden a esas fechas/unidades; no se corrigen splits, fusiones, cambios de unidad, retenciones particulares ni los flujos de bonos/YTM. El modo neto necesita distribuciones netas consistentes con esa metodología. Sin esas comprobaciones, el resultado no debe usarse como rentabilidad realizada de un activo real.

Se suma una descarga de trazabilidad que combina en cada fila el precio no ajustado, la distribución declarada, los metadatos originales y el nivel total-return derivado. Exporta la fórmula normalizada y conserva fuente/referencia; los textos libres reciben protección contra inyección de fórmulas en hojas de cálculo. El CSV se rechaza si las fechas de las entradas y del índice no coinciden fila por fila.

### Backtest histórico del capital y las cuotas — extensión de etapa B de issue #204

Sobre la serie histórica importada, el simulador permite contrastar el valor que habría alcanzado el capital original mantenido en el índice contra el valor final de las cuotas reinvertidas en sus fechas programadas. El backtest usa niveles observados iguales o anteriores a cada fecha, informa el desfase en días y rechaza cierres obsoletos (más de 45 días), fechas fuera de la cobertura o una serie que no esté expresada en USD. Calcula la valoración final de ambos caminos, su brecha, el rendimiento anualizado observado del capital y la XIRR de la cartera acumulada cuando existe una solución.

El backtest conserva el tipo del índice (`BRUTO_TOTAL_RETURN` o `NETO_TOTAL_RETURN`) y descarga un CSV con fechas valoradas, fuentes/referencias, desfases, montos finales, brecha y XIRR. No aplica una segunda deducción de costos/impuestos a los niveles observados. No cambia el plan ni guarda contratos/cuotas en base de datos; si el historial no cubre todo el calendario, muestra la causa y no extrapola.

### Benchmark neto y sensibilidad conservador/base/alto — etapa A de issue #204

El simulador USD distingue el rendimiento bruto de la inversión alternativa y calcula una tasa neta ilustrativa descontando costos anuales estimados e impuesto configurado sobre el rendimiento positivo posterior a costos. Se añade clase de activo, etiqueta del benchmark y margen editable que crea escenarios conservador/base/alto. La tabla compara el valor final contrafactual del capital inicial contra las mismas cuotas reinvertidas; el calendario, las cuotas contractuales y la unidad USD del plan no varían al cambiar un escenario. Se puede exportar la sensibilidad a CSV con los supuestos incluidos.

Los costos se modelan como proporción anual simple del capital y el impuesto como porcentaje estimado de la ganancia positiva; no es una liquidación fiscal ni modela en esta etapa todos los flujos de cada instrumento. Las tasas son hipótesis manuales, no retornos reales recuperados de mercado. La etapa B — importar series históricas fechadas con fuente, metodología y tratamiento de distribuciones — sigue pendiente; el código no inventa cotizaciones ni rendimientos históricos.

### Importación y plantilla CSV de cotizaciones por cuota

El modo de cotización individual ahora ofrece una plantilla CSV descargable e importación de tasas por vencimiento. El formato documenta el separador punto y coma (compatible con coma decimal), incluye número de cuota y fecha ISO, y permite fuente, lado, naturaleza y referencia. La importación comprueba columnas, fechas contra el calendario actual, duplicados, cotizaciones finitas/positivas y fuente antes de cargar la tabla. Las filas sin cotización pueden quedar vacías; una fila parcialmente completada se rechaza. Si cambia el calendario del plan, se eliminan las cotizaciones previas para no asociar un valor antiguo a una cuota distinta.

El CSV de resultados expone también la referencia de la cotización. Los campos libres de fuente/referencia reciben protección frente a fórmulas al abrir los CSV en aplicaciones de hojas de cálculo. No se persisten las cotizaciones: pertenecen al escenario de simulación actual.

### Cotizaciones individuales por vencimiento en modo USD — issue #202

El simulador incorpora un método explícito para ingresar una cotización independiente en cada cuota. La tabla presenta cuota y vencimiento calculados como campos bloqueados, con valores editables para ARS/USD, fuente/instrumento, lado comprador/vendedor, naturaleza (observada, proyectada o supuesto) y referencia opcional. Las cotizaciones quedan vacías por defecto: el tipo de cambio inicial no se copia silenciosamente a pagos futuros.

Cada valor se valida como `Decimal`, requiere fuente cuando se carga una tasa y se asocia a la fecha exacta del vencimiento. Las cuotas sin datos quedan sin equivalente ARS; el total ARS solo está disponible cuando todas las cotizaciones están completas. La tabla y el CSV distinguen cotización, fuente, lado, naturaleza y equivalente por cuota. Las cuotas y métricas USD no cambian cuando cambia la ruta ARS.

Se amplían las regresiones unitarias y E2E. El simulador sigue siendo analítico y no consulta tipos de cambio en vivo ni guarda operaciones.

### Precisión decimal en el simulador ARS/USD

Las entradas financieras del simulador de carencia dejan de depender de widgets numéricos que entregan `float`. Capital, tasas, cotización inicial ARS/USD y variación cambiaria proyectada se ingresan como texto validado y se convierten directamente a `Decimal`. Se aceptan formatos argentinos como `1.000.000,50` y `36,5000`, además del formato decimal canónico cuando no resulta ambiguo. Se rechazan valores vacíos, no finitos, separadores inconsistentes, importes fuera de rango y precisión mayor a la permitida. Los meses y plazos continúan como enteros.

Se amplía la regresión unitaria para formatos válidos/invalidos y la prueba E2E para recorrer ambos modos del simulador y confirmar que las entradas conservan su representación textual. La simulación sigue siendo analítica: no persiste préstamos ni pagos.

La UI no consulta cotizaciones en vivo ni valida externamente el benchmark ingresado; esos datos siguen siendo supuestos declarados por el usuario.

## Novedades del 9 de octubre de 2026

### Contraste de colores y legibilidad — UX D4

Las tres paletas incorporan una prueba automatizada de contraste WCAG AA para texto normal (mínimo 4.5:1), cubriendo combinaciones semánticas de superficies, botones, enlaces y estados de éxito, alerta, error y neutral. Se ajustaron tonos insuficientes en botones primarios, textos secundarios y estados de las paletas clara, intermedia y oscura. El tema oscuro sigue siendo el predeterminado.

La comprobación automática no sustituye la inspección visual manual en navegador, en distintos tamaños de ventana y con navegación por teclado. Esos controles de aceptación de D4 siguen pendientes y se deben registrar solo después de ejecutarlos realmente.


### Aislamiento de transacciones explícitas de pagos V3 — issue #159

Se detectó que el repositorio de pagos V3 usa `BEGIN IMMEDIATE` y `COMMIT/ROLLBACK` en llamadas separadas. El bloqueo individual al obtener la conexión no mantenía el `RLock` durante todo el ciclo, dejando una brecha frente a dos servicios que compartieran una misma instancia de `BaseDatos`. Se añadió `bloqueo_transaccion_explicita()` y el adaptador V3 lo mantiene desde `begin` hasta el cierre de la unidad de trabajo. El estado del contexto se guarda por hilo para evitar mezclar repositorios concurrentes.

Se añade una regresión donde dos servicios intentan registrar pagos con la misma revisión sobre una sola instancia compartida: la segunda transacción debe esperar al commit de la primera y luego rechazar la revisión obsoleta sin duplicar el pago. Este refuerzo no habilita un despliegue multiusuario ni reemplaza pruebas con dos sesiones reales de Streamlit. Issue #159 permanece abierto hasta cubrir ese nivel E2E y la operación bajo contención.


### Frontera de HTML confiable más estricta — issue #158

Se eliminó la fábrica pública que permitía etiquetar un string arbitrario como fragmento HTML confiable. El constructor ahora requiere un token interno; las pantallas quedan cubiertas por una prueba estática que impide importar o invocar el mecanismo de construcción. Los badges siguen disponibles: escapan el texto y validan la variante CSS. Las notas inline también escapan el texto y las celdas de estado se construyen combinando exclusivamente fragmentos tipados; el consumidor heredado de la pantalla de préstamos fue migrado a esa API. Se agregaron regresiones para el rechazo de construcción directa.

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
