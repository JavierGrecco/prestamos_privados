# Motor de Pagos V3 — F.3.1: persistencia SQLite del registro

F.3.1 implementa el primer adaptador real de infraestructura para la frontera
`RegistrarPagoV3`, sin reemplazar todavía el servicio legacy de pagos.

## Qué incorpora

- Migración v009.
- `revision_prestamo` para control optimista de concurrencia.
- `idempotency_key` + fingerprint único para evitar pagos duplicados.
- `motor_version`, `plan_hash` y `plan_json` para conservar la trazabilidad del
  plan V3 utilizado.
- `origen` y `referencias_devengamiento` en las imputaciones.
- Persistencia atómica de pago, imputaciones, cuotas, ledger y auditoría.
- `BEGIN IMMEDIATE` en la frontera crítica.
- Relectura de préstamo y cuotas dentro de la transacción antes de calcular.

## Seguridad financiera deliberada

F.3.1 no inventa reglas que todavía no están modeladas. En particular:

- No registra excedentes sin una decisión RAI/RNI.
- No habilita `opcion_adelanto` hasta implementar el recálculo completo.
- No agrega devengamientos dinámicos por su cuenta.
- No modifica `registrar_pago()` legacy.
- No llama repositorios legacy con transacciones anidadas dentro del camino V3.

Esto deja una ruta paralela, comprobable y reversible.

## Compatibilidad

La migración agrega únicamente columnas con valores por defecto e índices.
Los pagos históricos continúan identificados como `LEGACY` cuando no provienen
del motor V3.

El adaptador contiene un puente explícito para cuotas nuevas cuyos campos
`*_pendiente` aún están en cero: una cuota `PENDIENTE` sin pago parcial se
materializa usando su interés y capital contractuales. No se aplica el mismo
puente de forma silenciosa a cuotas vencidas/inconsistentes.

## Validación

Los tests de infraestructura cubren:

- esquema v009;
- persistencia completa;
- imputaciones por cuota/concepto;
- idempotencia;
- payload diferente con la misma clave;
- revisión obsoleta;
- rechazo de excedentes sin RAI/RNI;
- rollback total ante fallo del ledger;
- bloqueo entre escritores mediante `BEGIN IMMEDIATE`;
- construcción mediante fábrica.

## Próxima etapa

La siguiente etapa debe separar y persistir los **devengamientos financieros
reales** como eventos explícitos, incluyendo período, base, tasa, convención,
monto y origen. Solo después de eso debe integrarse al cálculo de mora/interés
adicional y, finalmente, al flujo RAI/RNI.
