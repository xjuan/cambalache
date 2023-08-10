## README Mac OS

There is an on going effort to run Cambalache using dependencies from mac port. 
See issue [#161](https://gitlab.gnome.org/jpu/cambalache/-/issues/161)

In the mean time you can run Cambalache building a docker image and installing
a X server.

Steps:
 - Install [Docker](https://www.docker.com/) and [Xquarts](https://www.xquartz.org/)
 - Build cambalache docker image
   - `docker build -t cambalache .`
 - Make sure docker can connect to the server
   - `xhost +localhost`
 - Run docker image
   - `docker run -e DISPLAY=host.docker.internal:0 cambalache`
