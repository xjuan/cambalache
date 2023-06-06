repo: ar.xjuan.Cambalache.json
	flatpak-builder --force-clean --repo=repo build ar.xjuan.Cambalache.json

cambalache.flatpak: repo
	flatpak build-bundle repo cambalache.flatpak ar.xjuan.Cambalache

install: cambalache.flatpak
	flatpak install --user cambalache.flatpak

.PHONY: install
