#!/bin/bash

if ! command -v compare >/dev/null 2>&1
then
    echo "compare could not be found"
    echo "sudo apt-get install imagemagick"
    exit 1
fi

for dir in images images/gtk+-3.0 images/gtk-4.0; do
	pushd $dir
	for i in *.screenshot.png; do
		if [ ! -f $i ]; then
			continue
		fi
		s=${i%.screenshot.png}
		echo Processing $i
		compare -compose src ${s}.png $i ${s}.diff.png;
		echo -e \n
	done
	popd
done