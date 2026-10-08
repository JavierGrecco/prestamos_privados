# J18 — Política unificada de imputación y devengamiento

## Decisión

El sistema debe tener una única política financiera para aplicar pagos. Legacy y
V3 pueden tener implementaciones distintas durante la transición, pero no deben
tomar decisiones financieras distintas sobre el mismo contrato.

La política se guarda por préstamo y se versiona por fecha de vigencia. Una
versión nueva no modifica las operaciones históricas.

## Configuración

La primera versión admite:

- **orden de obligaciones:** vencida más antigua primero;
- **waterfall:** por defecto MORA → INTERÉS → CAPITAL;
- **interés compensatorio después del vencimiento:** configurable;
- **mora:** habilitable, con tasa, base y convención;
- **capitalización de intereses:** deshabilitada en la política base.

La configuración no debe elegirse al registrar un pago. Debe surgir de la
política vigente del préstamo.

## Recomendación para este proyecto

La configuración predeterminada que considero más sólida es:

**Obligación más antigua vencida → MORA → INTERÉS → CAPITAL.**

Esto coincide con una práctica habitual de sistemas de servicing: separar la
selección de la obligación del orden de conceptos y permitir que las reglas
sean configurables a nivel de producto/contrato. Apache Fineract documenta
explícitamente esa separación y su configuración dinámica de payment
allocation. Mambu también aplica los pagos usando el orden configurado para el
producto y permite manejar pagos parciales. 

Para este sistema familiar conviene conservar un único perfil canónico como
default y permitir variantes solamente cuando el contrato realmente las
necesite.

## Por qué no conviene una configuración libre por operación

Cambiar el waterfall para un pago concreto haría que el mismo estado de deuda
produzca resultados diferentes según quién registre el pago. Eso perjudica:

- reproducibilidad;
- auditoría;
- conciliación;
- rollback;
- comparación Legacy/V3;
- evidencia para el canary.

Por eso la política debe resolverse antes del pago y quedar asociada al
préstamo.

## Interés y mora

Interés compensatorio y mora son conceptos diferentes. El motor debe poder
representarlos separadamente y decidir mediante política si el interés
compensatorio continúa después del vencimiento.

No debe existir capitalización implícita de intereses. El Código Civil y
Comercial establece como regla que no se deben intereses de los intereses,
salvo los supuestos específicos del artículo 770. También permite que la tasa
de interés moratorio sea acordada por las partes. 

Para préstamos sujetos a regulación financiera del BCRA existen además reglas
específicas sobre el interés punitorio y sobre la aplicación a cuotas vencidas
e impagas, por lo que la política concreta debe reflejar el contrato y el
régimen que resulte aplicable.

## Estado de la migración

La migración v015 crea la política canónica para los préstamos existentes y un
trigger que asigna la versión inicial a los nuevos préstamos.

El siguiente paso es migrar todas las rutas Legacy y V3 para que obtengan la
política vigente desde el mismo repositorio y eliminar decisiones financieras
hardcodeadas.

## Fuentes normativas y de industria

- Código Civil y Comercial de la Nación, arts. 768, 769, 770 y 900–903.
- BCRA, criterios sobre intereses punitorios en créditos con cuotas.
- Apache Fineract, Advanced Payment Allocation.
- Mambu, Processing Loan Repayments.
