# V3-B — Propiedades matemáticas y property-based testing

## Objetivo

Proteger el núcleo financiero puro con propiedades que deben mantenerse para
muchas combinaciones de entradas válidas, sin introducir una segunda
implementación de las fórmulas.

## Propiedades cubiertas

### Waterfall

- conservación de dinero: aplicado + excedente = recibido;
- aplicaciones estrictamente positivas;
- saldos posteriores no negativos;
- orden mora → interés → capital;
- procesamiento cronológico de obligaciones;
- determinismo: mismas entradas, mismo `PlanPago`.

### Devengamiento TNA

Para períodos segmentados bajo Actual/365, el interés es aditivo sobre una misma
base. La comparación tolera exclusivamente el efecto del redondeo monetario
en centavos.

### Devengamiento TEA

La acumulación se prueba de manera multiplicativa: la segunda etapa utiliza como
base el saldo generado por la primera. Se compara contra el cálculo directo y se
admite únicamente la diferencia causada por redondeos sucesivos.

### Convención Actual/365

Los días reportados deben coincidir exactamente con la diferencia real de fechas
y la fracción anual debe ser días / 365.

## Dependencia de testing

Hypothesis se incorpora únicamente a `requirements-dev.txt`, no al conjunto de
dependencias de runtime. CI instala las dependencias de desarrollo para ejecutar
la suite completa.

La versión mínima fijada es 6.168.5, verificada en PyPI el 5 de octubre de 2026;
Hypothesis publica soporte explícito para Python 3.11–3.14. citeturn209902search0turn209902search5

## Delimitación

Estas propiedades cubren el dominio puro. No sustituyen las pruebas de
persistencia, migraciones, atomicidad ni concurrencia ya incorporadas en H1-H4.
