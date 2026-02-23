#!/usr/bin/env python3
"""
Bluetooth Messenger
==================
A cross-platform Bluetooth messaging application using RFCOMM sockets.

Supports:
- Device discovery
- Send messages to paired devices
- Receive messages from other devices
- Message history
"""

import socket
import threading
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

# Try importing platform-specific Bluetooth libraries
try:
    import bluetooth
    BT_AVAILABLE = True
except ImportError:
    BT_AVAILABLE = False
    print("Warning: PyBlueZ not available. Install with: pip install pybluez")

try:
    import bleak
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False

import click


class BluetoothMessenger:
    """Main Bluetooth Messenger class"""
    
    # RFCOMM channel for serial port profile (SPP)
    RFCOMM_CHANNEL = 1
    UUID = "00001101-0000-1000-8000-00805F9B34FB"  # SPP UUID
    
    def __init__(self, device_name="BTMessenger", history_file=None):
        self.device_name = device_name
        self.server_socket = None
        self.client_socket = None
        self.running = False
        self.history_file = history_file or Path.home() / ".bt_messenger_history.json"
        self.message_history = self._load_history()
    
    def _load_history(self):
        """Load message history from file"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_history(self):
        """Save message history to file"""
        with open(self.history_file, 'w') as f:
            json.dump(self.message_history, f, indent=2)
    
    def add_message(self, direction, message, device=None):
        """Add message to history"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "direction": direction,  # "sent" or "received"
            "message": message,
            "device": device
        }
        self.message_history.append(entry)
        self._save_history()
        return entry
    
    def discover_devices(self, timeout=10):
        """Discover nearby Bluetooth devices"""
        print(f"🔍 Discovering devices for {timeout} seconds...")
        devices = []
        
        if BT_AVAILABLE:
            try:
                nearby_devices = bluetooth.discover_devices(
                    duration=timeout, 
                    lookup_names=True,
                    flush_cache=True
                )
                for addr, name in nearby_devices:
                    devices.append({
                        "address": addr,
                        "name": name
                    })
                    print(f"  📱 {name} ({addr})")
            except Exception as e:
                print(f"Error discovering devices: {e}")
        
        return devices
    
    def start_server(self, port=None):
        """Start RFCOMM server to receive messages"""
        if port is None:
            port = self.RFCOMM_CHANNEL
        
        self.running = True
        
        # Create Bluetooth RFCOMM socket
        self.server_socket = socket.socket(
            socket.AF_BLUETOOTH, 
            socket.SOCK_STREAM, 
            socket.BTPROTO_RFCOMM
        )
        
        try:
            self.server_socket.bind((socket.BDADDR_ANY, port))
            self.server_socket.listen(1)
            print(f"✅ Server started on RFCOMM channel {port}")
            print(f"   Device name: {self.device_name}")
            print(f"   Waiting for connections...")
            
            while self.running:
                try:
                    self.server_socket.settimeout(5.0)
                    client_socket, address = self.server_socket.accept()
                    print(f"📨 Connection from {address[0]}")
                    
                    # Receive message
                    data = client_socket.recv(1024)
                    if data:
                        message = data.decode('utf-8')
                        self.add_message("received", message, str(address[0]))
                        print(f"💬 Received: {message}")
                        
                        # Send acknowledgment
                        ack = f"ACK: Message received at {datetime.now().strftime('%H:%M:%S')}"
                        client_socket.send(ack.encode('utf-8'))
                    
                    client_socket.close()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"Error: {e}")
                        
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.stop()
    
    def send_message(self, device_address, message, port=None):
        """Send message to a Bluetooth device"""
        if port is None:
            port = self.RFCOMM_CHANNEL
        
        if not BT_AVAILABLE:
            print("❌ Bluetooth not available")
            return False
        
        print(f"📤 Sending to {device_address}...")
        
        try:
            # Create client socket
            sock = socket.socket(
                socket.AF_BLUETOOTH, 
                socket.SOCK_STREAM, 
                socket.BTPROTO_RFCOMM
            )
            sock.connect((device_address, port))
            
            # Send message
            sock.send(message.encode('utf-8'))
            print(f"✅ Message sent!")
            
            # Wait for acknowledgment
            sock.settimeout(5.0)
            try:
                ack = sock.recv(1024).decode('utf-8')
                print(f"📬 ACK: {ack}")
            except socket.timeout:
                print("⏳ No acknowledgment received")
            
            self.add_message("sent", message, device_address)
            sock.close()
            return True
            
        except Exception as e:
            print(f"❌ Failed to send: {e}")
            return False
    
    def interactive_send(self):
        """Interactive mode to send messages"""
        print("\n=== Bluetooth Messenger - Interactive Mode ===\n")
        
        # Discover devices
        devices = self.discover_devices()
        
        if not devices:
            print("❌ No devices found. Make sure Bluetooth is enabled.")
            return
        
        print(f"\nFound {len(devices)} device(s)")
        
        # Let user select device
        print("\nSelect a device:")
        for i, dev in enumerate(devices):
            print(f"  {i+1}. {dev['name']} ({dev['address']})")
        
        try:
            choice = int(input("\nEnter number: ")) - 1
            if 0 <= choice < len(devices):
                device = devices[choice]
                message = input("Enter message: ")
                self.send_message(device['address'], message)
            else:
                print("Invalid selection")
        except ValueError:
            print("Please enter a valid number")
    
    def show_history(self):
        """Display message history"""
        if not self.message_history:
            print("No message history")
            return
        
        print(f"\n=== Message History ({len(self.message_history)} messages) ===")
        for msg in self.message_history[-20:]:  # Show last 20
            direction = "📤" if msg['direction'] == 'sent' else "📥"
            time = datetime.fromisoformat(msg['timestamp']).strftime('%H:%M:%S')
            device = msg.get('device', 'Unknown')
            print(f"{direction} [{time}] {device}")
            print(f"   {msg['message']}")
            print()
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        print("🛑 Server stopped")


@click.group()
def cli():
    """Bluetooth Messenger - Send and receive messages via Bluetooth"""
    pass


@cli.command()
@click.option('--name', default='BTMessenger', help='Device name')
@click.option('--port', default=1, type=int, help='RFCOMM port')
def server(name, port):
    """Start server to receive messages"""
    messenger = BluetoothMessenger(device_name=name)
    
    # Handle Ctrl+C
    try:
        messenger.start_server(port)
    except KeyboardInterrupt:
        messenger.stop()


@cli.command()
@click.option('--device', required=True, help='Target device Bluetooth address')
@click.option('--message', required=True, help='Message to send')
@click.option('--port', default=1, type=int, help='RFCOMM port')
def send(device, message, port):
    """Send a message to a Bluetooth device"""
    messenger = BluetoothMessenger()
    messenger.send_message(device, message, port)


@cli.command()
def discover():
    """Discover nearby Bluetooth devices"""
    messenger = BluetoothMessenger()
    messenger.discover_devices()


@cli.command()
def interactive():
    """Interactive mode - discover and send messages"""
    messenger = BluetoothMessenger()
    messenger.interactive_send()


@cli.command()
def history():
    """Show message history"""
    messenger = BluetoothMessenger()
    messenger.show_history()


if __name__ == '__main__':
    cli()
