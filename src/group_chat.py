#!/usr/bin/env python3
"""
Group Chat Module
================
Multi-device encrypted group messaging for Bluetooth Messenger.

Features:
- Create/join group chats
- Group key distribution
- Message relay via mesh topology
- Member management
- Admin controls
"""

import os
import json
import uuid
import hashlib
import base64
import socket
import threading
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from encryption import EncryptionManager


@dataclass
class GroupMember:
    """Group member information"""
    member_id: str
    display_name: str
    bluetooth_address: str
    public_key: str
    is_admin: bool = False
    joined_at: str = ""
    last_seen: str = ""
    
    def __post_init__(self):
        if not self.joined_at:
            self.joined_at = datetime.now().isoformat()


@dataclass
class GroupMessage:
    """Encrypted group message"""
    message_id: str
    group_id: str
    sender_id: str
    sender_name: str
    content: str  # Encrypted content
    timestamp: str
    message_type: str = "text"  # text, system, file
    reply_to: Optional[str] = None


@dataclass
class Group:
    """Group chat information"""
    group_id: str
    name: str
    description: str
    created_by: str
    created_at: str
    group_key: str  # Encrypted group key for each member
    members: List[Dict] = field(default_factory=list)
    max_members: int = 8
    is_active: bool = True


class GroupChat:
    """
    Secure Group Chat Manager
    
    Implements:
    - Group creation and management
    - Group key distribution (each member gets unique encrypted key)
    - Message broadcasting
    - Member roles (admin, member)
    - Mesh-style message relay
    """
    
    MAX_GROUP_SIZE = 8  # Bluetooth mesh limitation
    GROUP_KEY_SIZE = 32
    
    def __init__(self, encryption_manager: EncryptionManager, device_id: str):
        self.encryption = encryption_manager
        self.device_id = device_id
        self.groups: Dict[str, Group] = {}
        self.my_member_id = base64.b64encode(os.urandom(16)).decode()[:8]
        self.message_handlers: List[callable] = []
        
        # For mesh networking
        self.known_members: Dict[str, GroupMember] = {}
    
    # =========================================================================
    # GROUP MANAGEMENT
    # =========================================================================
    
    def create_group(
        self, 
        name: str, 
        description: str = "",
        max_members: int = None
    ) -> Group:
        """
        Create a new group chat.
        
        Args:
            name: Group name
            description: Group description
            max_members: Maximum members (default 8)
            
        Returns:
            Created Group object
        """
        if max_members is None:
            max_members = self.MAX_GROUP_SIZE
        
        # Generate group key
        group_key = os.urandom(self.GROUP_KEY_SIZE)
        
        # Create group
        group_id = base64.b64encode(uuid.uuid4().bytes).decode()[:12].upper()
        
        group = Group(
            group_id=group_id,
            name=name,
            description=description,
            created_by=self.my_member_id,
            created_at=datetime.now().isoformat(),
            group_key=base64.b64encode(group_key).decode(),
            members=[],
            max_members=max_members
        )
        
        # Add creator as admin member
        admin_member = GroupMember(
            member_id=self.my_member_id,
            display_name="Me",
            bluetooth_address="",
            public_key="",
            is_admin=True
        )
        
        group.members.append(asdict(admin_member))
        self.groups[group_id] = group
        
        print(f"✓ Group created: {name} ({group_id})")
        return group
    
    def join_group(
        self, 
        group_id: str, 
        display_name: str,
        bluetooth_address: str,
        public_key: str
    ) -> bool:
        """
        Join an existing group.
        
        Args:
            group_id: Group to join
            display_name: Display name
            bluetooth_address: Our Bluetooth address
            public_key: Our public key
            
        Returns:
            True if successful
        """
        if group_id not in self.groups:
            print(f"✗ Group not found: {group_id}")
            return False
        
        group = self.groups[group_id]
        
        if len(group.members) >= group.max_members:
            print(f"✗ Group is full")
            return False
        
        # Check if already member
        for member in group.members:
            if member['member_id'] == self.my_member_id:
                print("Already a member")
                return True
        
        # Add as member
        new_member = GroupMember(
            member_id=self.my_member_id,
            display_name=display_name,
            bluetooth_address=bluetooth_address,
            public_key=public_key,
            is_admin=False
        )
        
        group.members.append(asdict(new_member))
        
        print(f"✓ Joined group: {group.name}")
        return True
    
    def leave_group(self, group_id: str) -> bool:
        """Leave a group"""
        if group_id not in self.groups:
            return False
        
        group = self.groups[group_id]
        group.members = [m for m in group.members if m['member_id'] != self.my_member_id]
        
        if not group.members:
            del self.groups[group_id]
        
        return True
    
    def get_group_info(self, group_id: str) -> Optional[Group]:
        """Get group information"""
        return self.groups.get(group_id)
    
    def list_groups(self) -> List[Group]:
        """List all groups"""
        return list(self.groups.values())
    
    # =========================================================================
    # GROUP MESSAGING
    # =========================================================================
    
    def send_to_group(
        self, 
        group_id: str, 
        message: str,
        message_type: str = "text"
    ) -> Optional[GroupMessage]:
        """
        Send a message to a group.
        
        Args:
            group_id: Target group
            message: Message content
            message_type: Type of message
            
        Returns:
            GroupMessage if successful
        """
        if group_id not in self.groups:
            print(f"✗ Group not found: {group_id}")
            return None
        
        group = self.groups[group_id]
        
        # Encrypt message for group
        encrypted_content = self._encrypt_group_message(message, group.group_key)
        
        group_message = GroupMessage(
            message_id=base64.b64encode(os.urandom(16)).decode()[:16],
            group_id=group_id,
            sender_id=self.my_member_id,
            sender_name="Me",
            content=encrypted_content,
            timestamp=datetime.now().isoformat(),
            message_type=message_type
        )
        
        # Notify handlers
        for handler in self.message_handlers:
            handler(group_message)
        
        return group_message
    
    def receive_message(self, message: GroupMessage) -> str:
        """
        Decrypt and process a received group message.
        
        Args:
            message: Received GroupMessage
            
        Returns:
            Decrypted message content
        """
        if message.group_id not in self.groups:
            return "[Unknown group]"
        
        group = self.groups[message.group_id]
        
        # Decrypt
        decrypted = self._decrypt_group_message(message.content, group.group_key)
        
        # Notify handlers
        for handler in self.message_handlers:
            handler(message)
        
        return decrypted
    
    def broadcast_presence(self, group_id: str, socket: socket.socket) -> bool:
        """
        Broadcast presence to all group members.
        
        Args:
            group_id: Group to announce to
            socket: Socket to use
            
        Returns:
            True if broadcast successful
        """
        if group_id not in self.groups:
            return False
        
        group = self.groups[group_id]
        
        # Create presence announcement
        announcement = {
            "type": "presence",
            "member_id": self.my_member_id,
            "group_id": group_id,
            "display_name": "Me",
            "timestamp": datetime.now().isoformat()
        }
        
        # In real implementation, would send to all known member addresses
        return True
    
    # =========================================================================
    # ENCRYPTION
    # =========================================================================
    
    def _encrypt_group_message(self, message: str, group_key: str) -> str:
        """Encrypt message for group"""
        # Derive encryption key from group key
        key_bytes = base64.b64decode(group_key)
        
        # Use encryption manager
        encrypted = self.encryption.encrypt_message(message, session_key=key_bytes)
        
        return encrypted
    
    def _decrypt_group_message(self, encrypted: str, group_key: str) -> str:
        """Decrypt group message"""
        key_bytes = base64.b64decode(group_key)
        
        message, _ = self.encryption.decrypt_message(encrypted, session_key=key_bytes)
        
        return message
    
    # =========================================================================
    # KEY DISTRIBUTION
    # =========================================================================
    
    def distribute_group_key(
        self, 
        group_id: str, 
        new_member_public_key: str
    ) -> Optional[str]:
        """
        Encrypt and distribute group key to new member.
        
        Args:
            group_id: Group ID
            new_member_public_key: New member's public key
            
        Returns:
            Encrypted group key (base64)
        """
        if group_id not in self.groups:
            return None
        
        group = self.groups[group_id]
        group_key_bytes = base64.b64decode(group.group_key)
        
        # Encrypt group key with new member's public key
        encrypted_key = self.encryption.encrypt_session_key(
            group_key_bytes,
            new_member_public_key
        )
        
        return encrypted_key.decode('utf-8')
    
    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================
    
    def on_message(self, handler: callable):
        """Register message handler"""
        self.message_handlers.append(handler)
    
    # =========================================================================
    # SERIALIZATION
    # =========================================================================
    
    def save_groups(self, file_path: str):
        """Save groups to file"""
        data = {
            group_id: asdict(group) 
            for group_id, group in self.groups.items()
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_groups(self, file_path: str):
        """Load groups from file"""
        if not os.path.exists(file_path):
            return
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        self.groups = {
            group_id: Group(**group_data)
            for group_id, group_data in data.items()
        }


class MeshNetwork:
    """
    Bluetooth Mesh Network for Multi-hop Messaging
    
    Allows messages to hop through multiple devices
    when direct connection isn't possible.
    """
    
    def __init__(self, group_chat: GroupChat):
        self.group_chat = group_chat
        self.peers: Dict[str, Dict] = {}  # address -> peer info
        self.message_cache: Set[str] = set()  # Message IDs to prevent duplicates
    
    def add_peer(self, address: str, info: Dict):
        """Add a peer to the mesh"""
        self.peers[address] = {
            **info,
            'last_seen': datetime.now().isoformat()
        }
    
    def remove_peer(self, address: str):
        """Remove a peer from mesh"""
        if address in self.peers:
            del self.peers[address]
    
    def relay_message(self, message: GroupMessage, exclude: Set[str] = None) -> int:
        """
        Relay a message to all known peers.
        
        Args:
            message: Message to relay
            exclude: Set of addresses to exclude
            
        Returns:
            Number of peers relayed to
        """
        if exclude is None:
            exclude = set()
        
        # Check if already seen
        if message.message_id in self.message_cache:
            return 0
        
        self.message_cache.add(message.message_id)
        
        # In real implementation, would send to each peer
        # For now, just return count
        return len([p for p in self.peers if p not in exclude])


def demo():
    """Demo group chat"""
    print("=" * 60)
    print("Group Chat Demo")
    print("=" * 60)
    
    # Create encryption manager
    enc = EncryptionManager()
    enc.generate_keypair()
    
    # Create group chat
    chat = GroupChat(enc, "device001")
    
    # Create group
    print("\n1. Creating group...")
    group = chat.create_group("Test Group", "A test group", max_members=5)
    print(f"   Group ID: {group.group_id}")
    print(f"   Members: {len(group.members)}")
    
    # Add more members
    print("\n2. Simulating members joining...")
    for name in ["Alice", "Bob", "Charlie"]:
        group.members.append({
            "member_id": base64.b64encode(os.urandom(8)).decode()[:8],
            "display_name": name,
            "is_admin": False
        })
        print(f"   ✓ {name} joined")
    
    print(f"   Total members: {len(group.members)}")
    
    # Send message
    print("\n3. Sending group message...")
    msg = chat.send_to_group(group.group_id, "Hello, everyone!")
    print(f"   Message ID: {msg.message_id}")
    
    # Receive message
    print("\n4. Receiving message...")
    decrypted = chat.receive_message(msg)
    print(f"   Decrypted: {decrypted}")
    
    # List groups
    print("\n5. Listing groups...")
    groups = chat.list_groups()
    for g in groups:
        print(f"   - {g.name} ({g.group_id}): {len(g.members)} members")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    demo()
