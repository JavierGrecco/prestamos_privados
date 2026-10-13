## Validación confirmada

Hay dos referencias de CI relevantes:

1. El commit base `d0e826b34191051ae8898cfc2a7a0931bd1dab39` pasó la suite completa con **947 pruebas en Python 3.11, 3.12, 3.13 y 3.14**, junto con `compileall`, `pip check` y `git diff --check`.
   - [CI del PR de servicio y seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38200730217)
   - [CI de push del mismo commit](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38200727708)
2. El commit intermedio `f540946fb01da583bb7d52c2448b77e674a360aa`, que añadió los nuevos métodos de consulta y el módulo de pantalla, pasó **949 pruebas en cada una de las cuatro versiones**. Ese job todavía no cubría la integración final de navegación y dispatch de `ui/app.py`.
   - [CI de ese commit intermedio](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38200931233)

**La pantalla de historial y su integración en navegación/aplicación pasaron CI con 951 pruebas en cada versión** en el commit `d541d08af57e6e3c44cedc92cc5cdbb96bb14f16`: [CI PR #244](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38201347422) y [CI push](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38201343588).

**El formulario guiado de propuesta y la corrección acumulativa de propuestas sucesivas pasaron CI con 966 pruebas en cada versión** en el commit `47869d9c46d59ae6a56bf7230db74c5940c3a80b`. Los cuatro jobs de Python 3.11, 3.12, 3.13 y 3.14 finalizaron correctamente, junto con `compileall`, `pip check` y `git diff --check`.
- [CI del PR #245](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38201941745)
- [CI de push](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38201938394)

Los commits de documentación posteriores no alteran el código validado. Esta evidencia es de CI remoto; la aplicación local debe probarse visualmente antes de habilitar la función. La última suite local ejecutada por el responsable (944 pruebas) corresponde a un commit anterior a estos cambios de identidad e interfaz, por lo que todavía conviene ejecutar la rama actual en su Mac.


## Límites actuales

Esta entrega **todavía no es una función terminada para usar desde la UI**:

- no modifica aportes, flujos ni valuaciones originales;
- no cambia rendimiento, XIRR ni reportes;
- el formulario guiado de propuesta ya pasó CI, pero todavía requiere aceptación visual en la aplicación local; no hay flujo de revisión/aprobación/aplicación;
- la UI de consulta ya recibe la identidad autenticada de la sesión; todavía no incorpora creación, aprobación ni aplicación de propuestas;
- una escritura SQL directa puede eludir reglas de aplicación, aunque los triggers impidan UPDATE/DELETE en la bitácora.

Por lo tanto, las propuestas quedan como evidencia separada y no alteran el resultado financiero.

## Próximas entregas

1. Validar CI y suite local de servicio, autorización y pantalla de historial.
2. Probar visualmente acceso y comparación con ADMIN, OPERADOR y LECTURA.
3. Revisar migración desde copias históricas representativas y comprobar backup/restauración.
4. Diseñar una pantalla separada para proponer y luego revisar/aprobar correcciones con doble control si corresponde.
5. Diseñar, probar y auditar cómo una corrección aprobada pasa a reportes y XIRR, evitando doble contabilización.
6. Realizar aceptación manual antes de habilitar cualquier aplicación financiera.
