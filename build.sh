#!/usr/bin/env bash

set -euo pipefail

APP_NAME="AudioFiles"
SCRIPT="audiofiles.py"

detect_arch() {
    ARCH="$(uname -m)"
    case "$ARCH" in
        x86_64|amd64)  ARCH="amd64" ;;
        aarch64|arm64) ARCH="arm64" ;;
        *)
            echo "Error: unsupported architecture '$ARCH'" >&2
            exit 1
            ;;
    esac
}

detect_platform() {
    local os
    os="$(uname -s)"

    # Allow override via BUILD_TARGET env var
    if [[ -n "${BUILD_TARGET:-}" ]]; then
        PLATFORM="$BUILD_TARGET"
        return
    fi

    case "$os" in
        Darwin) PLATFORM="macos" ;;
        Linux)
            # WSL reports as Linux but targets Windows
            if grep -qi microsoft /proc/version 2>/dev/null; then
                PLATFORM="windows"
            else
                PLATFORM="linux"
            fi
            ;;
        MINGW*|MSYS*|CYGWIN*|Windows_NT) PLATFORM="windows" ;;
        *)
            echo "Error: unsupported platform '$os'" >&2
            exit 1
            ;;
    esac
}

configure_flags() {
    BUNDLE_MODE="--onefile"
    EXTRA_FLAGS=()

    case "$PLATFORM" in
        macos)
            BUNDLE_MODE="--onedir"
            EXTRA_FLAGS=(
                --windowed
                --osx-bundle-identifier "com.audiofiles.app"
            )
            ;;
        windows)
            EXTRA_FLAGS=(
                --windowed
            )
            ;;
        linux)
            ;;
        *)
            echo "Error: invalid BUILD_TARGET '${BUILD_TARGET:-}' (use linux, macos, or windows)" >&2
            exit 1
            ;;
    esac
}

build() {
    # macOS uses plain APP_NAME so the menu bar displays correctly;
    # Linux/Windows use a suffixed name for the single-file executable.
    local name
    case "$PLATFORM" in
        macos) name="$APP_NAME" ;;
        *)     name="${APP_NAME}-${PLATFORM}-${ARCH}" ;;
    esac

    echo "Building ${name} (${PLATFORM}/${ARCH}) ..."

    uv run --extra dev pyinstaller \
        "$BUNDLE_MODE" \
        --noconfirm \
        --hidden-import=mutagen \
        --hidden-import=PIL \
        --name "$name" \
        "${EXTRA_FLAGS[@]}" \
        "$SCRIPT"

    rename_artifact "$name"
}

rename_artifact() {
    local name="$1"

    case "$PLATFORM" in
        macos)
            echo "Done: dist/${name}.app"
            ;;
        windows)
            rm -f "dist/${APP_NAME}.exe"
            mv "dist/${name}.exe" "dist/${APP_NAME}.exe"
            echo "Done: dist/${APP_NAME}.exe"
            ;;
        linux)
            rm -f "dist/${APP_NAME}"
            mv "dist/${name}" "dist/${APP_NAME}"
            echo "Done: dist/${APP_NAME}"
            ;;
    esac
}

main() {
    detect_arch
    detect_platform
    configure_flags
    build
}

main "$@"
