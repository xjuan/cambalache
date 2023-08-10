FROM debian:sid-slim

RUN apt-get update && apt-get install -y \
	python3-gi \
	gir1.2-gtk-3.0 \
	gir1.2-gtk-4.0 \
	gir1.2-gtksource-4 \
	gir1.2-handy-1 \
	gir1.2-adw-1 \
	gir1.2-webkit2-4.1 \
	gir1.2-webkit-6.0 \
	python3-lxml \
	meson \
	ninja-build \
	libgtk-3-dev \
	libgtk-4-dev \
	libhandy-1-dev \
	libadwaita-1-dev \
	gettext \
	desktop-file-utils

RUN useradd -ms /bin/bash discepolo
ENV DISPLAY :0

RUN mkdir -p /src/build

COPY . /src/
WORKDIR /src/build

RUN meson --prefix=/usr
RUN ninja
RUN ninja install

RUN rm -rf /src

USER discepolo
ENTRYPOINT ["/bin/sh", "-c", "$0 \"$@\"", "cambalache"]