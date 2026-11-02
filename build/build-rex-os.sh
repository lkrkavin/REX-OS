#!/bin/bash
# REX OS Build Script
# Builds REX-OS-0.1.0-amd64.iso

set -e

echo "=========================================="
echo "REX OS Build Script v0.1.0"
echo "=========================================="

# Configuration
PROJECT_NAME="REX-OS"
VERSION="0.1.0"
ARCHITECTURE="amd64"
ISO_NAME="${PROJECT_NAME}-${VERSION}-${ARCHITECTURE}.iso"
BUILD_CHROOT="/build/chroot"
OUTPUT_DIR="/build/output"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check if we're root
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root"
fi

# Create output directory
info "Creating output directory..."
mkdir -p "$OUTPUT_DIR"

# Check available disk space
AVAILABLE=$(df / | awk 'NR==2 {print $4}')
if [[ $AVAILABLE -lt 30720000 ]]; then
    error "Insufficient disk space. Need at least 30GB free."
fi

info "Starting live-build configuration..."

# Clean any previous build
lb clean 2>/dev/null || true

# Configure live-build
lb config \
    --distribution bookworm \
    --architecture amd64 \
    --binary-images iso-hybrid \
    --debian-installer false \
    --bootappend-live "boot=live components quiet splash" \
    --archive-areas "main contrib non-free" \
    --linux-flavours amd64 \
    --memtest none \
    --security True \
    --source False \
    --updates False

info "Build configuration complete."

# Check if there are packages to include
if [[ -f /build/live-build.conf ]]; then
    info "Applying live-build configuration..."
    . /build/live-build.conf
fi

info "Starting ISO build (this may take 30-60 minutes)..."

# Build the ISO
if lb build 2>&1 | tee /build/build.log; then
    info "Build completed successfully!"
else
    error "Build failed. Check /build/build.log for details."
fi

# Move ISO to output directory
if [[ -f live-image-amd64.hybrid.iso ]]; then
    mv live-image-amd64.hybrid.iso "${OUTPUT_DIR}/${ISO_NAME}"
    info "ISO created: ${OUTPUT_DIR}/${ISO_NAME}"
else
    error "ISO file not created"
fi

# Generate checksums
info "Generating checksums..."
cd "$OUTPUT_DIR"

sha256sum "$ISO_NAME" > "${ISO_NAME}.sha256"
sha512sum "$ISO_NAME" > "${ISO_NAME}.sha512"
b2sum "$ISO_NAME" > "${ISO_NAME}.blake2" 2>/dev/null || true

info "Checksums generated"

# Calculate ISO size
SIZE=$(du -h "$ISO_NAME" | cut -f1)
info "ISO size: $SIZE"

# Verify ISO integrity
info "Verifying ISO integrity..."
file "$ISO_NAME"

# Create release manifest
cat > "${OUTPUT_DIR}/MANIFEST.txt" << EOF
REX OS Release Manifest
=======================
Version: ${VERSION}
Build Date: $(date -Iseconds)
Architecture: ${ARCHITECTURE}
ISO: ${ISO_NAME}
Size: ${SIZE}

Checksums:
$(cat ${ISO_NAME}.sha256)
$(cat ${ISO_NAME}.sha512 2>/dev/null || echo "SHA-512: not available")

Build System: Debian Live Build 2024
EOF

info "Release manifest created"

# Summary
echo ""
echo "=========================================="
echo "         BUILD COMPLETE ✓"
echo "=========================================="
echo ""
echo "Output files:"
echo "  - ${OUTPUT_DIR}/${ISO_NAME}"
echo "  - ${OUTPUT_DIR}/${ISO_NAME}.sha256"
echo "  - ${OUTPUT_DIR}/${ISO_NAME}.sha512"
echo "  - ${OUTPUT_DIR}/MANIFEST.txt"
echo ""
echo "Next steps:"
echo "  1. Verify checksums: sha256sum -c ${ISO_NAME}.sha256"
echo "  2. Test in VM: qemu-system-x86_64 -m 4G -cdrom ${ISO_NAME}"
echo "  3. Report issues to: feedback@rex-os.org"
echo ""

# Cleanup
info "Cleaning up temporary files..."
lb clean

info "Build process finished successfully!"