# Principios de experiencia humana

## Propósito

Préstamos Privados administra dinero, pero la persona no debería necesitar
ser especialista en finanzas para entender qué está pasando.

La regla de producto es:

> **La persona primero. Toda cifra debe responder tres preguntas: qué es, por qué importa y qué puede hacer con ella.**

Este principio aplica tanto a quien invierte como a quien tiene una deuda.

## Reglas de lenguaje

### 1. Hablar como una persona

Preferimos:

- “Tenés invertido”
- “Te falta pagar”
- “Próximo pago estimado”
- “Cobraste”
- “Invertiste”
- “Hay un atraso”

y evitamos mostrar como texto principal expresiones internas como
capital_deudor_pendiente, cashflow, read model o fingerprint.

### 2. No esconder la incertidumbre

Toda información debe quedar claramente separada entre:

- **Confirmado / real:** ya ocurrió y está registrado.
- **Estimado:** todavía no ocurrió y sirve para planificar.

Una proyección nunca debe presentarse como una promesa.

### 3. No mezclar roles

Una persona puede ser deudora, inversora o ambas.

Cuando tiene ambos roles:

- “Tus inversiones” muestra solamente inversiones.
- “Tus préstamos” muestra solamente deudas.
- No se mezclan saldos de ambos roles bajo una etiqueta genérica.

### 4. Explicar antes de profundizar

La pantalla inicial debe mostrar lo esencial y reservar el detalle técnico para
una acción explícita como “Ver detalle financiero”.

### 5. Los términos difíciles necesitan una explicación

Cuando aparece un concepto financiero, debe existir una ayuda cercana o un
glosario.

## Glosario mínimo

**Capital:** dinero original del préstamo.

**Cuota:** importe que corresponde pagar en una fecha.

**Interés:** costo de usar dinero prestado. En una inversión forma parte de lo
que genera el cobro.

**Mora:** importe adicional que puede aplicarse cuando un pago llega después del
vencimiento, según las reglas del préstamo.

**Adelanto:** pago anticipado de capital que puede permitir bajar cuotas o
terminar antes, según las condiciones.

**Estimado:** dato futuro que todavía no ocurrió y se usa para planificar.

## Regla para cada nueva pantalla

Antes de agregar una cifra a la UI, responder:

1. ¿La persona sabe qué significa?
2. ¿Sabe si es real o estimada?
3. ¿Sabe por qué importa?
4. ¿Sabe qué puede hacer después?

Si alguna respuesta es “no”, la pantalla todavía necesita explicación.

## No significa esconder información

La simplicidad no elimina precisión.

La aplicación seguirá manteniendo:

- cálculos exactos;
- trazabilidad;
- auditoría;
- detalle de cada operación;
- información técnica para quienes administran el sistema.

La diferencia es que esa complejidad se revela cuando aporta valor, no antes.

## Aplicación inicial

M1 incorpora esta regla mediante una nueva superficie llamada **Mi espacio**.

Es una vista de solo lectura que adapta la información a la persona seleccionada
y separa:

- lo que tiene invertido;
- lo que todavía debe;
- el próximo movimiento esperado;
- la actividad que ya ocurrió;
- la explicación de los términos básicos.

No sustituye las pantallas administrativas ni modifica el motor financiero.
