# Desarrollo

## Entorno

Crear un entorno virtual y utilizar siempre las dependencias declaradas por el proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Para una instalación de ejecución sin herramientas de desarrollo, usar
`requirements.txt`.

## Validación rápida

Antes de abrir un PR:

```bash
python -m compileall -q aplicacion dominio infraestructura tests
python -m pip check
python -m pytest -q
git --no-pager diff --check
```

## Aplicación

```bash
python -m streamlit run ui/app.py
```

La base local aparece en `datos/prestamos.db` y no se versiona.

Para datos de demostración:

```bash
python scripts/seed_datos.py
```

## Trabajar sobre el motor financiero

La forma recomendada es:

1. escribir o ampliar una prueba que describa el comportamiento;
2. implementar la regla en dominio;
3. comprobar invariantes;
4. integrar mediante servicios;
5. agregar pruebas de persistencia;
6. validar que la UI sólo consuma el resultado.

En cambios financieros importantes no se debe empezar modificando Streamlit.

## Mantener el registro del proyecto

Cuando un cambio modifica el estado, el alcance o la prioridad del proyecto:

1. Actualizar el [Registro de cambios](REGISTRO_DE_CAMBIOS.md) con el problema, lo que se hizo y la validación disponible.
2. Actualizar el [Estado del proyecto](ESTADO_DEL_PROYECTO.md) si cambia lo terminado, en curso o pendiente.
3. Actualizar el [Roadmap](ROADMAP.md) cuando cambien prioridades o criterios de salida.
4. Enlazar los issues y PR que contienen la evidencia. No marcar un trabajo como terminado solo porque el código exista: deben estar cumplidos sus criterios de aceptación.
5. Escribir para una persona que recién llega al proyecto: frases simples, sin abreviaturas sin explicar y distinguiendo claramente hechos, estimaciones y pendientes.

## Git

Usar ramas de trabajo con nombres descriptivos:

```text
feature/...
fix/...
refactor/...
chore/...
```

El commit debe explicar el cambio, no el contexto de la conversación.

Ejemplos:

```text
feat: agrega planificación V3 de pagos
fix: corrige devengamiento sobre capital pendiente
refactor: unifica autoridad de cálculo de pagos
chore: limpia artefactos generados
```

## Qué revisar antes de mergear

- pruebas completas verdes;
- sin `__pycache__`, `.pyc`, `.DS_Store` o bases locales en Git;
- migraciones probadas sobre una base temporal;
- no introducir lógica financiera duplicada;
- documentación actualizada cuando cambia una decisión de arquitectura.

## Datos

No subir bases SQLite locales, WAL, SHM, credenciales, tokens ni archivos `.env`.

Para reproducir escenarios se deben usar migraciones, fixtures o scripts de seed.

## Evolución de V3

Durante la migración es correcto tener código paralelo. Lo que no es correcto es mantener indefinidamente varias autoridades de cálculo.

La consolidación del código debe ocurrir después de:

- caracterización Legacy;
- comparación de resultados;
- pruebas de rollback;
- pruebas de concurrencia;
- validación sobre datos existentes.
