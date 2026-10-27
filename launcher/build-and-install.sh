#!/bin/sh
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
: "${1:?Pass the authorised TV serial. Read docs/INSTALL.md first.}"
sh "$here/gradlew" -p "$here" --no-daemon assembleDebug
python3 "$here/../custom-tools/clean_install.py" install --serial "$1" --apk "$here/app/build/outputs/apk/debug/app-debug.apk"
printf '%s\n' 'Ordinary application only. Read docs/INSTALL.md before enabling Home.'
