# Plan de refactorización controlada del motor de pagos

## Objetivo

Eliminar cálculos financieros duplicados sin cambiar el resultado económico del sistema por accidente.

La refactorización se hace por etapas. Cada etapa deja una prueba que permite comprobar que el comportamiento anterior sigue siendo el esperado antes de eliminar código.

## Lo que encontramos

Actualmente hay varias piezas relacionadas con la imputación de pagos:

1. `ServicioPagos.registrar_pago()` contiene su propia lógica de reparto entre mora, interés y capital.
2. `dominio/imputacion.py` ya contiene una regla genérica de waterfall de imputación.
3. `dominio/escenarios_pago.py` calcula otra vez el reparto para poder simular un pago.
4. `dominio/plan_pago.py` agrega una tercera capa: toma el resultado y lo convierte en actualizaciones de cuotas.
5. `aplicacion/servicios/pagos_simulacion.py` / `pagos_simulacion_v2.py` construyen planes de simulación fuera del registro real.

Por eso no conviene conectar simplemente `registrar_pago()` a `planificar_pago()`. Primero hay que decidir qué pieza será la autoridad única y hacer que las otras la consuman.

## Orden elegido

### 1. Congelar y caracterizar el comportamiento actual

Antes de modificar `pagos.py` se obtiene una copia exacta del `registrar_pago()` que realmente está usando el proyecto local.

La caracterización debe cubrir al menos:

- pago exacto de una cuota;
- pago parcial;
- pago menor que el interés pendiente;
- pago que cubre interés pero no capital;
- mora nueva;
- mora arrastrada;
- interés arrastrado;
- capital arrastrado;
- cuota previamente parcial;
- pago superior a la deuda del período;
- RAI;
- RNI;
- excedente sin elegir RAI/RNI;
- tipo `COMPLEMENTO` cuando corresponde;
- imputaciones persistidas;
- saldo y estado de cuotas;
- interés extra generado;
- distribución a inversores;
- ledger;
- auditoría;
- rollback transaccional.

También se verifica qué ocurre ante entradas inválidas y ante errores provocados durante la transacción.

### 2. Separar claramente tres conceptos

No deben mezclarse:

- **deuda disponible para imputar:** lo que el préstamo debe en ese instante;
- **plan de aplicación:** cómo se reparte el pago y qué cuotas cambian;
- **efectos futuros:** por ejemplo, el interés que podría generarse sobre capital que queda pendiente.

La diferencia entre `interes_extra_generado_por_pago` y `interes_extra_estimado_proximo_periodo` debe conservarse: representan conceptos económicos distintos.

### 3. Elegir una única autoridad de cálculo

La dirección más consistente es que exista un único motor puro de dominio que:

1. reciba el estado financiero necesario;
2. aplique una sola vez el waterfall;
3. produzca el plan completo;
4. describa las actualizaciones de cuotas;
5. calcule los efectos derivados necesarios.

La función genérica de `dominio/imputacion.py` puede formar parte de esa autoridad para el waterfall de conceptos, pero no se debe forzar esa función a conocer detalles que pertenecen al ciclo de vida del préstamo.

### 4. Hacer que la simulación consuma esa autoridad

`simular_pago()` debe construir el estado de entrada y devolver el plan sin persistir cambios.

La simulación no debe tener un algoritmo alternativo.

### 5. Hacer que el registro consuma el mismo plan

`registrar_pago()` debe hacer principalmente trabajo de aplicación:

- validar el contexto;
- obtener el estado necesario;
- pedir el plan al dominio;
- persistir el pago;
- aplicar las actualizaciones de cuotas;
- procesar el eventual RAI/RNI;
- distribuir a inversores;
- registrar ledger y auditoría;
- confirmar todo dentro de una transacción.

No debe volver a decidir cuánto corresponde a mora, interés y capital.

### 6. Fortalecer pruebas de integración

Después de la integración se comparará explícitamente:

`resultado de simular_pago()` = `estado persistido por registrar_pago()`

para cada escenario relevante.

Además se verificará que una simulación no cambie la base.

### 7. Agregar una prueba estructural

Los tests funcionales no alcanzan para demostrar que dos algoritmos no vuelvan a divergir.

Se agregará una comprobación estructural que impida que `registrar_pago()` vuelva a contener el waterfall financiero y obligue a consumir el motor común.

La prueba estructural debe ser simple y estable; no debe depender de offsets de líneas.

### 8. Eliminar código anterior solamente después de estabilizar

Una vez verdes las regresiones:

- eliminar reglas duplicadas;
- simplificar imports;
- retirar módulos intermedios que ya no tengan una responsabilidad real;
- mantener compatibilidad pública de `ServicioPagos` donde sea necesario;
- documentar la nueva autoridad.

No se debe borrar `escenarios_pago.py` o `plan_pago.py` de entrada. Primero hay que demostrar cuál será su destino y qué comportamiento cubren.

## Qué no se va a cambiar durante esta etapa

- La interfaz Streamlit existente.
- Los temas visuales.
- La navegación.
- El esquema de datos, salvo que una prueba demuestre que una migración es realmente necesaria.
- La semántica de RAI/RNI.
- La distribución pro-rata entre inversores.
- El ledger y la auditoría.
- Los valores económicos existentes por el solo hecho de refactorizar.

## Criterio de finalización

La etapa se considera terminada cuando:

- el motor de cálculo existe en una sola autoridad;
- simulación y registro consumen esa autoridad;
- no queda un waterfall duplicado en `registrar_pago()`;
- las pruebas de regresión cubren los escenarios críticos;
- la simulación no modifica persistencia;
- el registro mantiene atomicidad;
- imputaciones, cuotas, inversores, ledger y auditoría siguen siendo consistentes;
- la suite completa queda verde;
- la inspección estructural confirma que no volvió a aparecer lógica duplicada.
