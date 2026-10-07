# H1 — Comparación Legacy vs V3

## Objetivo

Demostrar que el Motor de Pagos V3 reproduce correctamente el resultado económico del motor Legacy allí donde la regla debe ser equivalente, sin modificar todavía el flujo efectivo de producción.

H1 no es un reemplazo de Legacy. Es una etapa de validación antes del cut-over.

## Estrategia

Cada escenario se ejecuta sobre dos copias del mismo estado inicial:

```text
                 estado inicial
                       │
              ┌────────┴────────┐
              ▼                 ▼
           Legacy              V3
              │                 │
              ▼                 ▼
       resultado final   resultado final
              │                 │
              └────────┬────────┘
                       ▼
              proyección común
                       │
                       ▼
                  comparador
```

La comparación se realiza sobre una **proyección económica común**, no sobre el esquema interno de cada motor.

Esto es necesario porque durante la migración algunos campos tienen semánticas diferentes entre Legacy y V3. Esas diferencias de representación no deben convertirse automáticamente en divergencias financieras.

## Qué se compara

### Pago

- monto recibido;
- tipo de operación cuando tiene significado equivalente;
- interés extra generado;
- intereses ahorrados;
- opción de adelanto cuando existe.

### Imputaciones

Por cuota:

- número de cuota;
- concepto;
- monto.

El ID interno de la cuota no forma parte de la comparación.

### Estado de cuotas

Para cada cuota:

- número;
- estado;
- mora pendiente;
- interés pendiente;
- capital pendiente;
- monto pendiente.

### Distribución

Por inversor:

- importe distribuido.

### Ledger

Se compara la economía de los movimientos:

- entidad;
- entidad_id;
- tipo de movimiento;
- debe;
- haber.

La correlación UUID se considera un identificador técnico, no un resultado financiero.

### Auditoría

Se comprueba la presencia de la operación principal y su entidad, sin exigir igualdad de timestamps ni de identificadores técnicos.

## Qué no se compara directamente

No son diferencias económicas por sí mismas:

- IDs generados independientemente;
- timestamps;
- UUID de correlación;
- `motor_version`;
- `plan_json` propio de V3;
- `plan_hash`;
- campos de compatibilidad cuya semántica cambió durante la migración.

## Clasificación de divergencias

Toda diferencia detectada debe clasificarse:

1. **EQUIVALENTE** — mismo resultado económico.
2. **DIFERENCIA_ESPERADA** — cambia la representación o agrega trazabilidad sin cambiar la economía.
3. **DEFECTO_V3** — V3 produce un resultado incorrecto.
4. **LEGACY_TEMPORAL** — V3 aplica una regla mejor o más completa, pero Legacy sigue siendo la referencia operativa durante la transición.
5. **DECISIÓN_PENDIENTE** — la diferencia requiere una decisión funcional explícita.

Nunca se debe modificar V3 solamente para hacerla coincidir con Legacy.

## Escenarios iniciales

| ID | Escenario | Objetivo |
|---|---|---|
| H1-001 | Pago exacto en vencimiento | Equivalencia base |
| H1-002 | Pago parcial | Waterfall y saldos |
| H1-003 | Complemento de pago parcial | Arrastre |
| H1-004 | Pago con mora | Mora + interés + capital |
| H1-005 | Excedente + RAI | Prepago y recalculación |
| H1-006 | Excedente + RNI | Reducción de plazo |
| H1-007 | Pago tardío con interés devengado | Capital pendiente + devengamiento |
| H1-008 | Reintento idempotente | No duplicación |
| H1-009 | Conflicto de revisión | Concurrencia optimista |
| H1-010 | Fallo transaccional | Atomicidad |

Los escenarios H1-001 a H1-003 son el primer corte de equivalencia. Los demás se agregan después de estabilizar el comparador.

## Contrato del modo SOMBRA

El modo SOMBRA debe cumplir:

- Legacy sigue siendo el resultado efectivo.
- V3 no puede modificar persistencia.
- Un error del cálculo sombra de V3 no invalida un pago Legacy exitoso.
- Una divergencia queda observable y reproducible.
- El mismo comando tiene una huella determinista.

La implementación actual del puente ya contempla los modos `LEGACY`, `SOMBRA` y `V3`. H1 debe fortalecer el contrato de SOMBRA antes de utilizarlo como mecanismo real de adopción.

## Criterio de salida de H1

H1 no termina porque “los tests pasan”.

Termina cuando:

- existe una proyección económica común;
- los escenarios base están automatizados;
- las divergencias son estructuradas y clasificables;
- Legacy continúa siendo el motor efectivo;
- V3 puede evaluarse sin mutar producción;
- cada diferencia relevante tiene explicación;
- queda documentado qué condiciones habilitan H2 y posteriormente el cut-over.
