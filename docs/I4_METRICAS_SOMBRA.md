# I4 — Métricas de adopción y observabilidad de SOMBRA

## Objetivo

Medir objetivamente qué está ocurriendo durante la transición Legacy → V3 sin
recalcular operaciones financieras.

## Métricas disponibles

El read model expone:

- total de observaciones SOMBRA;
- cantidad de divergencias;
- cantidad de errores de sombra;
- préstamos con observaciones;
- fingerprints distintos;
- primera y última observación;
- distribución por tipo;
- distribución por préstamo;
- distribución por fingerprint.

También permite filtrar todas las métricas por un préstamo concreto.

## Decisión importante

No se presenta una "tasa de éxito" de SOMBRA porque la tabla de observaciones
solo contiene ejecuciones que generaron una divergencia o un error. Una operación
sin observación no está representada en ese conjunto y, por lo tanto, no puede
usarse honestamente como denominador.

Desde I5 existe un registro explícito del universo de ejecuciones SOMBRA,
incluyendo las que terminan sin divergencia. Por eso ahora pueden calcularse
tasas observables de coincidencia, divergencia y error sobre ese universo.

## Arquitectura

```text
SQLite
  ↓
MetricasSombraV3Query
  ↓
ServicioMetricasSombraV3
  ↓
read model / dashboard
```

No se modifica ninguna entidad financiera y no se depende de Streamlit.

## Próximo paso

I5 puede registrar también cada ejecución SOMBRA, incluyendo los casos sin
divergencia, para obtener métricas de cobertura y coincidencia reales.
