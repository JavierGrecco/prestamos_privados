# F1 — Finanzas personales y capacidad de pago

**Estado:** evolución F1 parcialmente implementada. PR #398 agregó cobros externos declarados por fecha; PR #400 los consolidó con cobros contractuales del sistema en una única proyección temporal; PR #402 incorporó comparación contra todas las cuotas y fechas de una nueva propuesta generada por el simulador oficial (1–360 cuotas; reserva limitada a los primeros 1–24 vencimientos elegidos). PR #404, integrada en `main` como [`d68a696`](https://github.com/JavierGrecco/prestamos_privados/commit/d68a696c0f8efef2ab6dd3a96a6e440ce1f0954c), distingue cobros externos `DECLARADO` y `REFERENCIA_DOCUMENTAL_DECLARADA`; la referencia se ingresa como texto y no representa un documento recibido o verificado. PR #418, integrada como [`355237e`](https://github.com/JavierGrecco/prestamos_privados/commit/355237ea5a1d89016a134b942b3939c906cf7e61), agrega la transición declarada a recibido y, cuando el dinero sigue disponible y no estaba incluido en el margen, actualiza la reserva líquida de la sesión. Los datos continúan en ARS y solo en sesión; no se crean pagos ni se persisten movimientos personales. Permanecen pendientes la verificación real de evidencia, la conciliación contable persistida, el presupuesto guiado y el registro detallado. Seguimiento: [#375](https://github.com/JavierGrecco/prestamos_privados/issues/375) y [#381](https://github.com/JavierGrecco/prestamos_privados/issues/381).
**Seguimiento:** [issue #375](https://github.com/JavierGrecco/prestamos_privados/issues/375).  
**Prioridad:** evolución **Post-MVP**; no bloquea ni reemplaza la aceptación de [#223](https://github.com/JavierGrecco/prestamos_privados/issues/223).


## Addendum funcional — recepción de cobros externos y actualización de reserva (27/11/2026)

La transición quedó integrada en `main` mediante la [PR #418](https://github.com/JavierGrecco/prestamos_privados/pull/418), commit [`355237e`](https://github.com/JavierGrecco/prestamos_privados/commit/355237ea5a1d89016a134b942b3939c906cf7e61).

- Un cobro externo pendiente puede marcarse como recibido y, si el importe completo sigue disponible, sumarse a **Ahorro líquido disponible hoy**.
- También se puede registrar como recibido sin sumarlo a la reserva cuando ya se utilizó.
- Si el cobro ya estaba incluido en el margen libre declarado, la acción de recepción no lo suma de nuevo a la reserva.
- Al convertirlo en recibido, deja de participar como cobro futuro; se registra la fecha de recepción declarada y se invalida el cálculo anterior para obligar a recalcular.
- La transición es solo de sesión. No verifica el cobro, no crea un movimiento real persistido ni escribe en SQLite, ledger o auditoría. Los valores desaparecen al cerrar la sesión y no deben confundirse con una conciliación contable.
- Si solo una parte del importe sigue disponible, registrá el cobro como recibido/utilizado y ajustá manualmente el total de ahorro líquido a lo que realmente permanece disponible.
- Validación de PR #418: 1.442 pruebas aprobadas y 2 omitidas por cada Python 3.11–3.14, sin advertencias; Chromium 2/2, CodeQL y auditoría de dependencias aprobados.

La mejora completa la transición práctica descrita en #381, sin adelantar la persistencia personal ni alterar el alcance Post-MVP.

## Estado de implementación — primer corte funcional

La **modalidad directa de margen libre declarado** ya está disponible desde **Mi espacio**:

- La persona informa el dinero que suele quedarle libre al mes después de pagar gastos y obligaciones actuales, la nueva cuota que quiere evaluar y un colchón opcional.
- La cuenta muestra el remanente o faltante mensual y, si el margen es positivo, qué proporción del margen declarado consumiría la cuota.
- Puede declarar ahorros líquidos disponibles y la parte que quiere proteger. Solo el excedente se considera respaldo utilizable; no se suma al margen mensual.
- Puede probar un escenario de 1 a 24 meses con menos margen libre y ver cuántos meses completos podría cubrir el respaldo, cuánto consumiría y qué faltante seguiría sin cubrir.
- Las obligaciones actuales ya están incluidas en el margen declarado: el cálculo no vuelve a descontar cuotas de préstamos existentes.
- La información se trata como declarada, no como sueldo, gasto o saldo bancario verificado. No calcula DTI ni aplica el 40% cuando no se conoce el ingreso.
- El modo directo básico conserva la entrada manual de una cuota representativa. Como alternativa, la persona puede generar una propuesta con capital, plazo de 1–360 meses, fecha de inicio, tasa TNA/TEA y sistema francés/alemán. El cálculo reutiliza el simulador del alta y no crea ni guarda un préstamo.
- Para personas con rol inversor se muestra un calendario informativo de cobros contractuales proyectados para los próximos 365 días. En la evaluación temporal se consulta el read model oficial hasta 1.095 días, para cubrir los escenarios configurables de 1–24 meses.
- La persona puede declarar hasta 100 cobros externos por sesión, en ARS, con importe, fecha, origen y estado. Puede clasificarlos como `DECLARADO` o `REFERENCIA_DOCUMENTAL_DECLARADA`; en el segundo caso ingresa una referencia textual. No se adjuntan ni verifican documentos, y la clasificación no altera el peso financiero del cobro. Conserva la opción individual de indicar si cada entrada ya está incluida en el margen libre.
- La proyección de respaldo consolida ambos orígenes por fecha, pero mantiene separados sus subtotales y el importe correspondiente a cada período. No se reimplementa amortización ni se pide volver a cargar cuotas que ya administra el sistema.
- Para prevenir doble conteo, los cobros contractuales propios aparecen inicialmente marcados como ya incluidos en el margen; la persona puede desmarcarlo si sabe que no los contempló. Los cobros externos mantienen su marca individual.
- Los escenarios de fecha prevista, demora de 30/60 días y no recepción se aplican a ambos orígenes. Un flujo solo cubre vencimientos a partir de su fecha de disponibilidad; los vencidos y los que quedan fuera del horizonte se informan por separado.
- Los cobros recibidos o cancelados no se suman como futuros. Si una entrada ya se recibió y sigue disponible, se declara en la reserva líquida actual una sola vez.
- Los importes se conservan únicamente en el estado de la sesión. No se escriben en SQLite, ledger, auditoría ni exportaciones.

**Implementación:** `aplicacion/consultas/capacidad_pago_directa.py` y `ui/pagina_mi_espacio.py`. Las pruebas están en `tests/test_capacidad_pago_directa.py` y en la aceptación E2E de `tests/test_ui_e2e.py`.

Esta entrega no equivale a tener implementado todo F1. La proyección temporal integra cobros contractuales oficiales y cobros externos declarados; estos últimos no verifican contratos, solvencia del pagador ni recepción efectiva. Los parámetros y registros externos siguen solo en sesión, y las proyecciones del sistema tampoco son pagos garantizados. PR #402 compara cada cuota de la nueva propuesta contra el margen declarado y el escenario de margen reducido, pero la simulación de caja/reserva se limita a los primeros 1–24 vencimientos elegidos. No genera una proyección de caja de 360 meses ni supone que el margen estresado se mantenga durante todo el contrato. Siguen pendientes la calidad/evidencia de cobros externos, la conciliación al recibir, la cuenta guiada, el registro de ingresos/gastos, los presupuestos y la persistencia privada con autorización.


## 1. Propósito

La aplicación ya puede proyectar los cobros y pagos de préstamos que tiene registrados. Esa información no alcanza para saber cuánto dinero le queda a una persona al terminar el mes: no conoce necesariamente su sueldo, los gastos de vivienda y alimentación, otras deudas, compras en cuotas, efectivo disponible ni gastos anuales.

F1 propone completar esa perspectiva con una sección de **Finanzas personales**. Su finalidad es que la persona pueda:

- registrar y entender sus ingresos y gastos;
- preparar un presupuesto y comparar lo previsto con lo que realmente ocurrió;
- conocer el peso de sus compromisos actuales;
- estimar cuánto margen mensual conserva;
- analizar qué pasaría al sumar una cuota nueva;
- identificar meses difíciles y probar escenarios antes de comprometerse.

El resultado no será un veredicto automático sobre una persona. Será un análisis explicable: los datos, el período, las fuentes y los supuestos deben estar visibles para que la persona tome su propia decisión.

## 2. Qué aporta respecto de las funciones actuales

| Capacidad existente | Qué resuelve | Qué no resuelve |
|---|---|---|
| M2 — Posición financiera | Capital, cobros y pagos conocidos por el sistema | No representa todos los ingresos, gastos, ahorros y deudas externas |
| M3 — Planificación | Proyección de cuotas y flujos futuros de préstamos registrados | No es un presupuesto doméstico: no conoce sueldo ni gastos cotidianos |
| M6 — Reportes personales | Resume posición, planificación, rendimiento y escenarios disponibles | Excluye expresamente ingresos y gastos externos, efectivo, ahorros y otras deudas no registradas |
| M7 — Comparador | Compara operaciones registradas | No determina si el presupuesto personal soporta una cuota nueva |

F1 debe reutilizar estas capacidades donde corresponda. No debe duplicar M2, implementar un segundo M3 ni crear una matemática de préstamos alternativa.

## 3. Experiencia funcional propuesta

La sección debe ofrecer tres modalidades de entrada. Son alternativas de uso, no niveles de usuario ni requisitos que haya que completar en orden. Una persona puede empezar por el modo más simple y agregar detalle después, sin perder sus datos.

### 3.0 Tres modalidades: de menos a más detalle

**A. Ya sé cuánto me queda libre (entrada directa)**

La persona ingresa un único importe mensual estimado. No necesita informar sueldo, registrar gastos, clasificar compras ni detallar sus deudas.

La pregunta debe ser concreta:

> ¿Cuánto dinero suele quedarte disponible cada mes después de pagar tus gastos habituales y las cuotas/deudas que ya tenés, pero antes de sumar el préstamo que estás evaluando?

Ayuda debajo del campo:

- Incluí alquiler, servicios, comida, transporte, salud y otros gastos normales.
- Incluí cuotas de préstamos, tarjetas y demás compromisos actuales.
- No incluyas la cuota del nuevo préstamo que estás simulando.
- Ingresá lo que habitualmente te queda, no tu sueldo ni el saldo total de tu cuenta.

Dato obligatorio: margen mensual libre estimado, moneda y fecha de referencia. Todo se conserva como **DECLARADO por la persona**, nunca como ingreso verificado ni como movimiento real.

Datos opcionales, sin hacer más largo el primer registro:
- cuánto suele quedar en un mes más ajustado;
- cuánto desea conservar cada mes como colchón y no comprometer;
- una nota breve sobre estacionalidad o cambios previsibles.

El valor se aplica como hipótesis mensual para los vencimientos de la propuesta. Si la persona informa un valor conservador, se presenta junto al habitual. Si no lo informa, el sistema no inventa una baja de ingresos ni aplica un porcentaje arbitrario: permite que la persona configure escenarios de tensión más adelante.

**Regla para no duplicar obligaciones:** el margen declarado ya está después de pagar las cuotas y compromisos actuales. Por lo tanto, las cuotas conocidas por Préstamos Privados pueden mostrarse en el detalle informativo, pero no vuelven a restarse del margen directo. Solo se resta la nueva cuota evaluada y, si la persona lo configura, el colchón mensual que desea preservar.

**B. Quiero una cuenta rápida**

La persona informa algunos totales, sin registrar movimiento por movimiento:
- ingreso mensual neto habitual;
- gastos habituales totales;
- pagos mensuales de deudas y compromisos actuales;
- reserva o ahorro mensual que desea mantener.

La aplicación calcula un margen estimado. Esta modalidad permite ver de dónde sale el resultado, pero no requiere categorizar consumos ni llevar un registro diario. Debe advertir cuando falte alguno de los componentes o el período de referencia sea insuficiente.

**C. Quiero llevar mis finanzas completas**

La persona puede registrar ingresos y gastos, usar categorías, recurrencias, presupuestos, movimientos reales y reportes históricos. Es la modalidad más detallada, pero debe ser totalmente opcional.

Las tres modalidades alimentan una misma evaluación de capacidad de pago, conservando el método, la fecha, la moneda, el origen y la naturaleza del dato. Cambiar de modalidad no debe borrar ni reescribir datos históricos; se debe indicar cuál es la estimación vigente utilizada en cada análisis.



### 3.1 Resumen mensual

Una vista inicial en lenguaje cotidiano, con fecha de corte y período seleccionados:

- ingresos netos recurrentes;
- ingresos variables y extraordinarios, separados;
- gastos esenciales fijos;
- gastos esenciales variables;
- gastos discrecionales;
- vencimientos y compromisos financieros;
- ahorro o reserva planificada;
- saldo disponible del período;
- diferencia contra el presupuesto;
- próximos compromisos y meses que podrían terminar en déficit.

Cada indicador debe permitir abrir el detalle que lo compone. Un gráfico sin posibilidad de explicar sus cifras no es suficiente.

### 3.2 Movimientos

Registro manual, rápido y comprensible de ingresos y gastos. Cada movimiento debe conservar, como mínimo:

- fecha del hecho y, si aplica, fecha de registro;
- importe y moneda originales;
- tipo: ingreso o gasto;
- categoría y descripción opcional;
- naturaleza: recurrente, variable, extraordinaria o periódica;
- estado/origen del dato;
- medio de pago o cuenta opcional;
- referencia opcional para conciliarlo con un plan o una obligación.

La primera versión debe priorizar que cargar un movimiento sea sencillo. La carga manual será la fuente inicial; las importaciones CSV se pueden evaluar después con controles de duplicados y revisión antes de confirmar.

### 3.3 Presupuesto

Permitir definir objetivos mensuales por categoría y compararlos con el resultado real. El presupuesto no debe confundirse con un gasto ya ocurrido.

Las categorías iniciales pueden incluir:

- vivienda y servicios;
- alimentación;
- salud;
- transporte;
- educación;
- impuestos y obligaciones;
- comunicaciones;
- cuidado personal/familiar;
- ocio y compras discrecionales;
- otros.

Además de la categoría, el movimiento debe poder clasificarse como:

- **esencial fijo:** alquiler, seguro, cuota obligatoria o servicio recurrente;
- **esencial variable:** alimentos, transporte o servicios cuyo importe cambia;
- **discrecional:** gasto que se puede reducir o posponer;
- **extraordinario:** gasto no habitual;
- **periódico/anual:** patente, matrícula, seguro anual, mantenimiento u otro gasto que no vence todos los meses.

Un gasto anual debe contemplarse en la planificación mediante una reserva mensual equivalente, pero no se debe fingir que ese importe se pagó en cada mes. La pantalla debe diferenciar el pago real de la provisión sugerida.

### 3.4 Compromisos

Consolidar compromisos que afectan el dinero disponible:

- cuotas futuras de préstamos que ya administra la aplicación;
- compromisos externos declarados por la persona;
- tarjetas y compras en cuotas;
- alquileres y obligaciones periódicas relevantes;
- otras deudas, con saldo, cuota, vencimiento y fecha de finalización cuando se conozcan.

Los compromisos que ya provengan de un préstamo interno deben importarse mediante las consultas oficiales del producto y no volver a cargarse como deuda externa.

### 3.5 Respaldo de liquidez y cobros a favor

El margen libre mensual y el capital de respaldo deben ser dos datos separados. El margen responde cuánto suele quedar luego de los gastos y obligaciones actuales; la reserva responde cuánto dinero acumulado podría usar la persona ante un bache temporal.

**Reserva líquida disponible hoy**

La persona puede declarar, sin obligación, dinero al que realmente podría acceder ahora: efectivo o saldo bancario disponible. También indica cuánto prefiere mantener fuera de uso. La cuenta usa:

`respaldo utilizable = max(0, reserva líquida disponible − reserva protegida)`

No se debe sumar la reserva al ingreso ni al margen mensual, porque se estaría presentando el mismo capital como si se generara todos los meses. Tampoco se debe asumir que todo el ahorro es sacrificable: la persona decide qué parte protege.

En la primera versión, el valor es declarado y temporal en sesión. No se valida contra un banco ni se conserva como un saldo real. No equivale a medir meses de gastos esenciales, porque el modo directo no solicita esos gastos.

**Mes de margen reducido**

La persona puede declarar cuánto le quedaría libre en un período difícil, después de gastos y compromisos actuales, pero antes de la nueva cuota. Puede indicar durante cuántos meses supone que podría repetirse esa situación. Se calcula el faltante de ese escenario y se compara con el respaldo utilizable.

El sistema debe informar:
- faltante mensual después de la nueva cuota y el colchón;
- dinero necesario para cubrir todos los meses indicados;
- cantidad de meses completos que la reserva alcanzaría a cubrir;
- saldo de reserva que quedaría, o faltante que todavía no podría cubrirse.

Este resultado es un escenario repetido, no una predicción de ingresos, ni una garantía de pago. No debe presentarse como “meses de gastos cubiertos” cuando no se conocen los gastos esenciales.

**Cobros futuros a favor**

Un importe que otra persona, cliente, entidad o inversión deberá pagarle al usuario no es efectivo disponible hoy. Se registra como **cobro esperado**, con importe, moneda, fecha prevista, origen y calidad del dato. Se convierte en disponibilidad real solo cuando el cobro se recibe y registra.

**Primera integración disponible en Mi espacio:** para personas con rol INVERSOR, el sistema muestra los cobros proyectados de préstamos propios con fecha contractual individual, identificador/número de préstamo e importe ARS. La consulta reutiliza `AnalisisFinancieroQuery.flujos_proyectados`; no implementa amortización ni crea movimientos. El horizonte visible es de 365 días. El usuario puede comparar fecha prevista, demora uniforme de 30 días, demora de 60 días y ausencia de cobro dentro del horizonte.

Esta vista sigue siendo informativa y de solo lectura: no crea pagos, asientos de ledger ni movimientos reales. PR #400 también incorpora estos flujos contractuales a la proyección temporal de respaldo junto con los cobros externos declarados. Antes de sumarlos, la interfaz pregunta si ya fueron considerados en el margen libre; el valor inicial es conservador para evitar el doble conteo. La procedencia se conserva en los subtotales y en cada período. La demora y la no recepción son hipótesis elegidas, no pronósticos. Los cobros externos siguen siendo declarados, no verificados.

PR #402 amplía la primera integración: al proponer un préstamo, se reutiliza la tabla del simulador oficial para comparar el importe y vencimiento de cada una de sus cuotas. El modo admite sistemas francés/alemán y TNA/TEA, y no crea una operación real. La reserva y los cobros se simulan contra los primeros 1–24 vencimientos elegidos; el resto del cronograma solo se compara contra el margen declarado.
Reglas obligatorias:
- Un cobro esperado no puede cubrir una cuota cuyo vencimiento sea anterior a la fecha estimada de recepción.
- Los cobros regulares que ya estén incluidos en el margen mensual declarado no se vuelven a sumar como cobros adicionales.
- Los cobros provenientes de préstamos e inversiones ya gestionados por la aplicación se obtienen desde las consultas oficiales existentes; no se duplican mediante una carga manual.
- El capital todavía colocado o pendiente de devolución no es reserva líquida. Solo sus cobros proyectados, en su fecha correspondiente, pueden entrar a una proyección de caja.
- Un cobro declarado o documentado sigue siendo incierto hasta su recepción. La aplicación no debe inventar una probabilidad de cobro ni tratar un compromiso de pago como garantía.
- Deben poder compararse, como mínimo, el escenario esperado, un retraso configurable (por ejemplo 30 o 60 días) y la ausencia de ese cobro dentro del horizonte.
- Si el cobro no se concreta en la fecha, no debe seguir figurando como dinero disponible; el escenario debe reflejar el faltante y la reserva restante.

Los activos no líquidos —vehículos, propiedades, mercadería, inversiones que requieren rescate o capital prestado a terceros— se muestran por separado. No se suman al respaldo por su valor nominal. Una futura versión podrá considerar su valor neto de realización, costos, plazo de liquidación y riesgo, con supuestos visibles.

**Relación con las decisiones de crédito**

Los cálculos existentes de adelantos, pagos parciales, pagos incompletos y falta de pago deben seguir siendo la autoridad para explicar cuánto cuesta cada alternativa. La nueva vista puede comparar sus efectos sobre la caja personal: por ejemplo, cuánto interés se ahorra al adelantar y cuánto respaldo líquido se consume con ese adelanto. Una cuota impaga o parcial puede mostrarse como escenario de costo y deuda remanente, nunca como una forma recomendada de financiar el presupuesto ni como sustituto de una reserva.

## 4. Reglas para no contar el mismo dinero dos veces

Este es uno de los puntos más importantes del diseño.

### Tarjetas de crédito

La compra se registra como gasto en la fecha de consumo o en las fechas de las cuotas según una política explícita que se defina para el presupuesto. El pago posterior del resumen cancela una obligación: no puede sumarse nuevamente como si fuera otro gasto de consumo.

La aplicación debe permitir conciliar compras, cuotas y pagos del resumen sin duplicar el impacto. Antes de implementar, la decisión debe quedar cubierta por ejemplos y pruebas.

### Transferencias entre cuentas propias

Mover dinero entre dos cuentas de la misma persona no es ingreso ni gasto. Se registra como transferencia para que no infle ambos lados del presupuesto.

### Cuotas y deudas

Una cuota de un préstamo que ya está dentro de Préstamos Privados debe entrar una sola vez. Una obligación externa puede registrarse manualmente, pero debe identificarse su origen para evitar que también se importe desde otra fuente.

### Ahorro y reserva

Separar dinero para ahorrar reduce el dinero que la persona considera disponible, pero no es un gasto de consumo. Debe aparecer como asignación o transferencia a reserva, no mezclarse con compras o servicios.

## 5. Ingresos: estabilidad y calidad de la información

Los ingresos necesitan más contexto que un importe mensual:

- recurrentes y relativamente estables;
- variables o estacionales;
- extraordinarios y no recurrentes;
- netos o brutos, indicando cuál se cargó;
- frecuencia de cobro y fecha estimada;
- moneda;
- fuente y calidad de la información.

No se debe considerar un bono, venta eventual o ingreso extraordinario como si fuera sueldo permanente. Para actividad independiente o ingresos variables, el análisis debe mostrar el período observado y permitir comparar el promedio con un escenario conservador. Si hay pocos meses de datos, debe advertirlo en lugar de producir una falsa precisión.

## 6. Evaluación de una nueva cuota

La función diferencial de F1 es comparar el presupuesto personal **sin** la nueva operación y **con** la cuota que se propone.

El cronograma de la propuesta debe provenir del simulador/preview oficial de préstamos. F1 no implementará una fórmula alternativa de amortización ni estimará una cuota por su cuenta.

Como lectura mensual inicial, el margen se puede explicar con esta estructura:

**Margen antes de la nueva cuota = ingresos netos recurrentes − gastos esenciales − compromisos actuales − reserva para gastos periódicos − ahorro planificado.**

Luego se compara ese margen con cada cuota del cronograma propuesto y se calcula el saldo resultante mes a mes. Los gastos discrecionales también deben poder verse y someterse a escenarios, pero no deben desaparecer del análisis solo porque la persona podría recortarlos.

### Indicadores que debe presentar

En la **entrada directa**, mostrar especialmente:
- margen mensual declarado antes del nuevo crédito;
- importe de la nueva cuota tomado del cronograma oficial;
- dinero que quedaría libre después de pagar esa cuota;
- proporción del margen declarado que consumiría la nueva cuota;
- meses en los que el margen posterior sería negativo o quedaría por debajo del colchón que la persona quiera preservar.

La proporción cuota/margen libre **no es una relación deuda/ingresos (DTI)**. No se calcula ni se etiqueta como tal porque el usuario no informó sus ingresos. En este modo tampoco se debe mostrar el 40% como si fuera un umbral aplicable a su situación: no conocemos el denominador de ingresos.

La cuenta debe ser visible y reproducible:

`margen_remanente_mes = margen_libre_declarado − cuota_nueva_del_mes − colchón_mensual_opcional`

Ejemplo ilustrativo: margen declarado ARS 250.000, cuota nueva ARS 160.000 y colchón elegido ARS 20.000 → remanente estimado ARS 70.000. Si la cuota supera el margen, mostrar el faltante; no bloquear el análisis ni presentar una aprobación/rechazo. Si la cuota varía, evaluar cada vencimiento del cronograma, sin reemplazarlo por un promedio. Si el margen declarado es cero o negativo, se conserva y se explica el déficit previo a la nueva cuota.

Cuando solo hay un importe mensual declarado, repetirlo en el horizonte es una hipótesis explícita, no una predicción. La persona puede mejorar esa hipótesis informando un margen menor para meses ajustados o usando el modo de cuenta rápida. Registrar fecha de actualización y guardar el valor/metodología usados en el snapshot de cada evaluación para poder reconstruirla después.


1. Ingresos recurrentes netos utilizados, período observado y calidad del dato.
2. Gastos esenciales fijos y variables.
3. Otros gastos y presupuesto discrecional.
4. Servicio mensual de las deudas actuales.
5. Cuota nueva y servicio total de deuda después de incorporarla.
6. Relación entre pagos de deuda e ingresos, solo cuando se hayan informado ambos datos y con numerador/denominador visibles; no llamar DTI a una relación calculada sobre ingresos netos.
7. Margen disponible antes y después de la cuota.
8. Menor saldo mensual proyectado y meses que resultarían deficitarios durante el plazo.
9. Reserva líquida declarada, parte protegida y respaldo realmente utilizable. En modo directo, mostrar cobertura de los faltantes del escenario que la persona configuró; solo estimar meses de gastos esenciales cuando se conozca ese presupuesto.
10. Supuestos que más cambian el resultado.

El porcentaje de ingresos comprometido por deudas es un indicador útil cuando se conocen los ingresos y todas las obligaciones que integran el numerador. En la entrada directa se informa margen residual, no salario: el sistema no puede deducir ni reconstruir el ingreso bruto a partir de ese valor. Por eso debe presentar el consumo del margen libre, no un DTI.

 Dos personas con el mismo porcentaje pueden tener niveles de ingreso residual, estabilidad laboral, gastos esenciales y reservas muy diferentes.

La guía pública argentina de endeudamiento responsable menciona como orientación general no superar aproximadamente el 40% de los ingresos mensuales en compromisos de deuda. Ese valor no debe convertirse en una regla universal, una frontera automática ni una aprobación/rechazo del sistema. Se debe mostrar como referencia contextual y explicar que la capacidad también depende del dinero que queda para vivir, la estabilidad de ingresos, otras obligaciones y la liquidez disponible.

## 7. Escenarios y riesgo de asumir el compromiso

La persona debe poder cambiar supuestos sin alterar los registros reales ni el contrato del préstamo. Los escenarios deben separar la caja disponible hoy de los cobros todavía no recibidos. Escenarios iniciales:

- pérdida o interrupción de uno de los ingresos;
- reducción de los ingresos variables;
- aumento de alimentos, alquiler, servicios u otros gastos esenciales;
- gasto extraordinario;
- demora de un cobro o ausencia de recepción dentro del horizonte;
- variación cambiaria cuando existan ingresos y obligaciones en monedas distintas.

Para cada escenario mostrar los meses afectados, el saldo disponible y el déficit acumulado si lo hubiera. No se deben presentar escenarios como pronósticos ni elegir uno silenciosamente como “el correcto”.

No se propone un puntaje de riesgo opaco. La explicación debe ser comprensible y permitir responder: qué dato hace que el compromiso sea más exigente, cuándo aparece el primer déficit y qué cambio de supuesto altera más el resultado.

## 8. Datos, moneda y estados

Los datos deben conservar su significado y su historia.

### Disponibilidad de activos y cobros

Además del estado del dato, cada recurso debe tener una disponibilidad económica explícita:

- **LIQUIDO_DISPONIBLE:** efectivo o saldo al que puede accederse hoy.
- **RESERVADO:** parte de la liquidez que la persona decidió no comprometer.
- **COBRO_PROYECTADO:** importe esperado con una fecha prevista; no es caja antes de recibirse.
- **NO_LIQUIDO:** activo o capital que requiere venta, rescate, vencimiento o recupero para convertirse en efectivo.
- **REAL_RECIBIDO:** cobro que ocurrió y fue registrado; recién entonces incrementa la caja real.

La fecha de cobro proyectada, la fecha contractual de vencimiento y la fecha efectiva de recepción deben conservarse por separado cuando no coincidan. La reserva no puede incluir simultáneamente el mismo importe que figura como cobro futuro.

### Naturaleza del dato

Como mínimo, separar:

- **REAL:** movimiento ocurrido y registrado;
- **DECLARADO:** dato informado por la persona, todavía no conciliado con evidencia externa;
- **PRESUPUESTADO:** objetivo o límite que la persona planea;
- **PROYECTADO:** movimiento futuro estimado a partir de recurrencias o compromisos.

Un dato documentado no se debe llamar “verificado por el banco” si no hubo una integración que realmente lo compruebe.

### Moneda

Guardar el importe y la moneda originales. Para mostrar equivalencias, conservar cotización, fecha, fuente, tipo de cambio y convención utilizada. No actualizar silenciosamente el valor histórico de una compra en ARS porque cambió la cotización del dólar.

### Correcciones y recurrencias

Una corrección debe conservar una traza del cambio. Una recurrencia genera ocurrencias proyectadas; solo se convierte en movimiento real cuando la persona confirma que ocurrió o lo concilia con una importación. Cambiar el importe de una plantilla recurrente no reescribe movimientos reales anteriores.

Los importes monetarios deben representarse mediante <code>Decimal</code>, persistirse con precisión decimal explícita y no depender de <code>float</code> para sumar o comparar dinero.

## 9. Titularidad, privacidad y permisos

Los gastos, ingresos, deudas y reservas permiten inferir información sensible sobre la vida de una persona. Por lo tanto, no son simplemente otra pantalla de la cartera de préstamos.

- El perfil financiero personal debe pertenecer a la cuenta local autenticada que lo creó.
- La asociación cuenta-persona existente puede usarse como vínculo explícito de contexto, pero no se debe deducir por coincidencia de nombres.
- El selector global de persona no debe abrir ni cambiar la titularidad de las finanzas personales.
- Ser ADMIN de la aplicación no debe otorgar acceso ordinario automático al contenido privado de cada perfil.
- La autorización debe verificarse en los casos de uso/consultas, no solamente ocultando opciones de navegación.
- Un prestamista u operador no debe ver el presupuesto, sueldo, consumos ni deudas externas de un deudor por el mero hecho de administrar un préstamo.
- Cualquier informe que la persona decida compartir debe ser generado y confirmado expresamente por el titular, con fecha de corte, datos incluidos y advertencias sobre los datos declarados.

**Límite importante:** una cuenta ADMIN con acceso al equipo y al archivo SQLite puede tener capacidad técnica de acceder a la base. El control de permisos de la aplicación no equivale a cifrado de datos en reposo. Antes de usar esta información en un entorno compartido o remoto será obligatorio revisar cifrado, backups, retención, acceso privilegiado y recuperación. La primera etapa se limita a uso local; no incorpora acceso remoto ni sincronización cloud.

Los importes y supuestos transitorios de **Mi espacio** residen en el estado de la sesión de Streamlit; no se guardan en SQLite. Al cerrar sesión, al detectar que la sesión de autenticación perdió vigencia (por desactivación, cambio de credenciales, permisos o vínculo de persona) o al entrar en estado no autenticado, la aplicación elimina todas las claves `mi_espacio_*`. Esto evita que los datos personales ingresados vuelvan a aparecer al iniciar sesión con otra cuenta en la misma sesión del navegador. La limpieza no reemplaza las medidas de seguridad del dispositivo ni implica cifrado de memoria.

## 10. Arquitectura propuesta

Mantener las responsabilidades actuales del proyecto:

- **Dominio:** tipos, clasificación, recurrencias y cálculos puros de presupuesto/margen/escenarios.
- **Aplicación:** casos de uso de registro y corrección, consultas mensuales y evaluación de nueva cuota.
- **Infraestructura:** tablas y repositorios SQLite, migraciones, persistencia transaccional y auditoría.
- **UI:** formularios de carga, resumen, categorías, presupuesto y comparador de cuota; no contiene fórmulas monetarias propias.

Los registros personales deben mantenerse separados del ledger de préstamos, de las inversiones y de los planes internos de reposición. La integración se realiza a través de consultas públicas existentes, con identificadores de origen para controlar duplicados.

No introducir microservicios, una segunda base de datos o una infraestructura distribuida solo para agregar esta sección. Primero se debe lograr un módulo local bien delimitado y probado.

## 11. Entrega por etapas

1. **Diseño y decisiones:** titularidad, permisos, definiciones del margen libre, moneda, corte, tratamiento de tarjetas, recurrencias, transferencias y reglas contra el doble conteo.
2. **Capacidad y respaldo de liquidez — primera versión funcional:** margen libre, cuota, colchón, ahorro líquido, reserva protegida y escenario repetido de margen ajustado. Es temporal, solo ARS y usa una cuota mensual representativa.
3. **Cobros futuros por fecha — integrado:** la simulación consolida proyecciones oficiales del rol inversor y cobros externos declarados, conserva procedencia y admite escenarios de fecha, demora/no recepción. Sigue pendiente la conciliación al recibir y la calidad/evidencia de los cobros externos.
4. **Cuenta rápida:** totales opcionales de ingresos, gastos, deudas y reserva, sin movimientos individuales.
5. **Finanzas completas:** registro manual de ingresos y gastos, categorías, presupuestos, recurrencias y reportes.
6. **Planificación contractual — primera comparación integrada:** se compara cada cuota del cronograma generado por el simulador oficial con el margen habitual y ajustado. La proyección de reserva/cobros se limita a los primeros 1–24 vencimientos elegidos; ampliar el análisis de caja a plazos mayores requiere supuestos explícitos y validación adicional.
7. **Importación:** evaluar CSV validado y conciliación asistida. Voz, fotos, lectura de resúmenes, inteligencia artificial externa y conexión bancaria quedan fuera hasta aprobar privacidad y pruebas de precisión.

La primera entrega no reemplaza la aceptación del MVP local ni habilita acceso de prestamistas a los datos personales del titular.

## 12. Pruebas y aceptación

Antes de presentar F1 como utilizable, cubrir al menos:

- evaluación de cuota con solo un margen libre declarado, sin sueldo, gasto ni movimientos registrados;
- margen directo neto de gastos y obligaciones actuales, sin volver a restar cuotas conocidas;
- cuota nueva mayor, igual o menor que el margen disponible y cálculo del saldo remanente;
- margen conservador opcional, colchón mensual y escenario de caída adicional;
- monedas incompatibles sin conversión silenciosa ni tipo de cambio implícito;
- vencimientos variables que se comparan mes por mes con el cronograma oficial;
- sueldo fijo, ingresos variables y meses sin ingresos;
- ingresos extraordinarios que no se convierten en base recurrente;
- gasto mensual variable y gasto anual;
- categoría esencial y discrecional;
- recurrencias modificadas sin reescribir el historial;
- compras con tarjeta, cuotas y pago del resumen sin doble conteo;
- transferencias propias que no alteran ingresos/gastos;
- deuda externa y cuotas de préstamos del sistema sin duplicación;
- importes ARS/USD y cotizaciones históricas preservadas;
- mes deficitario y reserva insuficiente;
- cuota nueva que comienza o termina dentro del horizonte;
- stress tests por pérdida de ingreso, aumento de gastos y gasto inesperado;
- protección entre cuentas y denegación de acceso a perfiles ajenos;
- respaldo y restauración de datos personales sin exponerlos en logs, fixtures o documentación.

Los criterios detallados, dependencias y decisiones abiertas se siguen en el [issue #375](https://github.com/JavierGrecco/prestamos_privados/issues/375).

## 13. Referencias de diseño

- [Argentina.gob.ar — Presupuesto y ahorro](https://www.argentina.gob.ar/economia/inclusion-financiera/presupuesto-y-ahorro): registrar ingresos y gastos, distinguir necesidades y deseos, comparar presupuesto con resultado real y planificar ahorros.
- [Argentina.gob.ar — Endeudamiento responsable](https://www.argentina.gob.ar/economia/inclusion-financiera/endeudamiento-responsable): evaluar el peso de las deudas sobre los ingresos y reconocer el riesgo de sobreendeudamiento.
- [CFPB — Monthly payment worksheet](https://files.consumerfinance.gov/f/documents/cfpb_buying-a-house_monthly-payment_worksheet.pdf): referencia metodológica para separar ingreso neto, deudas, gastos, ahorro y obligaciones nuevas. Se usa como patrón de estructura de cálculo, no como norma argentina.
- [CFPB — Debt-to-income ratio](https://www.consumerfinance.gov/ask-cfpb/what-is-a-debt-to-income-ratio-en-1791/): define DTI como pagos mensuales de deuda divididos por ingreso bruto mensual. F1 preserva esta distinción y no calcula DTI cuando el ingreso no se captura.

Estas referencias orientan la experiencia y la educación financiera; no sustituyen asesoramiento profesional ni definen por sí solas una regla crediticia.
