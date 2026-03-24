"""
main.py — Entry Point for the Body Scan Viewer

A Polyscope-based interactive tool for comparing SizeStream and CAESAR body scans.

Features:
    A. Import:      Load SizeStream OBJ + XLSX landmarks, CAESAR PLY + LND landmarks
    B. Registration: ICP rigid registration (CAESAR -> SizeStream coordinate space)
    C. Distance:    Landmark error heatmap and statistics
    D. Geodesic:    Measure geodesic (surface) distance between any two landmarks

Data location:
    The application expects data in the following structure relative to this file:
        TODO/SORO MADE Garments/
            CAESAR/         -> csr*.ply + csr*.lnd files
            SIZE_STREAM/    -> SS_OUT_*.obj + *.xlsx landmark file

    Output (registered meshes) is saved to:
        processed/          -> {subject}_registered.ply + {subject}_transform.npy

Important note:
    SizeStream geometry/landmarks are consumed in millimeters, while CAESAR PLY
    meshes may be authored in meters. During runtime the CAESAR mesh is
    normalized to millimeters for registration and distance computation, but
    saved outputs are converted back to the original CAESAR mesh unit so the
    exported files preserve their source-unit convention.

Example usage:
    # From the project root directory:
    python main.py

    # Or with a specific conda environment:
    D:\\conda\\envs\\FastIKD\\python.exe main.py

Dependencies:
    polyscope>=2.5.0, trimesh>=4.11.0, open3d>=0.19.0, scipy>=1.13.1,
    pandas>=2.3.3, openpyxl, numpy>=1.26.4, matplotlib
"""

import polyscope as ps
from config_loader import APP_CONFIG
from geometry_backend import VisContent
from gui_panel import UI_Menu


def main():
    # 1. Initialize Polyscope viewer
    viewer_cfg = APP_CONFIG.viewer
    ps.init()
    ps.set_program_name("Body Scan Viewer")
    ps.set_up_dir(viewer_cfg.up_dir)                                 # SizeStream uses Y=height (Y=0 at feet)
    ps.set_ground_plane_mode(viewer_cfg.ground_plane_mode)           # Clean background, no ground grid
    ps.set_transparency_mode(viewer_cfg.transparency_mode)           # Better default layered transparency
    ps.set_transparency_render_passes(viewer_cfg.transparency_render_passes)

    # 2. Create backend (auto-scans data folders and normalizes mixed units at runtime)
    content = VisContent()

    # 3. Create frontend (UI panel), inject backend reference
    ui = UI_Menu(content)

    # 4. Register the per-frame callback and start the viewer loop
    ps.set_user_callback(ui.render)
    ps.show()


if __name__ == "__main__":
    main()
