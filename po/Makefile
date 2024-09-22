FILES=\
    data/ar.xjuan.Cambalache.metainfo.xml.in \
    data/ar.xjuan.Cambalache.desktop.in \
    $(NULL)

PYTHON_FILES=$(shell find ../cambalache/ -name "*.py")
UI_FILES=$(shell find ../cambalache/ -name "*.ui")


cambalache.pot: POTFILES ../_build/.ninja_log
	meson compile -C ../_build/ cambalache-update-po

POTFILES: ${PYTHON_FILES} ${UI_FILES}
	@ echo Generating $@
	@ python3 filter_translatable.py ${FILES} ${PYTHON_FILES} ${UI_FILES} > $@

../_build/.ninja_log:
	cd .. && meson setup --wipe --prefix=~/.local _build .

.PHONY: clean

clean:
	rm -f POTFILES
