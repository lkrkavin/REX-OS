# REX OS 0.1.0 Testing Guide

## ⚠️ Important Notice

This is a **release candidate** (0.1.0-rc1). It is not production-ready but is functional enough for testing core features.

## Quick Start

### Virtual Machine Testing (Recommended)

1. **Download the ISO**
   ```
   REX-OS-0.1.0-amd64.iso
   SHA256: [checksum provided with release]
   ```

2. **Create a VM** (VirtualBox, VMware, or QEMU)
   ```bash
   # QEMU/KVM example
   qemu-system-x86_64 \
     -m 4G \
     -smp 2 \
     -drive file=REX-OS-0.1.0-amd64.iso,media=cdrom \
     -drive file=rex-os-disk.qcow2,format=qcow2 \
     -netdev user,id=net0,forward=... \
     -device virtio-net,netdev=net0
   ```

3. **VMware/VirtualBox Settings**
   - RAM: 4GB minimum (8GB recommended)
   - CPU: 2 cores minimum
   - Storage: 20GB virtual disk
   - Network: NAT or Bridged

### Live Mode Testing

The ISO boots into **Live Mode** by default. No installation or disk modification occurs.

1. Select "Start REX OS" from boot menu
2. Wait for desktop to appear (30-60 seconds)
3. Complete the **REX Welcome & Personalization Setup**
4. Explore the desktop environment
5. Press `Ctrl+Alt+F2` to access terminal if needed

### Installation (Optional)

To install to disk:
1. Click the "Install REX OS" icon on the desktop
2. Follow the installer prompts
3. **Never formats existing partitions without explicit confirmation**
4. Choose "Something else" for custom partitioning

## Feature Testing Checklist

### ✅ Core Desktop (Required)
- [ ] Desktop boots to REX Plasma environment
- [ ] Top bar appears with REX logo
- [ ] Floating dock is visible
- [ ] Wallpapers load correctly
- [ ] Theme applies (dark graphite/cyan)

### ✅ First-Startup Personalization (Required)
- [ ] REX Welcome appears on first boot
- [ ] Language selection works (EN, Tamil, Hindi)
- [ ] Profile creation completes
- [ ] Experience level selection saves
- [ ] Communication style preference applies
- [ ] Theme/Wallpaper preview works
- [ ] AI preferences are recorded

### ✅ Profile System (Required)
- [ ] Multiple user accounts supported
- [ ] Profile switching works
- [ ] Preferences persist across reboots
- [ ] User memory is separate per account

### ✅ AI Core Foundation (Required)
- [ ] AI Core starts automatically
- [ ] Local AI works (when Ollama present)
- [ ] Fallback responses work
- [ ] Intelligence pipeline processes queries

### ✅ REX Robot Assistant (Required)
- [ ] Robot widget appears on desktop
- [ ] Can drag to different positions
- [ ] State changes appropriately:
  - [ ] Idle (normal appearance)
  - [ ] Listening (eyes pulsing blue-green)
  - [ ] Thinking (purple eyes)
- [ ] Can be minimized/hidden

### ✅ Control Center (Required)
- [ ] Can be opened from top bar
- [ ] Network controls functional
- [ ] Display settings accessible
- [ ] Audio controls responsive
- [ ] Privacy settings accessible
- [ ] Account management works
- [ ] Update check functions

### ✅ REX Remote (Recommended)
- [ ] Server starts automatically
- [ ] Port 8765 open on localhost
- [ ] Can connect via WebSocket from phone
- [ ] System status streaming works
- [ ] Process list displays
- [ ] Screen capture works (if mss available)

### ✅ Security (Required)
- [ ] AppArmor profiles loaded
- [ ] Firewall (ufw) active
- [ ] Guest mode available
- [ ] No unauthenticated remote ports

## Testing Network Functionality

### Local Network Testing
```bash
# From another device on same network
# Find laptop IP:
ip addr show | grep inet

# Test connection (replace IP):
nc -zv 192.168.1.100 8765
```

### Cross-Network Testing (Requires Cloud Relay)
1. Enable REX Remote in Control Center
2. Pair devices using PIN or QR code
3. Test from external network
4. Note: Requires relay server access

## Testing AI Features

### Local AI (if Ollama installed)
```bash
# Install Ollama if needed
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull qwen3:0.6b

# Test AI
ollama run qwen3:0.6b "Hello from REX!"
```

### Internet-Based AI (requires API key)
1. Go to Control Center → AI Settings
2. Enter your API key (OpenAI, Anthropic, or Google)
3. Test connectivity
4. Note: API keys are stored locally, never transmitted

## Testing REX Remote Mobile App

### Prerequisites
- Android phone with app or modern browser
- Laptop running REX OS
- Both on same network (or relay enabled)

### Test Scenarios
1. **Monitor Mode**
   - Open app, connect to laptop
   - View system dashboard
   - Check process list
   - Receive notifications

2. **Interactive Mode**
   - Switch to Interactive Control
   - Move mouse cursor
   - Click on screen elements
   - Type text input
   - Test keyboard shortcuts

3. **Task Monitoring**
   - Start a long task (e.g., file copy)
   - Monitor progress from phone
   - Receive completion notification
   - Check task history

4. **File Transfer**
   - Upload file from phone to laptop
   - Download file from laptop to phone
   - Cancel transfers
   - View transfer history

## Known Limitations (0.1.0-rc1)

### AI Features
- Cloud AI requires API key setup
- Local AI needs model installed via Ollama
- Voice recognition works best with clear audio
- Tamil/Hindi support is experimental

### REX Remote
- Screen capture requires `mss` and `opencv`
- Wayland may need additional X11 compatibility
- Cross-network requires relay server
- Full-screen remote viewing not yet optimized

### Desktop Environment
- Some KDE Plasma widgets may have visual glitches
- Theme is work-in-progress
- Dock animations optimized for modern GPUs

### Security
- Full-device encryption requires disk preparation
- Some advanced AppArmor profiles not yet written
- Firewall rules subject to change

## Bug Reporting

### How to Report Issues
1. Open Control Center → Feedback
2. Or use terminal:
```bash
# Gather system info
uname -a > rex-system-info.txt
cat /etc/os-release >> rex-system-info.txt
journalctl -b -50 >> rex-system-info.txt

# Attach logs
ls -la /var/log/rex/
```

### What Information to Include
- REX OS version
- Hardware specifications
- Steps to reproduce
- Expected vs actual behavior
- Terminal output or logs
- Screenshot if UI bug

## System Requirements

### Minimum
- CPU: Intel/AMD 64-bit, 2 cores
- RAM: 4GB
- Storage: 20GB
- Graphics: Any with 3D acceleration

### Recommended
- CPU: Modern quad-core
- RAM: 8GB
- Storage: 40GB SSD
- Graphics: Modern integrated GPU

### Tested Configurations
- AMD Ryzen 5 + Integrated Graphics
- Intel Core i5 + Iris Xe
- 8GB RAM, 256GB SSD

## Performance Expectations

| Task | Expected Time |
|------|---------------|
| Boot to desktop | 15-30 seconds |
| AI response (local) | 1-3 seconds |
| AI response (cloud) | 0.5-2 seconds |
| Screen capture | <500ms |
| Process list update | <200ms |
| File transfer (WiFi) | 50-100 MB/s |

## Troubleshooting

### Black Screen on Boot
```bash
# Try nomodeset boot parameter
# At GRUB menu, press 'e' to edit
# Add nomodeset to kernel parameters
```

### No Internet
```bash
# Check network manager
nmcli device status

# Restart networking
sudo systemctl restart NetworkManager
```

### AI Not Responding
```bash
# Check if daemon is running
systemctl status rex-daemon

# Restart if needed
sudo systemctl restart rex-daemon

# Check Ollama (if using)
ollama list
```

### REX Remote Connection Failed
```bash
# Check if server is listening
ss -tlnp | grep 8765

# Check firewall
sudo ufw status 8765

# Test locally
curl http://127.0.0.1:8765
```

## Feedback

We want your feedback! Please test:
1. Boot speed and reliability
2. Onboarding experience
3. AI accuracy and helpfulness
4. Remote access stability
5. Security and privacy controls
6. Overall user experience

Your testing helps make REX OS better for everyone.

---

**REX OS 0.1.0-rc1** | Not for production use | Report issues to: feedback@rex-os.org