repo: ar.xjuan.Cambalache.json .git/objects
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
