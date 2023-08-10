## README MS Windows

These instructions have been tested on Windows 10.
They should also work on Windows 11.

## 1. Install WSL2
1. Start -> type `cmd` -> Right-click `Command Prompt` -> select `Run as administrator`.
2. Type this command:
```
wsl --install
```
By default, this will install Ubuntu 20.

## 2. Add Ubuntu 22 to WSL
1. Start -> type `store` -> Select `Microsoft Store`.
2. Click the search bar at the top.  Type: `ubuntu 22`
3. Click the result: `Ubuntu 22.04.x LTS`. Click `Install`.
 - Troubleshooting: If it says "There has been an error.", try rebooting Windows.

## 3. Configure a Linux user
1. New window appears with message:
> Installing, this may take a few minutes...
2. Then:
> Please create a default UNIX user account. The username does not need to match your Windows username.
>
> For more information visit: https://aka.ms/wslusers
>
> Enter new UNIX username:
3. Type a username you want to use, e.g., `jmoore`.
4. Type a password for the user, e.g. " ". (1 space character)
5. Repeat the password.
 - You should now be at a Linux command prompt.
## 4. Install software in Ubuntu 22
 - Start -> type `ubu` -> Select `Ubuntu 22.04.x`.
 - Paste these commands, one at a time. There will be interactive user prompts for password and Yes/No questions.
```
sudo apt update
sudo apt install flatpak
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
```
## 5. Install the `GWSL` X Windows Server for Microsoft Windows.
1. Start -> type `store` -> Select `Microsoft Store`.
2. Click the search bar at the top. Type: `gwsl`
3. Click the result: `GWSL`. Click `Install`.
4. Start -> type `gwsl` -> Select `GWSL`.
5. Set `Public` to Checked. This allows X Windows clients from Ubuntu 22 WSL2 installation to connect to the GWSL X-Windows server.
 - The System Tray notification area should have a new orange icon, the GWSL X server running.
## 6. Install and Run Cambalache as a flatpak
1. Create a startup script for needed daemon, environment variables:
```
vi ~/start_cam.sh
```
   You can put these commands on the command-line at first as a test, put them in another script, `~/.bashrc`, etc. Making a script helps when you want to start it from a MS Windows icon.

2. Paste these lines as the script:
```
#!/bin/sh
export WEBKIT_DISABLE_COMPOSITING_MODE=1
flatpak run --user ar.xjuan.Cambalache
```
- The middle line forces the Workspace area of Cambalache, displayed with `webkit`, to not try to use hardware acceleration. If it does try such acceleration in `WSL2`, the Workspace area cannot be drawn and remains blank, even though it is being rendered OK in `broadwayd`.

- The last line runs the flatpak for Cambalache.

   Save and quit (`Esc :wq`).

3. Make the script executable:
```
chmod +x start_cam.sh
```

4. Install Cambalache from flatpak.
```
sudo service dbus start
flatpak install --user flathub ar.xjuan.Cambalache
```
-  The first line starts the dbus service, required for flatpak to work. Modern Linux installations start dbus at boot, but WSL2 does not.

5. Run Cambalache from the command-line.
```
export DISPLAY="`grep nameserver /etc/resolv.conf | sed 's/nameserver //'`:0"
./start_cam.sh
```
- The first line defines how to find the X windows server. In WSL2, it is at the IP address of the host Windows computer. The $DISPLAY environment variable lets X clients in WSL get to the X Windows server running in MS Windows. It ends up being a value like: 
```
$ echo $DISPLAY
192.168.144.1:0
```
`GWSL` was installed, started, and confirmed running in the previous section. So, it is at that IP address, running in MS Windows, waiting for X windows clients to connect to it.

## 7. Starting Cambalache from Windows
1. Click the Windows taskbar Notification area (near the Clock) expand arrow -> (orange GWSL icon) -> `Dashboard`.
2. Click `Shortcut Creator`.
Enter the following settings:

 - Shortcut Label: Cambalache

 - Shortcut Command:
```
/home/(your WSL2 username)/start_cam.sh
```
e.g.
```
/home/jmoore/start_cam.sh
```

 - Run in: `Ubuntu-22.04` <-- IMPORTANT

 - Click `More Options`.

 - Select `Color Mode`: `Light Mode`. <-- especially if you run Windows in Dark Mode

 - Select `Use DBus (Sudo Required)`: `True`.

 When the icon is run, this will start dbus, required by flatpak - but will prompt for the user's password each time.

 WSL2 also has the dubiously helpful feature of closing all WSL2 processes when there are no WSL2 terminal sessions open for 15 seconds. So it would kill Cambalache.

 To defeat this, select this option. It keeps the WSL2 session running when there are no WSL2 console windows open.

 - Click `Add to Start Menu`.
 
3. Start -> type `cam` -> `Right-click` `Cambalache on Ubuntu 22.04`.
4. Select `Pin to Start`.
5. Click `Start` again.
 - Note how Cambalache is now featured prominently and can be started easily from Windows.
6. Click `Cambalache on Ubuntu 22.04` to start it.
