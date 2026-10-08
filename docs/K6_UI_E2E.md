# K6 — Aceptación end-to-end de la UI

K6 agrega una barrera de integración para la aplicación Streamlit completa.

## Qué se prueba

La prueba arranca el mismo entrypoint utilizado por producción:

```text
ui/app.py
```

La base SQLite se crea dentro de un directorio temporal y se selecciona con
`PRESTAMOS_DB_PATH`. Esto evita depender de `datos/prestamos.db` del
desarrollador.

La fixture crea un préstamo real mediante `ServicioPrestamos`, de modo que
las pantallas no se prueban solamente sobre una base vacía.

## Navegación cubierta

La aceptación comprueba que estas áreas pueden renderizarse sin excepción:

- Resumen;
- Préstamos;
- Motor V3;
- Análisis;
- Pagos;
- Operación.

También se recorre la navegación de ida y vuelta y se verifica que el estado
de la página se conserve.

## Ejecución

Suite completa:

```bash
python -m pytest -q
```

Solo la aceptación de UI:

```bash
python -m pytest -q tests/test_ui_e2e.py
```

La prueba usa `streamlit.testing.v1.AppTest`, que permite ejecutar la
aplicación y manipular sus widgets sin un navegador real.

## Configuración

La ejecución normal sigue usando:

```text
datos/prestamos.db
```

Para una base aislada:

```bash
PRESTAMOS_DB_PATH=/ruta/a/prestamos.db python -m streamlit run ui/app.py
```

## Fail closed

Si la aplicación no puede aplicar todas las migraciones pendientes, muestra el
incidente y detiene la ejecución en lugar de continuar con un schema
potencialmente incompleto.

## Alcance y límites

K6 demuestra integración funcional de la UI, pero no reemplaza:

- pruebas de navegador real;
- autenticación multiusuario;
- pruebas de carga;
- observabilidad externa;
- despliegue productivo controlado.
