"""Guardas para evitar borrados inseguros en branch housekeeping."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "branch-housekeeping.yml"


def test_limpieza_solo_selecciona_ramas_contenidas_en_main():
    """La comparación branch...main debe probar que branch no tiene commits únicos."""
    workflow = WORKFLOW.read_text(encoding="utf-8")

    # La comparación usa branch como BASE y main como HEAD.
    # behind_by cuenta commits de BASE que no están en HEAD: debe ser cero.
    condicion_segura = (
        'comparison.data.behind_by === 0 && '
        '["ahead", "identical"].includes(comparison.data.status)'
    )

    assert workflow.count(condicion_segura) == 2
    assert "comparison.data.ahead_by === 0" not in workflow
    assert "basehead: `${branch.commit.sha}...${mainSha}`" in workflow
    assert "basehead: `${branch.commit.sha}...main`" in workflow


def test_limpieza_confirma_si_una_rama_desaparecio_durante_el_borrado():
    """Una eliminación concurrente no debe convertir el mantenimiento en un falso fallo."""
    workflow = WORKFLOW.read_text(encoding="utf-8")

    # Hay tres contextos independientes: cierre de PR, push a main y ejecución manual.
    assert workflow.count("async function deleteBranchIfPresent(branchName)") == 3
    assert workflow.count("await github.rest.git.getRef({") == 3
    assert workflow.count('if (lookupError.status === 404) return "absent";') == 3

def test_limpieza_usa_runtime_node_24_sin_la_version_deprecada():
    """La automatización usa la versión actual de GitHub Script."""
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert workflow.count("actions/github-script@v9") == 3
    assert "actions/github-script@v7" not in workflow
