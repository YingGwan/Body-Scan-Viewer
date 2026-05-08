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
import polyscope as ps
from data_loader import PROCESSED_DIR
from derived_landmarks import from_barycentric, project_to_mesh, save_weights_to_yaml


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

        # Panel E: Derived Landmarks
        self._derived_computed = False
        self._derived_weights = {}
        self._derived_positions = {}
        self._derived_dirty = set()
        self._measurements_cache = {}
        self._weights_unsaved = False
        self._geo_needs_refresh = False
        self._lock_sum = True
        self._show_global_lm = True
        self._show_neck_lm = True
        self._show_armhole_lm = True

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
        if psim.TreeNode("E. Derived Landmarks"):
            self._panel_derived()
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
            self._derived_computed = False
            self._derived_weights = {}
            self._derived_positions = {}
            self._derived_dirty = set()
            self._measurements_cache = {}
            self._weights_unsaved = False
            self._geo_needs_refresh = False

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

    # --------------------------------------------------------------------------
    # Panel E: Derived Landmarks
    # --------------------------------------------------------------------------

    def _panel_derived(self):
        c = self.content

        can_compute = c.mesh_ss is not None and bool(c.ss_lm_dict)
        if not can_compute:
            _warn("Load SizeStream mesh + landmarks first")
            return

        if psim.Button("Compute / Initialize"):
            try:
                c.compute_derived_landmarks()
                c.compute_shoulder_measurements()
                self._derived_computed = True
                self._derived_weights = {
                    name: list(info["weights"])
                    for name, info in c.derived_lm_dict.items()
                }
                self._derived_positions = {
                    name: info["position"].copy()
                    for name, info in c.derived_lm_dict.items()
                }
                self._measurements_cache = {}
                for r in c.measurement_results:
                    if r.name.endswith("_Y"):
                        parent = r.name[:-2]
                        self._measurements_cache.setdefault(parent, {})["y_projection"] = r.value_mm
                    else:
                        self._measurements_cache.setdefault(r.name, {})[r.method] = r.value_mm
                self._derived_dirty.clear()
                self._weights_unsaved = False
                self._geo_needs_refresh = False
                self._set_status("Derived landmarks computed", "ok")
            except Exception as e:
                self._set_status(f"Derived landmarks failed: {e}", "err")
                return

        if not self._derived_computed:
            return

        psim.Separator()
        ch1, self._show_global_lm = psim.Checkbox("Show Global Landmarks", self._show_global_lm)
        if ch1:
            try:
                if ps.has_point_cloud("SS_Landmarks"):
                    ps.get_point_cloud("SS_Landmarks").set_enabled(self._show_global_lm)
            except Exception:
                pass

        ch2, self._show_neck_lm = psim.Checkbox("Show Neck Derived", self._show_neck_lm)
        if ch2:
            try:
                if ps.has_point_cloud("Derived_Neck"):
                    ps.get_point_cloud("Derived_Neck").set_enabled(self._show_neck_lm)
                for mname in (c.derived_lm_config or {}).get("measurements", {}):
                    if c.derived_lm_config["measurements"][mname].get("family") == "Neck":
                        if ps.has_curve_network(f"Geo_{mname}"):
                            ps.get_curve_network(f"Geo_{mname}").set_enabled(self._show_neck_lm)
            except Exception:
                pass

        ch3, self._show_armhole_lm = psim.Checkbox("Show Armhole Derived", self._show_armhole_lm)
        if ch3:
            try:
                if ps.has_point_cloud("Derived_Armhole"):
                    ps.get_point_cloud("Derived_Armhole").set_enabled(self._show_armhole_lm)
            except Exception:
                pass

        # -- Per-family collapsible sections with sliders --
        families_seen = []
        for lm_name, info in c.derived_lm_dict.items():
            if info["family"] not in families_seen:
                families_seen.append(info["family"])

        for family in families_seen:
            psim.Separator()
            if psim.TreeNode(f"{family} Landmarks"):
                for lm_name, info in c.derived_lm_dict.items():
                    if info["family"] != family:
                        continue
                    if psim.TreeNode(lm_name):
                        self._render_landmark_sliders(lm_name, info)
                        psim.TreePop()
                psim.TreePop()

        # -- Measurements collapsible --
        psim.Separator()
        if psim.TreeNode("Measurements"):
            for meas_name, vals in self._measurements_cache.items():
                geo_val = vals.get("geodesic", 0)
                y_val = vals.get("y_projection", 0)
                stale = " *" if self._geo_needs_refresh else ""
                if geo_val > 0 and y_val > 0:
                    _ok(f"{meas_name}: geo {geo_val:.1f}mm  dY {y_val:.1f}mm{stale}")
                elif geo_val > 0:
                    _ok(f"{meas_name}: geo {geo_val:.1f}mm{stale}")
                elif y_val > 0:
                    psim.TextUnformatted(f"  {meas_name}: dY {y_val:.1f}mm")
            psim.TreePop()

        psim.Separator()
        if self._geo_needs_refresh:
            if psim.Button("Refresh Geodesics"):
                self._refresh_geodesics()

        if self._weights_unsaved:
            if psim.Button("Save Weights to YAML"):
                self._save_weights()

        if psim.Button("Export Excel"):
            self._export_excel()

    def _render_landmark_sliders(self, lm_name, info):
        c = self.content
        w = self._derived_weights[lm_name]
        cfg = c.derived_lm_config["landmarks"][lm_name]
        tri_names = cfg["triangle"]

        changed = False
        for i, (label, tri_name) in enumerate(zip(["a", "b", "g"], tri_names)):
            ch, w[i] = psim.SliderFloat(
                f"{label} ({tri_name})##{lm_name}{i}", w[i], v_min=-2.0, v_max=2.0
            )
            if ch:
                changed = True

        _, self._lock_sum = psim.Checkbox(f"Lock a+b+g=1##{lm_name}", self._lock_sum)

        if changed:
            if self._lock_sum:
                w[2] = 1.0 - w[0] - w[1]
            self._derived_weights[lm_name] = w
            A = np.asarray(c.ss_lm_dict[tri_names[0]])
            B = np.asarray(c.ss_lm_dict[tri_names[1]])
            C = np.asarray(c.ss_lm_dict[tri_names[2]])
            P_bary = from_barycentric(w[0], w[1], w[2], A, B, C)
            P_surface = project_to_mesh(P_bary, c.mesh_ss)
            self._derived_positions[lm_name] = P_surface
            c.derived_lm_dict[lm_name]["position"] = P_surface
            c.derived_lm_dict[lm_name]["weights"] = tuple(w)

            family = info["family"]
            positions = [
                d["position"] for n, d in c.derived_lm_dict.items()
                if d["family"] == family
            ]
            try:
                ps.register_point_cloud(
                    f"Derived_{family}", np.array(positions),
                    color=[0.8, 0.1, 0.1], enabled=True, radius=0.005,
                )
            except Exception:
                pass

            self._update_y_projections()
            self._derived_dirty.add(lm_name)
            self._weights_unsaved = True
            self._geo_needs_refresh = True

        pos = self._derived_positions[lm_name]
        psim.TextUnformatted(f"  Pos: [{pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}]")

    def _update_y_projections(self):
        c = self.content
        combined = dict(c.ss_lm_dict)
        combined.update({n: d["position"] for n, d in c.derived_lm_dict.items()})
        config = c.derived_lm_config
        for meas_name, m_config in config["measurements"].items():
            if m_config.get("also_output_y_projection"):
                from derived_landmarks import resolve_landmark_name
                from_name = resolve_landmark_name(m_config["from"], config)
                to_name = resolve_landmark_name(m_config["to"], config)
                pt_a = combined.get(from_name)
                pt_b = combined.get(to_name)
                if pt_a is not None and pt_b is not None:
                    y_proj = abs(float(pt_a[1]) - float(pt_b[1]))
                    self._measurements_cache.setdefault(meas_name, {})["y_projection"] = y_proj

    def _refresh_geodesics(self):
        c = self.content
        try:
            c.compute_shoulder_measurements()
            self._measurements_cache = {}
            for r in c.measurement_results:
                if r.name.endswith("_Y"):
                    parent = r.name[:-2]
                    self._measurements_cache.setdefault(parent, {})["y_projection"] = r.value_mm
                else:
                    self._measurements_cache.setdefault(r.name, {})[r.method] = r.value_mm
            self._geo_needs_refresh = False
            self._set_status("Geodesics refreshed", "ok")
        except Exception as e:
            self._set_status(f"Geodesic refresh failed: {e}", "err")

    def _save_weights(self):
        c = self.content
        yaml_path = c._DERIVED_YAML
        try:
            for lm_name in self._derived_dirty:
                w = self._derived_weights[lm_name]
                save_weights_to_yaml(yaml_path, lm_name, w)
            self._derived_dirty.clear()
            self._weights_unsaved = False
            self._set_status("Weights saved to YAML", "ok")
        except Exception as e:
            self._set_status(f"Save failed: {e}", "err")

    def _export_excel(self):
        c = self.content
        if not c.measurement_results:
            self._set_status("No measurements to export", "warn")
            return
        sid = c.current_subject or "unknown"
        out_path = str(PROCESSED_DIR / f"{sid}_v3_results.xlsx")
        try:
            c.export_results_to_excel(out_path)
            self._set_status(f"Exported to {out_path}", "ok")
        except Exception as e:
            self._set_status(f"Export failed: {e}", "err")
