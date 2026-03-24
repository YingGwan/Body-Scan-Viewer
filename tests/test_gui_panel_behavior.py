"""
Behavior guards for gui_panel rendering.

These tests verify that the shared top-of-panel status log is not rendered,
and that geodesic endpoint preview updates immediately on selection.
"""

import importlib
import os
import sys
import types
import numpy as np


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakePsImModule(types.ModuleType):
    def __init__(self):
        super().__init__("polyscope.imgui")
        self.combo_results = []
        self.button_results = []

    def TextUnformatted(self, *args, **kwargs):
        return None

    def TextDisabled(self, *args, **kwargs):
        return None

    def Separator(self, *args, **kwargs):
        return None

    def TreeNode(self, *args, **kwargs):
        return True

    def TreePop(self, *args, **kwargs):
        return None

    def Combo(self, label, current, items):
        if self.combo_results:
            return self.combo_results.pop(0)
        return False, current

    def Button(self, *args, **kwargs):
        if self.button_results:
            return self.button_results.pop(0)
        return False


def test_render_does_not_show_shared_status_at_top(monkeypatch):
    fake_psim = FakePsImModule()
    fake_polyscope = types.ModuleType("polyscope")
    fake_polyscope.imgui = fake_psim
    monkeypatch.setitem(sys.modules, "polyscope", fake_polyscope)
    monkeypatch.setitem(sys.modules, "polyscope.imgui", fake_psim)
    sys.modules.pop("gui_panel", None)
    mod = importlib.import_module("gui_panel")

    fake_catalog = types.SimpleNamespace(all_ids=[], subjects={})
    fake_content = types.SimpleNamespace(catalog=fake_catalog)
    ui = mod.UI_Menu(fake_content)

    calls = []
    ui._panel_system = lambda: None
    ui._panel_import = lambda: None
    ui._panel_registration = lambda: None
    ui._panel_distance = lambda: None
    ui._panel_geodesic = lambda: None
    ui._show_status = lambda: calls.append("show")

    ui.render()

    assert calls == []


def test_geodesic_panel_updates_preview_on_selection_change(monkeypatch):
    fake_psim = FakePsImModule()
    fake_psim.combo_results = [
        (True, 1),   # start landmark changed
        (False, 2),  # end landmark unchanged
    ]
    fake_psim.button_results = [False]

    fake_polyscope = types.ModuleType("polyscope")
    fake_polyscope.imgui = fake_psim
    monkeypatch.setitem(sys.modules, "polyscope", fake_polyscope)
    monkeypatch.setitem(sys.modules, "polyscope.imgui", fake_psim)
    sys.modules.pop("gui_panel", None)
    mod = importlib.import_module("gui_panel")

    calls = []
    fake_content = types.SimpleNamespace(
        catalog=types.SimpleNamespace(all_ids=["sid"], subjects={"sid": types.SimpleNamespace(status_label="sid")}),
        ss_edge_graph=object(),
        ss_geodesic_solver=object(),
        ss_geodesic_mode="potpourri3d exact path",
        ss_lm_dict={
            "A": np.array([0.0, 0.0, 0.0]),
            "B": np.array([1.0, 0.0, 0.0]),
            "C": np.array([2.0, 0.0, 0.0]),
        },
        show_geodesic_endpoints=lambda a, b: calls.append((a.copy(), b.copy())),
    )
    ui = mod.UI_Menu(fake_content)
    ui._geo_start_idx = 0
    ui._geo_end_idx = 2

    ui._panel_geodesic()

    assert len(calls) == 1
    np.testing.assert_allclose(calls[0][0], [1.0, 0.0, 0.0])
    np.testing.assert_allclose(calls[0][1], [2.0, 0.0, 0.0])


def test_ui_menu_uses_distance_default_from_config(monkeypatch):
    fake_psim = FakePsImModule()
    fake_polyscope = types.ModuleType("polyscope")
    fake_polyscope.imgui = fake_psim
    fake_config_loader = types.ModuleType("config_loader")
    fake_config_loader.APP_CONFIG = types.SimpleNamespace(
        distance=types.SimpleNamespace(
            default_color_max_mm=55.0,
            slider_min_mm=5.0,
            slider_max_mm=80.0,
        )
    )

    monkeypatch.setitem(sys.modules, "polyscope", fake_polyscope)
    monkeypatch.setitem(sys.modules, "polyscope.imgui", fake_psim)
    monkeypatch.setitem(sys.modules, "config_loader", fake_config_loader)
    sys.modules.pop("gui_panel", None)
    mod = importlib.import_module("gui_panel")

    fake_catalog = types.SimpleNamespace(all_ids=[], subjects={})
    fake_content = types.SimpleNamespace(catalog=fake_catalog)
    ui = mod.UI_Menu(fake_content)

    assert ui.color_max_mm == 55.0
