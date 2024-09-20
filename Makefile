repo: ar.xjuan.Cambalache.json .git/objects
	flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
	flatpak install --noninteractive --user flathub org.gnome.Sdk//47
	flatpak install --noninteractive --user flathub org.gnome.Platform//47
	flatpak-builder --force-clean --repo=repo build ar.xjuan.Cambalache.json

cambalache.flatpak: repo
	flatpak build-bundle repo cambalache.flatpak ar.xjuan.Cambalache

.PHONY: install clean veryclean

install: cambalache.flatpak
	flatpak install --user cambalache.flatpak

clean:
	rm -rf repo cambalache.flatpak

veryclean: clean
	rm -rf .flatpak-builder
