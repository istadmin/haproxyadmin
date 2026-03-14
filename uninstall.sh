#!/bin/bash
# HAProxy Admin Uninstaller Script
# Must be run with sudo

set -e

# --- Default Configuration ---
DEFAULT_APP_DIR="/opt/haproxy-admin"
SERVICE_NAME="haproxy-admin"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SUDOERS_FILE="/etc/sudoers.d/haproxy-admin"

# --- Colors (safe fallback) ---
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
NC="\033[0m"

# --- Tracking ---
REMOVED_SERVICE="no"
REMOVED_SERVICE_FILE="no"
REMOVED_SUDOERS="no"
REMOVED_APP_DIR="no"

show_help() {
    echo "Usage: sudo ./uninstall.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help    Show this help message and exit"
    echo ""
    echo "This script removes HAProxy Admin application files, systemd service,"
    echo "and sudoers entries created by install.sh."
    exit 0
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_ok() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_err() {
    echo -e "${RED}[ERROR]${NC} $1"
}

confirm() {
    local prompt="$1"
    read -r -p "$prompt [y/N]: " reply
    [[ "$reply" =~ ^[Yy]$ ]]
}

# --- Arg Parsing ---
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
fi

# --- Root Check ---
if [ "$EUID" -ne 0 ]; then
    log_err "Please run this uninstaller as root (using sudo)"
    exit 1
fi

echo "========================================="
echo " HAProxy Admin Uninstaller"
echo "========================================="
echo

log_warn "This will remove the HAProxy Admin application installed by install.sh."
log_warn "It will stop and disable the '${SERVICE_NAME}' service if present."
log_warn "It will also remove the service file, sudoers file, and application directory."
echo

read -r -p "Enter installation directory to remove [${DEFAULT_APP_DIR}]: " APP_DIR
APP_DIR=${APP_DIR:-$DEFAULT_APP_DIR}

echo
echo "You are about to remove:"
echo "  Service name   : ${SERVICE_NAME}"
echo "  Service file   : ${SERVICE_FILE}"
echo "  Sudoers file   : ${SUDOERS_FILE}"
echo "  App directory  : ${APP_DIR}"
echo

if ! confirm "Do you want to proceed with uninstall"; then
    log_info "Uninstallation cancelled."
    exit 0
fi

echo
echo "========================================="
echo " Starting Uninstallation..."
echo "========================================="
echo

# --- Step 1: Stop and disable service ---
log_info "1. Stopping and disabling systemd service..."

if systemctl list-unit-files | grep -q "^${SERVICE_NAME}\.service"; then
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        systemctl stop "${SERVICE_NAME}"
        log_ok "Service '${SERVICE_NAME}' stopped."
    else
        log_info "Service '${SERVICE_NAME}' is not running."
    fi

    if systemctl is-enabled --quiet "${SERVICE_NAME}" 2>/dev/null; then
        systemctl disable "${SERVICE_NAME}"
        log_ok "Service '${SERVICE_NAME}' disabled."
    else
        log_info "Service '${SERVICE_NAME}' is not enabled."
    fi

    REMOVED_SERVICE="yes"
else
    log_info "Service '${SERVICE_NAME}' is not installed."
fi

# --- Step 2: Remove systemd service file ---
log_info "2. Removing systemd service file..."

if [ -f "${SERVICE_FILE}" ]; then
    rm -f "${SERVICE_FILE}"
    log_ok "Removed service file: ${SERVICE_FILE}"
    REMOVED_SERVICE_FILE="yes"
else
    log_info "Service file not found: ${SERVICE_FILE}"
fi

# --- Step 3: Reload systemd ---
log_info "3. Reloading systemd daemon..."
systemctl daemon-reload
systemctl reset-failed || true
log_ok "Systemd daemon reloaded."

# --- Step 4: Remove sudoers file ---
log_info "4. Removing sudoers configuration..."

if [ -f "${SUDOERS_FILE}" ]; then
    rm -f "${SUDOERS_FILE}"
    log_ok "Removed sudoers file: ${SUDOERS_FILE}"
    REMOVED_SUDOERS="yes"
else
    log_info "Sudoers file not found: ${SUDOERS_FILE}"
fi

# --- Step 5: Remove application directory ---
log_info "5. Removing application directory..."

if [ -d "${APP_DIR}" ]; then
    echo
    du -sh "${APP_DIR}" 2>/dev/null || true
    if confirm "Delete application directory '${APP_DIR}'"; then
        rm -rf "${APP_DIR}"
        log_ok "Removed application directory: ${APP_DIR}"
        REMOVED_APP_DIR="yes"
    else
        log_warn "Skipped deletion of application directory: ${APP_DIR}"
    fi
else
    log_info "Application directory not found: ${APP_DIR}"
fi

# --- Final Summary ---
echo
echo "========================================="
echo " Uninstallation Summary"
echo "========================================="
echo "Service handled        : ${REMOVED_SERVICE}"
echo "Service file removed   : ${REMOVED_SERVICE_FILE}"
echo "Sudoers file removed   : ${REMOVED_SUDOERS}"
echo "App directory removed  : ${REMOVED_APP_DIR}"
echo

if systemctl list-unit-files | grep -q "^${SERVICE_NAME}\.service"; then
    log_warn "The service unit still appears to exist in systemd."
else
    log_ok "The service unit no longer exists in systemd."
fi

echo
echo "Further steps you may want to do:"
echo "1. Verify the service is gone:"
echo "   systemctl status ${SERVICE_NAME}"
echo
echo "2. Check whether port 8080 is still being used by anything else:"
echo "   ss -ltnp | grep :8080"
echo
echo "3. If you had HAProxy or Nginx proxy rules pointing to this app,"
echo "   review and remove those manually if no longer needed."
echo
echo "4. If you skipped deleting the app directory, you can remove it later with:"
echo "   sudo rm -rf ${APP_DIR}"
echo

log_ok "HAProxy Admin uninstall process completed."