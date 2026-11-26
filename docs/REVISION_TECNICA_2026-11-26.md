# Revisión técnica integral — 26 de noviembre de 2026

## Alcance y método

Esta revisión toma como referencia `main` en el commit [`0bae21f`](https://github.com/JavierGrecco/prestamos_privados/commit/0bae21fd44918d8d3c2140311406755bbaba8954).

Se contrastaron los archivos de entrada del repositorio, documentación de producto, arquitectura, seguridad y operación con el árbol de código, las pruebas, los workflows de GitHub Actions, las ramas y los issues abiertos. También se revisaron los logs reales del workflow post-merge. La revisión no equivale a una auditoría externa, un pentest, una aceptación manual de la interfaz ni una validación financiera con datos productivos.

## Conclusión ejecutiva

El repositorio tiene una base técnica sustancial para un producto local de préstamos privados y análisis de reposición de capital. Sus fortalezas mejor demostradas son la separación por capas, el tratamiento explícito de operaciones financieras, el ledger y la auditoría, la prevención de duplicados, el rollback, una suite amplia de pruebas y un proceso de CI repetible.

La conclusión importante es que **la calidad técnica automatizada está mejor demostrada que la aceptación del producto completo**. El proyecto no debe describirse como terminado ni listo para producción. Su siguiente hito es aceptar dos recorridos reales desde la interfaz y demostrar conciliación, recuperación y operación local.

## Evidencia comprobada en el commit de referencia

| Control | Resultado | Qué permite afirmar |
|---|---|---|
| Pruebas automatizadas | 1.325 aprobadas en cada Python 3.11, 3.12, 3.13 y 3.14 | La suite actual pasa en las cuatro versiones; no son 5.300 pruebas distintas |
| Compilación | Aprobada | Los módulos incluidos en el workflow compilan |
| Dependencias | `pip check` y auditoría `pip-audit` aprobados | No se detectaron conflictos de dependencias ni hallazgos de auditoría en esa ejecución |
| CodeQL | Aprobado | El análisis configurado terminó correctamente en esa ejecución |
| Inventario AST | 318 archivos Python analizados; 0 errores | El auditor pudo analizar el conjunto configurado |
| Dependencias entre capas | 1.697 importaciones, 303 cruces | Fotografía cuantitativa para priorizar modularización |
| Hallazgos de arquitectura | 55 en 26 archivos: 7 pendientes, 3 excepciones documentadas y 45 usos de composición | Existen dependencias aún por revisar; las 45 composiciones son usos de borde clasificados, no 45 defectos |
| Ciclos de importación | 0 | La guarda global de CI no detectó ciclos |
| Limpieza de ramas | Aprobada | La limpieza automática terminó preservando las ramas históricas divergentes |

Evidencia: [pruebas](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45887341184) · [seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45887341158) · [limpieza](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45887341151).

## Fortalezas reales que vale la pena mostrar

### 1. Separación de responsabilidades

El dominio mantiene las reglas financieras; aplicación expone casos de uso y consultas; infraestructura concentra SQLite, repositorios y composición; Streamlit queda en la presentación. El inventario se ejecuta como parte de CI y detecta ciclos, dependencias pendientes y composición de borde.

No significa que la modularización esté completa: quedan siete hallazgos clasificados como pendientes y algunos puentes de compatibilidad.

### 2. Integridad de las operaciones financieras

El proyecto contempla dinero con `Decimal`, reglas de imputación, pagos parciales y adelantos, idempotencia, transacciones, rollback, ledger y auditoría. Esta es una fortaleza relevante para un sistema donde un pago puede afectar varias cuotas, intereses, mora y participaciones.

La suite cubre muchas de esas garantías. Aun así, un CI verde no demuestra por sí solo la corrección de todas las reglas contractuales ni sustituye casos numéricos aprobados por el negocio.

### 3. Transición controlada del motor de pagos

Existen dos implementaciones y herramientas de comparación, observación SOMBRA, preflight y control de modo. **Legacy sigue siendo el motor efectivo**. V3 no debe activarse por cantidad de pruebas, fecha o conveniencia técnica mientras continúen abiertas divergencias financieras (#145).

Esta cautela es una decisión de integridad, no una función incompleta que deba ocultarse.

### 4. Gestión de reposición de capital

El producto no se limita a registrar cuotas. Tiene planes guardados/versionados, aportes, movimientos de inversión, valuaciones declaradas, análisis de flujos, XIRR condicionada e informes exportables. El diferencial económico es separar capital por reponer, referencia de poder adquisitivo en USD y rendimiento objetivo/costo de oportunidad.

La conciliación completa entre los planes, posiciones e informes todavía requiere aceptación.

### 5. Sesiones SQLite

PR #369 aisló el recurso SQLite por sesión de Streamlit. Dos sesiones obtienen conexiones/instancias distintas, aunque comparten el archivo local. La prueba AppTest verifica ese aislamiento, la lectura de una escritura confirmada desde otra sesión y la liberación del recurso.

No es una arquitectura remota ni demuestra todavía pagos financieros concurrentes de punta a punta; esa prueba sigue en #159.

## Brechas y riesgos que permanecen abiertos

| Tema | Situación actual | Seguimiento |
|---|---|---|
| Aceptación del MVP | No hay aceptación manual integral reciente de los recorridos de préstamo y reposición | [#223](https://github.com/JavierGrecco/prestamos_privados/issues/223) |
| Reglas Legacy/V3 | Divergencias de mora y distribución en escenarios sensibles; Legacy sigue efectivo | [#145](https://github.com/JavierGrecco/prestamos_privados/issues/145) |
| Imputación por cuota con arrastre | La semántica y el tratamiento de hechos históricos aún requieren decisión | [#332](https://github.com/JavierGrecco/prestamos_privados/issues/332) |
| Calendario contractual | El alta real admite actualmente cuotas mensuales; el cálculo por fechas no gobierna todo el recorrido | [#189](https://github.com/JavierGrecco/prestamos_privados/issues/189) |
| Carencia inicial | Hay simulación y base técnica; no está habilitada como recorrido contractual completo | [#186](https://github.com/JavierGrecco/prestamos_privados/issues/186), [#192](https://github.com/JavierGrecco/prestamos_privados/issues/192) |
| Pagos concurrentes | Aislamiento de conexiones probado; falta E2E financiero con idempotencia, revisión obsoleta y rollback | [#159](https://github.com/JavierGrecco/prestamos_privados/issues/159) |
| Backup y recuperación | Hay herramientas y pruebas automatizadas; falta un simulacro manual de restauración en otra ruta | [#156](https://github.com/JavierGrecco/prestamos_privados/issues/156), [#160](https://github.com/JavierGrecco/prestamos_privados/issues/160) |
| HTML dinámico | Escape y contratos estáticos cubren patrones conocidos; revisión y prevención universal no están cerradas | [#158](https://github.com/JavierGrecco/prestamos_privados/issues/158) |
| Protección de `main` | La rama no tiene protección administrativa configurada | [#157](https://github.com/JavierGrecco/prestamos_privados/issues/157) |
| Identidad online | Solo existe autenticación local; no es multiusuario remoto ni servicio público | [#137](https://github.com/JavierGrecco/prestamos_privados/issues/137) |
| Distribución | No hay licencia pública declarada ni releases publicados | Pendiente de decisión de producto y distribución |

## Estado de GitHub y mantenimiento

Al corte de esta revisión no hay PRs abiertas. El repositorio conserva 15 ramas históricas divergentes además de `main`; no se consideran ramas activas y no se integran en bloque. La limpieza automática elimina ramas temporales integradas y preserva aquellas con commits exclusivos.

La rama `main` sigue sin protección administrativa. El flujo documentado es una sola rama de trabajo, una PR dirigida a `main`, CI verde, squash merge y eliminación de la rama integrada. La política está automatizada, pero la configuración de protección de rama continúa pendiente.

## Qué no se debe afirmar en una entrevista o presentación

- Que el MVP está terminado o listo para producción.
- Que V3 ya es el motor efectivo.
- Que hay soporte SaaS, acceso remoto o autenticación multiusuario online.
- Que todos los cálculos de carencia y modalidades no mensuales funcionan de punta a punta en préstamos reales.
- Que la prueba de sesiones SQLite equivale a aceptar pagos concurrentes.
- Que las cifras de 65–70%, 55–60%, 7,0/10 o 21–34 jornadas del informe del 12/10/2026 describen el estado actual: son estimaciones históricas no recalculadas.

## Próximo orden de trabajo recomendado

1. Acordar y documentar las reglas financieras pendientes (#145, #189, #186/#192 y #332) con casos numéricos revisables.
2. Completar los recorridos manuales de préstamo y reposición desde una instalación limpia; registrar defectos y evidencia en #223.
3. Conciliar pagos, saldos, ledger, posiciones e informes a una misma fecha de corte.
4. Ejecutar un backup y restaurarlo en otra ruta; después completar la E2E financiera multi-sesión.
5. Terminar la revisión de HTML y configurar la protección administrativa de `main`.
6. Recalcular la planificación restante solo después de esas pruebas y decisiones.

La capacidad de operación financiera asistida es posterior al MVP y está documentada por separado. No debe desplazar estas prioridades.

## Alcance de esta revisión

La revisión fue documental y de evidencia del repositorio y sus workflows. El commit de referencia pasó la matriz CI descrita arriba. No se ejecutó una aceptación manual en navegador, un pentest externo, un restore drill completo ni pruebas financieras con datos productivos. Esos puntos siguen abiertos deliberadamente.
