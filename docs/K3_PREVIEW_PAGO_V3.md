# K3 — Preview canónico de pagos V3

## Objetivo

El preview de la pantalla de pagos puede calcular el mismo PlanPago V3 que la ruta de registro, sin escribir en la base.

## Flujo

1. se relee el estado vigente del préstamo;
2. se obtienen tasa y configuración activas;
3. se generan, si corresponde, devengamientos incrementales;
4. se calcula el PlanPago V3 canónico;
5. si existe excedente, RAI/RNI se planifica solo cuando el usuario eligió una opción;
6. durante SOMBRA se compara el resultado contra la simulación histórica.

## Seguridad funcional

- el preview no persiste pagos, imputaciones ni cuotas;
- una divergencia entre histórico y V3 se muestra explícitamente;
- el modo V3 efectivo no permite confirmar si el preview canónico falla;
- Legacy conserva el comportamiento efectivo durante la transición.

## RAI/RNI

El preview utiliza la misma función pura de planificación de adelantos que la ruta V3.
La selección de RAI o RNI sigue siendo una decisión explícita del usuario y no existe una opción por defecto.

## Estado de transición

El preview histórico permanece visible como referencia cuando se usa SOMBRA o V3.
Esto permite comparar antes de retirar el cálculo histórico de la interfaz.

## Próximo paso

Una vez que K3 demuestre equivalencia sostenida en previews, se puede retirar gradualmente el preview histórico y dejar V3 como única fuente visible de planificación.