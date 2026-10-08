# K7 — Aceptación end-to-end de la UI

K7 agrega una prueba de aceptación sobre el entrypoint real de Streamlit.

## Objetivo

Comprobar que las piezas funcionales incorporadas a la UI pueden ejecutarse
juntas sobre una base aislada, sin depender de los datos locales del
desarrollador.

La prueba utiliza `streamlit.testing.v1.AppTest`, la herramienta nativa de
Streamlit para ejecutar aplicaciones de forma headless, simular interacciones
y verificar el contenido renderizado.

## Alcance

La fixture crea:

- un schema completo mediante las migraciones;
- una persona de prueba;
- un inversor de prueba;
- un préstamo real mediante `ServicioPrestamos`;
- una tabla de amortización real.

La aplicación se ejecuta utilizando el mismo archivo:

```text
ui/app.py
```

La base se inyecta mediante:

```text
PRESTAMOS_DB_PATH
```

Esto permite probar la aplicación sin tocar `datos/prestamos.db`.

## Recorrido aceptado

K7 verifica:

1. arranque de la aplicación;
2. Resumen;
3. Préstamos;
4. Motor V3;
5. Análisis;
6. Pagos;
7. Operación;
8. navegación de ida y vuelta;
9. acceso desde el detalle del préstamo al detalle financiero;
10. render de las cuatro pestañas del detalle financiero;
11. estado de sesión utilizado para navegar entre pantallas.

## Protección de arranque

La ruta de inicialización de la UI utiliza la base configurada y, si las
migraciones fallan, detiene la aplicación en lugar de continuar con un schema
potencialmente incompleto.

## Ejecución local

Solo K7:

```bash
python -m pytest -q tests/test_ui_e2e.py
```

Suite completa:

```bash
python -m pytest -q
```

Compile:

```bash
python -m compileall -q aplicacion dominio infraestructura tests
```

## Límites

K7 no reemplaza pruebas de navegador real, pruebas de carga, autenticación,
despliegue ni validación visual. Su objetivo es detectar regresiones de
integración entre el entrypoint de Streamlit y los servicios funcionales del
sistema.
