#!/bin/sh

# Bash "strict mode", to help catch problems and bugs in the shell
# script. Every bash script you write should include this. See
# http://redsymbol.net/articles/unofficial-bash-strict-mode/ for
# details. Thanks to those who contributed to this code.
set -euo pipefail

apk -U update
adduser -D $USER_NAME && \
         apk --no-cache add --virtual build-dependencies build-base python3-dev libpq-dev py3-pip libffi-dev gcc jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev


pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

rm -rf /var/cache/apk/*

cp -r /code/ $HOME_DIR
rm -r /code/*

apk del build-base py3-pip python3-dev libpq-dev gcc build-dependencies libffi-dev jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev