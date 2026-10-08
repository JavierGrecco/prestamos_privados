# K7 — Aceptación end-to-end de la UI

K7 agrega una barrera de integración para el entrypoint real de Streamlit.

## Objetivo

Comprobar que las funcionalidades expuestas en la primera vertical de UI
pueden ejecutarse juntas sobre una base SQLite aislada, sin depender de
`datos/prestamos.db` del desarrollador.

La prueba utiliza `streamlit.testing.v1.AppTest`, que permite ejecutar la app
de forma headless, simular interacciones y verificar los elementos renderizados.

## Datos de prueba

Cada caso crea una base temporal y aplica las migraciones completas.

La fixture crea además:

- una persona de prueba que actúa como deudor;
- un inversor de prueba;
- un préstamo real mediante `ServicioPrestamos`;
- la amortización inicial del préstamo.

## Recorrido

La aceptación cubre:

1. arranque de `ui/app.py`;
2. Resumen;
3. Préstamos;
4. Motor V3;
5. Análisis;
6. Pagos;
7. Operación;
8. navegación de ida y vuelta;
9. detalle financiero del préstamo;
10. pestañas de Amortización, Capital, Devengamientos y Recálculos.

## Base de datos configurable

La UI mantiene `datos/prestamos.db` como valor por defecto.

Para un entorno aislado se puede usar:

```bash
PRESTAMOS_DB_PATH=/ruta/a/prestamos.db python -m streamlit run ui/app.py
```

La función cacheada de conexión recibe explícitamente la ruta. Esto evita que
una base temporal pueda quedar reutilizada por error entre ejecuciones con
rutas diferentes.

## Fail-closed

Si las migraciones no pueden completarse, la UI muestra el error, cierra la
conexión y detiene la ejecución. No continúa operando sobre un schema
potencialmente incompleto.

## Ejecución local

Prueba específica:

```bash
python -m pytest -q tests/test_ui_e2e.py
```

Suite completa:

```bash
python -m pytest -q
```

Compilación:

```bash
python -m compileall -q aplicacion dominio infraestructura tests
```

## Alcance

K7 demuestra integración funcional del entrypoint y de las principales
navegaciones de Streamlit.

No reemplaza pruebas visuales en navegador, carga, autenticación multiusuario,
despliegue, monitoreo externo ni validación de negocio con datos productivos.
