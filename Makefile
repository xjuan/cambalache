repo: ar.xjuan.Cambalache.json .git/objects
	flatpak remote-add --user --if-not-exists flathub-beta https://flathub.org/beta-repo/flathub-beta.flatpakrepo
	flatpak install --noninteractive --user flathub-beta org.gnome.Sdk//47beta
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
