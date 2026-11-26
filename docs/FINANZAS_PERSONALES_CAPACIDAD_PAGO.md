# F1 — Finanzas personales y capacidad de pago

**Estado:** diseño de producto; todavía no implementado.  
**Seguimiento:** [issue #375](https://github.com/JavierGrecco/prestamos_privados/issues/375).  
**Prioridad:** evolución **Post-MVP**; no bloquea ni reemplaza la aceptación de [#223](https://github.com/JavierGrecco/prestamos_privados/issues/223).

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

La sección puede organizarse alrededor de cuatro vistas relacionadas.

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

1. Ingresos recurrentes netos utilizados, período observado y calidad del dato.
2. Gastos esenciales fijos y variables.
3. Otros gastos y presupuesto discrecional.
4. Servicio mensual de las deudas actuales.
5. Cuota nueva y servicio total de deuda después de incorporarla.
6. Relación entre deuda mensual e ingresos netos recurrentes, con numerador y denominador visibles.
7. Margen disponible antes y después de la cuota.
8. Menor saldo mensual proyectado y meses que resultarían deficitarios durante el plazo.
9. Reserva líquida declarada y meses aproximados de cobertura de gastos esenciales, solo cuando existan datos suficientes.
10. Supuestos que más cambian el resultado.

El porcentaje de ingresos comprometido por deudas es un indicador útil, pero no basta por sí solo. Dos personas con el mismo porcentaje pueden tener niveles de ingreso residual, estabilidad laboral, gastos esenciales y reservas muy diferentes.

La guía pública argentina de endeudamiento responsable menciona como orientación general no superar aproximadamente el 40% de los ingresos mensuales en compromisos de deuda. Ese valor no debe convertirse en una regla universal, una frontera automática ni una aprobación/rechazo del sistema. Se debe mostrar como referencia contextual y explicar que la capacidad también depende del dinero que queda para vivir, la estabilidad de ingresos, otras obligaciones y la liquidez disponible.

## 7. Escenarios y riesgo de asumir el compromiso

La persona debe poder cambiar supuestos sin alterar los registros reales ni el contrato del préstamo. Escenarios iniciales:

- pérdida o interrupción de uno de los ingresos;
- reducción de los ingresos variables;
- aumento de alimentos, alquiler, servicios u otros gastos esenciales;
- gasto extraordinario;
- demora de un cobro;
- variación cambiaria cuando existan ingresos y obligaciones en monedas distintas.

Para cada escenario mostrar los meses afectados, el saldo disponible y el déficit acumulado si lo hubiera. No se deben presentar escenarios como pronósticos ni elegir uno silenciosamente como “el correcto”.

No se propone un puntaje de riesgo opaco. La explicación debe ser comprensible y permitir responder: qué dato hace que el compromiso sea más exigente, cuándo aparece el primer déficit y qué cambio de supuesto altera más el resultado.

## 8. Datos, moneda y estados

Los datos deben conservar su significado y su historia.

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

## 10. Arquitectura propuesta

Mantener las responsabilidades actuales del proyecto:

- **Dominio:** tipos, clasificación, recurrencias y cálculos puros de presupuesto/margen/escenarios.
- **Aplicación:** casos de uso de registro y corrección, consultas mensuales y evaluación de nueva cuota.
- **Infraestructura:** tablas y repositorios SQLite, migraciones, persistencia transaccional y auditoría.
- **UI:** formularios de carga, resumen, categorías, presupuesto y comparador de cuota; no contiene fórmulas monetarias propias.

Los registros personales deben mantenerse separados del ledger de préstamos, de las inversiones y de los planes internos de reposición. La integración se realiza a través de consultas públicas existentes, con identificadores de origen para controlar duplicados.

No introducir microservicios, una segunda base de datos o una infraestructura distribuida solo para agregar esta sección. Primero se debe lograr un módulo local bien delimitado y probado.

## 11. Entrega por etapas

1. **Diseño y decisiones:** titularidad, permisos, categorías, moneda, fechas, tarjeta, recurrencias, transferencias y no duplicación.
2. **Registro personal básico:** ingresos, gastos, categorías y obligaciones externas con carga manual.
3. **Presupuesto:** importes previstos, ejecución real, comparación por mes y reportes explicables.
4. **Planificación integrada:** combinar la información personal con los flujos futuros M3 y cuotas internas, con corte común y trazabilidad de origen.
5. **Capacidad de pago:** sumar una cuota candidata, medir saldo mensual y probar escenarios durante todo el plazo.
6. **Importación:** evaluar CSV validado y conciliación asistida. Voz, fotos, lectura de resúmenes, inteligencia artificial externa y conexión bancaria quedan fuera hasta aprobar privacidad y pruebas de precisión.

Esta evolución no debe distraer ni sustituir el cierre de los recorridos de préstamos y reposición del MVP local.

## 12. Pruebas y aceptación

Antes de presentar F1 como utilizable, cubrir al menos:

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

Estas referencias orientan la experiencia y la educación financiera; no sustituyen asesoramiento profesional ni definen por sí solas una regla crediticia.
