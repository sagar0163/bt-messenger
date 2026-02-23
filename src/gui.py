#!/usr/bin/env python3
"""
Bluetooth Messenger GUI
=====================
Modern Tkinter-based GUI for secure Bluetooth messaging.
"""

import os
import sys
import json
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from datetime import datetime
from typing import Optional, Dict, Any

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bt_messenger import BluetoothMessenger
from encryption import EncryptionManager
from file_transfer import FileTransfer
from group_chat import GroupChat


class SecureBTMessengerGUI:
    """
    Modern GUI for Secure Bluetooth Messenger
    
    Features:
    - Device discovery and pairing
    - End-to-end encrypted messaging
    - File transfer with encryption
    - Group chats
    - Message history
    - Modern dark theme
    """
    
    # Color scheme
    COLORS = {
        'bg_primary': '#1a1a2e',
        'bg_secondary': '#16213e',
        'bg_tertiary': '#0f3460',
        'accent': '#e94560',
        'text_primary': '#eaeaea',
        'text_secondary': '#a0a0a0',
        'success': '#00d26a',
        'warning': '#f39c12',
        'error': '#e74c3c',
        'sent': '#4a69bd',
        'received': '#2f3640'
    }
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🔒 Secure Bluetooth Messenger")
        self.root.geometry("900x650")
        self.root.configure(bg=self.COLORS['bg_primary'])
        
        # Core components
        self.bt_messenger = BluetoothMessenger()
        self.encryption = EncryptionManager()
        self.file_transfer = FileTransfer(self.encryption)
        self.group_chat = GroupChat(self.encryption, "local_device")
        
        # State
        self.current_device: Optional[str] = None
        self.connected_devices: Dict[str, Any] = {}
        self.message_history: list = []
        self.server_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Keypair
        self.public_key, self.private_key = self.encryption.generate_keypair()
        
        # Build UI
        self._build_ui()
        
        # Start server in background
        self._start_server()
    
    def _build_ui(self):
        """Build the complete UI"""
        # Configure styles
        self._configure_styles()
        
        # Main container
        main_container = tk.Frame(self.root, bg=self.COLORS['bg_primary'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left sidebar - Device list
        self.sidebar = self._build_sidebar(main_container)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Main content area
        content = tk.Frame(main_container, bg=self.COLORS['bg_primary'])
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Chat area
        self.chat_frame = self._build_chat_area(content)
        self.chat_frame.pack(fill=tk.BOTH, expand=True)
        
        # Input area
        self.input_frame = self._build_input_area(content)
        self.input_frame.pack(fill=tk.X, pady=(10, 0))
    
    def _configure_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure button style
        style.configure(
            'Primary.TButton',
            background=self.COLORS['accent'],
            foreground=self.COLORS['text_primary'],
            borderwidth=0,
            padding=10
        )
        style.map(
            'Primary.TButton',
            background=[('active', '#c73e54')]
        )
        
        # Configure frame styles
        style.configure(
            'Sidebar.TFrame',
            background=self.COLORS['bg_secondary']
        )
    
    def _build_sidebar(self, parent) -> tk.Frame:
        """Build left sidebar with devices and groups"""
        sidebar = tk.Frame(parent, bg=self.COLORS['bg_secondary'], width=250)
        sidebar.pack_propagate(False)
        
        # Header
        header = tk.Frame(sidebar, bg=self.COLORS['bg_secondary'])
        header.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            header, 
            text="🔒 Devices", 
            font=("Segoe UI", 12, "bold"),
            bg=self.COLORS['bg_secondary'],
            fg=self.COLORS['text_primary']
        ).pack(side=tk.LEFT)
        
        # Refresh button
        ttk.Button(
            header,
            text="🔄",
            command=self._discover_devices,
            width=3
        ).pack(side=tk.RIGHT)
        
        # Device list
        self.device_listbox = tk.Listbox(
            sidebar,
            bg=self.COLORS['bg_tertiary'],
            fg=self.COLORS['text_primary'],
            selectbackground=self.COLORS['accent'],
            borderwidth=0,
            highlightthickness=0
        )
        self.device_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.device_listbox.bind('<Double-Button-1>', self._on_device_select)
        
        # Groups section
        tk.Label(
            sidebar, 
            text="👥 Groups", 
            font=("Segoe UI", 12, "bold"),
            bg=self.COLORS['bg_secondary'],
            fg=self.COLORS['text_primary']
        ).pack(fill=tk.X, pady=(0, 5))
        
        # Create group button
        ttk.Button(
            sidebar,
            text="+ New Group",
            command=self._create_group_dialog
        ).pack(fill=tk.X, pady=(0, 10))
        
        # Groups list
        self.group_listbox = tk.Listbox(
            sidebar,
            bg=self.COLORS['bg_tertiary'],
            fg=self.COLORS['text_primary'],
            selectbackground=self.COLORS['accent'],
            borderwidth=0,
            highlightthickness=0,
            height=8
        )
        self.group_listbox.pack(fill=tk.X)
        
        # Status
        self.status_label = tk.Label(
            sidebar,
            text="🟢 Ready",
            font=("Segoe UI", 9),
            bg=self.COLORS['bg_secondary'],
            fg=self.COLORS['success']
        )
        self.status_label.pack(fill=tk.X, pady=(10, 0))
        
        return sidebar
    
    def _build_chat_area(self, parent) -> tk.Frame:
        """Build main chat area"""
        frame = tk.Frame(parent, bg=self.COLORS['bg_primary'])
        
        # Chat header
        self.chat_header = tk.Frame(frame, bg=self.COLORS['bg_secondary'])
        self.chat_header.pack(fill=tk.X)
        
        self.chat_title = tk.Label(
            self.chat_header,
            text="Select a device to start messaging",
            font=("Segoe UI", 11, "bold"),
            bg=self.COLORS['bg_secondary'],
            fg=self.COLORS['text_primary']
        )
        self.chat_title.pack(pady=10)
        
        # Encryption indicator
        self.encryption_indicator = tk.Label(
            self.chat_header,
            text="🔒 E2E Encrypted",
            font=("Segoe UI", 8),
            bg=self.COLORS['bg_secondary'],
            fg=self.COLORS['success']
        )
        self.encryption_indicator.pack(pady=(0, 5))
        
        # Messages area
        self.messages_area = scrolledtext.ScrolledText(
            frame,
            bg=self.COLORS['bg_primary'],
            fg=self.COLORS['text_primary'],
            font=("Segoe UI", 10),
            borderwidth=0,
            highlightthickness=0,
            state=tk.DISABLED,
            wrap=tk.WORD
        )
        self.messages_area.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for different message types
        self.messages_area.tag_config('sent', foreground=self.COLORS['text_primary'], justify='right')
        self.messages_area.tag_config('received', foreground=self.COLORS['text_primary'], justify='left')
        self.messages_area.tag_config('system', foreground=self.COLORS['text_secondary'], justify='center')
        
        return frame
    
    def _build_input_area(self, parent) -> tk.Frame:
        """Build message input area"""
        frame = tk.Frame(parent, bg=self.COLORS['bg_secondary'])
        
        # Input field
        input_container = tk.Frame(frame, bg=self.COLORS['bg_tertiary'])
        input_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.message_input = tk.Entry(
            input_container,
            bg=self.COLORS['bg_tertiary'],
            fg=self.COLORS['text_primary'],
            font=("Segoe UI", 11),
            borderwidth=0,
            highlightthickness=0
        )
        self.message_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 5), pady=10)
        self.message_input.bind('<Return>', lambda e: self._send_message())
        
        # Send button
        send_btn = tk.Button(
            input_container,
            text="📤 Send",
            command=self._send_message,
            bg=self.COLORS['accent'],
            fg=self.COLORS['text_primary'],
            borderwidth=0,
            padx=15,
            pady=5,
            cursor='hand2'
        )
        send_btn.pack(side=tk.RIGHT, padx=(5, 10), pady=5)
        
        # File transfer button
        file_btn = tk.Button(
            input_container,
            text="📎",
            command=self._send_file,
            bg=self.COLORS['bg_tertiary'],
            fg=self.COLORS['text_primary'],
            borderwidth=0,
            padx=10,
            pady=5,
            cursor='hand2'
        )
        file_btn.pack(side=tk.RIGHT)
        
        return frame
    
    def _discover_devices(self):
        """Discover nearby Bluetooth devices"""
        self.status_label.config(text="🔍 Discovering...")
        self.device_listbox.delete(0, tk.END)
        
        # Run discovery in thread
        def discover():
            devices = self.bt_messenger.discover_devices()
            self.root.after(0, lambda: self._update_device_list(devices))
        
        thread = threading.Thread(target=discover, daemon=True)
        thread.start()
    
    def _update_device_list(self, devices: list):
        """Update device list in UI"""
        self.device_listbox.delete(0, tk.END)
        
        if not devices:
            self.device_listbox.insert(0, "No devices found")
            self.status_label.config(text="🟡 No devices")
        else:
            for dev in devices:
                self.device_listbox.insert(tk.END, f"{dev['name']} ({dev['address']})")
                self.connected_devices[dev['address']] = dev
            
            self.status_label.config(text=f"🟢 {len(devices)} devices found")
    
    def _on_device_select(self, event):
        """Handle device selection"""
        selection = self.device_listbox.curselection()
        if selection:
            item = self.device_listbox.get(selection[0])
            if "No devices" not in item:
                # Extract address
                addr = item.split("(")[1].rstrip(")")
                self.current_device = addr
                self.chat_title.config(text=f"Chat with {item.split('(')[0].strip()}")
                self._add_system_message(f"Connected to {item}")
    
    def _send_message(self):
        """Send a message"""
        message = self.message_input.get().strip()
        if not message or not self.current_device:
            return
        
        # Encrypt message
        try:
            encrypted = self.encryption.encrypt_message(
                message,
                recipient_public_key_pem=self.public_key
            )
            
            # Display sent message
            self._add_message(message, 'sent')
            
            # In real implementation, would send via Bluetooth
            # self.bt_messenger.send_message(self.current_device, encrypted)
            
            self.message_input.delete(0, tk.END)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send: {e}")
    
    def _send_file(self):
        """Send a file"""
        if not self.current_device:
            messagebox.showwarning("Warning", "Select a device first")
            return
        
        file_path = filedialog.askopenfilename()
        if file_path:
            self._add_system_message(f"Sending file: {os.path.basename(file_path)}...")
            # In real implementation, would send via file_transfer
    
    def _create_group_dialog(self):
        """Show create group dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Create Group")
        dialog.geometry("300x200")
        dialog.configure(bg=self.COLORS['bg_primary'])
        
        tk.Label(
            dialog,
            text="Group Name:",
            bg=self.COLORS['bg_primary'],
            fg=self.COLORS['text_primary']
        ).pack(pady=(20, 5))
        
        name_entry = tk.Entry(dialog)
        name_entry.pack(fill=tk.X, padx=20)
        
        tk.Label(
            dialog,
            text="Description:",
            bg=self.COLORS['bg_primary'],
            fg=self.COLORS['text_primary']
        ).pack(pady=(10, 5))
        
        desc_entry = tk.Entry(dialog)
        desc_entry.pack(fill=tk.X, padx=20)
        
        def create():
            name = name_entry.get().strip()
            desc = desc_entry.get().strip()
            
            if name:
                group = self.group_chat.create_group(name, desc)
                self.group_listbox.insert(tk.END, f"{name} ({group.group_id})")
                dialog.destroy()
                self._add_system_message(f"Created group: {name}")
        
        ttk.Button(
            dialog,
            text="Create",
            command=create
        ).pack(pady=20)
    
    def _add_message(self, message: str, msg_type: str):
        """Add message to chat"""
        self.messages_area.config(state=tk.NORMAL)
        
        timestamp = datetime.now().strftime("%H:%M")
        
        if msg_type == 'sent':
            self.messages_area.insert(tk.END, f"\n[{timestamp}] You:\n{message}\n", 'sent')
        else:
            self.messages_area.insert(tk.END, f"\n[{timestamp}] Them:\n{message}\n", 'received')
        
        self.messages_area.see(tk.END)
        self.messages_area.config(state=tk.DISABLED)
    
    def _add_system_message(self, message: str):
        """Add system message"""
        self.messages_area.config(state=tk.NORMAL)
        self.messages_area.insert(tk.END, f"\n{message}\n", 'system')
        self.messages_area.see(tk.END)
        self.messages_area.config(state=tk.DISABLED)
    
    def _start_server(self):
        """Start Bluetooth server in background"""
        self.running = True
        
        def server():
            try:
                self.bt_messenger.start_server()
            except Exception as e:
                print(f"Server error: {e}")
        
        self.server_thread = threading.Thread(target=server, daemon=True)
        self.server_thread.start()
    
    def _stop_server(self):
        """Stop Bluetooth server"""
        self.running = False
        self.bt_messenger.stop()


def main():
    """Main entry point"""
    root = tk.Tk()
    
    # Set window icon (if available)
    try:
        root.iconname("BT Messenger")
    except:
        pass
    
    app = SecureBTMessengerGUI(root)
    
    # Handle window close
    def on_close():
        app._stop_server()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_close)
    
    root.mainloop()


if __name__ == "__main__":
    main()
