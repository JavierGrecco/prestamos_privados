# Estado de modularización y trabajo pendiente

**Corte:** 15 de octubre de 2026 (hora Argentina).
**Base de referencia:** `main` en `a222d6ac77084a45009f87aa04198f68b270bc28` (PR #334 integrado).
**Seguimiento:** [#267 — Arquitectura modular](https://github.com/JavierGrecco/prestamos_privados/issues/267) · [#293 — Inventario automático](https://github.com/JavierGrecco/prestamos_privados/issues/293) · [#223 — MVP local](https://github.com/JavierGrecco/prestamos_privados/issues/223).

> Este documento distingue estructura del código, dependencias pendientes y aceptación del producto. El número de archivos o de pull requests no es un porcentaje de modularización.

## 1. Dimensión actual del código

En el snapshot de `main` indicado arriba, GitHub informa 570 archivos de código/documentación en el árbol del repositorio, incluidos 439 archivos Python y 118 documentos Markdown. Las cinco capas que debe inspeccionar el auditor reúnen 268 archivos Python; la suite añade 170 archivos de pruebas.

| Capa | Archivos Python en la base de referencia |
|---|---:|
| Dominio | 30 |
| Aplicación | 95 |
| Infraestructura | 100 |
| UI | 31 |
| Scripts operativos | 12 |
| Total en capas auditadas | 268 |

Estos valores describen el volumen revisado antes de añadir el auditor. No indican cuántos archivos están mal modularizados: un módulo puede estar bien separado o conservar acoplamientos. El comando reproducible para actualizar el inventario es:

```bash
python scripts/auditar_fronteras_modulares.py . --format markdown --max-hallazgos 0
```

El mismo análisis ofrece JSON para automatización y se ejecuta en CI. Sus resultados separan infracciones de límites, dependencias temporales documentadas y fábricas de composición usadas en el borde de la UI.

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
| Inventario y guardas de arquitectura | Ejecutar un análisis reproducible de todos los imports, SQL fuera de infraestructura y construcción de repositorios; usar sus hallazgos para ordenar las migraciones. | [#293](https://github.com/JavierGrecco/prestamos_privados/issues/293) |
| Pagos y composición | Retirar gradualmente dependencias concretas que todavía se ubican en servicios de aplicación, manteniendo un solo punto de composición y la transacción completa. | [#270](https://github.com/JavierGrecco/prestamos_privados/issues/270) |
| Alta de préstamo y unidad de trabajo | Verificar el uso de puertos y conservar una transacción indivisible entre alta, cuotas, participaciones, ledger y auditoría. | [#301](https://github.com/JavierGrecco/prestamos_privados/issues/301) |
| Entrada de UI | Eliminar el acceso directo conocido a `PersonaRepo` desde `ui/app.py` y comprobar el resto de consumidores concretos. | [PR #302](https://github.com/JavierGrecco/prestamos_privados/pull/302) |
| Pago por cuota y evidencia histórica | Definir la semántica de atribución de mora/interés/capital cuando un pago cubre cuotas anteriores, y decidir el tratamiento histórico antes de corregir. | [#332](https://github.com/JavierGrecco/prestamos_privados/issues/332) |
| Cierre de arquitectura | Demostrar APIs públicas pequeñas, ausencia de ciclos relevantes, dependencias permitidas, excepciones documentadas y compatibilidad de consumidores. | [#267](https://github.com/JavierGrecco/prestamos_privados/issues/267) |

La herramienta de inventario agregada en esta entrega hace medibles los primeros cuatro temas, pero no los resuelve automáticamente. El PR que la introduce debe pasar CI y su salida debe revisarse antes de actualizar el orden de las siguientes extracciones.

## 4. Cuánto falta para terminar la modularización

No se publica un porcentaje único antes de tener el inventario automático ejecutado sobre el commit final. La evaluación manual permite hablar de **seis frentes controlables** en la tabla anterior: uno de observabilidad/guardas, tres de dependencias y composición, uno de semántica de pagos relacionada y uno de aceptación global.

Como planificación provisional, reservar **8–15 jornadas de ingeniería** para cerrar los límites prioritarios, revisar consumidores, robustecer las guardas y consolidar documentación. El rango tiene confianza media-baja: el informe AST puede descubrir dependencias no conocidas, y el trabajo de pagos se limita por la necesidad de preservar resultados financieros y rollback. No incluye cerrar todo el MVP local ni efectuar el cut-over de V3.

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

- El auditor cubre las capas acordadas, se ejecuta en CI y ofrece salida legible y JSON reproducible.
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