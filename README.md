# Bluetooth Messenger
Cross-platform Bluetooth messaging application

## Features
- Send and receive messages via Bluetooth RFCOMM
- Discover nearby Bluetooth devices
- Simple CLI interface
- Message history
- Cross-platform (Linux, Windows, macOS)

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Linux (requires bluez)
sudo apt install bluetooth libbluetooth-dev

# Run
python src/bt_messenger.py --mode server    # Start as server (receive mode)
python src/bt_messenger.py --mode client    # Start as client (send mode)
```

## Usage

### Server Mode (Receive Messages)
```bash
python src/bt_messenger.py --mode server --name "MyPC"
```

### Client Mode (Send Messages)
```bash
python src/bt_messenger.py --mode client --device "AA:BB:CC:DD:EE:FF" --message "Hello!"
```

## Requirements
- Python 3.8+
- PyBlueZ (Linux) or bleak (Cross-platform)
- click
- tabulate
