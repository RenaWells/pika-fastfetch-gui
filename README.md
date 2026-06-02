# Pika Fastfetch GUI

<p align="center">
  <img src="data/icons/hicolor/256x256/apps/pika-fastfetch-gui.png" alt="Pika Fetch logo" width="160">
</p>

A customizable fastfetch-style GTK 4/libadwaita desktop app for PikaOS 4.

The GTK app is written in Python. System facts are collected by `scripts/collect.sh`, so the data layer is easy to customize with normal Bash.

## Features

- Live fastfetch-style preview
- Accent, logo, title, density, and font controls
- Toggle individual fields on and off
- Hide unknown values
- Auto refresh with configurable interval
- Copy the current summary to clipboard
- Export the current summary to `~/pika-fetch-summary.txt`
- Settings saved in `~/.config/pika-fastfetch-gui/settings.json`

## Run

```bash
cd ~/pika-fastfetch-gui
./run.sh
```

After installing the package, run:

```bash
pika-fastfetch-gui
```

## Requirements

Install these if they are missing:

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
```

Optional commands improve detail: `lscpu`, `lspci`, `flatpak`, `snap`, and `gsettings`.

## Customize

Edit `scripts/collect.sh` to add, remove, or rename rows. Each row should print:

```text
Label<TAB>Value
```

Edit `style.css` to change colors and typography.

## Build The Debian Package

Install packaging tools if needed:

```bash
sudo apt install build-essential debhelper dpkg-dev
```

```bash
cd ~/pika-fastfetch-gui
dpkg-buildpackage -us -uc -b
```

The `.deb`, `.changes`, and `.buildinfo` files are written to the parent directory. Upload those artifacts to your PikaOS apt repository with your normal repo publishing tooling.

For a new package-manager update, edit `debian/changelog` with a higher version, rebuild, and publish the new artifacts.

If you only need a local binary `.deb` and do not have the full Debian build toolchain installed:

```bash
cd ~/pika-fastfetch-gui
./scripts/build-local-deb.sh
```

That writes `dist/pika-fastfetch-gui_<version>_all.deb`.

## License

Pika Fastfetch GUI is licensed under the GNU General Public License v3.0 or later. See `LICENSE`.
