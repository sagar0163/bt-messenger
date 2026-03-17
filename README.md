# Bluetooth Messenger Pro
Enterprise-grade secure Bluetooth messaging with end-to-end encryption

## Features
- 🔒 **End-to-End Encryption** - AES-256-GCM + RSA key exchange
- 📁 **Secure File Transfer** - Encrypted file sharing via Bluetooth
- 👥 **Group Messaging** - Multi-device group chats
- 🎨 **GUI Application** - Modern Tkinter interface
- 📱 **Device Discovery** - Find and pair Bluetooth devices
- 💾 **Message History** - Encrypted local storage
- 🔑 **Key Management** - Secure key generation and storage

## Security Features
- **E2E Encryption**: AES-256-GCM for messages
- **Key Exchange**: RSA-2048 / RSA-4096
- **File Encryption**: EncFS-style file encryption
- **Secure Storage**: Encrypted SQLite database
- **Perfect Forward Secrecy**: Session keys rotate per message

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Linux
sudo apt install bluetooth libbluetooth-dev

# Run GUI
python src/gui.py

# Run CLI
python src/bt_messenger.py --help
```

## Quick Start

### GUI Mode
```bash
python src/gui.py
```

### CLI Mode
```bash
# Discover devices
python src/bt_messenger.py discover

# Start server
python src/bt_messenger.py server

# Send message
python src/bt_messenger.py send --device "AA:BB:CC:DD:EE:FF" --message "Hello"

# Send file
python src/bt_messenger.py send-file --device "AA:BB:CC:DD:EE:FF" --file document.pdf
```

## Security Architecture

### Encryption Layers
1. **RSA-2048** - Key exchange (initial)
2. **AES-256-GCM** - Message encryption (per message)
3. **HKDF** - Key derivation
4. **SHA-256** - Message integrity

### Key Management
- Keys stored in encrypted SQLite
- Master password protection
- Auto-key rotation every N messages
- Secure key deletion

## Project Structure
```
bt-messenger/
├── src/
│   ├── bt_messenger.py    # Core messaging
│   ├── encryption.py      # Crypto module
│   ├── file_transfer.py   # Secure file transfer
│   ├── group_chat.py      # Group messaging
│   ├── gui.py            # Tkinter GUI
│   ├── database.py       # Encrypted storage
│   └── key_manager.py    # Key management
├── tests/                # Unit tests
├── docs/                # Documentation
├── requirements.txt
└── README.md
```

## Requirements
- Python 3.9+
- PyBlueZ / bleak
- cryptography
- sqlcipher
- tkinter (built-in)
# Updated
# Update
