"""
Behavior guards for main.py viewer defaults.
"""

import importlib
import os
import sys
import types


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakePolyscope(types.ModuleType):
    def __init__(self):
        super().__init__("polyscope")
        self.calls = []

    def init(self):
        self.calls.append(("init",))

    def set_program_name(self, name):
        self.calls.append(("set_program_name", name))

    def set_up_dir(self, up_dir):
        self.calls.append(("set_up_dir", up_dir))

    def set_ground_plane_mode(self, mode):
        self.calls.append(("set_ground_plane_mode", mode))

    def set_transparency_mode(self, mode):
        self.calls.append(("set_transparency_mode", mode))

    def set_transparency_render_passes(self, passes):
        self.calls.append(("set_transparency_render_passes", passes))

    def set_user_callback(self, cb):
        self.calls.append(("set_user_callback", cb))

    def show(self):
        self.calls.append(("show",))


def test_main_uses_pretty_transparency_defaults(monkeypatch):
    fake_ps = FakePolyscope()
    fake_geometry_backend = types.ModuleType("geometry_backend")
    fake_gui_panel = types.ModuleType("gui_panel")
    fake_config_loader = types.ModuleType("config_loader")

    class FakeContent:
        pass

    class FakeUI:
        def __init__(self, content):
            self.content = content

        def render(self):
            return None

    fake_geometry_backend.VisContent = FakeContent
    fake_gui_panel.UI_Menu = FakeUI
    fake_config_loader.APP_CONFIG = types.SimpleNamespace(
        viewer=types.SimpleNamespace(
            up_dir="neg_z_up",
            ground_plane_mode="shadow_only",
            transparency_mode="simple",
            transparency_render_passes=4,
        )
    )

    monkeypatch.setitem(sys.modules, "polyscope", fake_ps)
    monkeypatch.setitem(sys.modules, "geometry_backend", fake_geometry_backend)
    monkeypatch.setitem(sys.modules, "gui_panel", fake_gui_panel)
    monkeypatch.setitem(sys.modules, "config_loader", fake_config_loader)
    sys.modules.pop("main", None)

    mod = importlib.import_module("main")
    mod.main()

    assert ("set_up_dir", "neg_z_up") in fake_ps.calls
    assert ("set_ground_plane_mode", "shadow_only") in fake_ps.calls
    assert ("set_transparency_mode", "simple") in fake_ps.calls
    assert ("set_transparency_render_passes", 4) in fake_ps.calls
