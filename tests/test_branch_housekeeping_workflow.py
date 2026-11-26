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



def test_limpieza_solo_retiro_un_commit_vacio_cuyo_padre_esta_en_main():
    """Un único commit sin cambios se elimina solo si su padre ya está en main."""
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'comparison.data.status === "diverged"' in workflow
    assert "comparison.data.behind_by === 1" in workflow
    assert "headCommit.data.parents.length === 1" in workflow
    assert "headCommit.data.tree.sha === parentCommit.data.tree.sha" in workflow
    assert "basehead: `${parentSha}...${mainSha}`" in workflow
    assert "parentComparison.data.behind_by === 0" in workflow
    assert "single empty commit; parent is already contained in main" in workflow
    assert "Could not verify empty-commit ancestry" in workflow


def test_manifest_archive_preserva_los_catorce_head_historicos_sin_mezclarlos():
    """El inventario fija SHA exactos y una única referencia de archivo."""
    import json
    import re

    manifest_path = ROOT / "docs" / "ARCHIVO_RAMAS_HISTORICAS_2026-11.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["format_version"] == 1
    assert manifest["archive_branch"] == "archive/legacy-branches-2026-11"
    assert manifest["archive_commit"] == "0f22a23d4e2dceed7b1a9020d79bc8d75925f378"
    assert manifest["archive_tree_sha"] == "0ff8027f4f23b0670cb2ef76c868a093e0081ef8"
    assert manifest["base_main_commit"] == "1192e5d3dca1515ecd0b1baf5ba8284d2e9d4908"
    assert manifest["expected_archived_parent_count"] == 15
    assert len(manifest["branches"]) == 14
    names = [entry["name"] for entry in manifest["branches"]]
    shas = [entry["sha"] for entry in manifest["branches"]]
    assert len(names) == len(set(names)) == 14
    assert len(shas) == len(set(shas)) == 14
    assert "main" not in names
    assert manifest["archive_branch"] not in names
    assert all(re.fullmatch(r"[0-9a-f]{40}", sha) for sha in shas)
    assert all(entry.get("category") and entry.get("reason") for entry in manifest["branches"])


def test_housekeeping_solo_borra_head_historicos_preservados_en_el_anclaje():
    """La limpieza exige manifiesto fijado, SHA actual y ancestro probado."""
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'path: "docs/ARCHIVO_RAMAS_HISTORICAS_2026-11.json"' in workflow
    assert 'manifest.archive_branch === "archive/legacy-branches-2026-11"' in workflow
    assert 'manifest.archive_commit === "0f22a23d4e2dceed7b1a9020d79bc8d75925f378"' in workflow
    assert "manifest.branches.length === 14" in workflow
    assert "archiveCommit.data.parents.length === manifest.expected_archived_parent_count" in workflow
    assert "expectedParents.every(sha => parentShas.has(sha))" in workflow
    assert "liveBranch.data.commit.sha !== archived.sha" in workflow
    assert "liveBranch.data.protected" in workflow
    assert "openHeads.has(currentBranch.name)" in workflow
    assert 'basehead: `${archived.sha}...${manifest.archive_commit}`' in workflow
    assert "archivedComparison.data.behind_by === 0" in workflow
    assert 'await deleteBranchIfPresent(archived.name)' in workflow
    assert "Historical branch archive cleanup skipped" in workflow


def test_limpieza_ancestral_preserva_la_referencia_de_archivo():
    """El anclaje no se borra por ser ancestro del main después de integrar."""
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'branch === "archive/legacy-branches-2026-11"' in workflow
    assert workflow.count('branch.name === "archive/legacy-branches-2026-11"') == 2
    assert 'currentBranch.name === manifest.archive_branch' in workflow
