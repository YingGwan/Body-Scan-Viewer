"""
test_registration.py — Tests for Registration Pipeline Components

Tests:
    - Axis swap matrix properties (det, axis mapping, roundtrip)
    - ICP registration function signature and basic behavior
    - Transform chain composition correctness

Run:
    cd 4-codeForSimeon
    python -m pytest tests/test_registration.py -v

Note:
    Full ICP integration tests require loading actual mesh data (~5 seconds).
    These are marked with @pytest.mark.slow and can be skipped with:
        python -m pytest tests/ -v -m "not slow"
"""

import sys
import os
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import build_axis_swap_matrix
from registration import classify_registration_quality


class TestAxisSwapMatrix:
    """Verify rotation matrix correctness for all 6 axis swap combinations."""

    @pytest.mark.parametrize("from_ax,to_ax", [
        (0, 1), (1, 0), (0, 2), (2, 0), (1, 2), (2, 1),
    ])
    def test_determinant_is_positive_one(self, from_ax, to_ax):
        """All rotation matrices must have det(R)=+1 (proper rotation)."""
        R = build_axis_swap_matrix(from_ax, to_ax)
        det = np.linalg.det(R[:3, :3])
        assert abs(det - 1.0) < 1e-10, f"det={det}"

    @pytest.mark.parametrize("from_ax,to_ax", [
        (0, 1), (1, 0), (0, 2), (2, 0), (1, 2), (2, 1),
    ])
    def test_axis_maps_correctly(self, from_ax, to_ax):
        """The from_axis unit vector should map to the to_axis unit vector."""
        R = build_axis_swap_matrix(from_ax, to_ax)
        src = np.zeros(3)
        src[from_ax] = 1.0
        result = R[:3, :3] @ src
        expected = np.zeros(3)
        expected[to_ax] = 1.0
        np.testing.assert_array_almost_equal(result, expected)

    @pytest.mark.parametrize("from_ax,to_ax", [
        (0, 1), (1, 0), (0, 2), (2, 0), (1, 2), (2, 1),
    ])
    def test_orthogonality(self, from_ax, to_ax):
        """R^T @ R should be identity (orthogonal matrix)."""
        R = build_axis_swap_matrix(from_ax, to_ax)
        R3 = R[:3, :3]
        np.testing.assert_array_almost_equal(R3.T @ R3, np.eye(3))

    def test_identity_for_same_axis(self):
        """Mapping axis to itself should return identity."""
        for ax in range(3):
            R = build_axis_swap_matrix(ax, ax)
            np.testing.assert_array_almost_equal(R, np.eye(4))

    def test_roundtrip_all_pairs(self):
        """Swap A->B then B->A should give identity."""
        for a in range(3):
            for b in range(3):
                if a == b:
                    continue
                R1 = build_axis_swap_matrix(a, b)
                R2 = build_axis_swap_matrix(b, a)
                combined = R2 @ R1
                np.testing.assert_array_almost_equal(
                    combined, np.eye(4), decimal=10,
                    err_msg=f"Roundtrip {a}->{b}->{a} failed"
                )


class TestTransformChain:
    """Test that transform chain composition is mathematically correct."""

    def test_chain_order(self):
        """T_total = T_icp @ T_centroid @ T_swap should apply in correct order."""
        # Create mock transforms
        T_swap = build_axis_swap_matrix(0, 1)  # X->Y rotation

        T_centroid = np.eye(4)
        T_centroid[:3, 3] = [100, 200, 300]   # translation

        T_icp = np.eye(4)
        T_icp[:3, 3] = [1, 2, 3]              # small ICP correction

        T_total = T_icp @ T_centroid @ T_swap

        # Apply to a test point
        pt = np.array([10, 20, 30, 1])  # homogeneous

        # Step-by-step application
        pt_step1 = T_swap @ pt
        pt_step2 = T_centroid @ pt_step1
        pt_step3 = T_icp @ pt_step2

        # Direct application of T_total
        pt_direct = T_total @ pt

        np.testing.assert_array_almost_equal(pt_step3, pt_direct)


class TestRegistrationQuality:
    """Regression tests for registration quality labeling."""

    def test_low_fitness_is_not_excellent(self):
        """No-correspondence results must not be labeled excellent."""
        assert classify_registration_quality(0.0, 0.0).startswith("Failed")

    def test_good_fit_can_still_be_excellent(self):
        """High-fitness low-rmse registrations remain excellent."""
        assert classify_registration_quality(4.9, 0.95) == "Excellent (<5mm)"

    def test_mid_rmse_with_good_fitness_is_acceptable(self):
        """Nominal registrations keep the existing acceptable band."""
        assert classify_registration_quality(10.0, 0.8) == "Acceptable (5-15mm)"


@pytest.mark.slow
class TestICPIntegration:
    """
    Full ICP integration test using actual mesh data.
    Marked slow because it loads PLY files and runs ICP (~5 seconds).
    """

    def test_registration_runs(self):
        """Smoke test: registration should complete without errors."""
        import trimesh
        from data_loader import scan_data_folders, parse_lnd, diagnose_coordinate_systems

        catalog = scan_data_folders()
        if 'csr0052a' not in catalog.subjects:
            pytest.skip("csr0052a not found")
        entry = catalog.subjects['csr0052a']
        if not entry.is_complete:
            pytest.skip("csr0052a is not complete")

        mesh_ss  = trimesh.load(str(entry.ss_obj_path), force='mesh')
        mesh_cae = trimesh.load(str(entry.caesar_ply_path), force='mesh', process=False)

        caesar_lnd = {}
        if entry.caesar_lnd_path:
            caesar_lnd = parse_lnd(str(entry.caesar_lnd_path))

        diag = diagnose_coordinate_systems(mesh_ss, mesh_cae, caesar_lnd)

        from registration import run_icp_registration
        mesh_reg, T_total, rmse, fitness, quality = run_icp_registration(
            mesh_ss, mesh_cae, diag, build_axis_swap_matrix
        )

        # Basic sanity checks
        assert mesh_reg is not None
        assert T_total.shape == (4, 4)
        assert rmse >= 0
        assert 0 <= fitness <= 1
        assert isinstance(quality, str)
        # RMSE should be reasonable (not inf or NaN)
        assert np.isfinite(rmse), f"RMSE is {rmse}"
        # Transform should be a proper matrix (det > 0)
        assert np.linalg.det(T_total[:3, :3]) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'not slow'])
