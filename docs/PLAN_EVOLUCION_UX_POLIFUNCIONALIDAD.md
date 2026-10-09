# Plan de evolución — UX, identidad y personas polifuncionales

**Fecha:** 9 de octubre de 2026  
**Estado:** D0 y D1 integradas. D2 está en desarrollo en la rama `feat/personas-polifuncionales-d2`; D3–D6 siguen pendientes.  
**Issue coordinadora:** [#173](https://github.com/JavierGrecco/prestamos_privados/issues/173)

## Objetivo del programa

Convertir Préstamos Privados en una herramienta sólida, elegante y fácil de usar, sin comprometer los hechos financieros ni reemplazar reglas del dominio por lógica de interfaz.

El trabajo se entrega en cambios pequeños, verificables y documentados. Cada entrega debe decir qué problema resuelve, qué archivos cambia, qué pruebas se ejecutaron, qué riesgos quedan y qué paso sigue.

## Principios de diseño acordados

### 1. Cuenta, persona y relación financiera son conceptos diferentes

- **Cuenta de acceso:** credenciales, estado de la cuenta y capacidades de la aplicación: ADMIN, OPERADOR o LECTURA.
- **Persona financiera:** individuo registrado en el negocio, con identidad y datos personales.
- **Rol financiero:** cómo participa una persona en una o más operaciones: DEUDOR, INVERSOR o GARANTE.
- **Relación con una operación:** un préstamo determina en qué condición concreta participa la persona, qué importe o exposición tiene y qué historial le corresponde.

Los roles financieros son acumulables. Una persona puede ser deudora en un préstamo, inversora en otro y garante de un tercero. Ser ADMIN de la aplicación tampoco impide que la persona vinculada a esa cuenta sea inversora, deudora o garante.

La capacidad ADMIN procede exclusivamente de la cuenta autenticada y nunca de `roles_persona`. El vínculo entre una cuenta y una persona debe definirse de forma explícita y puede ser opcional: un administrador necesita poder operar el sistema aunque todavía no tenga una persona financiera vinculada. El comportamiento final del vínculo (persona principal, unicidad y alcance) se decidirá en D2 antes de migrar datos.

Actualmente existe `ADMIN` entre los roles de persona. No se eliminará ni transformará automáticamente ningún registro histórico. D2 debe inspeccionar el uso real del dato, definir compatibilidad y diseñar la transición antes de cambiar el catálogo para altas nuevas.

### 2. Las garantías pertenecen a operaciones concretas

El rol general GARANTE identifica una función posible, pero no sustituye una garantía vinculada a un préstamo. D2 debe definir la entidad y las reglas necesarias para reflejar esa relación, incluyendo su estado y trazabilidad. Cualquier liberación o baja debe conservar historial y no borrar pagos, saldos ni otros hechos económicos.

### 3. La navegación se organiza por tarea y capacidad

- Una única definición de pantallas debe incluir clave técnica, etiqueta humana, grupo, capacidad requerida, contexto de persona y nivel de exposición (habitual, administración o avanzado).
- La navegación se genera desde esa definición; no mantiene una lista independiente de permisos.
- El acceso se comprueba también al renderizar la ruta. Ocultar una opción no es una frontera de seguridad.
- Las funciones técnicas avanzadas se separan de la operatoria cotidiana.
- El detalle financiero se alcanza desde un préstamo concreto, no como una tarea global sin contexto.
- Las pantallas administrativas no deben quedar bloqueadas porque todavía no se seleccionó una persona financiera.
- No se elige automáticamente una persona por llamarse “Javier” ni por ser la primera de la lista. La persona consultada es contexto explícito; Mi espacio utiliza la vinculación personal cuando exista, no una selección arbitraria.

### 4. Dirección visual

El **tema oscuro es la preferencia principal y será el predeterminado** durante este programa. No se considera defecto que el usuario elija dark. Se preservará y mejorará esa experiencia primero: jerarquía visual, tipografía, contraste, espaciado, estados, cabecera y navegación compacta.

Si se mantienen los temas claro e intermedio, los tokens CSS y los controles nativos deben seguir siendo coherentes en ellos. No se cambiará dark por claro ni se ocultarán elementos de la barra de Streamlit con hacks CSS. Se revisará la configuración soportada de la propia plataforma.

### 5. Instalación local predecible

La ruta de trabajo, el intérprete Python, el entorno virtual y la base de datos deben quedar explícitos. La guía cubrirá PowerShell, CMD y macOS/Linux. No se reemplaza ni migra una base existente como efecto lateral de iniciar la UI. La autenticación actual es local-only: no debe exponerse a Internet ni describirse como multiusuario online listo.

## Mapa propuesto de navegación

La agrupación final se valida en D3; es el punto de partida, no una promesa de implementación exacta.

| Grupo | Pantallas / acciones |
|---|---|
| **Inicio** | Resumen, Mi espacio |
| **Cartera** | Personas, Préstamos, Pagos |
| **Análisis** | Análisis financiero, Planificación, Escenarios, Rendimiento, Comparar, Reportes |
| **Administración** | Usuarios y accesos, Auditoría, Operación del sistema |
| **Avanzado** | Motor de pagos V3 y controles operativos sensibles, restringidos por capacidad específica |
| **Acciones contextuales** | Detalle financiero desde un préstamo; selección de persona solo cuando la función la necesita |

Un grupo completo no se muestra a todos por defecto. El catálogo y las capacidades determinan las opciones visibles; el backend/entrypoint vuelve a comprobar el permiso.

## Entregas y criterios de aceptación

### D0 — Plan, alcance y seguimiento (integrada)

**Objetivo:** dejar las decisiones iniciales, entregas y criterios de validación en el repositorio y abrir seguimiento trazable.

**Incluye:** este documento, índice de documentación e issues de trabajo.

**Entrega integrada:** [PR #180](https://github.com/JavierGrecco/prestamos_privados/pull/180). El plan está enlazado desde el índice, y D1–D6 tienen issues y criterios de aceptación. Esta entrega fue documental; no modificó la UI ni el esquema financiero.

### D1 — Primer arranque recuperable y estado vacío (integrada)

**Issue:** [#174](https://github.com/JavierGrecco/prestamos_privados/issues/174)  
**PR integrado:** [#181](https://github.com/JavierGrecco/prestamos_privados/pull/181)

**Objetivo:** hacer posible que una cuenta ADMIN recién creada llegue a Personas, cree el primer registro y continúe trabajando, incluso cuando la base no contiene personas.

**Pasos de trabajo:**
1. Reproducir el flujo de base vacía con AppTest y trazar el orden de navegación, selección de persona y autorización.
2. Quitar las dependencias innecesarias de persona seleccionada para Personas, Usuarios y otras superficies administrativas autorizadas.
3. Mostrar una guía y una acción explícita para crear la primera persona, sin elevar permisos.
4. Eliminar selecciones implícitas de personas por nombre o posición de la lista en los flujos donde no son apropiadas.
5. Agregar regresiones E2E para base sin personas, acceso permitido y acceso denegado.

**Aceptación:** login ADMIN → Personas → alta de persona → Resumen funciona sin mensajes bloqueantes; no se concede ningún permiso que la cuenta no tenía.

### D2 — Persona polifuncional, asociación de cuenta y garantía (en desarrollo)

**Issue:** [#175](https://github.com/JavierGrecco/prestamos_privados/issues/175)  
**Rama de trabajo:** `feat/personas-polifuncionales-d2`  
**Diseño:** [D2 — Modelo de personas y garantías](D2_MODELO_PERSONAS_GARANTIAS.md)

**Objetivo:** formalizar el modelo de persona y sus relaciones financieras, separándolo de los permisos de una cuenta.

**Pasos de trabajo:**
1. Inspeccionar referencias y datos históricos del rol ADMIN en personas.
2. Definir vínculo cuenta-persona y sus reglas antes de cambiar el esquema.
3. Diseñar garantía ligada a préstamo, con estado e historia explícitos.
4. Implementar migración compatible, solo después de validar diseño e invariantes.
5. Agregar pruebas de servicio, UI, migración y conservación de hechos económicos.

**Aceptación:** la combinación DEUDOR + INVERSOR + GARANTE funciona; los roles se evalúan por operación; ADMIN conserva capacidades sin necesitar un rol financiero; los históricos no se eliminan ni reinterpretan en silencio.

### D3 — Catálogo de navegación y matriz de capacidades

**Issue:** [#176](https://github.com/JavierGrecco/prestamos_privados/issues/176)

**Objetivo:** sustituir listas de navegación/permisos duplicadas por una definición central.

**Pasos de trabajo:**
1. Inventariar todas las pantallas, acciones sensibles y requerimientos de contexto.
2. Definir capacidades explícitas: consulta, operación, administración, auditoría y control de motor, según necesidad.
3. Generar grupos y menús desde el catálogo, filtrados por cuenta y alcance.
4. Revalidar autorización al abrir cada superficie; cubrir intentos de acceso directos y cambios de rol.
5. Convertir Detalle financiero en navegación contextual desde un préstamo.

**Aceptación:** matriz por ADMIN/OPERADOR/LECTURA sin contradicciones; no hay opciones visibles que terminen en denegación previsible; no hay rutas sensibles sin control.

### D4 — Rediseño visual de prioridad oscura

**Issue:** [#177](https://github.com/JavierGrecco/prestamos_privados/issues/177)

**Objetivo:** que la aplicación se vea y se sienta como un producto único, ordenado y profesional.

**Pasos de trabajo:**
1. Validar estructura del nuevo menú y cabecera antes de afinar los detalles.
2. Corregir anchura útil del área de trabajo, jerarquía, ritmo, márgenes, tipografía, tablas, tarjetas y controles.
3. Mantener dark como default y armonizar estilos propios con widgets nativos.
4. Tratar por separado el área avanzada para no mezclar tareas técnicas con la navegación habitual.
5. Validar en ancho de escritorio, ventana angosta y pantalla pequeña; hacer inspección manual, además de AppTest.

**Aceptación:** no hay solapamientos ni navegación interminable; controles legibles y usables; se prueba dark y, si permanecen, los temas alternativos; se documentan capturas y defectos conocidos.

### D5 — Instalación y cuentas en Windows, macOS y Linux

**Issue:** [#178](https://github.com/JavierGrecco/prestamos_privados/issues/178)

**Objetivo:** una instalación nueva no depende del entorno del desarrollador.

**Pasos de trabajo:**
1. Documentar requisitos y comandos por sistema operativo.
2. Verificar que el intérprete y el entorno virtual pertenecen a la raíz elegida.
3. Explicar la diferencia entre inicializar base nueva, inspeccionar una base existente y migrarla con backup.
4. Documentar la creación del ADMIN inicial, alta de usuarios, entrega segura de credenciales y recuperación offline.
5. Probar realmente los procedimientos disponibles y declarar las plataformas no verificadas en lugar de asumir su funcionamiento.

**Aceptación:** una persona sigue la guía sin ambigüedad sobre raíz, entorno virtual ni archivo SQLite; no se expone la UI a Internet y no hay credenciales predeterminadas.

### D6 — Aceptación integral y cierre

**Issue:** [#179](https://github.com/JavierGrecco/prestamos_privados/issues/179)

**Objetivo:** validar el flujo completo tras integrar las etapas anteriores.

**Incluye:** base vacía e histórica, todos los roles de cuenta, rutas permitidas/denegadas, persona vinculada/no vinculada, roles financieros múltiples, garantías, revocación de sesión, migraciones y conservación histórica, accesibilidad básica, validación visual y seguridad.

**Aceptación:** CI completo en verde, pruebas E2E integradas y un resumen de resultados demostrables, limitaciones y pasos operativos. El cut-over financiero V3 queda fuera de este programa y mantiene sus propios criterios de aprobación.

## Estrategia de ramas y entregas

Se trabajará de forma **secuencial**. No se crearán todas las ramas funcionales en paralelo desde un mismo commit: quedarían obsoletas al integrar etapas anteriores y obligarían a mezclar o rehacer los cambios.

1. Crear una rama a partir de `main` actualizado para una entrega.
2. Mantener el alcance de esa rama limitado a una issue/entrega y añadir las pruebas correspondientes.
3. Abrir un PR que incluya resumen, pruebas ejecutadas, limitaciones y siguiente paso.
4. Esperar CI y revisar el diff; no declarar verde un check pendiente ni funcional una UI que no se inspeccionó.
5. Integrar la entrega cuando cumpla la aceptación; actualizar esta hoja de ruta y el registro de cambios.
6. Crear la rama siguiente desde el nuevo `main`.

Convención sugerida: `fix/ux-d1-arranque`, `feat/personas-polifuncionales-d2`, `feat/navegacion-capacidades-d3`, `feat/ui-dark-d4`, `docs/instalacion-local-d5`, `test/ux-aceptacion-d6`. Solo debe existir una rama de trabajo activa de este programa a la vez.

### Plantilla mínima para registrar cada entrega

Cada PR y actualización de este documento debe tener:
- **Problema y resultado esperado**
- **Qué se cambió** (archivos y comportamiento)
- **Qué no se cambió**
- **Pruebas ejecutadas** (comando, resultado real y versiones)
- **Validación manual** (pantallas, temas, tamaños, si aplica)
- **Riesgos o limitaciones restantes**
- **Próxima entrega e issue relacionada**

## Límites de seguridad y calidad

- No exponer esta aplicación local-only a Internet.
- No convertir selección de persona en autenticación ni autorización.
- No introducir datos financieros binarios `float` ni duplicar cálculos de dominio en la UI.
- No modificar hechos históricos al migrar roles o garantías.
- No habilitar V3 efectivo como parte del rediseño visual.
- Mantener el trabajo abierto de seguridad HTML, concurrencia SQLite y migraciones históricas; el diseño visual no sustituye esos frentes.
