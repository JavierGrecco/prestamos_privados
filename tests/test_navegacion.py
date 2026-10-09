"""Contrato del catálogo de navegación y sus permisos por cuenta."""

from aplicacion.seguridad.capacidades import (
    CAP_ADMINISTRAR_SISTEMA,
    CAP_CONFIGURAR_MOTOR_V3,
    CAP_OPERAR,
    CAP_VER_MOTOR_V3,
    PoliticaCapacidades,
)
from aplicacion.seguridad.identidad import IdentidadSesion
from ui.navegacion import (
    CATALOGO_PAGINAS,
    PAGINAS,
    PAGINAS_POR_CLAVE,
    capacidad_requerida_para_pagina,
    paginas_permitidas_para,
    requiere_persona_para_pagina,
)


def _identidad(rol: str) -> IdentidadSesion:
    return IdentidadSesion(
        subject=f"test:{rol.lower()}",
        nombre=f"Usuario {rol}",
        proveedor="TEST",
        autenticada=True,
        roles=frozenset({rol}),
    )


def test_catalogo_tiene_claves_unicas_y_todas_las_rutas_tienen_metadatos():
    claves = [pagina.clave for pagina in CATALOGO_PAGINAS]

    assert len(claves) == len(set(claves))
    assert set(claves) == set(PAGINAS_POR_CLAVE)
    assert set(PAGINAS).issubset(set(PAGINAS_POR_CLAVE))
    assert "detalle_financiero" not in PAGINAS
    assert PAGINAS_POR_CLAVE["detalle_financiero"].navegable is False
    assert PAGINAS_POR_CLAVE["detalle_financiero"].pagina_padre == "prestamos"


def test_lectura_ve_analisis_permitido_pero_no_operacion_ni_administracion():
    permitidas = set(paginas_permitidas_para(_identidad("LECTURA")))

    assert {"resumen", "mi_espacio", "planificar", "reportes"} <= permitidas
    assert not {
        "personas",
        "prestamos",
        "pagos",
        "auditoria",
        "usuarios",
        "operacion",
        "motor_v3",
        "detalle_financiero",
    } & permitidas


def test_operador_puede_operar_pero_no_configurar_superficies_criticas():
    politica = PoliticaCapacidades()
    operador = _identidad("OPERADOR")
    permitidas = set(paginas_permitidas_para(operador, politica))

    assert {"personas", "prestamos", "pagos", "auditoria"} <= permitidas
    assert not {"usuarios", "operacion", "motor_v3"} & permitidas
    assert politica.puede(operador, CAP_OPERAR)
    assert not politica.puede(operador, CAP_ADMINISTRAR_SISTEMA)
    assert not politica.puede(operador, CAP_CONFIGURAR_MOTOR_V3)


def test_admin_ve_todas_las_pantallas_raiz_y_contexto_separado():
    admin = _identidad("ADMIN")
    politica = PoliticaCapacidades()
    permitidas = set(paginas_permitidas_para(admin, politica))

    assert permitidas == set(PAGINAS)
    assert politica.puede(admin, CAP_ADMINISTRAR_SISTEMA)
    assert politica.puede(admin, CAP_CONFIGURAR_MOTOR_V3)
    assert capacidad_requerida_para_pagina("detalle_financiero") == CAP_OPERAR
    assert requiere_persona_para_pagina("detalle_financiero")
    assert not requiere_persona_para_pagina("mi_espacio")


def test_consulta_de_motor_no_expone_el_selector_de_cambio(monkeypatch):
    from aplicacion.servicios.puente_motor_pago_v3 import ModoMotorPagoV3
    from ui.pagina_motor_v3 import renderizar_selector_modo

    mensajes = []

    class ServicioMotorFalso:
        def modo_actual(self):
            return ModoMotorPagoV3.SOMBRA

    monkeypatch.setattr(
        "ui.pagina_motor_v3.componentes.nota_contextual",
        lambda mensaje, tipo="info": mensajes.append((mensaje, tipo)),
    )

    modo = renderizar_selector_modo(
        ServicioMotorFalso(),
        permitir_cambio=False,
    )

    assert modo is ModoMotorPagoV3.SOMBRA
    assert mensajes
    assert "no cambiar el modo" in mensajes[0][0]
