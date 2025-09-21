cambalache.flatpak: repo
	flatpak build-bundle repo $@ ar.xjuan.Cambalache

repo: ar.xjuan.Cambalache.json .git/objects
	flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
	flatpak install --noninteractive --user flathub org.gnome.Sdk//49
	flatpak install --noninteractive --user flathub org.gnome.Platform//49
	flatpak-builder --force-clean --repo=repo build ar.xjuan.Cambalache.json


cambalache_arm.flatpak: repo_arm
	flatpak build-bundle --arch=aarch64 repo $@ ar.xjuan.Cambalache

repo_arm: ar.xjuan.Cambalache.json .git/objects
	flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
	flatpak install --noninteractive --user flathub org.gnome.Sdk/aarch64/49
	flatpak install --noninteractive --user flathub org.gnome.Platform/aarch64/49
	flatpak-builder --arch=aarch64 --force-clean --repo=repo build ar.xjuan.Cambalache.json


.PHONY: install clean veryclean

install: cambalache.flatpak
	flatpak install --user cambalache.flatpak

clean:
	rm -rf repo cambalache.flatpak

veryclean: clean
	rm -rf .flatpak-builder
