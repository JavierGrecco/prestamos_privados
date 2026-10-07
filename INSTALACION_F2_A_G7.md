# Instalación acumulativa Motor de Pagos V3 — desde F2 hasta G7

## Punto de partida

F2 ya está instalado en el proyecto y validado por el usuario con **230/230** tests.

## Qué instala este bundle

F3.1 + G1 + G2 + G3 + G4/G5 + G6 + G7.

G4/G5 incluye distribución a inversores, corrección del horizonte del waterfall,
RAI/RNI, historial de recálculo y el campo de compatibilidad `interes_extra_generado`.

G6 agrega migración gradual LEGACY/SOMBRA/V3.

G7 agrega el read model auditable y la proyección One Shot.

## Instalación

```bash
unzip -o ~/Downloads/MOTOR_PAGOS_V3_F2_A_G7_BUNDLE.zip \
  -d ~/Desktop/prestamos_privados_limpio
cd ~/Desktop/prestamos_privados_limpio

python -m compileall -q aplicacion dominio infraestructura tests
python -m pytest -q
```

### Objetivo de tests

Si se parte exactamente de F2 (230 tests) y no hay modificaciones incompatibles:

`230 + 13 + 20 + 5 + 6 + 25 + 7 + 12 + 1 = 319`

La última prueba adicional es la compatibilidad de `interes_extra_generado`.

## Importante

Este bundle todavía NO reemplaza `aplicacion/servicios/pagos.py` ni conecta Streamlit al nuevo registrador.
La migración productiva queda deliberadamente después de la caracterización LEGACY/V3.

No incluye `__pycache__`, `.pyc` ni `README.txt` de paquetes anteriores.
