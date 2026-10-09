# Desarrollo

## Entorno

La preparación recomendada es multiplataforma y verifica la raíz del checkout,
el intérprete y la compatibilidad de dependencias:

```bash
python scripts/preparar_entorno.py
```

Por defecto instala herramientas de desarrollo. Para instalar solo dependencias
de ejecución, usá `python scripts/preparar_entorno.py --runtime`. El ayudante
no abre ni migra SQLite. Ver [Instalación local reproducible](INSTALACION_LOCAL.md)
para los comandos específicos de PowerShell, CMD y macOS/Linux.

Para iniciar la UI con una base declarada explícitamente, activá primero el
`.venv` de esta copia y ejecutá:

```bash
python scripts/iniciar_local.py --db datos/prestamos-local.db
```

El iniciador valida que el intérprete pertenece a este checkout, inspecciona
migraciones y se niega a actualizar bases existentes sin autorización y backup
verificado. No reutilices el `.venv` de otra copia o sistema operativo.

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
