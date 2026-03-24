"""
registration.py — ICP Rigid Registration Pipeline (CAESAR -> SizeStream)

Performs coarse-to-fine ICP registration with automatic axis alignment.

Pipeline:
    1. Detect and correct axis orientation (e.g. CAESAR Z-up -> SizeStream Y-up)
    2. Centroid alignment (translate CAESAR centroid to SizeStream centroid)
    3. Coarse ICP (150mm search radius, Point-to-Plane, 50 iterations)
    4. Fine ICP (25mm search radius, Point-to-Plane, 100 iterations)
    5. Quality assessment (Excellent <5mm / Acceptable <15mm / Needs review)

Key function:
    - run_icp_registration(): full pipeline, returns (registered_mesh, T_total, rmse, fitness, quality)
"""

import numpy as np
from config_loader import APP_CONFIG


def _trimesh_to_o3d_pcd(mesh, n_sample=None, random_seed=None):
    """
    Convert a trimesh.Trimesh to an Open3D PointCloud, with random downsampling.

    Random downsampling to n_sample points keeps ICP fast (~1-2 seconds).
    A fixed seed ensures reproducible results across runs.

    Args:
        mesh:     trimesh.Trimesh
        n_sample: max points to keep (default 30000)

    Returns:
        o3d.geometry.PointCloud
    """
    import open3d as o3d

    pts = np.asarray(mesh.vertices)
    sampling_cfg = APP_CONFIG.registration.sampling
    if n_sample is None:
        n_sample = sampling_cfg.max_points
    if random_seed is None:
        random_seed = sampling_cfg.random_seed

    if len(pts) > n_sample:
        rng = np.random.RandomState(random_seed)
        idx = rng.choice(len(pts), n_sample, replace=False)
        pts = pts[idx]
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pts)
    return pcd


def classify_registration_quality(rmse: float, fitness: float) -> str:
    """
    Classify ICP quality using both correspondence coverage and residual error.

    A near-zero RMSE is meaningless when fitness is also near zero, because that
    usually indicates ICP failed to establish useful correspondences.
    """
    quality_cfg = APP_CONFIG.registration.quality
    if fitness < quality_cfg.fitness_fail_below:
        return f"Failed (fitness <{quality_cfg.fitness_fail_below:.1f})"
    if rmse < quality_cfg.excellent_rmse_below_mm:
        return f"Excellent (<{quality_cfg.excellent_rmse_below_mm:.0f}mm)"
    if rmse < quality_cfg.acceptable_rmse_below_mm:
        return (
            "Acceptable "
            f"({quality_cfg.excellent_rmse_below_mm:.0f}-{quality_cfg.acceptable_rmse_below_mm:.0f}mm)"
        )
    return f"Needs review (>{quality_cfg.acceptable_rmse_below_mm:.0f}mm)"


def run_icp_registration(mesh_ss, mesh_caesar, coord_diag, build_axis_swap_matrix_fn):
    """
    Full ICP registration pipeline: axis swap -> centroid -> coarse ICP -> fine ICP.

    Args:
        mesh_ss:                    trimesh.Trimesh, SizeStream reference mesh
        mesh_caesar:                trimesh.Trimesh, CAESAR mesh to be registered
        coord_diag:                 dict from diagnose_coordinate_systems(), or None
        build_axis_swap_matrix_fn:  callable(from_axis, to_axis) -> 4x4 matrix

    Returns:
        (mesh_registered, T_total, rmse, fitness, quality_str)
            mesh_registered: trimesh.Trimesh, CAESAR after registration
            T_total:         4x4 numpy array, complete transform chain
            rmse:            float, ICP inlier RMSE in mm
            fitness:         float, ICP fitness (fraction of inlier correspondences)
            quality_str:     str, human-readable quality rating
    """
    import open3d as o3d
    from open3d.pipelines.registration import (
        registration_icp,
        TransformationEstimationPointToPlane,
        ICPConvergenceCriteria,
    )

    mesh_cae = mesh_caesar.copy()  # Never modify the original

    # === Step 1: Axis rotation alignment ===
    T_swap = np.eye(4)
    if coord_diag and coord_diag['needs_axis_swap']:
        T_swap = build_axis_swap_matrix_fn(
            coord_diag['caesar_up_axis'], coord_diag['ss_up_axis']
        )
        mesh_cae.apply_transform(T_swap)
        print(f"  [reg] Applied axis rotation: "
              f"{'XYZ'[coord_diag['caesar_up_axis']]}-up -> "
              f"{'XYZ'[coord_diag['ss_up_axis']]}-up")

    # === Step 2: Centroid translation alignment ===
    t_init     = mesh_ss.centroid - mesh_cae.centroid
    T_centroid = np.eye(4)
    T_centroid[:3, 3] = t_init
    mesh_cae.apply_translation(t_init)
    print(f"  [reg] Centroid shift: [{t_init[0]:.1f}, {t_init[1]:.1f}, {t_init[2]:.1f}] mm")

    # === Step 3: Convert to Open3D point clouds ===
    pcd_ss  = _trimesh_to_o3d_pcd(mesh_ss)
    pcd_cae = _trimesh_to_o3d_pcd(mesh_cae)

    # Point-to-Plane ICP requires normals on the TARGET
    normals_cfg = APP_CONFIG.registration.target_normals
    pcd_ss.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(
            radius=normals_cfg.radius_mm,
            max_nn=normals_cfg.max_nn,
        )
    )

    # === Step 4: Coarse ICP (large search radius, fast convergence) ===
    coarse_cfg = APP_CONFIG.registration.coarse_icp
    print(f"  [reg] Running coarse ICP ({coarse_cfg.max_correspondence_distance_mm:.0f}mm)...")
    reg_coarse = registration_icp(
        source=pcd_cae,
        target=pcd_ss,
        max_correspondence_distance=coarse_cfg.max_correspondence_distance_mm,
        estimation_method=TransformationEstimationPointToPlane(),
        criteria=ICPConvergenceCriteria(
            max_iteration=coarse_cfg.max_iteration,
            relative_fitness=coarse_cfg.relative_fitness,
            relative_rmse=coarse_cfg.relative_rmse,
        ),
    )
    print(f"  [reg] Coarse ICP RMSE: {reg_coarse.inlier_rmse:.2f} mm, "
          f"fitness: {reg_coarse.fitness:.3f}")

    # === Step 5: Fine ICP (small radius, precision) ===
    fine_cfg = APP_CONFIG.registration.fine_icp
    print(f"  [reg] Running fine ICP ({fine_cfg.max_correspondence_distance_mm:.0f}mm)...")
    reg_fine = registration_icp(
        source=pcd_cae,
        target=pcd_ss,
        max_correspondence_distance=fine_cfg.max_correspondence_distance_mm,
        init=reg_coarse.transformation,
        estimation_method=TransformationEstimationPointToPlane(),
        criteria=ICPConvergenceCriteria(
            max_iteration=fine_cfg.max_iteration,
            relative_fitness=fine_cfg.relative_fitness,
            relative_rmse=fine_cfg.relative_rmse,
        ),
    )

    # === Step 6: Apply ICP result to full-resolution CAESAR mesh ===
    # mesh_cae already has T_swap + T_centroid applied; now add ICP delta
    mesh_registered = mesh_cae.copy()
    mesh_registered.apply_transform(reg_fine.transformation)

    # Complete transform chain: from raw CAESAR -> registered space
    T_total = reg_fine.transformation @ T_centroid @ T_swap

    # === Step 7: Quality assessment ===
    rmse    = float(reg_fine.inlier_rmse)
    fitness = float(reg_fine.fitness)
    quality = classify_registration_quality(rmse, fitness)

    print(f"  [reg] Final RMSE: {rmse:.2f} mm | Fitness: {fitness:.3f} | {quality}")

    return mesh_registered, T_total, rmse, fitness, quality
