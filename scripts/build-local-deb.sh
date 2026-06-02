#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
version="$(sed -n '1s/^[^(]*(\([^)]*\)).*/\1/p' "$root/debian/changelog")"
package="pika-fastfetch-gui"
arch="all"
build_root="$(mktemp -d)"
package_root="$build_root/${package}_${version}_${arch}"
out_dir="$root/dist"

cleanup() {
  if [[ "${KEEP_BUILD_DIR:-0}" != "1" ]]; then
    rm -rf "$build_root"
  else
    printf 'Kept build directory: %s\n' "$build_root"
  fi
}
trap cleanup EXIT

if [[ -z "$version" ]]; then
  printf 'Unable to parse package version from debian/changelog\n' >&2
  exit 1
fi

mkdir -p "$out_dir"

install -Dm755 "$root/pika-fastfetch-gui" "$package_root/usr/bin/pika-fastfetch-gui"
install -Dm755 "$root/pika_fastfetch_gui.py" "$package_root/usr/share/pika-fastfetch-gui/pika_fastfetch_gui.py"
install -Dm644 "$root/style.css" "$package_root/usr/share/pika-fastfetch-gui/style.css"
install -Dm755 "$root/scripts/collect.sh" "$package_root/usr/share/pika-fastfetch-gui/scripts/collect.sh"
install -Dm644 "$root/pika-fastfetch-gui.desktop" "$package_root/usr/share/applications/pika-fastfetch-gui.desktop"
install -Dm644 "$root/README.md" "$package_root/usr/share/doc/pika-fastfetch-gui/README.md"
install -Dm644 "$root/debian/copyright" "$package_root/usr/share/doc/pika-fastfetch-gui/copyright"

if command -v gzip >/dev/null 2>&1; then
  gzip -n -9 -c "$root/debian/changelog" > "$package_root/usr/share/doc/pika-fastfetch-gui/changelog.Debian.gz"
  chmod 644 "$package_root/usr/share/doc/pika-fastfetch-gui/changelog.Debian.gz"
else
  install -Dm644 "$root/debian/changelog" "$package_root/usr/share/doc/pika-fastfetch-gui/changelog.Debian"
fi

installed_size="$(du -sk "$package_root/usr" | awk '{print $1}')"
mkdir -p "$package_root/DEBIAN"
cat > "$package_root/DEBIAN/control" <<CONTROL
Package: $package
Version: $version
Section: utils
Priority: optional
Architecture: $arch
Maintainer: PikaOS Maintainers <contact@pika-os.com>
Installed-Size: $installed_size
Depends: bash, coreutils, gir1.2-adw-1, gir1.2-gtk-4.0, procps, python3, python3-gi
Recommends: libglib2.0-bin, pciutils, util-linux, x11-xserver-utils
Description: Custom fastfetch-style system overview for PikaOS
 Pika Fetch is a GTK4/libadwaita desktop application that displays a
 fastfetch-style system overview with configurable fields, colors, logo,
 title, density, font sizes, copy support, export support, and auto refresh.
CONTROL

dpkg-deb --build --root-owner-group "$package_root" "$out_dir/${package}_${version}_${arch}.deb"
