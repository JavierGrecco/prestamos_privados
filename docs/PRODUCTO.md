# Producto

## Propósito

**Préstamos Privados** es una aplicación para registrar, operar y analizar
préstamos privados con uno o varios inversores, manteniendo separadas las
reglas financieras, los hechos históricos y las proyecciones.

La experiencia de producto está pensada para que una persona pueda entender su
situación sin tener que conocer la implementación interna del motor.

## Recorrido principal

```text
Persona / operador
        ↓
     Streamlit
        ↓
   Casos de uso
        ↓
   Motor financiero
        ↓
SQLite + ledger + auditoría
        ↓
Read models y reportes
```

Las pantallas de producto consumen resultados de aplicación/read models. La UI
no es una autoridad financiera paralela.

## Superficies de la aplicación

| Superficie | Propósito |
|---|---|
| **Mi espacio** | Resumen personal de lo conocido, próximos movimientos y actividad reciente |
| **Préstamos** | Alta, consulta y ciclo de vida de préstamos |
| **Pagos** | Preview y registro de pagos con trazabilidad |
| **Detalle financiero** | Amortización, capital, devengamientos y RAI/RNI |
| **Análisis** | Cashflow, XIRR, rendimiento real y poder de compra |
| **Planificar** | Proyección de cobros y pagos conocidos |
| **Escenarios** | Lectura de los mismos flujos bajo supuestos macroeconómicos |
| **Rendimiento** | Interpretación de métricas históricas disponibles |
| **Comparar** | Comparación de 2 a 6 operaciones registradas |
| **Reportes** | Salida reutilizable de la situación financiera |
| **Personas** | Personas, roles y relaciones con préstamos |
| **Auditoría** | Reconstrucción y consulta de evidencia histórica |
| **Operación** | Integridad, backups, restore drill y readiness V3 |

## Alcance financiero

El sistema contempla:

- préstamos con deudor e inversores;
- tablas de amortización y convenciones de tasa/tiempo;
- pagos completos y parciales;
- mora y saldos arrastrados;
- adelantos RAI/RNI;
- devengamientos;
- distribución de cobros;
- ledger y auditoría;
- cashflows históricos y proyectados;
- análisis XIRR y rendimiento real cuando existe evidencia suficiente;
- escenarios de inflación/devaluación;
- comparación de operaciones registradas.

## Histórico, proyección y escenario

La aplicación diferencia tres lecturas que no deben mezclarse:

**Hecho real.** Algo que ya ocurrió y está respaldado por la información
registrada.

**Proyección.** Un movimiento futuro derivado de un contrato o estado
conocido.

**Escenario.** Una lectura alternativa de esos flujos bajo supuestos
explícitos.

La interfaz debe mostrar esta diferencia de forma comprensible y nunca
presentar una proyección como si fuera un hecho.

## Regla de producto

La persona primero; toda cifra debe explicar qué es, por qué importa y qué
puede hacer con ella.

La documentación permanente de UX está en
[PRINCIPIOS_UX.md](PRINCIPIOS_UX.md).

## Documentación funcional

La evolución por etapas queda documentada en:

- [M2 — Posición financiera](M2_POSICION_FINANCIERA.md)
- [M4 — Escenarios](M4_ESCENARIOS_PLANIFICACION.md)
- [M5 — Rendimiento explicado](M5_RENDIMIENTO_EXPLICADO.md)
- [M6 — Reportes personales](M6_REPORTES_PERSONALES.md)
- [M7 — Comparador de decisiones](M7_COMPARADOR_DECISIONES.md)
