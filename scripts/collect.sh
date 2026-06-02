#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -uo pipefail

tab=$'\t'

emit() {
  local key="${1//$'\t'/ }"
  local value="${2//$'\t'/ }"
  value="${value//$'\n'/, }"
  printf '%s\t%s\n' "$key" "$value"
}

first_line() {
  sed -n '1p' 2>/dev/null
}

command_value() {
  local fallback="$1"
  shift
  local value
  value="$("$@" 2>/dev/null | first_line || true)"
  printf '%s' "${value:-$fallback}"
}

os_name() {
  local pretty=""
  if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    source /etc/os-release
    pretty="${PRETTY_NAME:-${NAME:-Linux}}"
  fi
  printf '%s' "${pretty:-Linux}"
}

package_count() {
  local total=0
  local parts=()

  if command -v dpkg-query >/dev/null 2>&1; then
    local count
    count="$(dpkg-query -f='${binary:Package}\n' -W 2>/dev/null | wc -l | tr -d ' ')"
    [[ "$count" =~ ^[0-9]+$ ]] && parts+=("${count} deb") && total=$((total + count))
  fi

  if command -v flatpak >/dev/null 2>&1; then
    local count
    count="$(flatpak list --app 2>/dev/null | wc -l | tr -d ' ')"
    [[ "$count" =~ ^[0-9]+$ && "$count" -gt 0 ]] && parts+=("${count} flatpak") && total=$((total + count))
  fi

  if command -v snap >/dev/null 2>&1; then
    local count
    count="$(snap list 2>/dev/null | tail -n +2 | wc -l | tr -d ' ')"
    [[ "$count" =~ ^[0-9]+$ && "$count" -gt 0 ]] && parts+=("${count} snap") && total=$((total + count))
  fi

  if ((${#parts[@]} == 0)); then
    printf 'Unknown'
  else
    local joined="${parts[0]}"
    local part
    for part in "${parts[@]:1}"; do
      joined+=", ${part}"
    done
    printf '%s' "$joined"
  fi
}

uptime_text() {
  if command -v uptime >/dev/null 2>&1; then
    uptime -p 2>/dev/null | sed 's/^up //'
    return
  fi

  local seconds
  seconds="$(cut -d. -f1 /proc/uptime 2>/dev/null || printf '0')"
  local days=$((seconds / 86400))
  local hours=$(((seconds % 86400) / 3600))
  local mins=$(((seconds % 3600) / 60))
  printf '%sd %sh %sm' "$days" "$hours" "$mins"
}

memory_text() {
  awk '
    /MemTotal/ { total=$2 }
    /MemAvailable/ { avail=$2 }
    END {
      used=total-avail
      if (total > 0) {
        printf "%.1f GiB / %.1f GiB", used/1048576, total/1048576
      } else {
        printf "Unknown"
      }
    }
  ' /proc/meminfo 2>/dev/null
}

cpu_text() {
  if command -v lscpu >/dev/null 2>&1; then
    lscpu | awk -F: '/Model name/ { gsub(/^[ \t]+/, "", $2); print $2; exit }'
    return
  fi
  awk -F: '/model name/ { gsub(/^[ \t]+/, "", $2); print $2; exit }' /proc/cpuinfo 2>/dev/null
}

gpu_text() {
  if command -v lspci >/dev/null 2>&1; then
    lspci | awk -F'[:]' '/VGA|3D|Display/ { sub(/^[ \t]+/, "", $3); print $3; exit }'
  fi
}

theme_text() {
  if command -v gsettings >/dev/null 2>&1; then
    gsettings get org.gnome.desktop.interface gtk-theme 2>/dev/null | tr -d "'"
  fi
}

disk_text() {
  df -h / 2>/dev/null | awk 'NR==2 { printf "%s / %s (%s)", $3, $2, $5 }'
}

resolution_text() {
  local resolution=""
  if command -v xrandr >/dev/null 2>&1; then
    resolution="$(xrandr 2>/dev/null | awk '/ connected/ {
      for (i=1; i<=NF; i++) {
        if ($i ~ /^[0-9]+x[0-9]+\+/) {
          split($i, parts, "+")
          print parts[1]
          exit
        }
      }
    }')"
  fi
  printf '%s' "${resolution:-Unknown}"
}

battery_text() {
  local battery
  for battery in /sys/class/power_supply/BAT*; do
    [[ -d "$battery" ]] || continue
    local capacity status
    capacity="$(cat "$battery/capacity" 2>/dev/null || true)"
    status="$(cat "$battery/status" 2>/dev/null || true)"
    if [[ -n "$capacity" ]]; then
      printf '%s%% %s' "$capacity" "${status:-Unknown}"
      return
    fi
  done
  printf 'Unknown'
}

emit "OS" "$(os_name)"
emit "Host" "$(command_value Unknown hostname)"
emit "Kernel" "$(command_value Unknown uname -r)"
emit "Uptime" "$(uptime_text)"
emit "Packages" "$(package_count)"
emit "Shell" "${SHELL:-Unknown}"
emit "Desktop" "${XDG_CURRENT_DESKTOP:-${DESKTOP_SESSION:-Unknown}}"
emit "Session" "${XDG_SESSION_TYPE:-Unknown}"
emit "Resolution" "$(resolution_text)"
emit "CPU" "$(cpu_text)"
emit "GPU" "$(gpu_text || true)"
emit "Memory" "$(memory_text)"
emit "Disk" "$(disk_text)"
emit "Battery" "$(battery_text)"
emit "Theme" "$(theme_text || true)"
emit "Terminal" "${TERM_PROGRAM:-${TERM:-Unknown}}"
