#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly PYINFRA_SPEC="pyinfra>=3.10,<4"

SUDO_KEEPALIVE_PID=""

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

error() {
    log "ERROR: $*"
    exit 1
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

OPTIONS:
    --dry-run        Skip updates and run pyinfra in dry mode
    --skip-update    Skip system package update
    -h, --help       Show this help message

Examples:
    $0                  # Full setup
    $0 --dry-run        # Fast dry-run, no changes applied
    $0 --skip-update    # Setup without the system package update
EOF
}

check_fedora() {
    if [[ ! -f /etc/os-release ]]; then
        error "/etc/os-release not found"
    fi

    if ! grep -q '^ID=fedora' /etc/os-release; then
        error "This script is only supported on Fedora"
    fi

    log "Detected OS: Fedora"
}

# Warm the sudo timestamp and hold it open for the whole deploy, so a long run
# never stalls on a re-prompt against stdout that pyinfra has captured.
start_sudo_keepalive() {
    if ! sudo -v; then
        error "sudo authentication failed"
    fi

    while true; do
        sudo -n true 2> /dev/null || exit 0
        sleep 50
    done &
    SUDO_KEEPALIVE_PID=$!
}

stop_sudo_keepalive() {
    if [[ -n "$SUDO_KEEPALIVE_PID" ]]; then
        kill "$SUDO_KEEPALIVE_PID" 2> /dev/null || true
        SUDO_KEEPALIVE_PID=""
    fi
}

update_system() {
    log "Updating system packages..."
    if ! sudo dnf upgrade --refresh -y; then
        error "Failed to update system packages"
    fi
}

ensure_uv() {
    if command -v uv &> /dev/null; then
        return 0
    fi

    log "Installing uv..."
    if ! sudo dnf install -y uv; then
        error "Failed to install uv"
    fi
}

# Single source of truth for locating pyinfra; uv installs into ~/.local/bin, which
# is not always on PATH for non-login shells.
find_pyinfra() {
    local bin
    bin="$(command -v pyinfra || true)"
    if [[ -z "$bin" && -x "$HOME/.local/bin/pyinfra" ]]; then
        bin="$HOME/.local/bin/pyinfra"
    fi
    printf '%s' "$bin"
}

ensure_pyinfra() {
    local bin
    bin="$(find_pyinfra)"
    if [[ -n "$bin" ]]; then
        log "pyinfra is already installed: $("$bin" --version)"
        return 0
    fi

    # Pinned to the 3.x line the deploy is written against: `_if=` and
    # `did_change`/`will_change` on operation results.
    log "Installing pyinfra..."
    if ! uv tool install "${PYINFRA_SPEC}"; then
        error "Failed to install pyinfra"
    fi
}

ensure_tooling() {
    local dry_run="$1"
    local bin
    bin="$(find_pyinfra)"

    if [[ -n "$bin" ]]; then
        log "pyinfra is already installed: $("$bin" --version)"
        return 0
    fi

    if [[ "$dry_run" == "true" ]]; then
        error "pyinfra is required for --dry-run; install it first (dry-run never installs tools)"
    fi

    ensure_uv
    ensure_pyinfra
}

require_inventory() {
    if [[ ! -f "$SCRIPT_DIR/inventory.py" ]]; then
        error "inventory.py not found; copy inventory.example.py and customize it first"
    fi
}

run_pyinfra() {
    local dry_run="$1"

    local pyinfra_bin
    pyinfra_bin="$(find_pyinfra)"
    if [[ -z "$pyinfra_bin" ]]; then
        error "pyinfra executable not found on PATH or in ~/.local/bin"
    fi

    # deploy.py's include() calls, every files/ and templates/ src, the
    # packages.* imports and config.py all resolve against the CWD, not
    # against the script location. Without this the deploy only works when
    # invoked from its own directory.
    cd "$SCRIPT_DIR" || error "Cannot enter $SCRIPT_DIR"

    local pyinfra_args=(
        inventory.py
        deploy.py
        --sudo
    )

    if [[ "$dry_run" == "true" ]]; then
        pyinfra_args+=(--dry)
        log "Executing deploy in DRY RUN mode..."
    else
        log "Executing deploy..."
    fi

    if ! "$pyinfra_bin" "${pyinfra_args[@]}"; then
        error "pyinfra deploy failed"
    fi
}

main() {
    local skip_update="false"
    local dry_run="false"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h | --help)
                show_usage
                exit 0
                ;;
            --dry-run)
                skip_update="true"
                dry_run="true"
                shift
                ;;
            --skip-update)
                skip_update="true"
                shift
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done

    if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
        error "Run this script as your normal user, not root (it uses sudo where needed)"
    fi

    check_fedora
    require_inventory
    ensure_tooling "$dry_run"

    trap stop_sudo_keepalive EXIT
    start_sudo_keepalive

    if [[ "$skip_update" == "false" ]]; then
        update_system
    else
        log "Skipping system update (--skip-update specified)"
    fi

    run_pyinfra "$dry_run"

    if [[ "$dry_run" == "true" ]]; then
        log "Dry run completed (no changes made)"
    else
        log "System setup completed"
    fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
