FROM debian:sid-slim

RUN apt-get update && apt-get install -y \
	desktop-file-utils \
	gettext \
	gir1.2-adw-1 \
	gir1.2-gtk-3.0 \
	gir1.2-gtk-4.0 \
	gir1.2-gtksource-5 \
	gir1.2-handy-1 \
	gir1.2-webkit2-4.1 \
	gir1.2-webkit-6.0 \
	git \
	libadwaita-1-dev \
	libgirepository-1.0-dev \
	libgtk-3-dev \
	libgtk-4-dev \
	libhandy-1-dev \
	libwlroots-dev \
	meson \
	ninja-build \
	python3-gi \
	python3-lxml \
	python-gi-dev


RUN useradd -ms /bin/bash discepolo
ENV DISPLAY :0

RUN mkdir -p /src/build

COPY . /src/
WORKDIR /src

RUN git clone -b 0.18 https://gitlab.freedesktop.org/wlroots/wlroots.git && \
	cd wlroots && \
	meson setup build/  && \
	ninja -C build/ && \
	ninja -C build/ install

WORKDIR /src/build

RUN meson --prefix=/usr && ninja && ninja install

RUN rm -rf /src

RUN apt-get remove -y \
	git \
	libadwaita-1-dev \
	libgirepository-1.0-dev \
	libgtk-3-dev \
	libgtk-4-dev \
	libhandy-1-dev \
	libwlroots-dev \
	meson \
	ninja-build \
	python-gi-dev

USER discepolo
ENTRYPOINT ["/bin/sh", "-c", "$0 \"$@\"", "cambalache"]