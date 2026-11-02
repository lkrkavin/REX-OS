# REX OS Build Instructions

## Build Environment

### Prerequisites
- Linux environment (Debian/Ubuntu/Fedora)
- Docker (recommended for reproducibility)
- 50GB+ free disk space
- Internet connection for package downloads

### Quick Build (Docker)
```bash
# From project root
docker build -t rex-os-builder -f build/Dockerfile .

docker run --rm \
  -v $(pwd)/isos:/output \
  -v $(pwd)/build:/build \
  rex-os-builder
```

## Manual Build Process

### 1. Install Build Tools
```bash
# Debian/Ubuntu
sudo apt update
sudo apt install -y \
  live-build \
  git \
  squashfs-tools \
  xorriso \
  grub-efi-ia32 \
  grub-efi-amd64 \
  mtools

# Fedora
sudo dnf install -y \
  livecd-tools \
  git \
  squashfs-tools \
  xorriso \
  grub2-efi-ia32 \
  grub2-efi-x64 \
  mtools
```

### 2. Clone REX OS Build Repository
```bash
git clone https://github.com/rex-os/rex-os.git
cd rex-os
```

### 3. Run Live Build
```bash
# Using included script
./build/build-rex-os.sh

# Or manual live-build
lb config \
  --distribution bookworm \
  --architecture amd64 \
  --binary-images iso-hybrid \
  --debian-installer false \
  --archive-areas "main contrib non-free"

sudo lb build
```

## Docker Build Method

### Build Script
```bash
#!/bin/bash
# build/build-rex-os.sh

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$PROJECT_DIR")"

echo "Building REX OS 0.1.0..."

# Create output directory
mkdir -p "$ROOT_DIR/isos"

# Build using live-build
sudo lb build

# Move ISO to output
mv live-image-amd64.hybrid.iso "$ROOT_DIR/isos/REX-OS-0.1.0-amd64.iso"

# Generate checksum
cd "$ROOT_DIR/isos"
sha256sum REX-OS-0.1.0-amd64.iso > REX-OS-0.1.0-amd64.iso.sha256

echo "Build complete!"
echo "ISO: $ROOT_DIR/isos/REX-OS-0.1.0-amd64.iso"
echo "Checksum: $ROOT_DIR/isos/REX-OS-0.1.0-amd64.iso.sha256"
```

## Build Artifacts

After successful build, you should have:
- `isos/REX-OS-0.1.0-amd64.iso` - Bootable ISO
- `isos/REX-OS-0.1.0-amd64.iso.sha256` - SHA-256 checksum

## ISO Verification

```bash
# Verify checksum
cd isos
sha256sum -c REX-OS-0.1.0-amd64.iso.sha256

# Test ISO (loop mount)
sudo mount -o loop REX-OS-0.1.0-amd64.iso /mnt
ls /mnt
```

## Contributing to Build

### Adding Packages
Edit `build/live-build.conf`:
```
LB_BINARY_INCLUDE="package1 package2 package3"
```

### Custom Themes
Place KDE theme files in:
```
build/config/includes.chroot/usr/share/plasma/desktoptheme/rex/
build/config/includes.chroot/usr/share/wallpapers/rex/
```

### System Services
Place systemd unit files in:
```
build/config/includes.chroot/lib/systemd/system/
```

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/build.yml`):

```yaml
name: Build REX OS

on:
  push:
    tags:
      - 'v*'
  pull_request:
    paths:
      - 'build/**'
      - 'ais/**'
      - 'desktop/**'
      - 'services/**'

jobs:
  build:
    runs-on: ubuntu-latest
    container:
      image: docker.io/debian/bookworm:latest
      options: --privileged

    steps:
    - uses: actions/checkout@v4

    - name: Install dependencies
      run: |
        apt-get update
        apt-get install -y live-build git squashfs-tools xorriso

    - name: Build ISO
      run: |
        cd build
        lb config --distribution bookworm --architecture amd64
        lb build

    - name: Upload artifacts
      uses: actions/upload-artifact@v4
      with:
        name: rex-os-iso
        path: live-image-amd64.hybrid.iso
```

## Troubleshooting Build Issues

### Insufficient Disk Space
- Live build needs ~30GB temporary space
- Clean up with: `sudo lb clean`

### Package Not Found
- Check `build/live-build.conf` for correct package names
- Debian Bookworm package names differ from Ubuntu

### Boot Failure
- Verify ISO integrity: `file REX-OS-0.1.0-amd64.iso`
- Check GRUB configuration in ISO
- Look for `isolinux` or `grub` directory

### Missing Dependencies
```bash
# Check what's installed
lb build 2>&1 | grep "package not found"

# Install missing packages
apt-get install package-name
```

## Advanced Build Options

### Development Build (with debug symbols)
```bash
lb config --debug
```

### Minimal Build (core only)
```bash
# Remove unnecessary packages from LB_BINARY_INCLUDE
```

### Custom Kernel
```bash
# Set in live-build.conf
LB_KERNEL_IMAGE="linux-image-686-pae"  # or custom kernel
```

## Release Process

1. Run final build in clean environment
2. Verify ISO integrity
3. Generate checksums (SHA-256, SHA-512, BLAKE2)
4. Create release on GitHub
5. Publish checksum file separately
6. Test in VM before announcing release