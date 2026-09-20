#!/bin/sh
# Preview the site on this computer (Mac/Linux): ./preview.sh
cd "$(dirname "$0")" && python3 tools/build_site.py && (sleep 1; open http://localhost:8000/ 2>/dev/null || xdg-open http://localhost:8000/) & python3 -m http.server 8000 --bind 127.0.0.1
