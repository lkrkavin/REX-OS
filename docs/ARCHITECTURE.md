# REX OS Architecture

## Overview

REX OS is a modular, AI-powered operating system built on Debian with KDE Plasma as the desktop environment. This document describes the architecture and component relationships.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           REX OS Desktop                              │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐              │
│  │ REX Control  │  │ REX Robot    │  │ Application Hub  │              │
│  │ Center       │  │ Assistant    │  │ (OMNI)           │              │
│  └──────────────┘  └──────────────┘  └──────────────────┘              │
├─────────────────────────────────────────────────────────────────────────┤
│                    Universal Intelligence Engine                        │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐              │
│  │ Language     │  │ Intention    │  │ Memory System    │              │
│  │ Detection    │  │ Understanding│  │                  │              │
│  └──────────────┘  └──────────────┘  └──────────────────┘              │
├─────────────────────────────────────────────────────────────────────────┤
│                         AI Core Layer                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐              │
│  │ Ollama       │  │ Local Models │  │ Cloud Providers  │              │
│  │ Provider     │  │ (llama.cpp)  │  │ (OpenAI, etc.)   │              │
│  └──────────────┘  └──────────────┘  └──────────────────┘              │
├─────────────────────────────────────────────────────────────────────────┤
│                    Device Ecosystem (CONNECT)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐              │
│  │ Windows      │  │ Android      │  │ macOS            │              │
│  │ Companion    │  │ Remote       │  │ Companion        │              │
│  └──────────────┘  └──────────────┘  └──────────────────┘              │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### 1. AI Core (`ais/ai_core.py`)

**Purpose**: Centralized AI service with provider adapters

**Key Features**:
- Provider abstraction layer (Ollama, llama.cpp, OpenAI, Anthropic, Google)
- Local-first operation with offline fallback
- Model capability detection
- Streaming response support

**Dependencies**: Python 3.14+, FastAPI, SQLite

### 2. Universal Intelligence Engine (`ais/intelligence_pipeline.py`)

**Purpose**: Understand user intent and execute tasks

**Pipeline Stages**:
1. Input reception
2. Language detection (EN, Tamil, Hindi, Tanglish, Spanish, etc.)
3. Intent understanding
4. Context interpretation
5. Input normalization
6. Task decomposition
7. Capability identification
8. Permission checking
9. Tool selection
10. Operation execution
11. Result verification
12. Natural explanation generation

### 3. User Memory System (`ais/user_memory.py`)

**Purpose**: Store and retrieve user preferences, context, and history

**Data Stores**:
- User profiles and preferences
- Memory entries (context, instructions)
- Conversation history
- Task history
- Device registry
- Project tracking

### 4. REX Desktop Environment (`desktop/`)

**Purpose**: Customized KDE Plasma environment

**Components**:
- REX theme (Deep graphite, cyan highlights)
- REX Robot Assistant
- Control Center
- Top bar with integrated status
- Floating dock with animations

### 5. REX Control Center (`components/`)

**Purpose**: System configuration and management

**Categories**:
- Display & Screen
- Network (Wi-Fi, Bluetooth)
- Audio
- Notifications
- Privacy & Security
- Accounts & Profiles
- Devices
- Updates
- Power & Shutdown
- Accessibility

### 6. REX Robot Assistant (`components/rex_robot.py`)

**Purpose**: Visual AI companion

**States**:
- Idle (robot at rest)
- Listening (microphone active, eyes pulsing)
- Thinking (processing request)
- Speaking (TTS active)
- Executing (action in progress)
- Permission (awaiting user approval)
- Error (something went wrong)
- Offline (no AI connectivity)

**Features**:
- Draggable, resizable
- Position persistence
- Dock/minimize/hiding modes
- Qt-based smooth animations

### 7. REX Voice System (`voice/`)

**Purpose**: Voice interaction

**Components**:
- Speech recognition (Google Web Speech API, Vosk for offline)
- Text-to-speech (espeak-ng, pyttsx3)
- Wake word detection ("Hey Rex")
- Push-to-talk mode
- Voice history

### 8. REX OMNI (`components/omni.py`)

**Purpose**: Universal application discovery and launching

**Support**:
- Native Linux applications
- Flatpak packages
- Web applications
- Windows compatibility (WINE)
- Remote macOS apps (authorized agent)
- Android applications (via Waydroid or Anbox)

### 9. REX CONNECT (`devices/`)

**Purpose**: Secure device ecosystem

**Features**:
- Device discovery and pairing
- End-to-end encryption
- Capability negotiation
- File transfer
- Clipboard sharing
- Device status monitoring

### 10. REX Remote (`services/rex_remote_server.py`)

**Purpose**: Phone-to-computer remote access

**Modes**:
- Monitor Only: View screen, system status, processes
- Interactive Control: Mouse/keyboard control
- Full Remote Desktop: Complete desktop access

**Connectivity**:
- Outbound WebSocket connections
- Cloud relay support
- QR code pairing
- Token-based authentication

### 11. Cybersecurity Academy (`security/`)

**Purpose**: Defensive cybersecurity education

**Beginner Topics**:
- Computer fundamentals
- Linux basics
- Windows security
- Networking fundamentals
- DNS and HTTP/HTTPS
- Cryptography concepts
- Password security
- Digital forensics

**Advanced Workspace**:
- Terminal and diagnostics
- Log analysis
- Configuration auditing
- Network analysis tools
- CTF labs (isolated)
- Secure coding practices

### 12. Windows Companion (`devices/windows_companion.py`)

**Purpose**: Secure Windows integration

**Capabilities**:
- Application launching
- Process inspection
- Service management
- System information
- Registry analysis
- Settings backup/restore
- Rollback support

## Security Architecture

### Threat Model
- **Primary threats**: Remote code execution, privilege escalation, data exfiltration
- **Mitigation**: AppArmor, least privilege, encryption, audit logging

### Key Security Features
1. **AppArmor**: Mandatory access control for applications
2. **nftables**: Stateful firewall with default deny
3. **Secure Boot**: UEFI Secure Boot compatibility
4. **Full-disk encryption**: Optional LUKS encryption
5. **Flatpak sandbox**: Default application isolation
6. **Signed updates**: Package verification
7. **Secret management**: No hardcoded credentials

### Privacy by Design
- Local-first AI processing
- Encrypted device connections
- Auditable access logs
- User-controlled data deletion
- No telemetry without consent

## Data Flow

### Typical User Interaction

```
User Input → Language Detection → Intent Parser → Capability Check
    ↓
Permission Service → Task Decomposition → Tool Executor → AI Response
    ↓
Natural Language Explanation + Verification
```

### AI Processing Flow

```
User Request → NLP Processing → Query Formulation → AI Model
    ↓
Response Parsing → Capability Verification → Action Execution
    ↓
Result Verification → User Feedback
```

## API Layering

### Internal APIs (Unix sockets/Localhost)

1. **AI Core API** (port 8000): `http://127.0.0.1:8000/`
2. **REX Remote** (port 8765): WebSocket for remote control
3. **System Control** (Unix socket): Internal service communication

### External APIs (Secure)

1. **Cloud Relay** (wss://relay.rex-os.org): Authenticated outbound connections
2. **Mobile Companion**: REST/WS over HTTPS

## Configuration

Configuration is stored in:
- System: `/etc/rex/`
- User: `~/.config/rex/`
- Data: `/var/lib/rex/`

Configuration files:
- `rex-daemon.json` - Main service configuration
- `user_memory.json` - User preferences (SQLite database)
- `ai_providers.json` - AI provider settings
- `devices.json` - Paired devices
- `tasks.json` - Running task tracking