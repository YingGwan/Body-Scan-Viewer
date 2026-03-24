"""
test_data_loader.py — Unit Tests for Data Loading and Parsing

Tests:
    - scan_data_folders(): folder discovery correctness
    - load_ss_landmarks(): XLSX parsing (199 3D landmarks, 263 scalar measurements)
    - parse_lnd(): CAESAR .lnd parsing (73 landmarks, multi-word names)
    - diagnose_coordinate_systems(): axis detection
    - build_axis_swap_matrix(): rotation matrix properties (det=+1, axis mapping)

Run:
    cd 4-codeForSimeon
    python -m pytest tests/test_data_loader.py -v
"""

import sys
import os
import numpy as np
import pytest

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import (
    scan_data_folders, load_ss_landmarks, parse_lnd,
    align_caesar_landmarks_to_mesh,
    diagnose_coordinate_systems, build_axis_swap_matrix,
    SS_DIR, CAESAR_DIR, DATA_ROOT,
)


# ==============================================================================
# Folder scanning
# ==============================================================================

class TestScanDataFolders:
    """Test that scan_data_folders() correctly discovers all data files."""

    def test_catalog_has_subjects(self):
        """At least some subjects should be discovered."""
        catalog = scan_data_folders()
        assert len(catalog.subjects) > 0, "No subjects found in data folders"

    def test_complete_pairs(self):
        """There should be exactly 3 complete (SS+CAESAR) pairs."""
        catalog = scan_data_folders()
        complete = [s for s in catalog.subjects.values() if s.is_complete]
        assert len(complete) == 3, f"Expected 3 complete pairs, got {len(complete)}"

    def test_known_subjects(self):
        """The 3 known matching subjects should be present and complete."""
        catalog = scan_data_folders()
        for sid in ['csr0052a', 'csr0283a', 'csr1921a']:
            assert sid in catalog.subjects, f"{sid} not found"
            assert catalog.subjects[sid].is_complete, f"{sid} is not complete"

    def test_id_mismatch_detected(self):
        """The csr2019a/csr2119a mismatch should be in scan_errors."""
        catalog = scan_data_folders()
        mismatch_warnings = [e for e in catalog.scan_errors if 'mismatch' in e.lower() or '2019' in e or '2119' in e]
        assert len(mismatch_warnings) > 0, "ID mismatch warning not generated"

    def test_xlsx_found(self):
        """XLSX file should be discovered."""
        catalog = scan_data_folders()
        assert catalog.xlsx_path is not None, "XLSX not found"
        assert catalog.xlsx_path.suffix == '.xlsx'

    def test_no_exceptions(self):
        """scan_data_folders should never throw (errors go to scan_errors)."""
        catalog = scan_data_folders()  # Should not raise
        # If data dirs are missing, errors should be in scan_errors, not exceptions
        assert isinstance(catalog.scan_errors, list)

    def test_lnd_paths_for_complete_subjects(self):
        """Complete subjects should have .lnd paths."""
        catalog = scan_data_folders()
        for sid in ['csr0052a', 'csr0283a', 'csr1921a']:
            entry = catalog.subjects[sid]
            assert entry.caesar_lnd_path is not None, f"{sid} missing .lnd path"
            assert entry.caesar_lnd_path.suffix == '.lnd'


# ==============================================================================
# XLSX landmark parsing
# ==============================================================================

class TestLoadSSLandmarks:
    """Test XLSX parsing of SizeStream landmarks and measurements."""

    @pytest.fixture
    def lm_data(self):
        """Load XLSX data (cached per test class)."""
        catalog = scan_data_folders()
        if catalog.xlsx_path is None:
            pytest.skip("XLSX file not found")
        return load_ss_landmarks(str(catalog.xlsx_path))

    def test_subject_ids(self, lm_data):
        """Should discover 4 subjects from XLSX header."""
        assert len(lm_data['subject_ids']) == 4
        assert 'csr0052a' in lm_data['subject_ids']

    def test_landmarks_3d_count(self, lm_data):
        """Should have ~199 3D landmarks."""
        n_lm = len(lm_data['landmarks_3d'])
        assert n_lm >= 190, f"Expected ~199 landmarks, got {n_lm}"
        assert n_lm <= 210, f"Too many landmarks: {n_lm}"

    def test_landmark_shape(self, lm_data):
        """Each landmark should be shape (4, 3) — 4 subjects, 3 coordinates."""
        for name, coords in lm_data['landmarks_3d'].items():
            assert coords.shape == (4, 3), f"Landmark '{name}' has shape {coords.shape}"
            break  # Just test the first one

    def test_scalar_measurements_exist(self, lm_data):
        """Should have scalar measurements (non-landmark rows)."""
        assert len(lm_data['scalar_measurements']) > 100, \
            f"Expected >100 scalar measurements, got {len(lm_data['scalar_measurements'])}"

    def test_abdomen_back_exists(self, lm_data):
        """AbdomenBack should be in 3D landmarks (known body landmark)."""
        assert 'AbdomenBack' in lm_data['landmarks_3d']

    def test_coordinates_reasonable(self, lm_data):
        """Landmark coordinates should be in reasonable body-size range (mm)."""
        for name, coords in lm_data['landmarks_3d'].items():
            # Y values should be 0-2000mm (height), X/Z within +-500mm
            assert np.all(np.abs(coords) < 3000), \
                f"Landmark '{name}' has unreasonable coords: {coords}"

    def test_dynamic_column_discovery(self, lm_data):
        """col_indices should be populated (dynamic discovery working)."""
        assert len(lm_data['col_indices']) == 4


# ==============================================================================
# CAESAR .lnd parsing
# ==============================================================================

class TestParseLnd:
    """Test CAESAR .lnd file parsing."""

    @pytest.fixture
    def lnd_path(self):
        """Path to a .lnd file."""
        path = CAESAR_DIR / "csr0052a.lnd"
        if not path.exists():
            pytest.skip("csr0052a.lnd not found")
        return str(path)

    def test_landmark_count(self, lnd_path):
        """Should parse 73 landmarks from .lnd file."""
        lms = parse_lnd(lnd_path)
        assert len(lms) == 73, f"Expected 73 landmarks, got {len(lms)}"

    def test_sellion_exists(self, lnd_path):
        """Sellion (nose bridge) should be present."""
        lms = parse_lnd(lnd_path)
        assert 'Sellion' in lms, f"Sellion not found. Keys: {list(lms.keys())[:5]}"

    def test_multi_word_names(self, lnd_path):
        """Multi-word names like 'Rt. Infraorbitale' should be preserved."""
        lms = parse_lnd(lnd_path)
        multi_word = [k for k in lms if ' ' in k]
        assert len(multi_word) > 0, "No multi-word landmark names found"
        # "Rt." alone should NOT be a key (that would mean truncation)
        assert 'Rt.' not in lms, "Truncated name 'Rt.' found — multi-word parsing broken"

    def test_coordinates_are_float_arrays(self, lnd_path):
        """Each landmark value should be a 3-element float array."""
        lms = parse_lnd(lnd_path)
        for name, coords in lms.items():
            assert coords.shape == (3,), f"{name} has shape {coords.shape}"
            assert coords.dtype == np.float64
            break

    def test_sellion_reasonable_height(self, lnd_path):
        """Sellion X~464mm (CAESAR X=height axis), should be >300."""
        lms = parse_lnd(lnd_path)
        sellion = lms['Sellion']
        # X is the height axis for CAESAR; Sellion (nose) should be high
        assert sellion[0] > 300, f"Sellion X={sellion[0]}, expected >300 (height axis)"

    def test_vertex_indices_can_resolve_mesh_space(self):
        """When mesh vertices are provided, parse_lnd should use vertex_idx."""
        lnd_path = os.path.join(os.path.dirname(__file__), "_tmp_sample_parse_lnd.lnd")
        with open(lnd_path, "w", encoding="latin-1") as f:
            f.write("1 0 2 999 999 999 0 Sellion\n")
        mesh_vertices = np.array([
            [10.0, 20.0, 30.0],
            [40.0, 50.0, 60.0],
            [70.0, 80.0, 90.0],
        ])

        try:
            lms = parse_lnd(str(lnd_path), mesh_vertices=mesh_vertices)
            np.testing.assert_allclose(lms["Sellion"], mesh_vertices[2])
        finally:
            if os.path.exists(lnd_path):
                os.remove(lnd_path)

    def test_align_caesar_landmarks_to_mesh_recovers_best_rotation(self, monkeypatch):
        """Raw .lnd XYZ should be alignable via rigid rotation without unit scaling."""
        import sys
        import types

        class FakePointCloud:
            def __init__(self, points=None):
                self.points = np.asarray(points if points is not None else [], dtype=float)

        class FakeRegistrationResult:
            def __init__(self):
                self.transformation = np.eye(4)
                self.fitness = 1.0
                self.inlier_rmse = 0.0

        fake_o3d = types.ModuleType("open3d")
        fake_o3d.geometry = types.SimpleNamespace(PointCloud=FakePointCloud)
        fake_o3d.utility = types.SimpleNamespace(
            Vector3dVector=lambda pts: np.asarray(pts, dtype=float)
        )
        fake_o3d.pipelines = types.SimpleNamespace(
            registration=types.SimpleNamespace(
                registration_icp=lambda *args, **kwargs: FakeRegistrationResult(),
                TransformationEstimationPointToPoint=lambda: object(),
                ICPConvergenceCriteria=lambda **kwargs: object(),
            )
        )
        monkeypatch.setitem(sys.modules, "open3d", fake_o3d)

        raw_landmarks = {
            "A": np.array([100.0, 0.0, 0.0]),
            "B": np.array([150.0, 40.0, 10.0]),
            "C": np.array([220.0, -30.0, 60.0]),
            "D": np.array([310.0, 70.0, -20.0]),
        }
        # Best proper rotation from the orientation study: Ry(+90 deg) => new=[z, y, -x]
        expected_R = np.array([
            [0.0, 0.0, 1.0],
            [0.0, 1.0, 0.0],
            [-1.0, 0.0, 0.0],
        ])
        expected_points = np.array(list(raw_landmarks.values())) @ expected_R.T
        mesh_vertices = expected_points.copy()

        aligned, info = align_caesar_landmarks_to_mesh(raw_landmarks, mesh_vertices)

        assert info["rotation_label"] == "Ry(+90 deg)"
        np.testing.assert_allclose(info["rotation_matrix"], expected_R)
        np.testing.assert_allclose(
            np.array(list(aligned.values())),
            expected_points,
            atol=1e-8,
        )
        assert info["mean_mesh_error_mm"] < 1e-8


# ==============================================================================
# Coordinate system diagnosis
# ==============================================================================

class TestCoordinateDiagnosis:
    """Test axis detection and rotation matrix correctness."""

    def test_build_axis_swap_identity(self):
        """Same axis should return identity matrix."""
        R = build_axis_swap_matrix(1, 1)
        np.testing.assert_array_almost_equal(R, np.eye(4))

    def test_build_axis_swap_det_positive(self):
        """All rotation matrices should have det=+1 (proper rotation)."""
        for from_ax in range(3):
            for to_ax in range(3):
                R = build_axis_swap_matrix(from_ax, to_ax)
                det = np.linalg.det(R[:3, :3])
                assert abs(det - 1.0) < 1e-10, \
                    f"({from_ax}->{to_ax}): det={det}, expected 1.0"

    def test_x_to_y_maps_correctly(self):
        """X-up to Y-up: X axis [1,0,0] should map to Y axis [0,1,0]."""
        R = build_axis_swap_matrix(0, 1)
        x_axis = np.array([1, 0, 0])
        result = R[:3, :3] @ x_axis
        np.testing.assert_array_almost_equal(result, [0, 1, 0])

    def test_y_to_x_maps_correctly(self):
        """Y-up to X-up: Y axis [0,1,0] should map to X axis [1,0,0]."""
        R = build_axis_swap_matrix(1, 0)
        y_axis = np.array([0, 1, 0])
        result = R[:3, :3] @ y_axis
        np.testing.assert_array_almost_equal(result, [1, 0, 0])

    def test_roundtrip(self):
        """Swap X->Y then Y->X should give identity."""
        R1 = build_axis_swap_matrix(0, 1)
        R2 = build_axis_swap_matrix(1, 0)
        combined = R2 @ R1
        np.testing.assert_array_almost_equal(combined, np.eye(4), decimal=10)


# ==============================================================================
# Integration test: full scan + parse
# ==============================================================================

class TestIntegration:
    """End-to-end test: scan folders, parse XLSX, parse LND, check consistency."""

    def test_full_pipeline(self):
        """Run the full data discovery pipeline and check key invariants."""
        catalog = scan_data_folders()

        # At least 3 complete subjects
        complete_ids = [s.subject_id for s in catalog.subjects.values() if s.is_complete]
        assert len(complete_ids) >= 3

        # XLSX parsed successfully with landmark data
        assert catalog.lm_data is not None
        assert len(catalog.lm_data['landmarks_3d']) > 0

        # Complete subjects should have landmarks
        for sid in complete_ids:
            assert catalog.subjects[sid].has_landmarks, \
                f"{sid} is complete but has_landmarks=False"

        # Status labels should be non-empty strings
        for entry in catalog.subjects.values():
            label = entry.status_label
            assert isinstance(label, str) and len(label) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
