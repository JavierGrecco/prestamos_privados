# Servicio de correcciones auditables — estado de entrega

## Qué está disponible en la entrega v026

El PR #260 implementa una primera función utilizable de propuestas de corrección para datos declarados de planes de reposición. El servicio `ServicioCorreccionesAuditables` valida identidad/capacidades, verifica el hash actual del snapshot original, normaliza y valida el snapshot propuesto, registra la propuesta de forma atómica e idempotente y reconstruye la cadena de propuestas para consulta. Las pantallas de Streamlit permiten consultar el historial/comparación y cargar una nueva propuesta con motivo obligatorio.

Los datos cubiertos son aportes de reposición, flujos de inversión y valuaciones declaradas. El actor auditado surge del subject/proveedor de la sesión autenticada; no de un nombre editable.

## Qué significa “corrección” en esta fase

La aplicación mantiene inmutable el registro financiero original. La propuesta incluye el snapshot que se propone en su lugar para facilitar revisión, pero **no es el valor efectivo** y no actualiza automáticamente capital invertido, resultado, XIRR, posición financiera ni informes. La UI indica “Registrada · no aplicada”.

## Límites y trabajo pendiente

- Definir un flujo formal de aprobación (y separación de funciones, si corresponde).
- Aprobar el mecanismo de aplicación efectiva: asiento compensatorio o reconstrucción/versionado.
- Actualizar vistas actuales sin alterar informes históricos ni contar dos veces flujos/valuaciones.
- Añadir aceptación manual en la interfaz y verificar el proceso en una copia restaurada de base histórica.
- Mantener fuera de alcance cambios de préstamos/pagos contractuales y carencia.

No se debe usar la bitácora como reemplazo de una corrección contable efectiva: es evidencia de una propuesta, no una modificación aplicada.

## Validación automatizada

El código de PR #260 pasó **1.061 pruebas** en Python 3.11, 3.12, 3.13 y 3.14, junto con CodeQL y auditoría de dependencias. Este cambio revisa documentación; la suite completa debe ejecutarse nuevamente sobre el HEAD final antes de integración.

- [Matriz de pruebas del código v026](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38331895689)
- [CodeQL y auditoría del código v026](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38331895717)
