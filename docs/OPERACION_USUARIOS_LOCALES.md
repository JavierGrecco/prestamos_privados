# Cuentas de acceso locales

## Alcance

Esta versión incorpora autenticación local con cuentas almacenadas en SQLite.
Las cuentas de acceso son distintas de las personas del negocio: no hace falta
ser deudor ni inversor para iniciar sesión.

El modo disponible es **local**. No hay registro público, autenticación online,
verificación de email ni recuperación de contraseña por correo. No publiques ni
expongas esta instancia a Internet. Para un despliegue online hace falta integrar
un proveedor de identidad real y revisar el aislamiento por usuario antes de
habilitarlo; la variable `PRESTAMOS_AUTH_MODE` con otro valor detiene la app.

## Preparar una base nueva

Desde la raíz del repositorio y con el entorno virtual de esta misma carpeta:

```bash
python -m scripts.migrar_base datos/prestamos-local.db --aplicar
PRESTAMOS_AUTH_MODE=local \
PRESTAMOS_DB_PATH="$PWD/datos/prestamos-local.db" \
streamlit run ui/app.py
```

El primer inicio muestra el asistente **Configurar administrador local**.
Creá la cuenta inicial `admin` con un nombre y una contraseña de al menos 12
caracteres. No existe una contraseña por defecto y no se guarda la contraseña
en texto plano.

Para usar otra ruta, cambiá `PRESTAMOS_DB_PATH` tanto al ejecutar la migración
como al iniciar Streamlit.

## Actualizar una base existente

La migración v017 agrega el registro de cuentas sin modificar préstamos, pagos
ni movimientos económicos. Como el ciclo de vida de la base está protegido,
primero inspeccioná la versión y guardá un backup verificado:

```bash
python -m scripts.migrar_base datos/prestamos.db
python -m scripts.migrar_base datos/prestamos.db \
  --aplicar \
  --backup backups/prestamos-antes-de-usuarios.db
```

La ruta del backup debe ser nueva y el comando verifica la copia antes de
actualizar. Después de migrar, al abrir la aplicación por primera vez se pedirá
configurar el administrador local si la tabla de cuentas está vacía. Si la base
contiene datos que no querés exponer al primer usuario local, conservá la copia
original y trabajá con una base nueva en una ruta separada.

## Roles

| Rol | Acceso |
|---|---|
| **ADMIN** | Operación completa, Motor V3, auditoría y administración de cuentas |
| **OPERADOR** | Consultas y tareas operativas; no administra usuarios ni configura Motor V3 |
| **LECTURA** | Paneles y reportes de consulta; no accede a las pantallas operativas ni administra usuarios |

Los permisos derivan del rol guardado para la cuenta. Cambiar un nombre visible
o elegir otra persona del directorio no cambia las capacidades del usuario.

La pantalla **Usuarios** permite crear cuentas, cambiar nombre y rol, desactivar
cuentas y restablecer una contraseña. Las cuentas se desactivan en vez de
borrarse para conservar la historia de auditoría. El sistema evita desactivar
el último administrador activo. Los cambios se registran en la auditoría global
y los secretos nunca forman parte de esa evidencia.

## Recuperar una contraseña de administrador

Si el administrador se olvida la contraseña, el propietario del equipo puede
restablecerla desde una terminal local:

```bash
python -m scripts.restablecer_password_local datos/prestamos-local.db --usuario admin
```

El comando pide y confirma la nueva contraseña sin mostrarla en pantalla.
Requiere acceso al archivo SQLite y solo permite restablecer una cuenta ADMIN
activa. La operación queda auditada como mantenimiento local. No usar ni exponer
este comando como una ruta HTTP o una función de recuperación online.

Para resetear la contraseña de un operador o de lectura, ingresá como ADMIN y
usá **Usuarios → Administrar cuenta → Restablecer contraseña**.

## Uso desde una copia de trabajo

Los scripts deben ejecutarse desde la raíz del checkout que contiene el archivo
`scripts/migrar_base.py`. Si aparece `No module named scripts.migrar_base`,
esa copia todavía no tiene el archivo, o el comando se ejecutó desde otro
checkout. La carpeta del entorno virtual también debe corresponder al mismo
proyecto. Verificá:

```bash
pwd
git status
git branch --show-current
python -c "import sys; print(sys.executable)"
ls scripts/migrar_base.py
```

No borres ni reemplaces la base existente solo para resolver un error de
importación. Primero confirmá qué checkout y qué ruta de base está usando la
aplicación.

## Pendiente online

El alta pública, verificación de correo, recuperación por email, expiración de
sesiones en servidor y proveedor OIDC/SSO forman parte de una etapa posterior.
No se implementa autenticación casera para Internet en esta fase. Antes de abrir
un entorno multiusuario externo se debe completar N4, configurar secretos y
políticas de cookies/proxy, revisar los límites de acceso por persona y ejecutar
pruebas E2E de autorización.
