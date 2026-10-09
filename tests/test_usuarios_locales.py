"""Pruebas de cuentas de acceso local, contraseñas y administración RBAC."""

from pathlib import Path

import pytest

from aplicacion.seguridad.passwords_locales import hash_password, verificar_password
from aplicacion.servicios.usuarios_locales import ServicioUsuariosLocales
from ui.autenticacion_local import sesion_local_vigente
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones


@pytest.fixture
def db(tmp_path: Path):
    with BaseDatos(tmp_path / "usuarios.db") as db:
        aplicar_migraciones(db)
        yield db


def _crear_admin(servicio: ServicioUsuariosLocales):
    return servicio.crear_administrador_inicial(
        username="admin",
        nombre="Administrador local",
        password="una-frase-larga-y-segura-2026",
    )


def test_password_usa_hash_salt_distinto_y_verifica_sin_texto_plano():
    password = "una-frase-larga-y-segura-2026"
    hash_a = hash_password(password)
    hash_b = hash_password(password)

    assert hash_a != password
    assert hash_b != password
    assert hash_a != hash_b
    assert hash_a.split("$")[0] == "scrypt"
    assert verificar_password(password, hash_a)
    assert not verificar_password("otra-frase-completamente-distinta", hash_a)
    assert not verificar_password(password, "formato-desconocido")


def test_configuracion_inicial_crea_un_admin_y_audita_sin_secreto(db):
    servicio = ServicioUsuariosLocales(db)
    admin = _crear_admin(servicio)

    assert admin.username == "admin"
    assert admin.rol == "ADMIN"
    assert admin.activo is True
    assert not hasattr(admin, "password_hash")
    assert servicio.cantidad() == 1

    with pytest.raises(ValueError, match="configuración inicial"):
        servicio.crear_administrador_inicial(
            username="otroadmin",
            nombre="Segundo administrador inicial",
            password="otra-frase-larga-y-segura-2026",
        )

    eventos = db.consultar(
        """
        SELECT usuario, operacion, datos_nuevos
        FROM auditoria
        WHERE entidad = 'USUARIO_APP'
        """
    )
    assert any(evento["operacion"] == "USUARIO_ADMIN_INICIAL_CREADO" for evento in eventos)
    assert all("una-frase-larga-y-segura-2026" not in str(evento) for evento in eventos)


def test_login_es_case_insensitive_y_el_rol_sale_de_la_cuenta(db):
    servicio = ServicioUsuariosLocales(db)
    admin = _crear_admin(servicio)

    login = servicio.autenticar(
        username="  ADMIN ",
        password="una-frase-larga-y-segura-2026",
    )

    assert login is not None
    assert login.id == admin.id
    assert login.rol == "ADMIN"
    assert login.ultimo_acceso_en is not None
    fila = db.consultar_uno(
        "SELECT password_hash FROM usuarios_app WHERE id = ?",
        (admin.id,),
    )
    assert "una-frase-larga-y-segura-2026" not in fila["password_hash"]


def test_intentos_fallidos_bloquean_temporalmente_la_cuenta(db):
    servicio = ServicioUsuariosLocales(db)
    _crear_admin(servicio)

    for _ in range(5):
        assert servicio.autenticar(
            username="admin",
            password="esta-no-es-la-contrasena",
        ) is None

    fila = db.consultar_uno(
        """
        SELECT intentos_login_fallidos, bloqueado_hasta
        FROM usuarios_app WHERE username = 'admin'
        """
    )
    assert fila["intentos_login_fallidos"] == 5
    assert fila["bloqueado_hasta"] is not None
    assert servicio.autenticar(
        username="admin",
        password="una-frase-larga-y-segura-2026",
    ) is None


def test_solo_admin_puede_crear_cuentas_y_el_usuario_operador_no_administra(db):
    servicio = ServicioUsuariosLocales(db)
    admin = _crear_admin(servicio)
    operador = servicio.crear_usuario(
        actor_id=admin.id,
        username="operador1",
        nombre="Operador Uno",
        rol="OPERADOR",
        password="otra-frase-larga-y-segura-2026",
    )

    assert operador.rol == "OPERADOR"
    assert servicio.autenticar(
        username="operador1",
        password="otra-frase-larga-y-segura-2026",
    ).rol == "OPERADOR"
    with pytest.raises(PermissionError, match="ADMIN activa"):
        servicio.crear_usuario(
            actor_id=operador.id,
            username="tercerusuario",
            nombre="Tercero",
            rol="LECTURA",
            password="una-tercera-frase-larga-2026",
        )


def test_username_duplicado_y_roles_invalidos_se_rechazan(db):
    servicio = ServicioUsuariosLocales(db)
    admin = _crear_admin(servicio)

    with pytest.raises(ValueError, match="Ya existe"):
        servicio.crear_usuario(
            actor_id=admin.id,
            username="ADMIN",
            nombre="Duplicado",
            rol="LECTURA",
            password="otra-frase-larga-y-segura-2026",
        )
    with pytest.raises(ValueError, match="Rol inválido"):
        servicio.crear_usuario(
            actor_id=admin.id,
            username="usuariotest",
            nombre="Usuario de prueba",
            rol="SUPERUSER",
            password="otra-frase-larga-y-segura-2026",
        )
    with pytest.raises(ValueError, match="al menos 12"):
        servicio.crear_usuario(
            actor_id=admin.id,
            username="usuariotest",
            nombre="Usuario de prueba",
            rol="LECTURA",
            password="corta",
        )


def test_no_se_puede_desactivar_o_degradar_al_ultimo_admin(db):
    servicio = ServicioUsuariosLocales(db)
    admin = _crear_admin(servicio)

    with pytest.raises(ValueError, match="tu propia cuenta"):
        servicio.actualizar_usuario(
            actor_id=admin.id,
            usuario_id=admin.id,
            nombre=admin.nombre,
            rol="ADMIN",
            activo=False,
        )
    with pytest.raises(ValueError, match="al menos un administrador activo"):
        servicio.actualizar_usuario(
            actor_id=admin.id,
            usuario_id=admin.id,
            nombre=admin.nombre,
            rol="LECTURA",
            activo=True,
        )


def test_admin_puede_restablecer_password_y_la_auditoria_no_guarda_la_clave(db):
    servicio = ServicioUsuariosLocales(db)
    admin = _crear_admin(servicio)
    operador = servicio.crear_usuario(
        actor_id=admin.id,
        username="operador1",
        nombre="Operador Uno",
        rol="OPERADOR",
        password="otra-frase-larga-y-segura-2026",
    )
    revision_anterior = operador.revision_sesion
    assert sesion_local_vigente(operador, revision_anterior)

    servicio.restablecer_password(
        actor_id=admin.id,
        usuario_id=operador.id,
        password_nueva="password-temporal-muy-segura-2026",
    )

    operador_actualizado = servicio.obtener(operador.id)
    assert operador_actualizado is not None
    assert operador_actualizado.revision_sesion == revision_anterior + 1
    assert not sesion_local_vigente(operador_actualizado, revision_anterior)
    assert sesion_local_vigente(
        operador_actualizado,
        operador_actualizado.revision_sesion,
    )

    assert servicio.autenticar(
        username="operador1",
        password="otra-frase-larga-y-segura-2026",
    ) is None
    assert servicio.autenticar(
        username="operador1",
        password="password-temporal-muy-segura-2026",
    ) is not None
    eventos = db.consultar(
        "SELECT operacion, datos_nuevos FROM auditoria WHERE entidad = 'USUARIO_APP'"
    )
    assert any(
        evento["operacion"] == "PASSWORD_LOCAL_REESTABLECIDA_POR_ADMIN"
        for evento in eventos
    )
    assert all(
        "password-temporal-muy-segura-2026" not in str(evento)
        for evento in eventos
    )


def test_cambiar_rol_revoca_sesion_pero_editar_nombre_no(db):
    servicio = ServicioUsuariosLocales(db)
    admin = _crear_admin(servicio)
    operador = servicio.crear_usuario(
        actor_id=admin.id,
        username="operador1",
        nombre="Operador Uno",
        rol="OPERADOR",
        password="otra-frase-larga-y-segura-2026",
    )
    revision_original = operador.revision_sesion

    renombrado = servicio.actualizar_usuario(
        actor_id=admin.id,
        usuario_id=operador.id,
        nombre="Operador Actualizado",
        rol="OPERADOR",
        activo=True,
    )
    assert renombrado.revision_sesion == revision_original

    actualizado = servicio.actualizar_usuario(
        actor_id=admin.id,
        usuario_id=operador.id,
        nombre=renombrado.nombre,
        rol="LECTURA",
        activo=True,
    )
    assert actualizado.revision_sesion == revision_original + 1
    assert not sesion_local_vigente(actualizado, revision_original)

    desactivado = servicio.actualizar_usuario(
        actor_id=admin.id,
        usuario_id=operador.id,
        nombre=actualizado.nombre,
        rol="LECTURA",
        activo=False,
    )
    assert desactivado.revision_sesion == revision_original + 2
    assert desactivado.activo is False


def test_revision_de_sesion_faltante_o_invalida_falla_cerrado(db):
    servicio = ServicioUsuariosLocales(db)
    admin = _crear_admin(servicio)

    assert sesion_local_vigente(admin, admin.revision_sesion)
    assert not sesion_local_vigente(admin, None)
    assert not sesion_local_vigente(admin, admin.revision_sesion - 1)
    assert not sesion_local_vigente(admin, True)


def test_recuperacion_offline_solo_permite_admin_activo(db):
    servicio = ServicioUsuariosLocales(db)
    admin = _crear_admin(servicio)
    operador = servicio.crear_usuario(
        actor_id=admin.id,
        username="operador1",
        nombre="Operador Uno",
        rol="OPERADOR",
        password="otra-frase-larga-y-segura-2026",
    )

    with pytest.raises(ValueError, match="solo está habilitada"):
        servicio.restablecer_password_por_acceso_local(
            username="operador1",
            password_nueva="password-temporal-muy-segura-2026",
        )

    servicio.restablecer_password_por_acceso_local(
        username="admin",
        password_nueva="password-admin-recuperada-2026",
    )
    assert servicio.autenticar(
        username="admin",
        password="password-admin-recuperada-2026",
    ) is not None
