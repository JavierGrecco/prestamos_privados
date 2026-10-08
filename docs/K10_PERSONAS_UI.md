# K10 — Personas y roles desde la UI

K10 elimina la dependencia de datos precargados para comenzar a usar la
aplicación. La pantalla Personas queda disponible incluso con una base
SQLite recién creada.

## Alcance

La UI permite:

- listar y buscar personas;
- filtrar por estado y rol;
- crear personas;
- editar datos y estado;
- agregar roles;
- dar de baja roles sin borrar su historial;
- consultar préstamos relacionados como deudor o inversor.

Los roles disponibles son Deudor, Inversor, Garante y Administrador.

## Frontera de responsabilidades

Streamlit no escribe SQLite directamente.

El flujo es:

```text
UI
 ↓
ServicioPersonas
 ↓
PersonaRepo / PrestamoRepo / ParticipacionRepo
 ↓
SQLite
```

La pantalla de alta de préstamo también usa los roles activos para ofrecer
personas con rol Deudor e Inversor.

## Base vacía

Con cero personas:

```text
arranque
 ↓
navegación disponible
 ↓
Personas
 ↓
Nueva persona
 ↓
primer registro
 ↓
el resto de la aplicación queda habilitado
```

El script `scripts/seed_datos.py` continúa disponible como herramienta de
demostración, pero deja de ser requisito para el onboarding normal.

## Límites

La identidad del operador continúa siendo una futura responsabilidad de
autenticación/autorización. K10 administra los roles del negocio, pero todavía
no los convierte en permisos de acceso a la aplicación.
