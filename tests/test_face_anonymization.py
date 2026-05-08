import pathlib

import numpy as np
import trimesh

from face_anonymization import (
    anonymize_face_open3d,
    boundary_edge_counts,
    connected_component_face_counts,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]
SUBJECT_OBJ = (
    ROOT
    / "TODO"
    / "SORO MADE Garments"
    / "SIZE_STREAM"
    / "SS_OUT_csr0052a-F-CFW-NkAll.obj"
)
SPREADSHEET_TXT = ROOT / "TODO" / "SORO MADE Garments" / "Spreadsheet.TXT"


def _load_subject_landmarks(subject_obj_name):
    lines = SPREADSHEET_TXT.read_text(encoding="utf-8").splitlines()
    headers = lines[1].split("\t")
    row = None
    for candidate in lines[2:]:
        cols = candidate.split("\t")
        if cols and cols[0] == subject_obj_name:
            row = cols
            break
    assert row is not None, f"Missing spreadsheet row for {subject_obj_name}"

    landmarks = {}
    for name in ("Chin", "Head Circum Front", "Head Circum Right"):
        idx = headers.index(name)
        landmarks[name] = np.array(
            [float(row[idx]), float(row[idx + 1]), float(row[idx + 2])],
            dtype=float,
        )
    return landmarks


def test_open3d_face_anonymization_preserves_topology_on_real_scan():
    mesh = trimesh.load(str(SUBJECT_OBJ), force="mesh")
    landmarks = _load_subject_landmarks(SUBJECT_OBJ.name)

    before_boundaries = boundary_edge_counts(mesh.faces)
    before_components = connected_component_face_counts(mesh.faces)

    result = anonymize_face_open3d(mesh, landmarks, target_ratio=0.05)
    anonymized = result.mesh

    assert len(anonymized.vertices) == len(mesh.vertices)
    assert len(anonymized.faces) == len(mesh.faces)
    assert boundary_edge_counts(anonymized.faces) == before_boundaries
    assert connected_component_face_counts(anonymized.faces) == before_components

    assert result.selected_face_count > 500
    assert result.proxy_face_count < result.selected_face_count

    displacement = np.linalg.norm(anonymized.vertices - mesh.vertices, axis=1)
    assert displacement[result.selected_vertices].max() > 1.0
    assert np.count_nonzero(displacement > 1e-6) < len(mesh.vertices)
