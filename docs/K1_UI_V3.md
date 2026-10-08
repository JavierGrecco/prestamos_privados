# K1 — Integración funcional del Motor V3 en la UI

## Objetivo

Hacer utilizables desde Streamlit los avances estabilizados del Motor V3 sin mover reglas financieras a la interfaz.

## Qué se integra

La pantalla de registro de pagos puede trabajar con tres modos:

- **Legacy**: utiliza el registrador histórico;
- **Sombra**: Legacy sigue siendo efectivo y V3 calcula sobre el snapshot previo;
- **V3 efectivo**: requiere un preflight aprobado.

La UI no construye el waterfall ni modifica saldos directamente.

## Registro

El servicio ServicioRegistroPagoUI convierte la intención capturada por Streamlit en RegistrarPagoCommand y delega la ejecución.

Para V3 se utiliza el caso de uso completo con:

- devengamientos;
- distribución a inversores;
- RAI/RNI;
- revisión optimista;
- idempotencia.

La clave de idempotencia se conserva durante el intento de confirmación de la UI y se genera una nueva clave cuando el intento anterior falla sin persistir.

## Sombra

Con el modo Sombra:

UI → RegistrarPagoCommand → snapshot SQLite previo → Legacy (resultado efectivo) → V3 sobre snapshot → comparación → observabilidad

Una divergencia o un error de V3 sombra no reemplaza el resultado efectivo de Legacy.

## Estado del motor

La nueva página Motor V3 muestra:

- modo seleccionado;
- ejecuciones SOMBRA;
- tasa de coincidencia;
- divergencias;
- errores;
- criterios del preflight.

Esto permite observar la preparación del cut-over desde la misma aplicación.

## Seguridad funcional

V3 efectivo no se puede activar desde la UI si el preflight no está aprobado.

No existe fallback automático dentro de una operación financiera.

## Alcance pendiente

Esta etapa no completa todavía:

- preview 100% basado en el plan V3 canónico;
- sustitución del preview histórico;
- dashboard financiero avanzado;
- cut-over productivo;
- autenticación/autorización.

Esos trabajos requieren evidencia adicional y se mantienen separados de esta primera vertical.