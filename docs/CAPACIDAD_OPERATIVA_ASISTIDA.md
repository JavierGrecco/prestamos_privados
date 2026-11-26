# Capacidad de operación financiera asistida

**Estado:** diseño de producto documentado; no implementado.  
**Prioridad:** posterior a la aceptación del MVP local (#223).  
**Seguimiento:** [Issue #370](https://github.com/JavierGrecco/prestamos_privados/issues/370).

## 1. Propósito y diferencial

La capacidad busca que una persona pueda **registrar y comprender su actividad financiera con menos pasos, sin perder la precisión ni la trazabilidad del sistema**.

No es un chatbot que decide por el usuario, tampoco un gestor de gastos domésticos. Es una capa de interacción contextual que conecta lenguaje cotidiano con los casos de uso, consultas y modelos financieros que Préstamos Privados ya mantiene.

El diferencial está en la integración con el dominio del producto:

- entiende la relación entre persona, préstamo, cuota, pago, inversor y plan de reposición;
- reutiliza las reglas y los servicios que ya gobiernan los importes;
- separa hechos registrados, valores declarados, estimaciones y proyecciones;
- prepara y explica antes de ejecutar;
- conserva el control humano y la privacidad local como comportamiento predeterminado.

No debe crear otra cartera, otro ledger ni una contabilidad paralela.

## 2. Las tres capacidades

### 2.1. Registro contextual en lenguaje cotidiano

El usuario podrá escribir una instrucción como:

> Recibí ARS 250.000 de Ana hoy por la cuota del préstamo 0042.

El sistema no registra directamente. Traduce el texto a un **borrador tipado** con, como mínimo:

| Campo | Regla |
|---|---|
| Tipo de operación | Debe poder distinguir un pago de préstamo de un aporte, flujo o valuación de un plan |
| Persona | Se resuelve contra personas existentes; nombres repetidos requieren selección |
| Préstamo o plan | Se busca dentro de los registros disponibles y se muestran candidatos cuando hay más de uno |
| Importe | Se interpreta con reglas explícitas de formato regional y se representa como `Decimal` |
| Moneda | Debe estar identificada; un símbolo ambiguo o una moneda ausente requiere confirmación |
| Fecha de recepción | Se extrae o se propone la fecha local actual y se muestra antes de confirmar |
| Fecha valor | Se conserva separada de la fecha de recepción; nunca se altera silenciosamente |
| Medio y concepto | Se completan solo cuando están explícitos o se eligen desde la interfaz |

La primera implementación debe limitarse a **texto y a un tipo de operación por instrucción**. El primer caso a cubrir será el borrador de un pago recibido de un deudor para un préstamo existente. Los aportes y movimientos de inversión se incorporarán después de probar que el patrón funciona sin ambigüedades.

#### Tratamiento de ambigüedades

El flujo debe detenerse y pedir una aclaración cuando:

- una persona coincide con más de un registro;
- una persona tiene más de un préstamo posible y la instrucción no lo identifica;
- no se puede determinar si el texto describe dinero recibido o pagado;
- el importe o la moneda pueden interpretarse de más de una manera;
- la fecha es inválida o la expresión temporal no puede resolverse con certeza;
- la instrucción mezcla dos operaciones, contiene datos contradictorios o pide una acción no admitida.

No se debe seleccionar silenciosamente el primer resultado, inferir una relación inexistente ni convertir un dato estimado en un hecho.

#### Camino obligatorio de confirmación

1. Normalizar el texto sin ejecutarlo ni persistirlo.
2. Detectar intención y extraer campos candidatos.
3. Resolver persona, préstamo o plan contra consultas oficiales.
4. Mostrar los datos identificados, los pendientes y el nivel de ambigüedad.
5. Completar la aclaración mediante controles normales de la interfaz.
6. Ejecutar la vista previa oficial correspondiente.
7. Exigir una confirmación expresa del operador.
8. Delegar en el caso de uso actual, conservando idempotencia, transacción y auditoría.
9. Mostrar el resultado persistido y su identificador.

La confirmación debe volver a validar la revisión del préstamo y el modo efectivo del motor. Si cambiaron desde la vista previa, se invalida el borrador y se solicita generar una nueva vista previa.

### 2.2. Consultas financieras contextuales

El usuario podrá formular preguntas en lenguaje natural, por ejemplo:

- ¿Cuánto capital tengo colocado y cuánto se recuperó?
- ¿Qué cuotas vencen en los próximos siete días?
- ¿Cuánto aporté efectivamente a este plan?
- ¿Qué diferencia hay entre el capital nominal y el objetivo de reposición?
- ¿Qué parte del resultado es realizada y qué parte depende de valuaciones o supuestos?

Estas consultas son **de solo lectura**. La respuesta debe provenir de consultas y reportes existentes, no de cálculos improvisados ni de una respuesta generada sin evidencia.

Cada respuesta mostrará:

- fecha y hora de corte;
- persona, préstamo o plan al que se refiere;
- moneda y unidad de medida;
- fuente interna consultada;
- supuestos o filtros relevantes;
- separación entre registrado, declarado, estimado y proyectado;
- una indicación cuando los datos disponibles no alcancen para responder.

No debe presentar la información local como patrimonio total, saldo bancario ni disponibilidad completa de dinero. El sistema solo conoce los datos que se registraron en él.

### 2.3. Seguimiento del objetivo de reposición

La experiencia integrará el seguimiento de los planes de reposición existentes. La vista debe reunir, sin duplicar registros:

- capital inicial y objetivo de reposición;
- referencia de conservación de poder adquisitivo en USD, cotización, fecha y origen;
- aportes efectivamente registrados;
- flujos de inversión y costos externos asentados;
- valuaciones declaradas con su fecha y naturaleza;
- rendimiento realizado cuando sea calculable;
- rendimiento objetivo o benchmark como hipótesis;
- brecha pendiente y evolución temporal.

Los aportes, rescates y valuaciones no son equivalentes entre sí. Una valuación declarada no es efectivo disponible; un objetivo no es rentabilidad realizada; una proyección no es una obligación contractual.

La vista se apoyará en los planes, snapshots, consultas e informes existentes. **No se creará un nuevo concepto de cartera o espacio financiero independiente.**

## 3. Alcance incremental y prioridades

| Etapa | Entrega | Condición de salida |
|---|---|---|
| 0 | Aceptar el MVP local de préstamo y reposición | Recorridos manuales, conciliación y operación local demostrados |
| 1 | Interpretación local de texto para preparar borradores de pago | Campos explícitos, ambigüedad segura, preview oficial y confirmación |
| 2 | Consultas financieras de solo lectura | Respuestas respaldadas por consultas oficiales, con corte y supuestos |
| 3 | Vista integrada de objetivos de reposición | Conciliación con aportes, flujos, valuaciones y reportes sin doble conteo |
| 4 | Evaluar voz, imágenes u otros mecanismos de captura | Modelo de privacidad, retención y seguridad revisado y aprobado |

La etapa 0 no es negociable: esta capacidad no retrasa ni sustituye el cierre del MVP coordinado por #223.

## 4. Contrato técnico previsto

### Interpretación y borrador

La interpretación debe producir una estructura de aplicación tipada, no un comando financiero ejecutable. El borrador incluirá:

- tipo de intención;
- referencias candidatas a entidades existentes;
- campos extraídos y campos faltantes;
- errores y ambigüedades;
- fecha de creación del borrador;
- estado de revisión;
- huella de la instrucción normalizada para prevenir reuso accidental en la interfaz, sin convertirla en clave de registro.

El texto original será efímero. La persistencia comienza únicamente cuando el usuario confirma y el caso de uso financiero actual termina correctamente.

### Responsabilidades por capa

- **Interfaz (`ui`):** captura el texto, muestra el borrador, permite resolver ambigüedades y solicita confirmación.
- **Aplicación (`aplicacion`):** interpreta la intención, valida campos, resuelve el contexto mediante puertos y construye el borrador tipado.
- **Infraestructura (`infraestructura`):** provee los adaptadores y fábricas ya existentes para personas, préstamos, preview, consultas y registro.
- **Dominio (`dominio`):** conserva la autoridad sobre cálculos, intereses, mora, imputaciones, cuotas y reglas monetarias; no recibe texto libre ni depende de un proveedor de IA.

El parser no debe importar Streamlit, SQLite ni repositorios concretos. Tampoco debe generar SQL, ejecutar código, modificar registros directamente ni duplicar servicios financieros.

### Uso futuro de IA

La primera versión será local y determinista. No necesita un proveedor de IA para validar si el flujo aporta valor.

Una eventual IA podrá ayudar a interpretar frases difíciles o redactar explicaciones, pero solo recibirá los campos mínimos necesarios, con consentimiento explícito y un proveedor configurable. Nunca será autoridad de cálculo, identidad, autorización o escritura. Desactivar el proveedor no debe impedir el registro manual ni las consultas normales.

## 5. Seguridad, privacidad e integridad

- No enviar texto financiero, nombres, importes ni documentos fuera del equipo en la primera versión.
- No conservar prompts, audios ni imágenes por defecto; conservar solo los datos estructurados que el usuario confirmó como operación.
- No inferir identidad ni privilegios desde el texto. Se mantienen las capacidades del operador autenticado en el modo local.
- No ejecutar operaciones por intención implícita, doble clic ni repetición del mensaje.
- Utilizar la idempotencia ya provista por cada caso de uso; una huella de texto no sustituye la clave idempotente del registro.
- Mantener una sola transacción y el rollback completo de pagos, imputaciones, ledger y auditoría.
- Invalidar borradores cuando cambien el préstamo, su revisión, el modo del motor o los datos relevantes.
- No crear conexiones bancarias, sincronización remota ni acceso multiusuario como efecto colateral de esta función.

## 6. Pruebas y criterios de aceptación

La función no se considera terminada por demostrar que reconoce una frase. Debe superar, al menos, estos grupos de pruebas:

1. **Lenguaje y formato:** variantes de redacción, importes con formato argentino, decimales, fechas explícitas, expresiones relativas, tildes y espacios.
2. **Ambigüedad:** personas homónimas, varios préstamos, moneda omitida, símbolo ambiguo, verbo de dirección dudosa, fechas imposibles e instrucciones múltiples.
3. **Seguridad de ejecución:** ninguna escritura antes de confirmar, ninguna operación por defecto, rechazo de intenciones no admitidas y ausencia de acceso directo a SQL.
4. **Integridad financiera:** preview igual al caso de uso vigente; revisión obsoleta invalida la confirmación; la repetición no duplica; un error revierte toda la unidad transaccional.
5. **Consultas:** fecha de corte, moneda, fuentes, filtros, supuestos y distinción entre datos registrados, declarados y proyectados.
6. **Reposición:** aportes, flujos y valuaciones no se mezclan ni duplican; la brecha se reconcilia con los reportes del plan.
7. **Privacidad:** los textos originales no quedan en logs, tablas ni exportaciones; ninguna llamada externa ocurre en el modo local.

La experiencia se acepta cuando una persona puede completar el recorrido desde la instrucción hasta la confirmación, comprender qué va a ocurrir antes de hacerlo y verificar el mismo resultado en el historial financiero habitual.

## 7. Lo que deliberadamente no incluye

- Seguimiento genérico de gastos, presupuestos domésticos o categorías de consumo.
- Una métrica de dinero «seguro para gastar» sin conocer las cuentas y obligaciones externas.
- Escritura automática o confirmación implícita de pagos, aportes o valuaciones.
- Cálculos financieros realizados por un modelo de lenguaje.
- Lectura bancaria, SMS, notificaciones, billeteras o Apple Pay.
- Voz, fotografía de comprobantes o aplicación móvil nativa en la primera entrega.
- Sincronización cloud, operación remota o una nueva identidad multiusuario.
- Recomendaciones de inversión presentadas como garantía o asesoramiento personalizado.

## 8. Decisión de producto

La capacidad debe hacer que Préstamos Privados sea más fácil de operar y entender sin alterar su principal promesa: **cada cifra debe poder explicarse, cada movimiento debe tener respaldo y cada escritura debe permanecer bajo control del operador**.

Se construirá de forma incremental, reutilizando el producto existente y con evidencia de aceptación por etapa. Hasta entonces es una dirección aprobada para el backlog, no una función disponible.
