# Estado de modularización y trabajo pendiente

**Corte:** 15 de octubre de 2026 (hora Argentina).
**Base de referencia del inventario:** `34826733719ec4736972a0b8d4095ee8a9c85060` (PR #338 integrado).
**Seguimiento:** [#267 — Arquitectura modular](https://github.com/JavierGrecco/prestamos_privados/issues/267) · [#293 — Inventario automático](https://github.com/JavierGrecco/prestamos_privados/issues/293) · [#223 — MVP local](https://github.com/JavierGrecco/prestamos_privados/issues/223).

> Este documento distingue estructura del código, dependencias pendientes y aceptación del producto. El número de archivos o de pull requests no es un porcentaje de modularización.

## 1. Dimensión actual del código

En el snapshot de `main` indicado arriba, el árbol contiene 575 archivos, incluidos 443 archivos Python, 119 archivos Markdown y 172 archivos de pruebas. El auditor cubre 270 archivos Python en las cinco capas acordadas; no cuenta los tests como módulos de producción.

| Capa | Archivos Python en la base de referencia |
|---|---:|
| Dominio | 30 |
| Aplicación | 96 |
| Infraestructura | 100 |
| UI | 31 |
| Scripts operativos | 13 |
| Total en capas auditadas | 270 |

Estos valores describen el volumen revisado antes de añadir el auditor. No indican cuántos archivos están mal modularizados: un módulo puede estar bien separado o conservar acoplamientos. El comando reproducible para actualizar el inventario es:

```bash
python scripts/auditar_fronteras_modulares.py . --format markdown --max-hallazgos 0
```

El mismo análisis ofrece JSON para automatización y se ejecuta en CI. Sus resultados separan infracciones de límites, dependencias temporales documentadas y fábricas de composición usadas en el borde de la UI.

### Medición de referencia y seguimiento

La línea base del PR #335 detectó **1.545 importaciones**, de las que **288 cruzaban entre capas**, con **83 observaciones en 26 archivos**: 49 pendientes de migración, 7 excepciones temporales y 27 usos informativos de composición.

Después del PR #336, la misma auditoría detectó **81 observaciones en 26 archivos**: **46 pendientes de migración**, 7 excepciones documentadas y 28 usos informativos de composición. La regla `CONSTRUYE-REPOSITORIO` bajó de 23 a 21; `UI-ACCESO-INFRA-DIRECTO` bajó de 21 a 20. No hubo errores de análisis. Son conteos de referencias, no defectos confirmados ni módulos distintos.

El PR #337 añadió el detector de ciclos entre módulos y el PR #338 extrajo `IdentidadSesion` a un módulo neutral. La auditoría integrada en PR #338 confirmó **0 ciclos de importación**, con 270 archivos analizados y ningún error de análisis. Antes de la extracción se había encontrado un ciclo entre `aplicacion.seguridad.capacidades` y `aplicacion.seguridad.identidad`; la guarda nueva impide su regreso. El ciclo aparente del paquete de migraciones también dejó de aparecer tras corregir la resolución de imports relativos.

## 2. Qué ya está modularizado

- El dominio concentra reglas financieras reutilizables: amortización, interés, mora, política de imputación, escenarios, rendimiento y planes de pago.
- Aplicación ya cuenta con puertos tipados, comandos de registro, consultas de solo lectura y servicios separados para las superficies financieras principales.
- Infraestructura concentra repositorios SQLite, consultas SQL y fábricas de composición para personas, préstamos, pagos, detalle financiero, reportes y otros módulos.
- La escritura Legacy de pagos ya delega parte de su trabajo en colaboradores específicos para distribución a inversores, recálculo de adelantos RAI/RNI, cuotas anteriores y cuota objetivo. El manejador conserva la unidad transaccional.
- La estructura de pagos tiene pruebas de caracterización, idempotencia, concurrencia y rollback; existen guardas AST para límites concretos, además de CI multiversión y controles de seguridad.
- El PR #334 añadió una prueba de SOMBRA sobre arrastre entre cuotas y mejoró la lectura humana de las referencias persistidas. No cambió reglas financieras.

## 3. Frentes que siguen abiertos

| Frente | Qué falta | Seguimiento |
|---|---|---|
| Inventario y guardas de arquitectura | Auditor AST integrado en CI. El PR #338 resolvió el ciclo de identidad; la ejecución actual detecta cero ciclos y una prueba evita regresiones. Queda pendiente convertir límites migrados y estables en bloqueos estrictos, de forma gradual. | [#293](https://github.com/JavierGrecco/prestamos_privados/issues/293) |
| Pagos y composición | Retirar gradualmente dependencias concretas que todavía se ubican en servicios de aplicación, manteniendo un solo punto de composición y la transacción completa. | [#270](https://github.com/JavierGrecco/prestamos_privados/issues/270) |
| Alta de préstamo y unidad de trabajo | Verificar el uso de puertos y conservar una transacción indivisible entre alta, cuotas, participaciones, ledger y auditoría. | [#301](https://github.com/JavierGrecco/prestamos_privados/issues/301) |
| Entrada de UI | Esta entrega migra `ui/app.py` a `crear_servicio_personas` y elimina la doble consulta dentro de un render. Quedan otros accesos directos de UI señalados por el inventario y la frontera separada de arranque/migraciones. | [#302](https://github.com/JavierGrecco/prestamos_privados/issues/302) |
| Pago por cuota y evidencia histórica | Definir la semántica de atribución de mora/interés/capital cuando un pago cubre cuotas anteriores, y decidir el tratamiento histórico antes de corregir. | [#332](https://github.com/JavierGrecco/prestamos_privados/issues/332) |
| Cierre de arquitectura | Demostrar APIs públicas pequeñas, ausencia de ciclos relevantes, dependencias permitidas, excepciones documentadas y compatibilidad de consumidores. | [#267](https://github.com/JavierGrecco/prestamos_privados/issues/267) |

El inventario hace medibles las dependencias; las extracciones siguen siendo trabajo manual deliberado. Los PR #335–#338 pasaron CI completo; la UI raíz usa composición pública y el ciclo de identidad quedó resuelto. Esta entrega migra también las consultas de personas de la página principal y del formulario de alta de préstamo; queda revisar el informe actualizado antes de elegir el siguiente bloque.

## 4. Cuánto falta para terminar la modularización

No convierto el conteo de observaciones en un porcentaje: mide referencias y construcciones, no módulos completos. El inventario actualizado después del PR #338 mantiene 46 observaciones pendientes concentradas en 26 archivos; son referencias/construcciones, no módulos distintos. El detector informa cero ciclos. El plan técnico se organiza en **seis frentes controlables**: inventario/guardas, UI y composición, pagos, alta de préstamos, semántica de trazabilidad financiera y aceptación global.

Como planificación provisional, reservar **8–15 jornadas de ingeniería** para cerrar los límites prioritarios, revisar consumidores, robustecer las guardas y consolidar documentación. La estimación tiene confianza media-baja: algunas observaciones se resolverán en conjunto y otras requerirán migrar consumidores uno por uno; el trabajo de pagos debe preservar resultados y rollback. No incluye cerrar todo el MVP local ni efectuar el cut-over de V3.

Una frontera se considerará cerrada solo cuando tenga contrato público, adaptador en el borde permitido, pruebas de caracterización/rollback cuando corresponda y una guarda contra regresiones. No es necesario convertir el proyecto en microservicios.

## 5. ¿Cuántas herramientas o utilidades quedan por implementar?

El MVP local no tiene una lista aislada de utilidades faltantes; tiene **siete paquetes de cierre funcional** definidos en `ROADMAP_MVP_LOCAL.md` (fases 0–6). Varias pantallas, simuladores, exportaciones y controles ya existen. El trabajo restante se concentra en conectar, reconciliar, aceptar y endurecer esas capacidades:

1. Aprobar reglas de contrato, calendario, mora y carencia.
2. Integrar el mismo calendario aprobado entre simulación, alta, pagos y reportes.
3. Terminar la conexión y aceptación del autocrédito/reposición: hechos, valuaciones, referencia USD y rendimiento objetivo sin doble contabilización.
4. Validar de punta a punta el préstamo privado desde la UI.
5. Validar de punta a punta el plan propio y conciliar posiciones e informes.
6. Completar operación segura local: instalación, backup/restauración, actualizaciones, concurrencia y controles de seguridad/gobierno.
7. Registrar aceptación final por una persona distinta del implementador y cerrar los defectos críticos.

El roadmap estima 21–34 jornadas para estos siete paquetes de MVP al corte del 12 de octubre; hay que revisar esa estimación después del inventario y de la aceptación manual. Eso no significa que falten siete programas nuevos: gran parte del código está integrado y aún requiere validación y conexión real.

## 6. Criterios de salida

- El auditor cubre las capas acordadas, se ejecuta en CI y ofrece salida legible y JSON reproducible, incluidos los componentes de importación cíclica.
- Las excepciones temporales tienen motivo, responsable de seguimiento y siguiente paso; no se ocultan.
- La UI no construye repositorios financieros ni ejecuta SQL.
- Los servicios de aplicación dependen de puertos/casos de uso y las fábricas concretas permanecen en la frontera de composición.
- No hay ciclos de negocio sin decisión documentada.
- Los pagos conservan atomicidad, exactitud decimal, idempotencia, ledger, auditoría y compatibilidad histórica.
- La documentación muestra lo que está integrado y lo que sigue en curso; el MVP solo se declara terminado tras la aceptación funcional y operativa.

## Referencias

- [Arquitectura modular objetivo](ARQUITECTURA_MODULAR_OBJETIVO.md)
- [Inventario de imputaciones por cuota](ANALISIS_IMPUTACIONES_POR_CUOTA.md)
- [Roadmap operativo del MVP local](ROADMAP_MVP_LOCAL.md)
- [Estado del proyecto](ESTADO_DEL_PROYECTO.md)
- [Registro de cambios](REGISTRO_DE_CAMBIOS.md)