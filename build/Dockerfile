# Dockerfile for REX OS Build
# Build with: docker build -t rex-os-builder .

FROM debian:bookworm-slim

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y \
    # Live build tools
    live-build \
    live-boot \
    live-config \

    # System utilities
    git \
    squashfs-tools \
    xorriso \
    rsync \
    wget \
    curl \
    ca-certificates \

    # Boot tools
    grub-efi-ia32 \
    grub-efi-amd64 \
    mtools \

    # Python for post-processing
    python3 \
    python3-pip \

    # Housekeeping
    && rm -rf /var/lib/apt/lists/*

# Create build directory
WORKDIR /build

# Copy build configuration
COPY live-build.conf /build/
COPY build-rex-os.sh /build/

# Copy include files
COPY includes/ /build/config/includes.chroot/

# Make build script executable
RUN chmod +x /build/build-rex-os.sh

# Default command
CMD ["/build/build-rex-os.sh"]