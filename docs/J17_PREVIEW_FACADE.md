# J17.1 — Fachada única de preview de pagos

## Objetivo

Reducir la superficie de transición entre preview histórico y preview V3 sin
cambiar ninguna regla financiera.

## Cambio

La UI de registro de pagos consume `ServicioPreviewPago`.

La fachada expone:

- deuda usada para capturar intención;
- simulación histórica explícita;
- simulación de adelanto;
- preview canónico V3;
- selección de ruta por modo.

## Qué no cambia

- Legacy sigue disponible;
- V3 sigue protegido por preflight;
- las matemáticas de ambos motores no se reescriben;
- el preview no persiste datos financieros;
- una divergencia se sigue mostrando.

## Contrato

Para LEGACY, la fachada devuelve el resultado de la simulación histórica.
Para SOMBRA y V3, la fachada devuelve el `PreviewPagoV3` canónico.

Esto permite que una futura migración de consumidores ocurra en una frontera
de aplicación estable.

## Evidencia

Las pruebas verifican que:

- la UI no importa directamente `ServicioPagosConSimulacion`;
- `ServicioPreviewPago` es la entrada pública;
- el modo LEGACY selecciona la ruta histórica;
- SOMBRA/V3 seleccionan el preview V3;
- no se agregan cálculos financieros a la UI.

## Próximo paso

La siguiente fase de J17 es ampliar la comparación por regla y migrar los
consumidores restantes antes de retirar cualquier API histórica.

## Principio

> Una transición segura reduce primero la superficie pública y recién después retira implementaciones.

## J17.3 — Consulta de deuda compartida ✅

La lectura de la deuda del próximo pago dejó de depender del servicio Legacy.
Ahora existe `ServicioDeudaProximoPago` como consulta de solo lectura compartida.

Esto permite que la UI capture la intención de pago sin necesitar una instancia
del servicio de registro histórico para esa lectura.

Legacy conserva temporalmente la simulación histórica y las operaciones de
compatibilidad que todavía son necesarias para comparación y rollback.


## J17.5 — Clasificación de divergencias del preview ✅

La comparación Legacy/V3 expone un estado estable:

- `EQUIVALENTE`;
- `DIVERGENCIA`.

Cuando existe una divergencia también identifica qué conceptos difieren:
deuda total, mora, interés, capital o excedente.

La UI usa esa información para explicar la diferencia sin elegir
automáticamente qué resultado es correcto. La resolución financiera de las
divergencias permanece en el issue #145.


## J17.5 — Mora y waterfall

La política de mora contractual ya está modelada explícitamente en V3 y
reproduce la base/tasa/convención de la consulta Legacy actual.

La diferencia que permanece en pago vencido es de INTERÉS/CAPITAL por el
interés incremental sobre capital pendiente. En arrastre posterior a un pago
parcial permanece una diferencia de distribución por el alcance del
waterfall.

El detalle y el criterio para resolver ambas decisiones están en
[docs/J17_5_DIVERGENCIAS_FINANCIERAS.md](J17_5_DIVERGENCIAS_FINANCIERAS.md).
