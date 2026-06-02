# SPDX-License-Identifier: GPL-3.0-or-later

PREFIX ?= /usr
BINDIR ?= $(PREFIX)/bin
DATADIR ?= $(PREFIX)/share/pika-fastfetch-gui
APPLICATIONSDIR ?= $(PREFIX)/share/applications
DOCDIR ?= $(PREFIX)/share/doc/pika-fastfetch-gui

.PHONY: install deb clean

install:
	install -Dm755 pika-fastfetch-gui "$(DESTDIR)$(BINDIR)/pika-fastfetch-gui"
	install -Dm755 pika_fastfetch_gui.py "$(DESTDIR)$(DATADIR)/pika_fastfetch_gui.py"
	install -Dm644 style.css "$(DESTDIR)$(DATADIR)/style.css"
	install -Dm755 scripts/collect.sh "$(DESTDIR)$(DATADIR)/scripts/collect.sh"
	install -Dm644 pika-fastfetch-gui.desktop "$(DESTDIR)$(APPLICATIONSDIR)/pika-fastfetch-gui.desktop"
	install -Dm644 README.md "$(DESTDIR)$(DOCDIR)/README.md"
	install -Dm644 LICENSE "$(DESTDIR)$(DOCDIR)/LICENSE"

deb:
	dpkg-buildpackage -us -uc -b

clean:
	rm -rf __pycache__
