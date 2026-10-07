# Desarrollo

## Entorno

Crear un entorno virtual y utilizar siempre las dependencias declaradas por el proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Validación rápida

Antes de abrir un PR:

```bash
python -m compileall -q aplicacion dominio infraestructura tests
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
