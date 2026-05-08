"""
data_loader.py — Data Discovery, XLSX Landmark Parsing, and CAESAR .lnd Parsing

This module handles all file I/O and data discovery for the Body Scan Viewer.
It scans the fixed data directories on startup to build a catalog of available
subjects, parses the SizeStream XLSX landmark file, and reads CAESAR .lnd files.

Key components:
    - SubjectEntry / DataCatalog: dataclasses describing discovered data
    - scan_data_folders(): auto-discover all subjects at startup
    - load_ss_landmarks(): parse XLSX 3D landmarks (three-row-group format)
    - parse_lnd(): parse CAESAR .lnd anatomical landmark files
    - diagnose_coordinate_systems(): detect height-axis differences between datasets
    - build_axis_swap_matrix(): construct a proper rotation (det=+1) to align axes
"""

import pathlib
import re
import itertools
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from config_loader import APP_CONFIG

# ==============================================================================
# Fixed path constants (no user input needed)
# ==============================================================================
PROJECT_ROOT  = pathlib.Path(__file__).resolve().parent
DATA_ROOT     = APP_CONFIG.paths.data_root
SS_DIR        = APP_CONFIG.paths.size_stream_dir
CAESAR_DIR    = APP_CONFIG.paths.caesar_dir
PROCESSED_DIR = APP_CONFIG.paths.processed_dir


# ==============================================================================
# Data structures
# ==============================================================================

@dataclass
class SubjectEntry:
    """
    Represents one subject discovered during folder scanning.
    Tracks which files (SS OBJ, CAESAR PLY, CAESAR LND, XLSX landmarks)
    are available for this subject.
    """
    subject_id:      str
    ss_obj_path:     Optional[pathlib.Path] = None
    caesar_ply_path: Optional[pathlib.Path] = None
    caesar_lnd_path: Optional[pathlib.Path] = None
    has_landmarks:   bool = False

    @property
    def is_complete(self) -> bool:
        """True if both SizeStream OBJ and CAESAR PLY are available."""
        return self.ss_obj_path is not None and self.caesar_ply_path is not None

    @property
    def status_label(self) -> str:
        """Human-readable label for the subject combo dropdown."""
        lm = "+LM" if self.has_landmarks else "   "
        if self.is_complete:
            return f"{self.subject_id}  [SS+CAESAR {lm}]"
        elif self.ss_obj_path:
            return f"{self.subject_id}  [SS only  !!]"
        else:
            return f"{self.subject_id}  [CAESAR only !!]"


@dataclass
class DataCatalog:
    """
    Result of scan_data_folders(). Contains all discovered subjects,
    the XLSX path, any scan warnings/errors, and parsed landmark data.
    """
    subjects:    dict  = field(default_factory=dict)   # {subject_id: SubjectEntry}
    xlsx_path:   Optional[pathlib.Path] = None
    scan_errors: list  = field(default_factory=list)   # user-friendly error strings
    lm_data:     Optional[dict] = None                 # output of load_ss_landmarks()

    @property
    def all_ids(self) -> list:
        """Return subject IDs sorted: complete pairs first, then partial."""
        complete = sorted(k for k, v in self.subjects.items() if v.is_complete)
        partial  = sorted(k for k, v in self.subjects.items() if not v.is_complete)
        return complete + partial


# ==============================================================================
# Folder scanning
# ==============================================================================

def scan_data_folders() -> DataCatalog:
    """
    Scan the fixed data directories and build a DataCatalog.
    Never raises exceptions — all errors are collected in catalog.scan_errors.

    Scans:
        1. SIZE_STREAM/ for SS_OUT_*.obj files
        2. SIZE_STREAM/ for *.xlsx landmark files
        3. CAESAR/ for csr*.ply and matching .lnd files
        4. Parses the XLSX to mark which subjects have landmark data
        5. Detects subject ID mismatches (e.g. csr2019a vs csr2119a)
    """
    catalog = DataCatalog()

    # --- 1. Scan SIZE_STREAM for OBJ files ---
    if not SS_DIR.is_dir():
        catalog.scan_errors.append(
            f"[ERR] SIZE_STREAM folder not found: {SS_DIR}\n"
            "  -> Please verify 'TODO/SORO MADE Garments/SIZE_STREAM/' exists"
        )
    else:
        for obj_path in sorted(SS_DIR.glob("SS_OUT_*.obj")):
            m = re.search(r'SS_OUT_(csr\d+[a-z])', obj_path.name)
            if m:
                sid = m.group(1)
                if sid not in catalog.subjects:
                    catalog.subjects[sid] = SubjectEntry(subject_id=sid)
                catalog.subjects[sid].ss_obj_path = obj_path

        # Find XLSX (allow flexible filename)
        xlsx_list = sorted(SS_DIR.glob("*.xlsx"))
        if xlsx_list:
            catalog.xlsx_path = xlsx_list[0]
            if len(xlsx_list) > 1:
                catalog.scan_errors.append(
                    f"[!!] Multiple .xlsx found, using: {xlsx_list[0].name}"
                )
        else:
            catalog.scan_errors.append(
                "[!!] No .xlsx found in SIZE_STREAM/\n"
                "  -> Please verify 'Extracted SS Measurements and LMs.xlsx' is present"
            )

    # --- 2. Scan CAESAR for PLY + LND files ---
    if not CAESAR_DIR.is_dir():
        catalog.scan_errors.append(
            f"[ERR] CAESAR folder not found: {CAESAR_DIR}"
        )
    else:
        for ply_path in sorted(CAESAR_DIR.glob("csr*.ply")):
            sid = ply_path.stem
            if sid not in catalog.subjects:
                catalog.subjects[sid] = SubjectEntry(subject_id=sid)
            catalog.subjects[sid].caesar_ply_path = ply_path

            lnd = ply_path.with_suffix('.lnd')
            if lnd.exists():
                catalog.subjects[sid].caesar_lnd_path = lnd
            else:
                catalog.scan_errors.append(
                    f"[!!] {sid}: no .lnd file found, CAESAR landmarks unavailable"
                )

    # --- 3. Parse XLSX landmarks, mark subjects that have landmark data ---
    if catalog.xlsx_path:
        try:
            catalog.lm_data = load_ss_landmarks(str(catalog.xlsx_path))
            for sid in catalog.lm_data.get('subject_ids', []):
                if sid in catalog.subjects:
                    catalog.subjects[sid].has_landmarks = True
        except Exception as e:
            catalog.scan_errors.append(
                f"[ERR] XLSX parse failed: {e}\n"
                "  -> Make sure the file is not open in Excel, and is .xlsx (not .xls)"
            )

    # --- 4. Detect subject ID mismatches ---
    ss_ids      = {sid for sid, e in catalog.subjects.items() if e.ss_obj_path}
    caesar_ids  = {sid for sid, e in catalog.subjects.items() if e.caesar_ply_path}
    ss_only     = sorted(ss_ids - caesar_ids)
    caesar_only = sorted(caesar_ids - ss_ids)
    if ss_only or caesar_only:
        catalog.scan_errors.append(
            f"[!!] Subject ID mismatch:\n"
            f"  SS only: {ss_only}\n  CAESAR only: {caesar_only}\n"
            f"  -> Possibly a naming difference (e.g. csr2019a vs csr2119a)"
        )

    # NOTE: processed/ directory is NOT created here — deferred to save time
    return catalog


# ==============================================================================
# XLSX landmark parsing
# ==============================================================================

def load_ss_landmarks(xlsx_path: str) -> dict:
    """
    Parse SizeStream XLSX to extract scalar measurements and 3D landmarks.

    The XLSX "Sheet1" has this layout:
        Row 0 (header): [label, NaN, SS_OUT_csr0052a..., SS_OUT_csr0283a..., ...]
        Col B:           landmark/measurement name (or NaN for continuation rows)
        Cols C-F:        numeric values per subject

    Scalar measurements occupy a single row each.
    3D landmarks occupy three consecutive rows (name, NaN, NaN) = (X, Y, Z).

    Returns:
        {
          'subject_ids':         ['csr0052a', ...],
          'col_indices':         [2, 3, 4, 5],
          'scalar_measurements': {name: np.array(n_subjects)},
          'landmarks_3d':        {name: np.array(n_subjects, 3)},
        }
    """
    try:
        import pandas as pd
        df = pd.read_excel(xlsx_path, sheet_name='Sheet1', header=None, engine='openpyxl')
    except (ModuleNotFoundError, ImportError):
        return _load_ss_landmarks_from_txt_export(xlsx_path)

    # --- Step 1: Dynamically discover subject columns (not hardcoded) ---
    header_row  = df.iloc[0]
    subject_ids = []
    col_indices = []
    for col_idx in range(df.shape[1]):
        cell = header_row.iloc[col_idx]
        if isinstance(cell, str) and 'SS_OUT_' in cell:
            m = re.search(r'SS_OUT_(csr\d+[a-z])', cell)
            if m:
                subject_ids.append(m.group(1))
                col_indices.append(col_idx)

    if not subject_ids:
        raise ValueError(
            "No 'SS_OUT_csr...' columns found in XLSX header row.\n"
            "  -> Verify sheet name is 'Sheet1' and row 1 contains OBJ filenames"
        )

    # --- Step 2: Parse data rows ---
    rows   = df.iloc[1:].reset_index(drop=True)
    n_rows = len(rows)
    scalar_measurements = {}
    landmarks_3d        = {}
    i = 0

    while i < n_rows:
        name_cell = rows.iloc[i, 1]  # Column B = landmark/measurement name

        # Skip blank / NaN rows
        if pd.isna(name_cell) or str(name_cell).strip() == '':
            i += 1
            continue

        name = str(name_cell).strip()

        # Check if this is a three-row-group (3D landmark: name, NaN, NaN)
        has_y = (i + 1 < n_rows) and pd.isna(rows.iloc[i + 1, 1])
        has_z = (i + 2 < n_rows) and pd.isna(rows.iloc[i + 2, 1])
        next_named = (i + 3 >= n_rows) or (
            pd.notna(rows.iloc[i + 3, 1]) and
            str(rows.iloc[i + 3, 1]).strip() != ''
        )

        if has_y and has_z and next_named:
            # --- 3D landmark (three-row group) ---
            try:
                x = rows.iloc[i,     col_indices].to_numpy(dtype=float)
                y = rows.iloc[i + 1, col_indices].to_numpy(dtype=float)
                z = rows.iloc[i + 2, col_indices].to_numpy(dtype=float)
                landmarks_3d[name] = np.stack([x, y, z], axis=1)  # shape (n_subjects, 3)
            except (ValueError, TypeError) as e:
                print(f"  [skip] Landmark '{name}' coord parse failed: {e}")
            i += 3
        else:
            # --- Scalar measurement (single row) ---
            try:
                scalar_measurements[name] = rows.iloc[i, col_indices].to_numpy(dtype=float)
            except (ValueError, TypeError):
                pass
            i += 1

    return {
        'subject_ids':         subject_ids,
        'col_indices':         col_indices,
        'scalar_measurements': scalar_measurements,
        'landmarks_3d':        landmarks_3d,
    }


def _load_ss_landmarks_from_txt_export(xlsx_path: str) -> dict:
    """Fallback parser for the tab-delimited Spreadsheet.TXT export."""
    xlsx = pathlib.Path(xlsx_path)
    candidates = [
        xlsx.with_name("Spreadsheet.TXT"),
        xlsx.parent / "Spreadsheet.TXT",
        xlsx.parent.parent / "Spreadsheet.TXT",
        PROJECT_ROOT / "TODO" / "SORO MADE Garments" / "Spreadsheet.TXT",
    ]
    txt_path = next((p for p in candidates if p.exists()), None)
    if txt_path is None:
        raise ModuleNotFoundError(
            "pandas/openpyxl are unavailable and Spreadsheet.TXT was not found"
        )

    lines = txt_path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 3:
        raise ValueError(f"Spreadsheet.TXT is too short: {txt_path}")

    headers = lines[1].split("\t")
    data_rows = []
    subject_ids = []
    for line in lines[2:]:
        cols = line.split("\t")
        if not cols:
            continue
        match = re.search(r"SS_OUT_(csr\d+[a-z])", cols[0])
        if match:
            subject_ids.append(match.group(1))
            data_rows.append(cols)

    if not subject_ids:
        raise ValueError(f"No SS_OUT_csr rows found in {txt_path}")

    scalar_measurements = {}
    landmarks_3d = {}
    i = 1
    while i < len(headers):
        name = headers[i].strip()
        if not name:
            i += 1
            continue

        is_landmark = (
            i + 2 < len(headers)
            and headers[i + 1].strip() == ""
            and headers[i + 2].strip() == ""
        )
        if is_landmark:
            coords = []
            valid = True
            for row in data_rows:
                try:
                    coords.append([
                        float(row[i]),
                        float(row[i + 1]),
                        float(row[i + 2]),
                    ])
                except (IndexError, ValueError):
                    valid = False
                    break
            if valid:
                landmarks_3d[name] = np.asarray(coords, dtype=float)
            i += 3
        else:
            values = []
            valid = True
            for row in data_rows:
                try:
                    values.append(float(row[i]))
                except (IndexError, ValueError):
                    valid = False
                    break
            if valid:
                scalar_measurements[name] = np.asarray(values, dtype=float)
            i += 1

    return {
        'subject_ids':         subject_ids,
        'col_indices':         list(range(len(subject_ids))),
        'scalar_measurements': scalar_measurements,
        'landmarks_3d':        landmarks_3d,
    }


# ==============================================================================
# CAESAR .lnd file parsing
# ==============================================================================

def parse_lnd(lnd_path: str, mesh_vertices=None) -> dict:
    """
    Parse a CAESAR .lnd landmark file.

    File format (space-separated):
        idx  quality  vertex_idx  X  Y  Z  value  NAME [NAME_CONTINUED...]

    Header lines (SUBJECT_ID, SCAN_TYPE, etc.) have fewer than 8 fields and
    are automatically skipped by the len(parts) < 8 guard.

    Multi-word names like "Rt. Infraorbitale" are preserved via ' '.join(parts[7:]).

    Encoding fallback: latin-1 -> utf-8 -> utf-8-sig (CAESAR-era files often
    use latin-1).

    Returns:
        {landmark_name: np.array([X, Y, Z])}  — typically 73 landmarks
    """
    lines = None
    for encoding in ('latin-1', 'utf-8', 'utf-8-sig'):
        try:
            with open(lnd_path, 'r', encoding=encoding) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue

    if lines is None:
        raise IOError(f"Cannot read .lnd file with any encoding: {lnd_path}")

    landmarks = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) < 8:
            # Header lines (SUBJECT_ID, SCAN_TYPE, STD_LAND, etc.) all have <8 fields
            continue
        try:
            vertex_idx = int(parts[2])
            x, y, z = float(parts[3]), float(parts[4]), float(parts[5])
            name = ' '.join(parts[7:])  # Preserve multi-word names
            coords = np.array([x, y, z], dtype=float)
            if mesh_vertices is not None and 0 <= vertex_idx < len(mesh_vertices):
                coords = np.asarray(mesh_vertices[vertex_idx], dtype=float)
            landmarks[name] = coords
        except (ValueError, IndexError):
            continue

    return landmarks


def _axis_aligned_rotation_candidates() -> list:
    """
    Enumerate all proper axis-aligned 3D rotations (det=+1).

    These cover all 24 right-handed rotations obtainable by axis permutation
    plus sign flips. Common named rotations are labeled for readability; the
    rest fall back to a compact perm/sign description.
    """
    common_labels = {
        tuple(np.eye(3, dtype=int).reshape(-1)): "identity",
        tuple(np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=int).reshape(-1)): "Rx(+90 deg)",
        tuple(np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=int).reshape(-1)): "Rx(-90 deg)",
        tuple(np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], dtype=int).reshape(-1)): "Ry(+90 deg)",
        tuple(np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0]], dtype=int).reshape(-1)): "Ry(-90 deg)",
        tuple(np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], dtype=int).reshape(-1)): "Rz(+90 deg)",
        tuple(np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1]], dtype=int).reshape(-1)): "Rz(-90 deg)",
        tuple(np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]], dtype=int).reshape(-1)): "Rx(180 deg)",
        tuple(np.array([[-1, 0, 0], [0, 1, 0], [0, 0, -1]], dtype=int).reshape(-1)): "Ry(180 deg)",
        tuple(np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]], dtype=int).reshape(-1)): "Rz(180 deg)",
    }

    candidates = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((-1, 1), repeat=3):
            matrix = np.zeros((3, 3), dtype=float)
            for row_idx, src_axis in enumerate(perm):
                matrix[row_idx, src_axis] = signs[row_idx]
            if round(np.linalg.det(matrix)) != 1:
                continue

            matrix_i = matrix.astype(int)
            label = common_labels.get(
                tuple(matrix_i.reshape(-1)),
                f"perm={perm},signs={signs}",
            )
            candidates.append((label, matrix))

    return candidates


def align_caesar_landmarks_to_mesh(raw_landmarks: dict, mesh_vertices) -> tuple:
    """
    Align raw CAESAR .lnd XYZ landmarks into the current PLY mesh frame.

    The CAESAR .lnd raw XYZ values appear to be in a mesh-sized metric scale
    already, but often in a different orientation than the high-resolution PLY.
    To avoid assuming a single hard-coded rotation, we try all 24 proper
    axis-aligned rotations, centroid-align each candidate to the mesh, refine
    with a rigid point-to-point ICP, and keep the lowest post-fit landmark-to-
    mesh nearest-neighbor error.

    This function intentionally does NOT project landmarks onto the mesh
    surface. The returned points preserve the residual fit error so the viewer
    can display the true offset.

    Returns:
        (
            {name: np.array([x, y, z])},
            {
                'rotation_label': str,
                'rotation_matrix': np.ndarray (3, 3),
                'icp_transform': np.ndarray (4, 4),
                'mean_mesh_error_mm': float,
                'median_mesh_error_mm': float,
                'max_mesh_error_mm': float,
                'fitness': float,
                'rmse': float,
            }
        )
    """
    if not raw_landmarks:
        return {}, None

    try:
        import open3d as o3d
    except ImportError:
        return dict(raw_landmarks), {
            'rotation_label': 'identity',
            'rotation_matrix': np.eye(3),
            'icp_transform': np.eye(4),
            'mean_mesh_error_mm': float('nan'),
            'median_mesh_error_mm': float('nan'),
            'max_mesh_error_mm': float('nan'),
            'fitness': 0.0,
            'rmse': float('nan'),
            'warning': 'open3d unavailable; using raw .lnd XYZ without mesh alignment',
        }

    from scipy.spatial import cKDTree

    registration = o3d.pipelines.registration
    names = list(raw_landmarks.keys())
    raw_points = np.array([raw_landmarks[name] for name in names], dtype=float)
    mesh_vertices = np.asarray(mesh_vertices, dtype=float)

    if raw_points.size == 0 or mesh_vertices.size == 0:
        return dict(raw_landmarks), {
            'rotation_label': 'identity',
            'rotation_matrix': np.eye(3),
            'icp_transform': np.eye(4),
            'mean_mesh_error_mm': float('nan'),
            'median_mesh_error_mm': float('nan'),
            'max_mesh_error_mm': float('nan'),
            'fitness': 0.0,
            'rmse': float('nan'),
        }

    mesh_center = mesh_vertices.mean(axis=0)
    tree = cKDTree(mesh_vertices)

    target_pcd = o3d.geometry.PointCloud()
    target_pcd.points = o3d.utility.Vector3dVector(mesh_vertices)

    best = None
    ones = np.ones((len(raw_points), 1), dtype=float)

    for rotation_label, rotation_matrix in _axis_aligned_rotation_candidates():
        rotated = raw_points @ rotation_matrix.T
        candidate_points = rotated - rotated.mean(axis=0) + mesh_center

        source_pcd = o3d.geometry.PointCloud()
        source_pcd.points = o3d.utility.Vector3dVector(candidate_points)

        reg = registration.registration_icp(
            source_pcd,
            target_pcd,
            400.0,
            np.eye(4),
            registration.TransformationEstimationPointToPoint(),
            registration.ICPConvergenceCriteria(max_iteration=80),
        )

        aligned_points = (np.hstack([candidate_points, ones]) @ reg.transformation.T)[:, :3]
        distances, _ = tree.query(aligned_points)
        result = {
            'rotation_label': rotation_label,
            'rotation_matrix': np.array(rotation_matrix, dtype=float, copy=True),
            'icp_transform': np.array(reg.transformation, dtype=float, copy=True),
            'mean_mesh_error_mm': float(np.mean(distances)),
            'median_mesh_error_mm': float(np.median(distances)),
            'max_mesh_error_mm': float(np.max(distances)),
            'fitness': float(reg.fitness),
            'rmse': float(reg.inlier_rmse),
            'aligned_points': aligned_points,
        }

        rank_key = (
            result['mean_mesh_error_mm'],
            result['max_mesh_error_mm'],
            result['rmse'],
        )
        if best is None or rank_key < best['rank_key']:
            result['rank_key'] = rank_key
            best = result

    aligned = {
        name: best['aligned_points'][idx]
        for idx, name in enumerate(names)
    }

    info = {
        'rotation_label': best['rotation_label'],
        'rotation_matrix': best['rotation_matrix'],
        'icp_transform': best['icp_transform'],
        'mean_mesh_error_mm': best['mean_mesh_error_mm'],
        'median_mesh_error_mm': best['median_mesh_error_mm'],
        'max_mesh_error_mm': best['max_mesh_error_mm'],
        'fitness': best['fitness'],
        'rmse': best['rmse'],
    }
    return aligned, info


# ==============================================================================
# Coordinate system diagnosis
# ==============================================================================

def diagnose_coordinate_systems(mesh_ss, mesh_caesar, caesar_lnd: dict) -> dict:
    """
    Detect the height (up) axis for both SizeStream and CAESAR meshes.

    SizeStream uses Y-up (Y=0 at feet, ~1700 at head).
    CAESAR up-axis is inferred from the mesh vertex ranges themselves.

    The axis with the largest vertex range is assumed to be the height axis.
    If a Sellion landmark is available, we attempt a soft cross-check only.
    Some CAESAR landmark files use a different unit/axis convention than the
    mesh, so this validation must never override the mesh-based diagnosis.

    Args:
        mesh_ss:     trimesh.Trimesh of SizeStream body
        mesh_caesar: trimesh.Trimesh of CAESAR body
        caesar_lnd:  dict from parse_lnd()

    Returns:
        {
          'ss_up_axis':      int (0=X, 1=Y, 2=Z),
          'caesar_up_axis':  int,
          'needs_axis_swap': bool,
        }
    """
    ss_range = mesh_ss.vertices.max(axis=0) - mesh_ss.vertices.min(axis=0)
    c_range  = mesh_caesar.vertices.max(axis=0) - mesh_caesar.vertices.min(axis=0)

    ss_up = int(np.argmax(ss_range))
    c_up  = int(np.argmax(c_range))

    # Soft cross-check only: .lnd files may not share the mesh's unit/axis convention
    sellion_key = next((k for k in caesar_lnd if k.upper() == 'SELLION'), None)
    if sellion_key:
        sellion = caesar_lnd[sellion_key]
        plausible = []
        for axis in range(3):
            foot_approx = float(mesh_caesar.vertices[:, axis].min())
            height_est = float(sellion[axis]) - foot_approx
            if 1500.0 <= height_est <= 1900.0:
                plausible.append(f"{'XYZ'[axis]}={height_est:.0f}mm")
        if plausible:
            print(f"  [diag] CAESAR landmark cross-check: {', '.join(plausible)}")
        else:
            print(
                "  [diag] Skipping Sellion height cross-check: "
                ".lnd and mesh may use different unit/axis conventions"
            )

    result = {
        'ss_up_axis':      ss_up,
        'caesar_up_axis':  c_up,
        'needs_axis_swap': ss_up != c_up,
    }
    print(f"[diag] SizeStream: {'XYZ'[ss_up]}-up  |  CAESAR: {'XYZ'[c_up]}-up")
    if result['needs_axis_swap']:
        print(f"  -> Axis alignment needed (auto-handled during registration)")
    return result


def build_axis_swap_matrix(from_axis: int, to_axis: int) -> np.ndarray:
    """
    Build a 4x4 rotation matrix that maps `from_axis` onto `to_axis`.

    Uses proper 90-degree rotations (NOT axis permutations), so det(R)=+1
    (preserves right-handedness). All 6 combinations verified.

    Common case for the current datasets: CAESAR Z-up (2) -> SizeStream Y-up (1)
    => Rx(-90 degrees)

    Args:
        from_axis: source axis index (0=X, 1=Y, 2=Z)
        to_axis:   target axis index (0=X, 1=Y, 2=Z)

    Returns:
        4x4 numpy rotation matrix (identity if from_axis == to_axis)
    """
    R = np.eye(4)
    rotation_map = {
        (0, 1): [[ 0, -1,  0], [ 1,  0,  0], [ 0,  0,  1]],  # X->Y: Rz(+90)
        (1, 0): [[ 0,  1,  0], [-1,  0,  0], [ 0,  0,  1]],  # Y->X: Rz(-90)
        (0, 2): [[ 0,  0, -1], [ 0,  1,  0], [ 1,  0,  0]],  # X->Z: Ry(+90)
        (2, 0): [[ 0,  0,  1], [ 0,  1,  0], [-1,  0,  0]],  # Z->X: Ry(-90)
        (1, 2): [[ 1,  0,  0], [ 0,  0, -1], [ 0,  1,  0]],  # Y->Z: Rx(+90)
        (2, 1): [[ 1,  0,  0], [ 0,  0,  1], [ 0, -1,  0]],  # Z->Y: Rx(-90)
    }
    if (from_axis, to_axis) in rotation_map:
        R[:3, :3] = np.array(rotation_map[(from_axis, to_axis)])
    # If from_axis == to_axis, return identity (no rotation needed)
    return R
