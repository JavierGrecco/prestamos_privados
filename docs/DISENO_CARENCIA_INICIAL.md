# Diseño financiero: carencia inicial y primera cuota diferida

**Estado:** simulador integrado en main (PR #187); no habilita todavía préstamos operativos con carencia. La API aditiva de amortización por fechas está en PR #190 (issue #189), aún sin conectar al alta real.  
**Issue:** [#186](https://github.com/JavierGrecco/prestamos_privados/issues/186)  
**Implementación en curso:** [PR #187](https://github.com/JavierGrecco/prestamos_privados/pull/187)

## Decisión de producto

Un préstamo privado puede acordarse con varios meses sin cuotas regulares. Esa condición debe ser un **atributo del contrato de préstamo**, no una inversión separada ni una excepción improvisada en la interfaz.

La persona que presta conserva un crédito a cobrar. Su rendimiento se mide por el calendario y los importes de los flujos de caja que recibe, por ejemplo con XIRR. No es correcto llamar “inversión separada” al saldo del préstamo solo porque la recuperación empieza más tarde.

Antes de confirmar la operación, ambas partes deberían poder entender:

- cuándo se entrega el capital;
- cuándo termina el período sin cuotas y cuándo vence la primera cuota;
- si el interés se cobra durante ese período, se perdona, se difiere o se capitaliza;
- cuánto interés se devenga, cuánto se paga y cuánto queda pendiente;
- cuánto capital se amortiza después de la carencia;
- el importe y el detalle de cada cuota posterior;
- el total que terminaría pagando el deudor y el rendimiento anualizado estimado del prestamista;
- qué supuestos cambiarían si se modifica la fecha, tasa, plazo o tratamiento de intereses.

La pantalla actual se llama **Simular carencia inicial** y vive en **Análisis e informes → Simular carencia**. Es una simulación previa: no crea ni modifica préstamos, no persiste las condiciones elegidas ni habilita una modalidad contractual.

## No confundir los cinco tratamientos

### 1. Carencia sin interés compensatorio

Durante la carencia no se cobra interés corriente. El capital queda pendiente pero no aumenta. El simulador muestra el interés de referencia que habría resultado de aplicar la tasa como indicador del costo de oportunidad, pero no lo suma a la deuda.

Es útil cuando una familia acuerda que el período inicial será gratuito. No hay que presentar el interés de referencia como una obligación real.

### 2. Pagar solo intereses durante la carencia

El deudor abona el interés de cada período y no devuelve capital durante ese tramo. Al finalizar la carencia, comienza el cronograma normal de amortización sobre el capital original.

Esto **no** es una carencia total de pagos: el prestatario sigue teniendo pagos periódicos desde el comienzo.

### 3. Carencia total con interés simple diferido a la primera cuota

No hay desembolsos del deudor durante la carencia. Se calcula interés sobre el capital acordado, sin añadir los intereses acumulados al capital. Al primer vencimiento regular, el saldo de interés diferido se agrega como un concepto separado a esa cuota.

Es sencillo de explicar, pero puede producir una primera cuota muy alta. El simulador tiene que destacarla claramente.

### 4. Carencia total con interés simple distribuido en las cuotas posteriores

No hay pagos durante la carencia. El interés simple acumulado se mantiene separado y se distribuye entre las cuotas regulares posteriores. Ese componente no pasa a generar interés por sí mismo.

En términos nominales, distribuirlo entre más cuotas puede ser más llevadero que concentrarlo todo en la primera cuota, aunque el total nominal se parezca. Como los pagos llegan en distintas fechas, el rendimiento del prestamista puede cambiar.

### 5. Capitalización explícita al final de la carencia

El interés acumulado se incorpora al capital en una fecha pactada; las cuotas posteriores calculan intereses sobre ese capital aumentado. Esto es distinto de devengar interés y dejarlo pendiente.

La capitalización está disponible **solo como escenario de análisis**, con advertencia, y actualmente solo para TNA. La combinación con TEA está deshabilitada hasta definir una regla matemática y contractual inequívoca. No debe habilitarse para registrar préstamos reales por el mero hecho de que el sistema pueda calcularla.

## Ejemplo comparativo

Supuestos ilustrativos: préstamo de **$1.000.000**, TNA del **36%**, 12 meses sin cuotas regulares y luego 24 cuotas francesas mensuales. Se supone una TEM del 3% y se mantiene el capital de $1.000.000 durante la carencia cuando no se capitaliza.

| Tratamiento | Durante la carencia | Después de la carencia | Total nominal ilustrativo |
|---|---|---|---:|
| Sin interés | No paga; no se cobra interés corriente | 24 cuotas calculadas sobre $1.000.000 | $1.417.137,96 |
| Pagar interés durante la carencia | 12 pagos de $30.000 | 24 cuotas calculadas sobre $1.000.000 | $1.777.137,96 |
| Diferido a la primera cuota | No paga; se acumulan $360.000 de interés simple separado | La primera cuota suma esos $360.000 a su importe regular | $1.777.137,96 |
| Distribuido sin capitalizar | No paga; se acumulan $360.000 de interés simple separado | Se añaden $15.000 de ese componente a cada una de las 24 cuotas | $1.777.137,96 |
| Capitalizado al final (solo análisis) | No paga; se acumulan $360.000 | El capital amortizable pasa a $1.360.000 y los intereses posteriores se calculan sobre ese importe | Aproximadamente $1.927.307,63 |

Los importes están sujetos al calendario y al redondeo de la tabla de amortización; son un ejemplo para comparar conceptos, no una cotización ni una recomendación contractual. En el ejemplo, distribuir el interés no capitalizado no cambia el total nominal frente a agregarlo a la primera cuota o cobrarlo mes a mes, pero sí cambia el momento en que el prestamista recibe ese dinero y cuánto debe afrontar el deudor en cada fecha.

El interés total del deudor debe calcularse como la suma efectiva de los pagos menos el capital entregado, no multiplicando una cuota teórica por la cantidad de cuotas: el motor ajusta la última cuota para cerrar el saldo monetario exactamente en cero.

## TNA, TEA y convención de días

La tasa y el tratamiento del interés son decisiones distintas.

- Con TNA del 36% y convención mensual, la tasa periódica es 3%. $1.000.000 de capital constante produce $30.000 de interés simple por mes.
- Con TEA del 30%, la TEM equivalente es aproximadamente 2,21045%. Si el interés se calcula cada mes sobre capital constante y no se capitaliza, doce tramos simples dan alrededor de $265.253,40, no $300.000. Por eso no se debe prometer que el rendimiento anual realizado será igual a la TEA indicada cuando el acuerdo no capitaliza los intereses.
- En períodos irregulares, fecha inicial y fecha final importan. El helper aislado puede usar convenciones de días reales; el simulador integral todavía se limita a MENSUAL porque la tabla de amortización posterior no soporta aún todas esas convenciones de manera homogénea.

La interfaz debe mostrar la modalidad y convención en uso; no elegir una fórmula diferente para la misma operación ni resolver este problema con código de presentación.

## Qué mide el rendimiento del prestamista

El interés nominal del contrato no es necesariamente el rendimiento anual efectivo del prestamista. Para estimarlo se toma la salida de dinero en la fecha de desembolso como flujo negativo y cada cobro esperado en su fecha como flujo positivo. Con esos flujos se calcula la XIRR, cuando existe una solución estable.

Así se distingue entre:

- **interés contractual:** importe que el acuerdo establece;
- **interés cobrado:** dinero recibido por ese concepto;
- **interés devengado y pendiente:** obligación calculada, pero que aún no entró en caja;
- **capital amortizado:** devolución efectiva del principal;
- **rendimiento anualizado estimado:** resultado de los flujos y sus fechas, no una copia del rótulo TNA/TEA.

La simulación no es una promesa de cobro puntual ni incluye automáticamente riesgo de incumplimiento, inflación futura, impuestos o gastos que no se hayan configurado.

## Contexto normativo argentino

El Código Civil y Comercial de la Nación distingue intereses compensatorios, moratorios y la capitalización de intereses. En particular:

- el artículo 767 trata los intereses compensatorios pactados;
- el artículo 770 establece como regla que no se deben intereses de los intereses, con excepciones expresas que incluyen una cláusula de capitalización bajo las condiciones allí previstas;
- el artículo 771 contempla la reducción judicial de intereses desproporcionados;
- el artículo 1527 regula el carácter oneroso del mutuo de dinero y la periodicidad supletoria de los intereses, salvo estipulación distinta.

Fuente oficial: [Código Civil y Comercial de la Nación, texto actualizado](https://www.argentina.gob.ar/normativa/nacional/ley-26994-235975/actualizacion).

Este resumen es contexto de diseño de software, no asesoramiento jurídico. La aplicabilidad de una cláusula debe revisarse con un profesional para el caso y contrato concretos; la relación familiar no sustituye esa verificación.

## Arquitectura y plan de implementación

### Ya existe en PR #187

- Cálculo puro del interés simple de carencia por tramos fechados, usando la autoridad de interés existente.
- Simulador de escenarios con conceptos separados de capital, interés cobrado, diferido, no cobrado y capitalizado.
- Calendario y primera fecha de vencimiento visibles.
- Comparación de total pagado, costo nominal del deudor y XIRR estimada del prestamista.
- Pantalla sin persistencia, con pruebas de que navegar y cambiar el escenario no altera la cartera.

### Antes de habilitar préstamos reales con carencia

1. Aprobar las semánticas de TNA/TEA durante y después de la carencia, incluidas fechas irregulares, fin de mes, años bisiestos y reglas de redondeo.
2. Extender una sola autoridad de amortización para aceptar la fecha contractual del primer vencimiento y las convenciones requeridas. La carencia cero debe reproducir exactamente los calendarios existentes.
3. Definir un contrato persistente e inmutable con la modalidad elegida, fechas, tasa, convención, plazo posterior y reglas para cada componente de interés. Registrar cambios como eventos auditables, sin reinterpretar la historia.
4. Integrar alta y vista previa del préstamo; explicar cada condición con lenguaje comprensible tanto para deudor como prestamista.
5. Conectar el plan persistido con la aplicación de pagos, mora, RAI/RNI, cancelaciones anticipadas, varios inversores, reportes y XIRR realizada.
6. Ejecutar regresiones E2E sobre bases temporales y confirmar que préstamos preexistentes, pagos parciales y saldos no cambian por introducir el nuevo camino.

Hasta completar esos pasos, las condiciones elegidas en el simulador son escenarios y no deben poder confirmarse como préstamos reales con carencia.

## Criterios de aceptación

- Carencia cero reproduce el calendario ya existente.
- El usuario distingue fecha de desembolso, fin de carencia y primer vencimiento regular.
- Capital e interés diferido se concilian por separado; no hay interés sobre interés implícito.
- La suma de cobros, capital devuelto, interés pagado, pendiente y capitalizado coincide con el calendario y el contrato sin diferencias no explicadas.
- El rendimiento del prestamista se basa en flujos fechados y no se presenta como idéntico a TNA/TEA.
- La interfaz explica qué cambia entre las alternativas, muestra la primera cuota y el costo total, y no guarda ni modifica préstamos durante una simulación.
- La capitalización nunca se activa por defecto; requiere una política explícita y una revisión de validez contractual.
- Los préstamos existentes conservan calendario, saldos y hechos históricos.
