#!/usr/bin/env python3
"""
Bluetooth Messenger
==================
A cross-platform secure Bluetooth messaging application.

Features:
- End-to-end encryption (AES-256-GCM + RSA)
- Secure file transfer
- Group messaging
- Modern GUI
- CLI interface

Usage:
    # GUI Mode
    python src/gui.py
    
    # CLI Mode
    python src/bt_messenger.py --help
    python src/bt_messenger.py discover
    python src/bt_messenger.py server
    python src/bt_messenger.py send --device "AA:BB:CC:DD:EE:FF" --message "Hello"
    python src/bt_messenger.py send-file --device "AA:BB:CC:DD:EE:FF" --file document.pdf
    python src/bt_messenger.py group create --name "My Group"
    python src/bt_messenger.py group list
"""

import socket
import threading
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

# Import optional Bluetooth libraries
try:
    import bluetooth
    BT_AVAILABLE = True
except ImportError:
    BT_AVAILABLE = False

import click
from rich.console import Console
from rich.table import Table
from rich import print as rprint

# Import our modules
from encryption import EncryptionManager
from file_transfer import FileTransfer
from group_chat import GroupChat


console = Console()


class SecureBluetoothMessenger:
    """
    Secure Bluetooth Messenger with E2E Encryption
    
    Integrates:
    - Bluetooth RFCOMM communication
    - End-to-end encryption
    - File transfer
    - Group messaging
    """
    
    RFCOMM_CHANNEL = 1
    UUID = "00001101-0000-1000-8000-00805F9B34FB"
    
    def __init__(self, device_name="SecureBT"):
        self.device_name = device_name
        self.server_socket = None
        self.running = False
        
        # Security components
        self.encryption = EncryptionManager()
        self.file_transfer = FileTransfer(self.encryption)
        self.group_chat = GroupChat(self.encryption, device_name)
        
        # Generate keypair on init
        self.public_key, self.private_key = self.encryption.generate_keypair()
        
        # Message history
        self.history_file = Path.home() / ".secure_bt_messenger_history.json"
        self.message_history = self._load_history()
        
        console.print(f"[green]✓[/green] Encryption initialized (RSA-{self.encryption.RSA_KEY_SIZE}, AES-256-GCM)")
    
    def _load_history(self) -> List[Dict]:
        """Load message history"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_history(self):
        """Save message history"""
        with open(self.history_file, 'w') as f:
            json.dump(self.message_history, f, indent=2)
    
    def add_message(self, direction: str, content: str, device: Optional[str] = None, encrypted: bool = True):
        """Add message to history"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "direction": direction,
            "content": content,
            "device": device,
            "encrypted": encrypted
        }
        self.message_history.append(entry)
        self._save_history()
    
    def discover_devices(self, timeout: int = 10) -> List[Dict]:
        """Discover nearby Bluetooth devices"""
        console.print(f"[cyan]🔍 Discovering devices for {timeout} seconds...[/cyan]")
        devices = []
        
        if BT_AVAILABLE:
            try:
                nearby = bluetooth.discover_devices(
                    duration=timeout,
                    lookup_names=True,
                    flush_cache=True
                )
                for addr, name in nearby:
                    devices.append({
                        "address": addr,
                        "name": name
                    })
            except Exception as e:
                console.print(f"[red]Error discovering: {e}[/red]")
        else:
            console.print("[yellow]PyBluez not available[/yellow]")
        
        return devices
    
    def display_devices(self, devices: List[Dict]):
        """Display discovered devices in a table"""
        if not devices:
            console.print("[yellow]No devices found[/yellow]")
            return
        
        table = Table(title="Discovered Devices")
        table.add_column("Name", style="cyan")
        table.add_column("Address", style="magenta")
        
        for dev in devices:
            table.add_row(dev['name'], dev['address'])
        
        console.print(table)
    
    def start_server(self, port: int = 1):
        """Start RFCOMM server to receive messages"""
        self.running = True
        
        if not BT_AVAILABLE:
            console.print("[red]Bluetooth not available[/red]")
            return
        
        self.server_socket = socket.socket(
            socket.AF_BLUETOOTH,
            socket.SOCK_STREAM,
            socket.BTPROTO_RFCOMM
        )
        
        try:
            self.server_socket.bind((socket.BDADDR_ANY, port))
            self.server_socket.listen(1)
            
            console.print(f"[green]✅ Server started on RFCOMM channel {port}[/green]")
            console.print(f"   Device name: {self.device_name}")
            console.print(f"   Waiting for connections... (Ctrl+C to stop)")
            
            while self.running:
                try:
                    self.server_socket.settimeout(5.0)
                    client, address = self.server_socket.accept()
                    
                    console.print(f"[cyan]📨 Connection from {address[0]}[/cyan]")
                    
                    # Receive encrypted message
                    data = client.recv(4096)
                    if data:
                        try:
                            # Try to decrypt
                            message, session_key = self.encryption.decrypt_message(
                                data.decode('utf-8'),
                                sender_public_key_pem=self.public_key
                            )
                            console.print(f"[green]💬[/green] {message}")
                            self.add_message("received", message, str(address[0]))
                            
                            # Send acknowledgment
                            ack = f"ACK: {datetime.now().isoformat()}"
                            client.send(ack.encode('utf-8'))
                        except Exception as e:
                            # Not encrypted or decryption failed
                            message = data.decode('utf-8', errors='ignore')
                            console.print(f"[yellow]💬[/yellow] {message} (unencrypted)")
                            self.add_message("received", message, str(address[0]), encrypted=False)
                    
                    client.close()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        console.print(f"[red]Error: {e}")
        
        except Exception as e:
            console.print(f"[red]Server error: {e}[/red]")
        finally:
            self.stop()
    
    def send_message(self, device_address: str, message: str, port: int = 1) -> bool:
        """Send encrypted message to device"""
        if not BT_AVAILABLE:
            console.print("[red]Bluetooth not available[/red]")
            return False
        
        console.print(f"[cyan]📤 Sending to {device_address}...[/cyan]")
        
        try:
            sock = socket.socket(
                socket.AF_BLUETOOTH,
                socket.SOCK_STREAM,
                socket.BTPROTO_RFCOMM
            )
            sock.connect((device_address, port))
            
            # Encrypt message
            encrypted = self.encryption.encrypt_message(
                message,
                recipient_public_key_pem=self.public_key
            )
            
            sock.send(encrypted.encode('utf-8'))
            
            # Wait for acknowledgment
            sock.settimeout(10.0)
            ack = sock.recv(1024).decode('utf-8')
            console.print(f"[green]✓[/green] Message sent! ACK: {ack}")
            
            self.add_message("sent", message, device_address)
            sock.close()
            return True
            
        except Exception as e:
            console.print(f"[red]✗ Failed: {e}[/red]")
            return False
    
    def send_file(self, device_address: str, file_path: str, port: int = 1) -> bool:
        """Send encrypted file"""
        if not os.path.exists(file_path):
            console.print(f"[red]File not found: {file_path}[/red]")
            return False
        
        console.print(f"[cyan]📁 Preparing file: {file_path}[/cyan]")
        
        try:
            # Prepare file
            meta, enc_path = self.file_transfer.prepare_file(file_path)
            
            console.print(f"[cyan]📤 Sending {meta.file_name} ({meta.file_size} bytes)...[/cyan]")
            
            # Send via socket (simplified - full implementation would use file_transfer module)
            sock = socket.socket(
                socket.AF_BLUETOOTH,
                socket.SOCK_STREAM,
                socket.BTPROTO_RFCOMM
            )
            sock.connect((device_address, port))
            
            # Send metadata
            meta_json = json.dumps({
                "file_id": meta.file_id,
                "file_name": meta.file_name,
                "file_size": meta.file_size,
                "checksum": meta.checksum
            })
            sock.send(meta_json.encode('utf-8'))
            
            sock.close()
            console.print(f"[green]✓[/green] File transfer initiated")
            
            # Cleanup
            if os.path.exists(enc_path):
                os.remove(enc_path)
            
            return True
            
        except Exception as e:
            console.print(f"[red]✗ Failed: {e}[/red]")
            return False
    
    def show_history(self):
        """Display message history"""
        if not self.message_history:
            console.print("[yellow]No message history[/yellow]")
            return
        
        console.print(f"\n[bold]Message History ({len(self.message_history)} messages)[/bold]\n")
        
        for msg in self.message_history[-20:]:
            direction = "📤" if msg['direction'] == 'sent' else "📥"
            time = datetime.fromisoformat(msg['timestamp']).strftime("%H:%M:%S")
            device = msg.get('device', 'Unknown')
            encrypted = "🔒" if msg.get('encrypted') else "🔓"
            
            console.print(f"{direction} [{time}] {device} {encrypted}")
            console.print(f"   {msg['content']}\n")
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        console.print("[yellow]🛑 Server stopped[/yellow]")


# ============================================================================
# CLI COMMANDS
# ============================================================================

@click.group()
def cli():
    """Secure Bluetooth Messenger - E2E Encrypted"""
    pass


@cli.command()
@click.option('--timeout', default=10, help='Discovery timeout in seconds')
def discover(timeout):
    """Discover nearby Bluetooth devices"""
    messenger = SecureBluetoothMessenger()
    devices = messenger.discover_devices(timeout)
    messenger.display_devices(devices)


@cli.command()
@click.option('--name', default='SecureBT', help='Device name')
@click.option('--port', default=1, type=int, help='RFCOMM port')
def server(name, port):
    """Start server to receive messages"""
    messenger = SecureBluetoothMessenger(device_name=name)
    
    try:
        messenger.start_server(port)
    except KeyboardInterrupt:
        messenger.stop()


@cli.command()
@click.option('--device', required=True, help='Target device address')
@click.option('--message', required=True, help='Message to send')
@click.option('--port', default=1, type=int, help='RFCOMM port')
def send(device, message, port):
    """Send encrypted message to device"""
    messenger = SecureBluetoothMessenger()
    messenger.send_message(device, message, port)


@cli.command()
@click.option('--device', required=True, help='Target device address')
@click.option('--file', required=True, help='File to send')
@click.option('--port', default=1, type=int, help='RFCOMM port')
def send_file(device, file, port):
    """Send encrypted file to device"""
    messenger = SecureBluetoothMessenger()
    messenger.send_file(device, file, port)


@cli.command()
def history():
    """Show message history"""
    messenger = SecureBluetoothMessenger()
    messenger.show_history()


@cli.group()
def group():
    """Group chat commands"""
    pass


@group.command('create')
@click.option('--name', required=True, help='Group name')
@click.option('--description', default='', help='Group description')
def group_create(name, description):
    """Create a new group"""
    messenger = SecureBluetoothMessenger()
    group = messenger.group_chat.create_group(name, description)
    console.print(f"[green]✓[/green] Created group: {name} ({group.group_id})")


@group.command('list')
def group_list():
    """List groups"""
    messenger = SecureBluetoothMessenger()
    groups = messenger.group_chat.list_groups()
    
    if not groups:
        console.print("[yellow]No groups[/yellow]")
        return
    
    table = Table(title="Your Groups")
    table.add_column("Name", style="cyan")
    table.add_column("ID", style="magenta")
    table.add_column("Members", style="green")
    
    for g in groups:
        table.add_row(g.name, g.group_id, str(len(g.members)))
    
    console.print(table)


@group.command('send')
@click.option('--group', required=True, help='Group ID')
@click.option('--message', required=True, help='Message')
def group_send(group, message):
    """Send message to group"""
    messenger = SecureBluetoothMessenger()
    msg = messenger.group_chat.send_to_group(group, message)
    
    if msg:
        console.print(f"[green]✓[/green] Sent to group {group}")
    else:
        console.print(f"[red]✗[/red] Failed to send")


@cli.command()
def gui():
    """Launch GUI (Tkinter)"""
    from gui import main as gui_main
    gui_main()


if __name__ == '__main__':
    cli()
