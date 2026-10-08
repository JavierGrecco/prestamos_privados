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