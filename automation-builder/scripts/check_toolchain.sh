            #!/usr/bin/env bash
            set -euo pipefail

            check_command() {
              local label="$1"
              local command_name="$2"
              if command -v "$command_name" >/dev/null 2>&1; then
                printf '[ok] %s -> %s
' "$label" "$(command -v "$command_name")"
              else
                printf '[warn] %s missing (%s)
' "$label" "$command_name"
              fi
            }

            check_path() {
              local label="$1"
              local path="$2"
              if [ -e "$path" ]; then
                printf '[ok] %s -> %s
' "$label" "$path"
              else
                printf '[warn] %s missing (%s)
' "$label" "$path"
              fi
            }

            check_command "Node.js" node
            check_command "npm" npm
            check_command "npx" npx
            check_command "ffmpeg" ffmpeg
            check_command "ImageMagick" magick
            check_path "Brave browser" "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
            check_path "Google Chrome" "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

            printf '
If browser binaries are missing, expect Cloudflare-protected flows to fail in headless mode.
'
