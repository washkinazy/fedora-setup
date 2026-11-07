#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly PYINFRA_SPEC="pyinfra>=3.10,<4"
readonly PYINFRA_PYTHON="3.14"

SUDO_KEEPALIVE_PID=""
PYINFRA_BIN=""

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

# Keep sudo credentials alive during the deploy.
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

configure_repository_policy() {
    local policy_file policy_path
    policy_file="$(mktemp)"
    policy_path="/etc/dnf/repos.override.d/99-zz-fedora-setup.repo"
    if ! (cd "$SCRIPT_DIR" && python3 -m packages.repo_policy) > "$policy_file"; then
        rm -f "$policy_file"
        error "Failed to render repository policy"
    fi
    if ! sudo cmp -s "$policy_file" "$policy_path"; then
        log "Configuring package bindings and repository priorities..."
        if ! sudo install -D -o root -g root -m 0644 "$policy_file" "$policy_path"; then
            rm -f "$policy_file"
            error "Failed to install repository policy"
        fi
    fi
    rm -f "$policy_file"
}

# uv installs pyinfra in ~/.local/bin, which may be absent from PATH.
find_pyinfra() {
    local bin
    bin="$(command -v pyinfra || true)"
    if [[ -z "$bin" && -x "$HOME/.local/bin/pyinfra" ]]; then
        bin="$HOME/.local/bin/pyinfra"
    fi
    printf '%s' "$bin"
}

ensure_tooling() {
    local dry_run="$1"
    local version
    PYINFRA_BIN="$(find_pyinfra)"
    if [[ -n "$PYINFRA_BIN" ]] && version="$("$PYINFRA_BIN" --version 2>&1)"; then
        log "pyinfra is already installed: $version"
        return 0
    fi

    if [[ "$dry_run" == "true" ]]; then
        error "A working pyinfra is required for --dry-run; run setup without --dry-run to install or repair it (dry-run never installs tools)"
    fi

    if ! command -v uv &> /dev/null; then
        log "Installing uv..."
        sudo dnf install -y uv || error "Failed to install uv"
    fi

    log "Installing or repairing pyinfra with managed Python ${PYINFRA_PYTHON}..."
    uv python install "$PYINFRA_PYTHON" || error "Failed to install managed Python"
    uv tool install --python "$PYINFRA_PYTHON" --managed-python --force --reinstall \
        "${PYINFRA_SPEC}" || error "Failed to install pyinfra"
    PYINFRA_BIN="$(find_pyinfra)"
    [[ -n "$PYINFRA_BIN" ]] || error "pyinfra executable not found after installation"
    if ! version="$("$PYINFRA_BIN" --version 2>&1)"; then
        error "pyinfra is still unusable at $PYINFRA_BIN: $version"
    fi
    log "pyinfra ready: $version"
}

require_inventory() {
    if [[ ! -f "$SCRIPT_DIR/inventory.py" ]]; then
        error "inventory.py not found; copy inventory.example.py and customize it first"
    fi
}

run_pyinfra() {
    local dry_run="$1"

    # Resolve deployment assets relative to the project directory.
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

    if ! "$PYINFRA_BIN" "${pyinfra_args[@]}"; then
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

    trap stop_sudo_keepalive EXIT
    start_sudo_keepalive

    if [[ "$dry_run" == "false" ]]; then
        configure_repository_policy
    fi
    ensure_tooling "$dry_run"

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
