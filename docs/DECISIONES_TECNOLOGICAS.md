# Decisión tecnológica y estrategia de evolución

**Fecha:** 27 de noviembre de 2026  
**Estado:** decisión vigente para el MVP local; evolución futura condicionada a necesidades demostrables.  
**Seguimiento:** [Arquitectura modular (#267)](https://github.com/JavierGrecco/prestamos_privados/issues/267) y [MVP local (#223)](https://github.com/JavierGrecco/prestamos_privados/issues/223).

## Decisión ejecutiva

Mantener **Python como lenguaje del dominio, la aplicación y la autoridad financiera**, **SQLite como persistencia local**, **Streamlit como interfaz del MVP** y **CSS como capa de presentación**.

No incorporar ahora JavaScript/TypeScript en las pantallas ni dividir el producto en servicios. No se trata de rechazar el ecosistema web: se reserva **TypeScript para componentes interactivos concretos** o para una futura interfaz web independiente si la experiencia de producto lo justifica.

La decisión busca evitar dos riesgos actuales: duplicar reglas financieras y sumar complejidad de construcción, empaquetado, pruebas y seguridad antes de cerrar la aceptación del MVP.

## Línea base verificada

En el código de main de esta fecha:

- pyproject.toml declara Python >=3.11, Streamlit >=1.65.0 y Plotly >=7.1.0.
- dominio/, aplicacion/, infraestructura/ y ui/ son capas Python con responsabilidades separadas.
- La UI usa Streamlit y tres hojas CSS (estilos_base.css, estilos_controles.css y estilos_componentes.css) cargadas por ui/estilos.py. Hay tres paletas: clara, intermedia y oscura.
- ui/componentes.py centraliza la construcción de fragmentos HTML confiables y el escape de texto variable. La UI no debe convertir entradas de usuario en HTML/JavaScript ejecutable.
- No hay un frontend JavaScript/TypeScript propio en el repositorio. Los componentes visuales compartidos actuales se construyen desde Python/HTML/CSS.
- Decimal, las reglas de dominio, las transacciones SQLite, el ledger y la auditoría permanecen bajo autoridad Python.

La auditoría modular ejecutada en CI sobre el HEAD f5367f4 analizó 323 archivos Python, 1.748 importaciones y 318 cruces entre capas; encontró 54 observaciones clasificadas y cero ciclos. De esas observaciones, 7 son construcciones pendientes de migración, 1 es una excepción temporal documentada y 46 corresponden a usos de composición en el borde. El inventario es una medición de dependencias, no un porcentaje de arquitectura terminada.

## Por qué el núcleo debe seguir en Python

La robustez financiera no depende de que un lenguaje sea más nuevo o se use en el navegador. Depende de una única autoridad de cálculo, precisión decimal explícita, políticas aprobadas, persistencia transaccional, idempotencia, trazabilidad y pruebas con ejemplos económicos.

Este repositorio ya tiene esas responsabilidades implementadas y probadas en Python. Reescribirlas en JavaScript/TypeScript crearía dos implementaciones de mora, amortización, devengamientos, waterfall, imputaciones y redondeo que podrían divergir.

Además, el tipo Number de JavaScript usa IEEE 754 de doble precisión; los enteros solo son exactos hasta 2^53 - 1 y los decimales binarios no representan exactamente todas las fracciones decimales. TypeScript agrega comprobaciones estáticas antes de ejecutar el programa, pero no reemplaza la validación de datos en tiempo de ejecución ni convierte Number en un tipo monetario exacto.

Por eso:

- Los importes y las reglas financieras continúan calculándose en Python con los tipos y políticas existentes.
- Si se incorpora un contrato HTTP o un componente web, los importes Decimal se transportarán como **cadenas decimales explícitas** o como unidades menores enteras con escala y moneda declaradas; nunca se confiará en un number del navegador como autoridad contable.
- El frontend podrá formatear y presentar importes, pero no decidir intereses, mora, imputaciones, saldos, XIRR ni redondeos financieros.
- Toda acción iniciada desde la interfaz debe volver a un caso de uso Python, donde se validan identidad, permisos, valores, revisión e idempotencia.

## Papel de cada tecnología

| Tecnología | Decisión actual | Responsabilidad |
|---|---|---|
| Python | Mantener y fortalecer | Dominio, casos de uso, contratos, persistencia, cálculos, reportes y automatizaciones |
| SQLite | Mantener para el alcance local | Datos operativos, ledger, auditoría y transacciones |
| Streamlit | Mantener para cerrar el MVP | Navegación, formularios, estados de sesión y composición de pantallas |
| CSS | Usar ahora | Temas, jerarquía visual, responsive, estados, foco y accesibilidad |
| HTML controlado | Uso acotado | Componentes compartidos cuya salida escape texto variable |
| JavaScript | No agregar de forma general | Solo comportamiento de navegador que no pueda resolverse bien con Streamlit/CSS |
| TypeScript | Preferido si aparece frontend propio | Componentes web con contratos tipados y pruebas de interacción |
| React | Opcional, no decidido | Solo para componentes con estado e interacción complejos que justifiquen un framework |
| FastAPI | Futuro condicionado | Adaptador HTTP a los casos de uso Python si se necesita una API para otro cliente |
| Rust/Go u otro lenguaje compilado | No incorporar ahora | Solo ante un cuello de botella medido o una integración técnica que lo exija |

## Dónde sí puede aportar JavaScript/TypeScript

Hay dos caminos graduales; no requieren reescribir el motor financiero.

### 1. Componente web dentro de Streamlit

Es el camino de menor alcance cuando una pantalla necesita una interacción que los widgets actuales no resuelven bien: por ejemplo, una línea de tiempo de flujos con selección múltiple, una visualización financiera con zoom/selección coordinada, o una grilla de comparación muy interactiva.

Antes de crear uno, se debe probar si Streamlit nativo o Plotly resuelve el problema. Si no alcanza, se puede evaluar un componente personalizado de Streamlit. Para una pieza pequeña, TypeScript sin framework reduce dependencias; para una experiencia con mucho estado y varios subcomponentes, React + TypeScript puede justificarse.

La documentación vigente de Streamlit presenta Components v2 como la vía recomendada para componentes nuevos, con comunicación bidireccional y soporte de HTML/CSS/JavaScript; también ofrece plantillas con TypeScript y React. Es una opción técnica disponible, no una razón suficiente para incorporarla al producto hoy.

**Límite de seguridad:** Streamlit considera confiable el código HTML/CSS/JavaScript de un componente y no lo sanitiza. Sus scripts pueden ejecutarse con acceso al DOM de la aplicación. Nunca se deben interpolar en esos bloques nombres, notas, referencias, datos de préstamos, valores de la base, archivos ni respuestas de herramientas sin una validación/serialización segura. Los eventos del componente expresan intenciones; Python vuelve a validar y ejecuta el caso de uso.

### 2. Interfaz web independiente

Solo conviene evaluar una SPA (por ejemplo, React + TypeScript) cuando exista una necesidad de producto sostenida: acceso desde múltiples dispositivos, navegación y formularios más complejos que Streamlit, colaboración en tiempo real, experiencia móvil avanzada, diseño público/externo o una separación clara entre clientes y backend.

En ese escenario, la primera opción sería conservar el dominio y la aplicación Python y exponerlos a través de una API HTTP (FastAPI es un candidato razonable). La API sería otro adaptador del mismo monolito modular, no un segundo motor financiero ni un microservicio por pantalla. El despliegue, la autenticación, las sesiones, la autorización y la protección de datos tendrían que diseñarse como una etapa propia.

## Qué mejorar con CSS ahora

CSS es suficiente para muchas mejoras visuales y de interacción: jerarquía, espaciado, responsive, tablas, tarjetas, estados hover/disabled, foco de teclado, contraste y respeto por movimiento reducido. No necesita JavaScript para esos cambios.

Las hojas actuales se apoyan en selectores del DOM de Streamlit y BaseWeb. Esos selectores pueden cambiar con una actualización de Streamlit; por eso, las modificaciones de estilos deben ser pequeñas y estar cubiertas por pruebas de navegador cuando alteren controles o recorridos críticos. No se debe usar CSS para ocultar errores de flujo, controles inaccesibles ni información financiera importante.

## Criterios para aprobar una nueva tecnología

Una propuesta de JavaScript/TypeScript, React, API o backend adicional debe mostrar todo lo siguiente:

1. Una necesidad de usuario que la interfaz actual no resuelve de forma suficiente.
2. Una prueba de concepto pequeña frente a la alternativa nativa de Streamlit/Plotly/CSS.
3. Contrato explícito entre Python y frontend; DTOs validados y sin lógica financiera duplicada.
4. Coste operativo completo: build, dependencias, seguridad, empaquetado local, pruebas y actualizaciones.
5. Cobertura funcional y de navegador equivalente al riesgo introducido.
6. Beneficio medible en usabilidad, accesibilidad, mantenimiento o capacidad funcional.

Si la propuesta no supera esos criterios, no se agrega tecnología.

## Ruta acordada

- **Ahora — MVP local:** mantener Python + Streamlit + SQLite; continuar fortaleciendo el CSS y cerrar aceptación funcional/operativa. No abrir una migración de frontend.
- **Luego — necesidad visual concreta:** seleccionar un caso acotado de lectura, prototipar un componente TypeScript y probarlo con datos sintéticos; la acción real seguirá en Python.
- **Más adelante — cambio de producto:** si el MVP evoluciona a producto web multiusuario, diseñar API, autenticación, modelo de despliegue y frontend como una decisión arquitectónica nueva.

La incorporación de JavaScript/TypeScript no autoriza activar V3, cambiar Legacy, modificar el significado de las imputaciones ni reescribir datos históricos.

## Referencias técnicas

- [Streamlit: overview de componentes personalizados](https://docs.streamlit.io/develop/concepts/custom-components/overview)
- [Streamlit: Components v2](https://docs.streamlit.io/develop/concepts/custom-components/components-v2)
- [Streamlit: componentes empaquetados con TypeScript/React](https://docs.streamlit.io/develop/concepts/custom-components/components-v2/package-based)
- [Streamlit: advertencia de seguridad para HTML/CSS/JavaScript de componentes](https://docs.streamlit.io/develop/api-reference/custom-components/st.components.v2.component)
- [TypeScript Handbook: comprobación estática de tipos](https://www.typescriptlang.org/docs/handbook/intro.html)
- [MDN: representación numérica IEEE 754 en JavaScript](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Numbers_and_strings)
