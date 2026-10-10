# Hoja de ruta: terminar la aplicación local

**Última revisión:** 10 de octubre de 2026  
**Objetivo:** entregar una aplicación local que permita administrar préstamos entre personas y gestionar un plan interno de reposición de capital con análisis de inversión, todo desde la interfaz visual.  
**Seguimiento coordinador:** [Issue #223 — MVP local P0](https://github.com/JavierGrecco/prestamos_privados/issues/223)  
**Informe ejecutivo:** [Estado, estimación y hoja de ruta para la comisión](INFORME_COMISION_DIRECTIVA_ESTADO_Y_HOJA_DE_RUTA_2026-10-09.md)

## Cómo leer esta hoja de ruta

Este es el documento de seguimiento del equipo. Resume **dónde estamos, qué sigue, qué depende de una decisión y cómo se acepta cada entrega**. Los issues enlazados conservan el detalle técnico; este documento define el orden de trabajo.

- **Hecho:** integrado y validado para el alcance descrito.
- **En curso:** existe implementación, pero falta completar o validar una parte importante.
- **Pendiente:** todavía no se puede usar el recorrido completo.
- **Bloqueado por decisión:** no avanzar con reglas económicas contradictorias o implícitas.

Una pantalla, una función de dominio o una suite verde no se consideran suficientes por sí solas. Una entrega termina cuando la persona puede completar el recorrido desde la interfaz, los importes coinciden con los ejemplos aceptados y la operación queda guardada y recuperable.

## Resumen ejecutivo

| Frente | Estado actual | Siguiente resultado |
|---|---|---|
| Préstamos privados entre personas | **En curso** | Cerrar reglas contractuales/temporales y validar alta, pagos, saldos, auditoría e informes de punta a punta |
| Autocrédito y reposición propia | **En curso: plan, aportes e inversión declarada integrados** | Planes versionados, aportes de reposición, flujos de inversión, valuaciones históricas y XIRR condicional. El informe por plan se descarga desde la UI en Markdown/JSON/CSV ([PR #238](https://github.com/JavierGrecco/prestamos_privados/pull/238)); separa la proyección actual de los movimientos declarados y no consolida automáticamente valores. Faltan aceptación manual, integración controlada con posiciones/reportes y conciliación con evidencia externa |
| Análisis de inversión / benchmark | **Avanzado, no es un contrato operativo** | Conectar sus supuestos y resultados al plan persistido, distinguiendo hipótesis de resultados realizados |
| Carencia inicial | **Base técnica parcial integrada** | Integrar el snapshot contractual con el alta, calendario, cuotas y pagos; aprobar antes las reglas temporales |
| Entorno visual | **Integrado, aceptación manual pendiente** | Recorrer los dos casos de uso en navegador y corregir los problemas encontrados |
| Instalación, backup y recuperación | **Preparado; verificación integral pendiente** | Validar instalación, reinicio, actualización de una copia histórica y restauración |
| Motor de pagos V3 | **Adopción controlada pendiente** | Resolver diferencias financieras antes de habilitar un canary real o retirar Legacy |

**Estimación restante revisada al 10/10:** 20–32 jornadas de ingeniería, como referencia 4–7 semanas de dedicación completa o 6–10 semanas calendario con dedicación parcial, aceptación y posibles ajustes de reglas. Si se aprueba como requisito la cobertura del precio contado del vehículo, reservar 2–4 jornadas adicionales. Es una estimación, no una promesa.

## Qué ya está construido

La base del producto no se debe rehacer. Se debe completar y conectar lo que ya existe.

- La aplicación local está construida con Python, SQLite y Streamlit.
- Hay altas de préstamos, personas y roles; registro y consulta de pagos; estados de préstamo; detalle financiero, auditoría y exportaciones.
- El núcleo financiero usa `Decimal`, conserva trazabilidad y cuenta con pruebas de regresión.
- El Motor V3 dispone de controles de preflight, modo SOMBRA, idempotencia y recuperación; **Legacy sigue siendo la autoridad efectiva** mientras no se apruebe la salida financiera.
- El simulador de reposición USD incluye cotizaciones por cuota, escenarios de rendimiento bruto/neto, importación o derivación de índices de retorno total, backtest histórico y exportaciones trazables.
- Desde el [PR #225](https://github.com/JavierGrecco/prestamos_privados/pull/225), los análisis USD se guardan con supuestos, resultados, calendario y hash de integridad. El [PR #227](https://github.com/JavierGrecco/prestamos_privados/pull/227) añade identidad de plan, versiones inmutables, cierre y migración de snapshots previos (v023). El [PR #229](https://github.com/JavierGrecco/prestamos_privados/pull/229) añade aportes reservados para reposición (v024). El [PR #232](https://github.com/JavierGrecco/prestamos_privados/pull/232) agrega flujos de inversión, valuaciones históricas y resultado/XIRR declarados cuando los datos alcanzan (v025). El [PR #237](https://github.com/JavierGrecco/prestamos_privados/pull/237) incorpora la proyección guardada al informe: Markdown explica el benchmark y los valores proyectados, JSON conserva el snapshot completo y CSV distingue proyecciones/supuestos de hechos registrados. El [PR #238](https://github.com/JavierGrecco/prestamos_privados/pull/238) habilita las tres descargas directamente desde la UI, solo para la versión vigente. Los datos de inversión son declarados por el usuario: no se concilian aún con un broker ni crean contratos o pagos de préstamos.
- Existe infraestructura para guardar snapshots contractuales inmutables de condiciones de carencia (migración v021 y repositorio). **Esa base no implica que el alta visual, el cronograma y los pagos ya operen con carencia de punta a punta.**
- Hay guías de instalación local y herramientas para inspeccionar la base y respaldarla. Falta demostrar el proceso completo con una aceptación manual registrada.

## La ruta de trabajo

### Fase 0 — Acordar el alcance y las reglas financieras

**Estado: en curso; requiere decisiones explícitas antes de cambiar importes.**  
**Esfuerzo orientativo: 2–3 jornadas.**

Acordar un pequeño conjunto de ejemplos numéricos de referencia para tasas, fechas, carencia, mora, pagos parciales e imputación entre interés y capital. Definir la diferencia entre un préstamo real entre personas y un plan interno de reposición propia.

Hasta que la comisión apruebe otra cosa, el criterio seguro es mantener Legacy como autoridad operativa actual y no activar el cut-over de V3. La diferencia entre Legacy y V3 debe resolverse por regla contractual y evidencia, no por preferencia de implementación.

**Se considera terminada cuando:**
- las modalidades incluidas en el MVP están escritas en lenguaje comprensible;
- cada regla sensible tiene al menos un ejemplo numérico esperado;
- está definida la autoridad de cálculo para el primer MVP;
- quedó escrito qué se posterga para después.

Referencias: [#145 — diferencias Legacy/V3](https://github.com/JavierGrecco/prestamos_privados/issues/145), [#189 — convenciones temporales](https://github.com/JavierGrecco/prestamos_privados/issues/189), [#223 — seguimiento del MVP local](https://github.com/JavierGrecco/prestamos_privados/issues/223).

### Fase 1 — Cerrar el préstamo privado real

**Estado: en curso.**  
**Esfuerzo orientativo: 4–6 jornadas.**

Conectar condiciones contractuales, versión de tasa, fechas, calendario de cuotas y tratamiento de carencia autorizado. Evitar que una simulación use reglas distintas de las que se guardan. Los préstamos existentes deben conservar sus importes, fechas y hechos históricos.

**Se considera terminado cuando:** una persona puede crear el préstamo desde la UI, revisar y confirmar las condiciones, consultar el cronograma persistido y registrar pagos de los casos acordados sin divergencias inexplicadas en saldo, mora, distribución o auditoría.

Referencias: [#192 — snapshot contractual de carencia](https://github.com/JavierGrecco/prestamos_privados/issues/192), [#189 — cálculo por fechas](https://github.com/JavierGrecco/prestamos_privados/issues/189), [#145 — criterio financiero de salida](https://github.com/JavierGrecco/prestamos_privados/issues/145).

### Fase 2 — Integrar el plan interno persistido con la operación local

**Estado: en curso. La persistencia básica ya está integrada: planes/versiones/cierre (PR #227), aportes de reposición (PR #229), movimientos/valuaciones/XIRR (PR #232) y proyección guardada en el reporte (PR #237). Falta aceptación manual y conexión con posiciones y reportes de toda la aplicación.**
**Esfuerzo orientativo: 3–5 jornadas.**

Ya están integrados el guardado de análisis, la identidad/versionado/cierre del plan,

El objetivo económico tiene tres componentes: **reponer el capital, conservar el poder de compra y añadir un rendimiento objetivo por el tiempo transcurrido**. El plan debe mostrar el costo de oportunidad y la brecha frente al benchmark, pero no registrar la rentabilidad hipotética como ganancia efectivamente realizada ni crear una deuda legal contra la misma persona.

**Hitos técnicos integrados:** identidad y versiones inmutables del plan, registro separado de aportes de reposición, movimientos de inversión y valuaciones históricas, hashes de integridad y cálculo condicionado de resultado/XIRR reportados.

**La fase se considera terminada cuando:** se acepta manualmente el recorrido de la UI; usuarios pueden distinguir capital reservado, capital invertido, flujos cobrados, costos externos y valuación no realizada; y los resultados declarados se conectan con reportes/posiciones sin doble contabilizar movimientos ni proyecciones.

Referencias: [#194 — roles coincidentes y autocrédito](https://github.com/JavierGrecco/prestamos_privados/issues/194), [#202 — reposición y rendimiento objetivo](https://github.com/JavierGrecco/prestamos_privados/issues/202), [#204 — benchmark de inversión](https://github.com/JavierGrecco/prestamos_privados/issues/204).

### Fase 3 — Terminar los dos recorridos visuales

**Estado: pendiente de aceptación integral.**  
**Esfuerzo orientativo: 4–6 jornadas.**

Hacer que ambas modalidades resulten claras y utilizables desde Streamlit. Antes de confirmar un préstamo, mostrar monto, partes, tasa, vencimientos, cuotas, costo total y condiciones. Para el plan interno, mostrar capital a reponer, equivalente de referencia, objetivo de rendimiento, escenario de inversión y brecha, identificando los datos observados y los supuestos.

**Se considera terminado cuando:** el usuario puede completar ambos recorridos sin scripts, SQL manual ni necesidad de entender las capas técnicas del proyecto.

### Fase 4 — Unir movimientos, posiciones y reportes

**Estado: pendiente de cierre integrado.**  
**Esfuerzo orientativo: 3–5 jornadas.**

En el préstamo real, conectar pagos, mora, adelantos, capital pendiente, participación de los inversores y vista del deudor. En el plan interno, mostrar el avance de reposición y el contraste de inversión sin confundir proyecciones con dinero cobrado o ganancias realizadas.

**Se considera terminado cuando:** las pantallas de detalle, la posición de cada persona y las exportaciones concuerdan con los hechos guardados y utilizan una fecha de corte coherente.

### Fase 5 — Asegurar la operación local

**Estado: parcialmente implementado; faltan pruebas operativas.**  
**Esfuerzo orientativo: 4–6 jornadas.**

Completar pruebas de migraciones históricas, backup/restauración, aislamiento real de sesiones, seguridad de HTML y aceptación visual. Configurar protección de `main` con PR y checks obligatorios cuando el equipo administrador pueda hacerlo. No afirmar que un escenario fue probado manualmente si solo pasó por CI.

**Se considera terminado cuando:** la instalación y el reinicio funcionan, una copia histórica puede actualizarse y verificarse, una restauración se demuestra en una base separada y las pruebas de seguridad y regresión están verdes.

Referencias: [#156 — migraciones históricas](https://github.com/JavierGrecco/prestamos_privados/issues/156), [#157 — proteger main](https://github.com/JavierGrecco/prestamos_privados/issues/157), [#158 — seguridad de HTML](https://github.com/JavierGrecco/prestamos_privados/issues/158), [#159 — concurrencia SQLite/Streamlit](https://github.com/JavierGrecco/prestamos_privados/issues/159), [#160 — upgrades controlados](https://github.com/JavierGrecco/prestamos_privados/issues/160), [#179 — aceptación integral](https://github.com/JavierGrecco/prestamos_privados/issues/179).

### Fase 6 — Aceptación del usuario y entrega

**Estado: pendiente.**  
**Esfuerzo orientativo: 3–5 jornadas.**

Una persona que no implementó el código sigue la guía desde una instalación limpia, opera un préstamo ficticio completo y un plan interno de reposición, reinicia la aplicación, verifica los saldos y reportes, genera un backup y demuestra una restauración sobre una copia.

**Se considera terminado cuando:** se completaron los criterios de aceptación, no quedan defectos financieros críticos abiertos, los pendientes conocidos están documentados y la comisión acepta el alcance entregado.

## Cómo se relacionan las tareas

Las fases tienen dependencias, no son una lista de funcionalidades independientes:

```text
Fase 0: reglas aprobadas
       |
       +--> Fase 1: préstamo real y carencia
       |
       +--> Fase 2: plan interno persistente
                    |
Fases 1 + 2 --------+
       |
Fase 3: recorridos visuales completos
       |
Fase 4: pagos, posiciones e informes
       |
Fase 5: instalación, seguridad y recuperación
       |
Fase 6: aceptación y entrega local
```

Las pruebas automatizadas y el mantenimiento de la documentación acompañan todas las fases. La adopción/cut-over de V3 no se fuerza para cumplir el calendario del MVP: requiere su propio criterio de equivalencia y una base operativa autorizada.

## Qué queda fuera de esta entrega

Para terminar lo local sin dispersar al equipo, quedan fuera del MVP: despliegue por Internet, identidad online, modo multiusuario remoto, conexión automática a mercados y órdenes de inversión. El modelado completo de bonos, impuestos, retenciones y acciones corporativas también se considera una evolución posterior. La cobertura del precio de contado del vehículo se agrega al MVP solo si se confirma como requisito del primer piloto.

## Forma de trabajo y seguimiento

Para cada PR:
1. indicar qué fase e issue atiende;
2. explicar el cambio en lenguaje de producto;
3. enumerar las reglas financieras afectadas o declarar que no cambian;
4. agregar pruebas para los casos normales, límites y regresiones;
5. registrar resultados de CI y lo que todavía requiere revisión manual;
6. actualizar el [Registro de cambios](REGISTRO_DE_CAMBIOS.md) y el estado de la fase.

No marcar una tarea como terminada porque se creó una clase, pantalla o migración. Debe cumplir su criterio de salida y dejar evidencia revisable.

## Enlaces de referencia

- [Issue coordinador del MVP local (#223)](https://github.com/JavierGrecco/prestamos_privados/issues/223)
- [Informe para la comisión](INFORME_COMISION_DIRECTIVA_ESTADO_Y_HOJA_DE_RUTA_2026-10-09.md)
- [Estado actual del proyecto](ESTADO_DEL_PROYECTO.md)
- [Producto y superficies de la aplicación](PRODUCTO.md)
- [Instalación local](INSTALACION_LOCAL.md)
- [Diseño del autocrédito](DISENO_AUTOPRESTAMO_COBERTURA_CAMBIARIA.md)
- [Diseño de carencia](DISENO_CARENCIA_INICIAL.md)
- [Registro de cambios](REGISTRO_DE_CAMBIOS.md)
