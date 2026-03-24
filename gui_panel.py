"""
gui_panel.py — Frontend (View) Layer for the Body Scan Viewer

Draws the ImGui control panel inside the Polyscope side panel.
Each panel corresponds to a pipeline step (A-D), with a System panel at top.

Panels:
    System  — shows scan results, warnings, and subject count
    A. Import — subject dropdown, file status preview, Load buttons
    B. Registration — Run ICP button, quality metrics, Save button
    C. Distance — color range slider, Compare button, statistics table
    D. Geodesic — landmark sliders (live preview), Compute button, length display

Design principles:
    - Progressive unlock: buttons are grayed out until prerequisites are met
    - Friendly errors: all exceptions are caught and displayed as status messages
    - ASCII-safe markers: [OK] [!!] [ERR] (no Unicode that may not render)
    - Status history: last 3 messages visible (not just the most recent one)
    - Subject switch detection: changing the dropdown clears all state
"""

import numpy as np
import polyscope.imgui as psim
from config_loader import APP_CONFIG


# ==============================================================================
# Status display helpers (ASCII-safe, colored)
# ==============================================================================

def _ok(msg):
    """Green status text for success messages."""
    psim.TextColored((0.3, 1.0, 0.3, 1.0), f"[OK] {msg}")

def _warn(msg):
    """Yellow status text for warnings."""
    psim.TextColored((1.0, 0.85, 0.1, 1.0), f"[!!] {msg}")

def _err(msg):
    """Red status text for errors."""
    psim.TextColored((1.0, 0.35, 0.35, 1.0), f"[ERR] {msg}")

def _info(msg):
    """Gray status text for informational messages."""
    psim.TextDisabled(f"     {msg}")


# ==============================================================================
# UI_Menu class
# ==============================================================================

class UI_Menu:
    """
    ImGui control panel for the Body Scan Viewer.
    Receives a VisContent backend instance via dependency injection.
    The render() method is called every frame by Polyscope's callback loop.
    """

    def __init__(self, content):
        """
        Initialize UI state.

        Args:
            content: VisContent backend instance (dependency injection)
        """
        self.content = content

        # Subject selection state
        self.sel_idx    = 0
        self._prev_idx  = 0     # Must match sel_idx to avoid first-frame reset
        self._combo_ids    = []
        self._combo_labels = []
        self._build_combo()

        # Status message history (last 3)
        self._status_history = []  # [(msg, kind), ...]

        # Distance panel: color range slider
        self.color_max_mm = APP_CONFIG.distance.default_color_max_mm

        # Geodesic panel: landmark dropdown indices
        self._geo_start_idx = 0
        self._geo_end_idx   = 1
        self._geo_len_str   = "--"
        self._geo_preview_key = None

    # --------------------------------------------------------------------------
    # Combo list builder
    # --------------------------------------------------------------------------

    def _build_combo(self):
        """Rebuild dropdown labels from the catalog."""
        cat = self.content.catalog
        self._combo_ids    = cat.all_ids
        self._combo_labels = (
            [cat.subjects[s].status_label for s in self._combo_ids]
            if self._combo_ids else ["(no subjects found)"]
        )

    # --------------------------------------------------------------------------
    # Status message management
    # --------------------------------------------------------------------------

    def _set_status(self, msg, kind="info"):
        """
        Push a status message. Keeps at most 3 messages.

        Args:
            msg:  text to display
            kind: "ok", "warn", "err", or "info"
        """
        self._status_history.append((msg, kind))
        if len(self._status_history) > 3:
            self._status_history.pop(0)

    def _show_status(self):
        """Render all status messages in the history."""
        for msg, kind in self._status_history:
            {"ok": _ok, "warn": _warn, "err": _err}.get(kind, _info)(msg)

    # --------------------------------------------------------------------------
    # Main render (called every frame)
    # --------------------------------------------------------------------------

    def render(self):
        """Top-level render function. Draws all panels."""
        psim.TextUnformatted("Body Scan Viewer")
        psim.Separator()

        if psim.TreeNode("System"):
            self._panel_system()
            psim.TreePop()
        if psim.TreeNode("A. Import"):
            self._panel_import()
            psim.TreePop()
        if psim.TreeNode("B. Registration"):
            self._panel_registration()
            psim.TreePop()
        if psim.TreeNode("C. Distance"):
            self._panel_distance()
            psim.TreePop()
        if psim.TreeNode("D. Geodesic"):
            self._panel_geodesic()
            psim.TreePop()

    # --------------------------------------------------------------------------
    # Panel: System (scan results overview)
    # --------------------------------------------------------------------------

    def _panel_system(self):
        """Show scan summary: how many subjects found, any warnings/errors."""
        cat = self.content.catalog
        n_total   = len(cat.subjects)
        n_matched = sum(1 for e in cat.subjects.values() if e.is_complete)

        if n_matched > 0:
            _ok(f"Found {n_matched}/{n_total} complete subject pairs")
        else:
            _err("No usable subjects found. Check data folders.")

        for err in cat.scan_errors:
            if "[ERR]" in err:
                _err(err.replace("[ERR] ", ""))
            elif "[!!]" in err:
                _warn(err.replace("[!!] ", ""))
            else:
                _info(err)

    # --------------------------------------------------------------------------
    # Panel A: Import
    # --------------------------------------------------------------------------

    def _panel_import(self):
        """
        Subject selector dropdown + file status preview + Load buttons.

        Detects subject switch (dropdown change) and triggers reset_subject().
        Buttons are disabled (grayed out) when prerequisite files are missing.
        """
        if not self._combo_ids:
            _err("No subjects available")
            return

        # Subject dropdown
        changed, self.sel_idx = psim.Combo(
            "Subject", self.sel_idx, self._combo_labels
        )

        # Subject switch detection
        if self.sel_idx != self._prev_idx:
            self._prev_idx = self.sel_idx
            self.content.reset_subject()
            self._geo_len_str = "--"
            self._geo_preview_key = None
            self._status_history.clear()
            self.color_max_mm = APP_CONFIG.distance.default_color_max_mm

        sid   = self._combo_ids[self.sel_idx]
        entry = self.content.catalog.subjects[sid]

        # File status preview
        psim.Separator()
        (_ok if entry.ss_obj_path    else _err)(
            f"SS:  {entry.ss_obj_path.name if entry.ss_obj_path else 'not found'}"
        )
        (_ok if entry.caesar_ply_path else _warn)(
            f"PLY: {entry.caesar_ply_path.name if entry.caesar_ply_path else 'not found'}"
        )
        (_ok if entry.has_landmarks   else _warn)(
            f"LM:  {'landmark data available' if entry.has_landmarks else 'no landmark data'}"
        )
        (_ok if entry.caesar_lnd_path else _warn)(
            f"LND: {entry.caesar_lnd_path.name if entry.caesar_lnd_path else 'CAESAR .lnd not found'}"
        )
        if self.content.mesh_caesar is not None and self.content.caesar_unit_ctx is not None:
            _info(
                f"CAESAR runtime unit: mm (source: {self.content.caesar_unit_ctx.original_unit})"
            )
        psim.Separator()

        # Load SizeStream button (disabled if no OBJ)
        if not entry.ss_obj_path:
            psim.BeginDisabled()
        if psim.Button("Load SizeStream  (Fixed Reference)"):
            try:
                self.content.load_sizestream(sid)
                self._set_status(f"SizeStream loaded: {sid}", "ok")
            except Exception as e:
                self._set_status(f"Load failed: {e}", "err")
        if not entry.ss_obj_path:
            psim.EndDisabled()

        # Load CAESAR button (disabled if no PLY)
        if not entry.caesar_ply_path:
            psim.BeginDisabled()
        if psim.Button("Load CAESAR"):
            try:
                self.content.load_caesar(sid)
                self._set_status("CAESAR loaded", "ok")
                if self.content.caesar_lm_warning is not None:
                    self._set_status(self.content.caesar_lm_warning, "warn")
                if self.content.caesar_lm_pos is not None:
                    lm_msg = (
                        f"CAESAR landmarks loaded: {len(self.content.caesar_lm_pos)} (.lnd)"
                    )
                    if self.content.caesar_lm_alignment is not None:
                        align = self.content.caesar_lm_alignment
                        lm_msg += (
                            f" | {align['rotation_label']}"
                            f" | mean mesh err={align['mean_mesh_error_mm']:.1f}mm"
                            f" | max={align['max_mesh_error_mm']:.1f}mm"
                        )
                    self._set_status(
                        lm_msg,
                        "info"
                    )
                if self.content.caesar_unit_ctx is not None:
                    self._set_status(
                        f"CAESAR viewer/runtime unit: mm (source: "
                        f"{self.content.caesar_unit_ctx.original_unit})",
                        "info"
                    )
                # Show coordinate diagnosis warning if needed
                if self.content.coord_diag and self.content.coord_diag['needs_axis_swap']:
                    d = self.content.coord_diag
                    self._set_status(
                        f"Axis mismatch: SS={'XYZ'[d['ss_up_axis']]}-up, "
                        f"CAESAR={'XYZ'[d['caesar_up_axis']]}-up (auto-fixed at registration)",
                        "warn"
                    )
            except Exception as e:
                self._set_status(f"CAESAR load failed: {e}", "err")
        if not entry.caesar_ply_path:
            psim.EndDisabled()

    # --------------------------------------------------------------------------
    # Panel B: Registration
    # --------------------------------------------------------------------------

    def _panel_registration(self):
        """
        ICP registration panel.
        Requires both meshes loaded. Shows quality metrics and Save button.
        """
        c   = self.content
        can = c.mesh_ss is not None and c.mesh_caesar is not None

        if not can:
            _warn("Load SizeStream + CAESAR first (Panel A)")
            return

        if psim.Button("Run ICP Registration"):
            try:
                rmse, fitness, quality = c.run_registration()
                self._set_status(
                    f"Done | RMSE={rmse:.1f}mm | {quality} | Fitness={fitness:.3f}",
                    "ok"
                )
                # Sync auto-adapted color_max from backend
                self.color_max_mm = c.color_max_mm
            except Exception as e:
                self._set_status(f"Registration failed: {e}", "err")

        if c.mesh_registered is not None:
            psim.Separator()
            _ok(f"RMSE:    {c.icp_rmse:.2f} mm")
            _ok(f"Fitness: {c.icp_fitness:.3f}")
            quality_cfg = APP_CONFIG.registration.quality
            _info(
                f"Rating: fitness<{quality_cfg.fitness_fail_below:.1f} Failed | "
                f"<{quality_cfg.excellent_rmse_below_mm:.0f}mm Excellent | "
                f"<{quality_cfg.acceptable_rmse_below_mm:.0f}mm Acceptable"
            )
            if psim.Button("Save to processed/"):
                try:
                    out = c.save_registered(c.current_subject)
                    self._set_status(f"Saved: {out.name}", "ok")
                except Exception as e:
                    self._set_status(f"Save failed: {e}", "err")

    # --------------------------------------------------------------------------
    # Panel C: Distance comparison
    # --------------------------------------------------------------------------

    def _panel_distance(self):
        """
        Landmark distance comparison panel.
        Requires registration complete + SS landmarks available.
        Color range slider lets user adjust heatmap sensitivity.
        """
        c   = self.content
        can = c.mesh_registered is not None and c.lm_pos_ss is not None

        if not can:
            _warn("Need: [1] SS landmarks  [2] completed registration")
            return

        # Color range slider (synced to backend, not overwritten by code)
        distance_cfg = APP_CONFIG.distance
        _, self.color_max_mm = psim.SliderFloat(
            "Color Max (mm)", self.color_max_mm,
            distance_cfg.slider_min_mm,
            distance_cfg.slider_max_mm,
        )
        c.color_max_mm = self.color_max_mm

        if psim.Button("Compare Distances"):
            try:
                c.compare_landmark_distances()
                d = c.landmark_distances
                self._set_status(
                    f"Done | mean={d.mean():.1f}mm | max={d.max():.1f}mm",
                    "ok"
                )
            except Exception as e:
                self._set_status(f"Compare failed: {e}", "err")

        if c.landmark_distances is not None:
            d = c.landmark_distances
            psim.Separator()
            psim.Text(f"  Landmarks:  {len(d)}")
            psim.Text(f"  Mean:       {d.mean():.2f} mm")
            psim.Text(f"  Max:        {d.max():.2f} mm  <- {c.lm_names_ss[d.argmax()]}")
            psim.Text(f"  Std:        {d.std():.2f} mm")

    # --------------------------------------------------------------------------
    # Panel D: Geodesic
    # --------------------------------------------------------------------------

    def _panel_geodesic(self):
        """
        Geodesic measurement panel.
        Uses landmark sliders for zero-background UX; dragging updates endpoint preview live.
        Falls back to bounding-box estimated endpoints if no landmarks are available.
        """
        c   = self.content
        can = c.ss_edge_graph is not None

        if not can:
            _warn("Load SizeStream mesh first")
            return

        if c.ss_geodesic_solver is not None:
            _info(f"Mode: {c.ss_geodesic_mode}")
        else:
            _warn(f"Mode: {c.ss_geodesic_mode}")

        if c.ss_lm_dict:
            # Primary UI: landmark sliders (drag to update endpoint preview live)
            lm_names = list(c.ss_lm_dict.keys())
            n = len(lm_names)

            # Clamp indices to valid range (safety for subject switch)
            self._geo_start_idx = min(self._geo_start_idx, n - 1)
            self._geo_end_idx   = min(self._geo_end_idx,   n - 1)

            _, self._geo_start_idx = psim.SliderInt("Start##geo_start", self._geo_start_idx, 0, n - 1)
            psim.TextUnformatted(f"  {lm_names[self._geo_start_idx]}")
            _, self._geo_end_idx = psim.SliderInt("End##geo_end",   self._geo_end_idx,   0, n - 1)
            psim.TextUnformatted(f"  {lm_names[self._geo_end_idx]}")
            pt_a = c.ss_lm_dict[lm_names[self._geo_start_idx]]
            pt_b = c.ss_lm_dict[lm_names[self._geo_end_idx]]
            preview_key = ("lm", self._geo_start_idx, self._geo_end_idx)
        else:
            # Fallback: estimate endpoints from bounding box
            bb = c.mesh_ss.bounds  # [min_xyz, max_xyz]
            pt_a = np.array([0.0, bb[1][1] * 0.9, 0.0])   # near head
            pt_b = np.array([0.0, bb[0][1] + 50.0, 0.0])   # near feet
            _warn("No landmark data, using estimated endpoints")
            preview_key = (
                "bbox",
                tuple(np.round(pt_a, 3)),
                tuple(np.round(pt_b, 3)),
            )

        if hasattr(c, "show_geodesic_endpoints") and preview_key != self._geo_preview_key:
            c.show_geodesic_endpoints(pt_a, pt_b)
            self._geo_preview_key = preview_key
            self._geo_len_str = "--"

        psim.Separator()
        if psim.Button("Compute Geodesic"):
            try:
                length = c.compute_and_show_geodesic(pt_a, pt_b)
                if np.isinf(length):
                    self._set_status("No connected path between points", "warn")
                    self._geo_len_str = "--"
                else:
                    self._geo_len_str = f"{length:.1f}"
                    self._set_status(
                        f"Geodesic: {length:.1f} mm = {length/10:.1f} cm", "ok"
                    )
            except Exception as e:
                self._set_status(f"Geodesic failed: {e}", "err")

        if self._geo_len_str != "--":
            try:
                length_val = float(self._geo_len_str)
                _ok(f"Length: {self._geo_len_str} mm  ({length_val/10:.1f} cm)")
            except ValueError:
                pass
