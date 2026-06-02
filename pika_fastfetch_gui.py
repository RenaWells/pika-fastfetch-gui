#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk


APP_ID = "local.pika.FastfetchGui"
BASE_DIR = pathlib.Path(__file__).resolve().parent
COLLECTOR = BASE_DIR / "scripts" / "collect.sh"
CONFIG_DIR = pathlib.Path.home() / ".config" / "pika-fastfetch-gui"
CONFIG_FILE = CONFIG_DIR / "settings.json"
EXPORT_FILE = pathlib.Path.home() / "pika-fetch-summary.txt"

FIELD_ORDER = [
    "OS",
    "Host",
    "Kernel",
    "Uptime",
    "Packages",
    "Shell",
    "Desktop",
    "Session",
    "Resolution",
    "CPU",
    "GPU",
    "Memory",
    "Disk",
    "Battery",
    "Theme",
    "Terminal",
]

LOGOS = {
    "Pika": [
        "        .-:/+oossssoo+/:.",
        "    `:+ssssssssssssssssss+:`",
        "  -+ssssssssssssssssssssss+-",
        " /ssssssssssso++osssssssssss/",
        ":ssssssssss+.    .+ssssssssss:",
        "osssssssss/  PIKA  /sssssssso",
        "sssssssss+   OS 4   +sssssssss",
        "osssssssss/        /sssssssso",
        ":ssssssssss+.    .+ssssssssss:",
        " /ssssssssssso++osssssssssss/",
        "  -+ssssssssssssssssssssss+-",
        "    `:+ssssssssssssssssss+:`",
        "        .-:/+oossssoo+/:.",
    ],
    "Compact": [
        "   /\\_/\\",
        "  / pika\\",
        " /  os 4 \\",
        " \\ fast  /",
        "  \\____/",
    ],
    "Block": [
        "██████╗ ██╗██╗  ██╗ █████╗",
        "██╔══██╗██║██║ ██╔╝██╔══██╗",
        "██████╔╝██║█████╔╝ ███████║",
        "██╔═══╝ ██║██╔═██╗ ██╔══██║",
        "██║     ██║██║  ██╗██║  ██║",
        "╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝",
    ],
}

ACCENTS = {
    "Pika Green": ("#79d08a", "#141414", "#1e2220", "#f7f5ef"),
    "Aqua": ("#4fc3d7", "#111719", "#1d282b", "#f2fbfc"),
    "Rose": ("#f27b9b", "#191215", "#2b1d22", "#fff3f6"),
    "Amber": ("#e8b84e", "#17140e", "#2a2418", "#fff8e8"),
    "Mono": ("#d7d7d7", "#111111", "#232323", "#f4f4f4"),
}


@dataclass
class Settings:
    title_mode: str = "os"
    custom_title: str = "PikaOS"
    logo: str = "Pika"
    custom_logo: str = ""
    accent: str = "Pika Green"
    font_size: int = 14
    logo_size: int = 14
    compact: bool = False
    show_unknown: bool = True
    auto_refresh: bool = False
    refresh_seconds: int = 30
    enabled_fields: list[str] | None = None

    @classmethod
    def load(cls) -> "Settings":
        settings = cls(enabled_fields=FIELD_ORDER.copy())
        if not CONFIG_FILE.exists():
            return settings
        try:
            raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return settings

        for key in settings.__dataclass_fields__:
            if key in raw:
                setattr(settings, key, raw[key])
        settings.enabled_fields = [
            field for field in (settings.enabled_fields or FIELD_ORDER) if field in FIELD_ORDER
        ]
        if not settings.enabled_fields:
            settings.enabled_fields = FIELD_ORDER.copy()
        settings.font_size = clamp_int(settings.font_size, 10, 22)
        settings.logo_size = clamp_int(settings.logo_size, 9, 22)
        settings.refresh_seconds = clamp_int(settings.refresh_seconds, 5, 600)
        if settings.logo not in [*LOGOS.keys(), "Custom"]:
            settings.logo = "Pika"
        if settings.accent not in ACCENTS:
            settings.accent = "Pika Green"
        if settings.title_mode not in ["os", "host", "custom"]:
            settings.title_mode = "os"
        return settings

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(self.__dict__, indent=2), encoding="utf-8")


def clamp_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = minimum
    return max(minimum, min(maximum, parsed))


class InfoRow(Gtk.Box):
    def __init__(self, key: str, value: str, compact: bool) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=14 if compact else 18)
        self.set_css_classes(["info-row", "compact-row" if compact else "comfortable-row"])

        key_label = Gtk.Label(label=key)
        key_label.set_xalign(0)
        key_label.set_width_chars(10)
        key_label.set_css_classes(["info-key"])

        value_label = Gtk.Label(label=value or "Unknown")
        value_label.set_xalign(0)
        value_label.set_hexpand(True)
        value_label.set_wrap(True)
        value_label.set_selectable(True)
        value_label.set_css_classes(["info-value"])

        self.append(key_label)
        self.append(value_label)


class FastfetchWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="Pika Fetch")
        self.set_default_size(1120, 680)
        self.set_size_request(760, 500)

        self.settings = Settings.load()
        self.data: list[tuple[str, str]] = []
        self.field_switches: dict[str, Adw.SwitchRow] = {}
        self.auto_refresh_source: int | None = None
        self.dynamic_css = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self.dynamic_css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
        )

        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        toolbar_view = Adw.ToolbarView()
        self.toast_overlay.set_child(toolbar_view)

        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="Pika Fetch", subtitle="Custom fastfetch-style dashboard"))
        toolbar_view.add_top_bar(header)

        refresh_button = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_button.set_tooltip_text("Refresh")
        refresh_button.connect("clicked", lambda _button: self.refresh())
        header.pack_end(refresh_button)

        copy_button = Gtk.Button(icon_name="edit-copy-symbolic")
        copy_button.set_tooltip_text("Copy summary")
        copy_button.connect("clicked", lambda _button: self.copy_summary())
        header.pack_end(copy_button)

        export_button = Gtk.Button(icon_name="document-save-symbolic")
        export_button.set_tooltip_text("Export text summary")
        export_button.connect("clicked", lambda _button: self.export_summary())
        header.pack_end(export_button)

        reset_button = Gtk.Button(icon_name="edit-undo-symbolic")
        reset_button.set_tooltip_text("Reset customization")
        reset_button.connect("clicked", lambda _button: self.reset_settings())
        header.pack_start(reset_button)

        self.root = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.root.set_wide_handle(True)
        self.root.set_position(700)
        toolbar_view.set_content(self.root)

        self.preview = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=28)
        self.preview.set_margin_top(28)
        self.preview.set_margin_bottom(28)
        self.preview.set_margin_start(28)
        self.preview.set_margin_end(28)
        self.preview.set_hexpand(True)
        self.preview.set_vexpand(True)
        self.preview.set_css_classes(["preview"])
        self.root.set_start_child(self.preview)
        self.root.set_resize_start_child(True)
        self.root.set_shrink_start_child(False)

        self.logo = Gtk.Label()
        self.logo.set_xalign(0)
        self.logo.set_yalign(0.5)
        self.logo.set_selectable(True)
        self.logo.set_css_classes(["ascii-logo"])
        self.preview.append(self.logo)

        self.info_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.info_panel.set_hexpand(True)
        self.info_panel.set_vexpand(True)
        self.preview.append(self.info_panel)

        self.title = Gtk.Label(label="PikaOS")
        self.title.set_xalign(0)
        self.title.set_wrap(True)
        self.title.set_css_classes(["fetch-title"])
        self.info_panel.append(self.title)

        self.rows = Gtk.ListBox()
        self.rows.set_selection_mode(Gtk.SelectionMode.NONE)
        self.rows.set_css_classes(["info-list"])
        self.info_panel.append(self.rows)

        self.status = Gtk.Label(label="")
        self.status.set_xalign(0)
        self.status.set_css_classes(["status"])
        self.info_panel.append(self.status)

        self.settings_scroller = Gtk.ScrolledWindow()
        self.settings_scroller.set_min_content_width(330)
        self.settings_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.settings_scroller.set_css_classes(["settings-scroll"])
        self.root.set_end_child(self.settings_scroller)
        self.root.set_resize_end_child(False)
        self.root.set_shrink_end_child(False)
        self.settings_scroller.set_child(self._build_settings_panel())

        self._apply_settings(save=False)
        self.refresh()

    def _build_settings_panel(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()
        page.set_margin_top(12)
        page.set_margin_bottom(12)
        page.set_margin_start(12)
        page.set_margin_end(12)

        appearance = Adw.PreferencesGroup(title="Appearance")
        page.add(appearance)

        self.accent_combo = Gtk.ComboBoxText()
        for name in ACCENTS:
            self.accent_combo.append(name, name)
        self.accent_combo.set_active_id(self.settings.accent)
        self.accent_combo.connect("changed", self._on_accent_changed)
        appearance.add(self._action_row("Accent", self.accent_combo))

        self.logo_combo = Gtk.ComboBoxText()
        for name in [*LOGOS.keys(), "Custom"]:
            self.logo_combo.append(name, name)
        self.logo_combo.set_active_id(self.settings.logo)
        self.logo_combo.connect("changed", self._on_logo_changed)
        appearance.add(self._action_row("Logo", self.logo_combo))

        self.logo_entry = Gtk.Entry()
        self.logo_entry.set_placeholder_text("Custom ASCII logo")
        self.logo_entry.set_text(self.settings.custom_logo)
        self.logo_entry.connect("changed", self._on_custom_logo_changed)
        appearance.add(self._action_row("Custom logo text", self.logo_entry))

        self.title_combo = Gtk.ComboBoxText()
        self.title_combo.append("os", "OS name")
        self.title_combo.append("host", "Host name")
        self.title_combo.append("custom", "Custom")
        self.title_combo.set_active_id(self.settings.title_mode)
        self.title_combo.connect("changed", self._on_title_mode_changed)
        appearance.add(self._action_row("Title source", self.title_combo))

        self.title_entry = Gtk.Entry()
        self.title_entry.set_text(self.settings.custom_title)
        self.title_entry.connect("changed", self._on_custom_title_changed)
        appearance.add(self._action_row("Custom title", self.title_entry))

        density = Adw.PreferencesGroup(title="Layout")
        page.add(density)

        self.compact_switch = Adw.SwitchRow(title="Compact rows")
        self.compact_switch.set_active(self.settings.compact)
        self.compact_switch.connect("notify::active", self._on_compact_changed)
        density.add(self.compact_switch)

        self.unknown_switch = Adw.SwitchRow(title="Show unknown values")
        self.unknown_switch.set_active(self.settings.show_unknown)
        self.unknown_switch.connect("notify::active", self._on_unknown_changed)
        density.add(self.unknown_switch)

        self.font_spin = Gtk.SpinButton.new_with_range(10, 22, 1)
        self.font_spin.set_value(self.settings.font_size)
        self.font_spin.connect("value-changed", self._on_font_changed)
        density.add(self._action_row("Info font size", self.font_spin))

        self.logo_spin = Gtk.SpinButton.new_with_range(9, 22, 1)
        self.logo_spin.set_value(self.settings.logo_size)
        self.logo_spin.connect("value-changed", self._on_logo_size_changed)
        density.add(self._action_row("Logo font size", self.logo_spin))

        refresh = Adw.PreferencesGroup(title="Refresh")
        page.add(refresh)

        self.auto_refresh_switch = Adw.SwitchRow(title="Auto refresh")
        self.auto_refresh_switch.set_active(self.settings.auto_refresh)
        self.auto_refresh_switch.connect("notify::active", self._on_auto_refresh_changed)
        refresh.add(self.auto_refresh_switch)

        self.refresh_spin = Gtk.SpinButton.new_with_range(5, 600, 5)
        self.refresh_spin.set_value(self.settings.refresh_seconds)
        self.refresh_spin.connect("value-changed", self._on_refresh_seconds_changed)
        refresh.add(self._action_row("Refresh seconds", self.refresh_spin))

        fields = Adw.PreferencesGroup(title="Visible Fields")
        page.add(fields)
        for field in FIELD_ORDER:
            row = Adw.SwitchRow(title=field)
            row.set_active(field in (self.settings.enabled_fields or FIELD_ORDER))
            row.connect("notify::active", self._on_field_changed, field)
            self.field_switches[field] = row
            fields.add(row)

        return page

    def _action_row(self, title: str, widget: Gtk.Widget) -> Adw.ActionRow:
        row = Adw.ActionRow(title=title)
        widget.set_valign(Gtk.Align.CENTER)
        row.add_suffix(widget)
        row.set_activatable_widget(widget)
        return row

    def refresh(self) -> None:
        self.status.set_label("Refreshing...")
        GLib.Thread.new("collector", self._collect_thread, None)

    def _collect_thread(self, _data: object) -> None:
        try:
            result = subprocess.run(
                [str(COLLECTOR)],
                cwd=str(BASE_DIR),
                check=True,
                text=True,
                capture_output=True,
                timeout=8,
            )
            parsed = self._parse_output(result.stdout)
            GLib.idle_add(self._apply_data, parsed, None)
        except Exception as exc:
            GLib.idle_add(self._apply_data, [], str(exc))

    def _parse_output(self, output: str) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        for line in output.splitlines():
            if "\t" not in line:
                continue
            key, value = line.split("\t", 1)
            rows.append((key.strip(), value.strip() or "Unknown"))
        return rows

    def _apply_data(self, rows: list[tuple[str, str]], error: str | None) -> bool:
        self.data = rows
        self._render_preview()
        host_value = self._value_for("Host")

        if error:
            self.status.set_label("Collector failed")
            self.toast_overlay.add_toast(Adw.Toast(title=f"Unable to refresh: {error}"))
        else:
            visible_count = len(self._visible_rows())
            self.status.set_label(
                f"{visible_count} fields visible" + (f" for {host_value}" if host_value else "")
            )
        return False

    def _render_preview(self) -> None:
        while child := self.rows.get_first_child():
            self.rows.remove(child)

        self.logo.set_label(self._logo_text())
        self.title.set_label(self._title_text())

        for key, value in self._visible_rows():
            self.rows.append(InfoRow(key, value, self.settings.compact))

    def _visible_rows(self) -> list[tuple[str, str]]:
        enabled = set(self.settings.enabled_fields or FIELD_ORDER)
        rows_by_key = {key: value for key, value in self.data}
        visible: list[tuple[str, str]] = []
        for key in FIELD_ORDER:
            if key not in enabled:
                continue
            value = rows_by_key.get(key, "Unknown")
            if not self.settings.show_unknown and value == "Unknown":
                continue
            visible.append((key, value))
        return visible

    def _value_for(self, key: str) -> str:
        return next((value for row_key, value in self.data if row_key == key), "")

    def _title_text(self) -> str:
        if self.settings.title_mode == "custom":
            return self.settings.custom_title.strip() or "Pika Fetch"
        if self.settings.title_mode == "host":
            return self._value_for("Host") or "Pika Fetch"
        return self._value_for("OS") or "PikaOS"

    def _logo_text(self) -> str:
        if self.settings.logo == "Custom":
            custom = self.settings.custom_logo.strip()
            return custom or "PIKA\nOS 4"
        return "\n".join(LOGOS.get(self.settings.logo, LOGOS["Pika"]))

    def _summary_text(self) -> str:
        return "\n".join(
            [
                self._logo_text(),
                "",
                self._title_text(),
                *(f"{key}: {value}" for key, value in self._visible_rows()),
            ]
        )

    def copy_summary(self) -> None:
        if not self.data:
            return
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(self._summary_text())
        self.toast_overlay.add_toast(Adw.Toast(title="Summary copied"))

    def export_summary(self) -> None:
        try:
            EXPORT_FILE.write_text(self._summary_text() + "\n", encoding="utf-8")
        except OSError as exc:
            self.toast_overlay.add_toast(Adw.Toast(title=f"Export failed: {exc}"))
            return
        self.toast_overlay.add_toast(Adw.Toast(title=f"Exported to {EXPORT_FILE}"))

    def reset_settings(self) -> None:
        self.settings = Settings(enabled_fields=FIELD_ORDER.copy())
        self.accent_combo.set_active_id(self.settings.accent)
        self.logo_combo.set_active_id(self.settings.logo)
        self.logo_entry.set_text(self.settings.custom_logo)
        self.title_combo.set_active_id(self.settings.title_mode)
        self.title_entry.set_text(self.settings.custom_title)
        self.compact_switch.set_active(self.settings.compact)
        self.unknown_switch.set_active(self.settings.show_unknown)
        self.font_spin.set_value(self.settings.font_size)
        self.logo_spin.set_value(self.settings.logo_size)
        self.auto_refresh_switch.set_active(self.settings.auto_refresh)
        self.refresh_spin.set_value(self.settings.refresh_seconds)
        for field, row in self.field_switches.items():
            row.set_active(field in FIELD_ORDER)
        self._apply_settings()
        self.toast_overlay.add_toast(Adw.Toast(title="Customization reset"))

    def _apply_settings(self, save: bool = True) -> None:
        if save:
            self.settings.save()
        self._apply_dynamic_css()
        self._render_preview()
        self._update_auto_refresh()

    def _apply_dynamic_css(self) -> None:
        accent, start, end, text = ACCENTS[self.settings.accent]
        css = f"""
        .preview {{
          background: linear-gradient(135deg, {start}, {end});
        }}
        .ascii-logo {{
          color: {accent};
          font-size: {self.settings.logo_size}px;
        }}
        .fetch-title {{
          color: {text};
        }}
        .info-key {{
          color: {accent};
          font-size: {self.settings.font_size}px;
        }}
        .info-value {{
          color: {text};
          font-size: {self.settings.font_size}px;
        }}
        .status {{
          color: alpha({text}, 0.68);
        }}
        .info-list row:hover {{
          background: alpha({accent}, 0.12);
        }}
        """
        self.dynamic_css.load_from_data(css.encode("utf-8"))

    def _update_auto_refresh(self) -> None:
        if self.auto_refresh_source is not None:
            GLib.source_remove(self.auto_refresh_source)
            self.auto_refresh_source = None
        if not self.settings.auto_refresh:
            return
        seconds = self.settings.refresh_seconds
        self.auto_refresh_source = GLib.timeout_add_seconds(seconds, self._auto_refresh_tick)

    def _auto_refresh_tick(self) -> bool:
        self.refresh()
        return True

    def _on_accent_changed(self, combo: Gtk.ComboBoxText) -> None:
        self.settings.accent = combo.get_active_id() or "Pika Green"
        self._apply_settings()

    def _on_logo_changed(self, combo: Gtk.ComboBoxText) -> None:
        self.settings.logo = combo.get_active_id() or "Pika"
        self._apply_settings()

    def _on_custom_logo_changed(self, entry: Gtk.Entry) -> None:
        self.settings.custom_logo = entry.get_text()
        if self.settings.logo == "Custom":
            self._apply_settings()
        else:
            self.settings.save()

    def _on_title_mode_changed(self, combo: Gtk.ComboBoxText) -> None:
        self.settings.title_mode = combo.get_active_id() or "os"
        self._apply_settings()

    def _on_custom_title_changed(self, entry: Gtk.Entry) -> None:
        self.settings.custom_title = entry.get_text()
        if self.settings.title_mode == "custom":
            self._apply_settings()
        else:
            self.settings.save()

    def _on_compact_changed(self, row: Adw.SwitchRow, _pspec: object) -> None:
        self.settings.compact = row.get_active()
        self._apply_settings()

    def _on_unknown_changed(self, row: Adw.SwitchRow, _pspec: object) -> None:
        self.settings.show_unknown = row.get_active()
        self._apply_settings()

    def _on_font_changed(self, spin: Gtk.SpinButton) -> None:
        self.settings.font_size = spin.get_value_as_int()
        self._apply_settings()

    def _on_logo_size_changed(self, spin: Gtk.SpinButton) -> None:
        self.settings.logo_size = spin.get_value_as_int()
        self._apply_settings()

    def _on_auto_refresh_changed(self, row: Adw.SwitchRow, _pspec: object) -> None:
        self.settings.auto_refresh = row.get_active()
        self._apply_settings()

    def _on_refresh_seconds_changed(self, spin: Gtk.SpinButton) -> None:
        self.settings.refresh_seconds = spin.get_value_as_int()
        self._apply_settings()

    def _on_field_changed(self, row: Adw.SwitchRow, _pspec: object, field: str) -> None:
        enabled = set(self.settings.enabled_fields or FIELD_ORDER)
        if row.get_active():
            enabled.add(field)
        else:
            enabled.discard(field)
        self.settings.enabled_fields = [item for item in FIELD_ORDER if item in enabled]
        self._apply_settings()


class FastfetchApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)

    def do_activate(self) -> None:
        self._load_css()
        win = self.props.active_window
        if win is None:
            win = FastfetchWindow(self)
        win.present()

    def _load_css(self) -> None:
        display = Gdk.Display.get_default()
        if display is None:
            return
        provider = Gtk.CssProvider()
        provider.load_from_path(str(BASE_DIR / "style.css"))
        Gtk.StyleContext.add_provider_for_display(
            display,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )


def main() -> int:
    if not Gtk.init_check() or Gdk.Display.get_default() is None:
        print("Pika Fetch needs a running graphical GTK session.", file=sys.stderr)
        return 1
    app = FastfetchApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
