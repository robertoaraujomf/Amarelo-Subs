#!/usr/bin/env bash
set -e

APP_NAME="amarelo-subs"
APP_VERSION="1.0.0"
APP_MAINTAINER="Roberto Araujo <robertoaraujomf1@gmail.com>"
APP_DESCRIPTION="Automated subtitle creation, formatting, translation, synchronization and video burning"
DEB_DIR="/tmp/${APP_NAME}-deb"
INSTALL_DIR="${DEB_DIR}/opt/${APP_NAME}"
DESKTOP_DIR="${DEB_DIR}/usr/share/applications"
ICON_DIR="${DEB_DIR}/usr/share/pixmaps"

rm -rf "${DEB_DIR}"
mkdir -p "${INSTALL_DIR}"
mkdir -p "${DESKTOP_DIR}"
mkdir -p "${ICON_DIR}"
mkdir -p "${DEB_DIR}/DEBIAN"

cp -r src "${INSTALL_DIR}/"
# Remove __pycache__ do pacote
find "${INSTALL_DIR}/src" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${INSTALL_DIR}/src" -name "*.pyc" -delete 2>/dev/null || true
cp main.py "${INSTALL_DIR}/"
cp requirements.txt "${INSTALL_DIR}/"
cp config.json "${INSTALL_DIR}/"

cat > "${INSTALL_DIR}/run.sh" << 'RUNEOF'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"
if [ ! -f venv/bin/activate ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi
exec python3 main.py "$@"
RUNEOF
chmod +x "${INSTALL_DIR}/run.sh"

cat > "${DEB_DIR}/usr/share/applications/amarelo-subs.desktop" << 'DESKEOF'
[Desktop Entry]
Name=Amarelo Subs
Comment=Create, format, translate, sync and burn subtitles into videos
Exec=/opt/amarelo-subs/run.sh
Icon=amarelo-subs
Terminal=false
Type=Application
Categories=AudioVideo;Video;Utility;
DESKEOF

cp assets/icons/app_icon.png "${ICON_DIR}/amarelo-subs.png"

cat > "${DEB_DIR}/DEBIAN/control" << EOF
Package: ${APP_NAME}
Version: ${APP_VERSION}
Section: video
Priority: optional
Architecture: amd64
Depends: python3, python3-venv, python3-pip, ffmpeg
Maintainer: ${APP_MAINTAINER}
Description: ${APP_DESCRIPTION}
 Automated subtitle tool that reads video files from a directory,
 creates, formats, translates, synchronizes and burns subtitles
 directly into the video output.
EOF

cat > "${DEB_DIR}/DEBIAN/postinst" << 'POSTEOF'
#!/bin/bash
set -e
if [ "$1" = "configure" ]; then
    echo "Installing Python dependencies for Amarelo Subs..."
    cd /opt/amarelo-subs
    if [ ! -f venv/bin/activate ]; then
        python3 -m venv venv
    fi
    . venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "Amarelo Subs installed successfully."
fi
POSTEOF
chmod 755 "${DEB_DIR}/DEBIAN/postinst"

dpkg-deb --build "${DEB_DIR}" "${APP_NAME}_${APP_VERSION}_amd64.deb"
echo "Done: ${APP_NAME}_${APP_VERSION}_amd64.deb"
