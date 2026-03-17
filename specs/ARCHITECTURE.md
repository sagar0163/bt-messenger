# Architecture Document: Bluetooth Messenger Pro

## 1. System Overview

Bluetooth Messenger Pro is a Python-based desktop application providing secure peer-to-peer messaging over Bluetooth. The system implements a layered architecture with clear separation between UI, business logic, and security components.

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                     │
│  ┌─────────────────────┐    ┌─────────────────────────────┐│
│  │   GUI (Tkinter)     │    │   CLI (Click/Rich)          ││
│  │     src/gui.py      │    │   src/bt_messenger.py       ││
│  └─────────────────────┘    └─────────────────────────────┘│
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   Business Logic Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │ Message      │  │ Group Chat   │  │ File Transfer      │ │
│  │ Handler      │  │ Manager      │  │ Module             │ │
│  └──────────────┘  └──────────────┘  └────────────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │ Contacts     │  │ Read         │  │ Message Reactions  │ │
│  │ Manager      │  │ Receipts     │  │                    │ │
│  └──────────────┘  └──────────────┘  └────────────────────┘ │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    Security Layer                            │
│  ┌──────────────────┐    ┌────────────────────────────────┐ │
│  │ Encryption       │    │ Key Manager                    │ │
│  │ Module           │    │ - Key generation               │ │
│  │ - AES-256-GCM    │    │ - Key storage                   │ │
│  │ - RSA key exch.  │    │ - Key rotation                  │ │
│  └──────────────────┘    └────────────────────────────────┘ │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    Data Layer                                │
│  ┌──────────────────┐    ┌────────────────────────────────┐ │
│  │ Database         │    │ Bluetooth                      │ │
│  │ (SQLAlchemy +    │    │ (PyBluez / Bleak)              │ │
│  │  SQLCipher)      │    │                                │ │
│  └──────────────────┘    └────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 3. Component Design

### 3.1 User Interface Components

#### GUI (src/gui.py)
- Tkinter-based graphical interface
- Device discovery panel
- Chat window with message display
- File transfer dialog
- Settings and configuration

#### CLI (src/bt_messenger.py)
- Click-based command parsing
- Rich-formatted output
- Commands: discover, server, send, send-file

### 3.2 Business Logic Components

#### Message Handler (src/bt_messenger.py)
- Message composition and parsing
- Message queuing and retry logic
- Delivery confirmation

#### Group Chat (src/group_chat.py)
- Group creation and management
- Multi-cast message distribution
- Member list synchronization

#### File Transfer (src/file_transfer.py)
- File chunking for large files
- Progress tracking
- Resume capability

#### Contacts Manager (src/contacts.py)
- Contact storage and retrieval
- Device address management
- Contact verification

#### Message Reactions (src/message_reactions.py)
- Reaction processing
- Reaction aggregation
- UI update triggers

#### Read Receipts (src/read_receipts.py)
- Read status tracking
- Delivery confirmation
- Timestamp management

#### Typing Indicators (src/typing_indicators.py)
- Real-time typing status
- Timeout handling
- Broadcast mechanism

### 3.3 Security Components

#### Encryption Module (src/encryption.py)
- **AES-256-GCM**: Symmetric encryption for messages
- **RSA-2048/4096**: Asymmetric key exchange
- **HKDF**: Key derivation
- **SHA-256**: Message integrity

#### Key Manager (src/key_manager.py)
- Key pair generation
- Secure key storage (Keyring + SQLCipher)
- Key rotation logic
- Master password management

### 3.4 Data Components

#### Database (src/database.py)
- SQLAlchemy ORM
- SQLCipher encryption
- Message storage
- Contact storage
- Key metadata

#### Bluetooth Adapter
- PyBluez for Linux
- Bleak for cross-platform
- Device discovery
- Connection management

## 4. Data Flow

```
User Input (Message/File)
         │
         ▼
    ┌────────────┐
    │ UI Layer   │ ───▶ Validation
    └────────────┘
         │
         ▼
    ┌────────────┐
    │ Business   │ ───▶ Message Composition
    │ Logic      │ ───▶ Group Routing
    └────────────┘
         │
         ▼
    ┌────────────┐
    │ Encryption │ ───▶ AES Encrypt
    │ Module     │ ───▶ RSA Key Exchange
    └────────────┘
         │
         ▼
    ┌────────────┐
    │ Bluetooth  │ ───▶ Device Connection
    │ Adapter    │ ───▶ Data Transmission
    └────────────┘
         │
         ▼
    ┌────────────┐
    │ Database   │ ───▶ Store Encrypted
    └────────────┘
```

## 5. Security Architecture

### Encryption Layers
1. **RSA-2048/4096**: Initial key exchange
2. **AES-256-GCM**: Message encryption
3. **HKDF**: Session key derivation
4. **SHA-256**: Message integrity verification

### Key Management Flow
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Generate    │────▶│ Encrypt     │────▶│ Store in    │
│ RSA Keys    │     │ with Master │     │ SQLCipher   │
└─────────────┘     │ Password    │     └─────────────┘
                    └─────────────┘
```

### Perfect Forward Secrecy
- Session keys derived per message
- HKDF with unique salt per message
- Previous keys cannot be derived from current key

## 6. Database Schema

### Messages Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| sender | TEXT | Sender device MAC |
| recipient | TEXT | Recipient device MAC |
| encrypted_content | BLOB | AES-encrypted message |
| timestamp | INTEGER | Unix timestamp |
| status | TEXT | sent/delivered/read |

### Contacts Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| device_address | TEXT | Bluetooth MAC |
| display_name | TEXT | Contact name |
| public_key | BLOB | RSA public key |
| last_seen | INTEGER | Last connection |

### Keys Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| device_address | TEXT | Associated device |
| session_key | BLOB | Encrypted session key |
| salt | BLOB | HKDF salt |
| created_at | INTEGER | Key creation time |

---

*Document Version: 1.0*  
*Created: 2026-03-17*
