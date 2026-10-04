"""
Script de precarga de datos de ejemplo.

Ejecutar:
    cd /Users/javygrecco/Desktop/prestamos_privados
    source venv/bin/activate
    python scripts/seed_datos.py

Crea:
  - Una persona "Javier" (el usuario que ve la app).
  - Dos familiares como inversores.
  - Un préstamo del auto de $20M a 36 meses con 3 inversores
    (Javier es el deudor).
  - Un préstamo donde Javier es inversor.

Es idempotente: si ya existen datos, no los duplica.
"""
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

# Asegurar que la raíz del proyecto esté en el path
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from infraestructura.db import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo
from aplicacion.servicios import ServicioPrestamos


def main() -> None:
    """Crea los datos de ejemplo si no existen."""
    ruta = RAIZ / "datos" / "prestamos.db"
    print(f"Usando base: {ruta}")

    with BaseDatos(ruta) as db:
        # Aplicar migraciones
        aplicar_migraciones(db)

        personas_repo = PersonaRepo(db)

        # Verificar si ya hay datos
        existentes = personas_repo.listar()
        if existentes:
            print(f"Ya hay {len(existentes)} personas en la base.")
            print("No se cargan datos de ejemplo (idempotente).")
            return

        print("Cargando datos de ejemplo...")

        # 1. Crear personas
        javier_id = personas_repo.crear(
            nombre="Javier",
            apellido="Grecco",
            documento="30123456",
            email="javier@ejemplo.com",
        )
        personas_repo.agregar_rol(javier_id, "DEUDOR")
        personas_repo.agregar_rol(javier_id, "INVERSOR")

        maria_id = personas_repo.crear(
            nombre="María",
            apellido="González",
            documento="31234567",
        )
        personas_repo.agregar_rol(maria_id, "INVERSOR")

        pedro_id = personas_repo.crear(
            nombre="Pedro",
            apellido="López",
            documento="32345678",
        )
        personas_repo.agregar_rol(pedro_id, "INVERSOR")

        ana_id = personas_repo.crear(
            nombre="Ana",
            apellido="Martínez",
            documento="33456789",
        )
        personas_repo.agregar_rol(ana_id, "INVERSOR")

        print(f"  ✓ 4 personas creadas")

        # 2. Crear el préstamo del auto (Javier es deudor)
        servicio = ServicioPrestamos(db)
        prestamo_auto_id = servicio.crear_completo(
            deudor_id=javier_id,
            capital=Decimal("20000000"),
            plazo_meses=36,
            tasa_anual=Decimal("0.30"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date(2026, 1, 1),
            inversores=[
                {"persona_id": maria_id, "monto": Decimal("10000000")},
                {"persona_id": pedro_id, "monto": Decimal("6000000")},
                {"persona_id": ana_id, "monto": Decimal("4000000")},
            ],
            usuario="seed",
            tc_inicial=Decimal("1500"),
            destino="Cambio de auto",
        )
        print(f"  ✓ Préstamo del auto creado (ID {prestamo_auto_id})")

        # 3. Crear un segundo préstamo donde Javier es inversor
        #    (un familiar le presta a un tercero)
        deudor_externo_id = personas_repo.crear(
            nombre="Luis",
            apellido="Fernández",
            documento="34567890",
        )
        personas_repo.agregar_rol(deudor_externo_id, "DEUDOR")

        prestamo_inversion_id = servicio.crear_completo(
            deudor_id=deudor_externo_id,
            capital=Decimal("5000000"),
            plazo_meses=24,
            tasa_anual=Decimal("0.28"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date(2026, 1, 1),
            inversores=[
                {"persona_id": javier_id, "monto": Decimal("3000000")},
                {"persona_id": maria_id, "monto": Decimal("2000000")},
            ],
            usuario="seed",
            tc_inicial=Decimal("1500"),
            destino="Viaje",
        )
        print(f"  ✓ Préstamo de inversión creado (ID {prestamo_inversion_id})")

        print("\n¡Listo! Datos cargados correctamente.")
        print("\nPara ver la app:")
        print("  streamlit run ui/app.py")


if __name__ == "__main__":
    main()