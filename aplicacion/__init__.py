"""
Capa de aplicación: casos de uso del sistema.

Esta capa orquesta las operaciones de alto nivel. Toma las piezas
del dominio (motor financiero) y de la infraestructura (repositorios)
y las combina en flujos con sentido de negocio.

Ejemplos:
  - Crear un préstamo completo con sus cuotas y participaciones.
  - Registrar un pago, calcular la imputación y distribuir a inversores.
  - Cambiar la tasa de un préstamo y recalcular cuotas futuras.

Reglas de esta capa:
  - Cada caso de uso es una operación atómica.
  - Usa transacciones para garantizar consistencia.
  - Emite correlacion_id para poder rastrear todo.
  - Registra auditoría de los cambios de estado.
"""