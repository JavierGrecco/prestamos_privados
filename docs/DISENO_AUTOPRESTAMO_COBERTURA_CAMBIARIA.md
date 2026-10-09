# Diseño: autopréstamo, reposición de capital y cobertura cambiaria

**Estado:** diseño funcional y financiero; pendiente de implementación y revisión jurídica.  
**Issue:** [#194 — Autopréstamo, roles coincidentes y cobertura cambiaria por unidad de valor](https://github.com/JavierGrecco/prestamos_privados/issues/194)

## 1. El problema que debe resolver el producto

Una persona puede retirar ahorros/inversiones para comprar un auto al contado, evitar una financiación comercial costosa y luego reponer el capital mes a mes. Quiere saber si ese plan reconstruye los ahorros y cuánto valor conserva con el tiempo.

Hay tres resultados distintos:
1. **Reposición nominal:** volver a separar en el futuro la misma cantidad de pesos.
2. **Conservación de valor:** reconstruir una cantidad equivalente de una unidad de referencia, por ejemplo USD.
3. **Ganancia:** reconstruir el capital inicial y además obtener un rendimiento positivo medido en la misma unidad.

No deben presentarse como sinónimos. El cambio del valor de un saldo convertido a dólares tampoco es por sí mismo efectivo cobrado ni ganancia realizada.

## 2. Autopréstamo, préstamo real y compra conjunta

La aplicación debe permitir que una persona cumpla más de un rol en la misma operación. Actualmente el documento de roles del proyecto indica que el deudor no puede ser inversor de su propio préstamo; ese rechazo debe revisarse, no eliminarse sin distinguir el caso de uso.

- **Autopréstamo/plan interno:** una persona compra el auto con fondos propios y se compromete consigo misma a reponer la cartera. Sirve para presupuestar, medir disciplina de ahorro y fijar una meta. No crea un acreedor distinto ni una deuda jurídicamente exigible contra sí misma. En patrimonio consolidado, el crédito y la deuda internos se eliminan.
- **Préstamo real a la pareja:** una persona aporta fondos y la otra los recibe. Si pactan una obligación real, deben documentar moneda, fechas, tasa, carencia, pagos anticipados e incumplimientos.
- **Compra conjunta:** ambos aportan capital y se benefician del bien. Debe registrarse cuánto puso cada persona y qué parte se pretende reponer; no suponer que el total es deuda de una persona ni inferir solidaridad legal.
- **Financiación mixta:** una parte puede ser aporte propio interno y otra un préstamo real de la pareja. Separar ambos tramos evita atribuir interés externo a fondos propios.

Los roles de inversor/aportante y deudor deben poder coincidir por persona y operación para seguimiento interno. La relación interna o entre partes distintas debe quedar explícita. Los paneles individuales pueden mostrar el plan; el patrimonio consolidado no debe contar una cuenta por cobrar a uno mismo como riqueza adicional. En un hogar con varias personas, una vista consolidada opcional puede eliminar saldos e intereses internos sin borrar las posiciones individuales.

## 3. Separar moneda contractual, referencia y moneda pagada

No usar un único campo ambiguo llamado moneda. El modelo debe distinguir:

- moneda del desembolso real (p. ej., ARS);
- moneda/unidad contractual (ARS nominal o USD);
- unidad de referencia usada para medir conservación (USD MEP, por ejemplo, o UVA/CER);
- moneda e importe efectivamente entregados en cada pago;
- moneda usada en reportes.

La unidad de referencia no cambia automáticamente la moneda contractual. Una obligación denominada en USD, una deuda en pesos referenciada al dólar y un plan interno de reconstrucción de USD son tratamientos distintos.

## 4. Alternativas a comparar

| Modalidad | Cálculo | Qué aporta | Limitación |
|---|---|---|---|
| **ARS nominal** | Capital y cuotas en ARS; tasa en ARS | Cuota nominal previsible | Puede perder valor real y en USD |
| **USD denominados** | Capital, saldo, interés y cuota calculados en USD | Conserva las unidades USD de la obligación si se cumple lo pactado | El deudor asume el riesgo cambiario |
| **ARS referenciados al dólar** | La deuda se expresa en pesos por una regla de cambio | Intenta seguir una cotización | La validez de una deuda en pesos indexada requiere análisis jurídico específico |
| **UVA/CER** | Valor expresado en unidades cuyo valor sigue el CER | Referencia a inflación | No garantiza equivalencia en USD ni al precio de un auto |
| **Plan interno de reposición en USD** | Meta y recuperación medidas en unidades USD | Mide cuántos USD de referencia se reconstruyen | No crea cobertura de mercado si los pagos y ahorros futuros siguen en ARS |

La recomendación de producto es comparar estas alternativas como escenarios, pero no habilitarlas todas como contratos reales hasta verificar su tratamiento normativo y transaccional.

### Para el cambio del auto

Si el objetivo central es reconstruir una reserva que conserve su valor en dólares, una unidad USD explícita es un benchmark económico razonable. La tasa, si se busca ganancia, también debe expresarse en USD; no se debe aplicar automáticamente una TNA/TEA en pesos como si fuese una tasa en dólares.

- **Solo conservar capital:** simular tasa de interés USD del 0% y reponer la misma cantidad de unidades USD iniciales.
- **Buscar ganancia USD:** establecer una tasa en USD expresamente elegida. Separar capital, interés USD, equivalente en ARS y rendimiento anualizado de flujos fechados.
- La tasa adecuada no se infiere de elecciones o de una predicción cambiaria; se decide comparando inversiones reales, liquidez, riesgo, costos e impuestos.

Un plan interno no produce por sí mismo el rendimiento que habría obtenido la inversión retirada. Puede ayudar a reconstruir la cartera en el futuro; solo hay ganancia externa si el dinero repuesto se ahorra o invierte y realmente genera un rendimiento.

## 5. Cotización inicial y cotización de cada pago

Para una modalidad de referencia USD, se necesita una cotización base y un dato reproducible para cada pago.

### Al desembolsar

Guardar importe ARS utilizado, fuente/instrumento, lado de cotización al que la persona puede adquirir USD, fecha y hora/fecha de mercado, valor expresado como ARS por USD, usuario y evidencia. Calcular las unidades USD iniciales como:

**USD de referencia inicial = capital ARS / cotización inicial (ARS por USD).**

La cotización base fija las unidades USD del plan; no se reemplaza por un dato posterior.

### En cada pago

Si una cuota calculada en USD se paga por su equivalente en ARS, se necesita una cotización nueva para cada pago real, conforme a la regla definida. La cuenta de valuación es:

**Equivalente ARS del pago = importe USD de cuota × cotización ARS/USD aplicable al pago.**

El cronograma USD no se modifica por el salto del tipo de cambio; cambia el equivalente en pesos. El registro debe conservar la moneda e importe realmente pagados, unidades USD canceladas, cotización, fecha, fuente e importe equivalente resultante.

Cargar el tipo de cambio al llegar la primera cuota es útil como primer punto de actualización, pero no protege las cuotas restantes si luego se dejan en pesos fijos. Para conservar la medición en el tiempo, hay que registrar la cotización aplicable a cada pago o a cada fecha de fijación expresamente pactada.

Separar las fechas:
- vencimiento contractual;
- pago efectivo;
- cotización usada para convertir.

La política debe definir fines de semana/feriados, cotización faltante, pagos fuera de horario de mercado y pagos atrasados. Tras confirmar un pago, su cotización queda preservada; una corrección requiere motivo y trazabilidad, no una sobrescritura silenciosa.

### ¿Qué cotización elegir?

No hay un único valor válido para todos los objetivos. La fuente debe representar el objetivo del acuerdo y ser verificable.

- Para reconstruir valor USD, se puede permitir un **Dólar MEP de referencia** definido por fuente/instrumento, cargado manualmente o integrado mediante un proveedor reproducible. El nombre “MEP” sin fuente, lado y regla temporal es ambiguo.
- Como alternativa, se puede seleccionar el **tipo de cambio minorista vendedor publicado por el BCRA**. Es un dato oficial público, pero puede no coincidir con el costo al que la persona recompra dólares en el mercado financiero.

La fuente, instrumento, lado y fecha deben ser parte de la simulación/acuerdo. No usar una cotización actual para reconstruir retroactivamente un pago antiguo.

Fuente pública: [BCRA — Principales variables](https://www.bcra.gob.ar/principales-variables/), que incluye cotización minorista vendedora, cambio mayorista de referencia, CER y UVA.

## 6. Carencia, tasa y rendimiento

La moneda de la tasa debe coincidir con la unidad del cálculo. Si el cronograma está en USD, la tasa es USD; si es ARS nominal, la tasa es ARS. Para un plan interno, el interés puede ser una meta de reposición, pero no se debe informar como ganancia efectivamente cobrada.

- Sin interés durante carencia: una tasa de referencia no se agrega a la deuda.
- Interés simple diferido: conservarlo como componente separado.
- Capitalización: habilita interés sobre interés y requiere una cláusula explícita, cálculo verificado y revisión jurídica.

El informe debe separar capital original, amortización, interés contractual, equivalente ARS de cada flujo, diferencia de valuación FX, gastos conocidos/pendientes y rendimiento en la unidad pertinente. El rendimiento debe evaluarse con flujos fechados, no a partir de la suma de pesos pagados.

## 7. Cláusulas gatillo

Una “cláusula gatillo” no es un seguro universal contra la devaluación. No se recomienda que un umbral arbitrario cambie automáticamente el capital, la tasa, moneda o cuota contractual.

Sí conviene tener **alertas operativas** configurables que detecten:
- cuota convertida que supera el presupuesto;
- variación cambiaria superior a un umbral desde la cotización base;
- cuota que supera una proporción seleccionada del ingreso mensual;
- insuficiencia de liquidez prevista para la primera cuota o los meses siguientes.

La alerta debe proponer comparar escenarios, ajustar el presupuesto o negociar una modificación. Solo un acuerdo expreso y trazable puede modificar el contrato; la validez de cláusulas de revisión, conversión o pago alternativo requiere revisión jurídica.

## 8. Normativa argentina revisada el 09/10/2026

Fuentes oficiales:
- [Código Civil y Comercial actualizado](https://www.argentina.gob.ar/normativa/nacional/ley-26994-235975/actualizacion), especialmente arts. 765–772: moneda pactada, intereses compensatorios, capitalización, facultad judicial de reducir intereses y obligaciones de valor.
- [DNU 70/2023, Boletín Oficial](https://www.boletinoficial.gob.ar/detalleAviso/primera/301122/1), arts. 250–251, que sustituyen los arts. 765–766 del Código.
- [Ley 23.928 actualizada](https://www.argentina.gob.ar/normativa/nacional/ley-23928-328/actualizacion), en particular art. 7, sobre nominalismo de obligaciones en pesos y restricciones de actualización.
- [Ley 27.798, art. 62](https://www.argentina.gob.ar/normativa/nacional/ley-27798-422000/texto), excepción acotada para determinadas operaciones provinciales/CABA, no una excepción general para préstamos personales.
- [BCRA — Principales variables](https://www.bcra.gob.ar/principales-variables/).

El artículo 765 vigente establece que, en una obligación de moneda pactada, el deudor se libera entregando las cantidades comprometidas en dicha moneda; el art. 766 se refiere a la especie designada. El art. 767 trata intereses compensatorios y el 770 limita la capitalización con excepciones expresas. La Ley 23.928 mantiene restricciones a la indexación de deudas en pesos con excepciones específicas. Por eso, una obligación en USD que se pretenda cancelar con equivalente en ARS y una deuda en pesos referenciada al dólar no deben presumirse jurídicamente intercambiables. La redacción y validez de un contrato real deben revisarse con asesoramiento jurídico argentino. Este documento es diseño de software, no asesoramiento legal.

## 9. Requisitos técnicos y secuencia

- Modelar roles por operación, permitir aportes de varios participantes y distinguir aportes internos de préstamos reales.
- Separar moneda del desembolso, unidad contractual, unidad de referencia y moneda de pago.
- Mantener el cronograma en su unidad original; no contaminar el saldo contractual con conversiones de reporte.
- Guardar cotización base y una cotización auditable por cada pago confirmado.
- Usar Decimal, no float, para dinero y conversiones.
- Separar interés, capital y componente de carencia al imputar pagos parciales, mora y adelantos RAI/RNI.
- No recalcular cuotas históricas; la nueva modalidad debe ser explícita, versionada y opt-in.
- Probar fines de semana/feriados, cotización faltante, correcciones auditadas, mora, pagos parciales, adelantos y reconciliación entre unidades.
- Mostrar alertas de capacidad de pago y escenarios de devaluación antes de aceptar un acuerdo.

Orden recomendado: (1) la base de snapshot persistente de carencia se integró por PR #193, pero no habilita aún la operación real; (2) resolver roles coincidentes y tramos internos/externos; (3) la simulación en unidades USD con cotización base y cotización por cuota se integró por PR #198; (4) [issue #199](https://github.com/JavierGrecco/prestamos_privados/issues/199) / PR #200 llevan el modo USD a la UI con equivalentes ARS opcionales basados en una trayectoria proyectada; (5) capturar la cotización observada por pago real y su evidencia; (6) comparar ARS nominal, USD, USD referenciado y CER/UVA; (7) obtener revisión jurídica; (8) recién después habilitar alta real y conectar ledger, pagos, mora e informes.

Hasta completar la secuencia, el autopréstamo y la cobertura cambiaria deben presentarse como herramientas de análisis/planificación, no como un contrato operativo habilitado.
