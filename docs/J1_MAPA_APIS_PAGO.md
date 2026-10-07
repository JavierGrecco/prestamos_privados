# J1 — Mapa de APIs y duplicaciones de pagos

## Objetivo

Identificar qué piezas del registro de pagos son autoridad financiera, cuáles son
casos de uso/composición y cuáles son capas transitorias de migración.

No se eliminan módulos en esta fase.

## Inventario actual

| Pieza | Rol | Tratamiento |
|---|---|---|
| `dominio.motor_pagos_v3.calcular_plan_pago` | Motor puro de waterfall | **Autoridad de cálculo** |
| `dominio.motor_pagos_v3.PlanPago` | Resultado del motor V3 | **Modelo candidato estable** |
| `dominio.plan_pago.PlanPago` | Plan histórico/paralelo | **Duplicación a estudiar** |
| `aplicacion.servicios.registro_pago_v3.RegistrarPagoV3` | Registro transaccional base | Mantener como componente interno |
| `RegistrarPagoV3ConDevengamientos` | Registro + devengamientos | Mantener temporalmente |
| `RegistrarPagoV3Completo` | Registro + devengamientos + distribución | Mantener temporalmente |
| `RegistrarPagoV3CompletoConAdelantos` | Registro completo + RAI/RNI | **Candidato a caso de uso final** |
| `fabrica_registro_pago_v3.py` | Composición de dependencias | **Composition root** |
| `puente_motor_pago_v3.py` | Frontera de migración/cut-over | Mantener hasta fin de adopción |
| `ejecutor_sombra_pago_v3.py` | Coordinación de SOMBRA | Mantener mientras exista SOMBRA |
| `sombra_pago_v3_sqlite.py` | Adaptador SQLite para SOMBRA | Mantener como adaptador |
| `pago_one_shot_v3.py` | Read model | Mantener como consulta, no como motor |
| `simulacion_pagos_v3.py` | Adaptador de simulación | Mantener mientras consumidor real exista |

## Regla de autoridad

La pieza que debe concentrar la regla financiera es:

```text
Dominio V3
    ↓
calcular_plan_pago()
    ↓
PlanPago V3
```

Los servicios de aplicación deben orquestar esa autoridad y las capas de
infraestructura deben persistir sus resultados.

## Consolidación candidata

La dirección futura es una única entrada de aplicación para el caso de uso
completo. El detalle exacto se decidirá después del inventario de consumidores.

Una posible composición es:

```text
RegistrarPagoCommand
        ↓
RegistrarPagoV3CompletoConAdelantos
        ↓
motor V3 + política temporal + adelanto
        ↓
repositorio transaccional
```

La fábrica puede seguir siendo el composition root sin transformarse en otra
API financiera.

## Qué no debe hacerse

No se debe:

- borrar `dominio.plan_pago.py` porque tenga un nombre parecido;
- renombrar todos los servicios V3 simultáneamente;
- mover reglas financieras a la UI;
- convertir el bridge en el motor;
- mantener dos algoritmos de waterfall independientes.

Cada retiro futuro debe estar respaldado por:

1. referencias reales;
2. tests que demuestren ausencia de consumidores;
3. una API de reemplazo definida;
4. CI completamente verde.

## Herramienta de auditoría

J1 incorpora `scripts/auditar_apis_pago.py`.

Uso:

```bash
python scripts/auditar_apis_pago.py .
python scripts/auditar_apis_pago.py . --json
```

El análisis usa AST y no importa ni ejecuta los módulos del proyecto.

## Siguiente trabajo de J1

La siguiente iteración debe usar el resultado del auditor para construir una
matriz:

```API candidata → consumidores → tests → reemplazo → deprecación → retiro
```

Solo después de esa matriz se debe tocar la estructura de módulos.
