#!/usr/bin/env python3
"""
Contact Management Module
========================
Secure contact management for Bluetooth Messenger.

Features:
- Add/remove contacts
- Contact profiles with avatars
- Favorite contacts
- Block/unblock contacts
- Contact groups
- Online status tracking
"""

import os
import json
import base64
import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class ContactProfile:
    """Contact profile information"""
    contact_id: str
    display_name: str
    bluetooth_address: str
    public_key: str
    avatar: Optional[str] = None  # Base64 encoded
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: str = ""
    is_favorite: bool = False
    is_blocked: bool = False
    created_at: str = ""
    last_seen: str = ""
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class ContactGroup:
    """Contact group"""
    group_id: str
    name: str
    description: str = ""
    color: str = "#e94560"
    contacts: List[str] = field(default_factory=list)
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class ContactManager:
    """
    Secure Contact Manager
    
    Features:
    - CRUD operations for contacts
    - Contact groups
    - Favorites
    - Block list
    - Search and filter
    - Import/export
    """
    
    def __init__(self, storage_dir: Optional[str] = None):
        # Default storage location
        if storage_dir is None:
            storage_dir = Path.home() / ".bt-messenger"
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.contacts_file = self.storage_dir / "contacts.json"
        self.groups_file = self.storage_dir / "contact_groups.json"
        
        # Load contacts
        self.contacts: Dict[str, ContactProfile] = {}
        self.groups: Dict[str, ContactGroup] = {}
        
        self._load_contacts()
        self._load_groups()
    
    # =========================================================================
    # CRUD OPERATIONS
    # =========================================================================
    
    def add_contact(
        self,
        bluetooth_address: str,
        display_name: str,
        public_key: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        notes: str = ""
    ) -> ContactProfile:
        """
        Add a new contact.
        
        Args:
            bluetooth_address: Bluetooth MAC address
            display_name: Display name
            public_key: RSA public key
            email: Optional email
            phone: Optional phone
            notes: Optional notes
            
        Returns:
            Created ContactProfile
        """
        # Generate contact ID
        contact_id = self._generate_contact_id(bluetooth_address)
        
        if contact_id in self.contacts:
            raise ValueError(f"Contact already exists: {bluetooth_address}")
        
        contact = ContactProfile(
            contact_id=contact_id,
            display_name=display_name,
            bluetooth_address=bluetooth_address,
            public_key=public_key,
            email=email,
            phone=phone,
            notes=notes
        )
        
        self.contacts[contact_id] = contact
        self._save_contacts()
        
        return contact
    
    def update_contact(
        self,
        contact_id: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        notes: Optional[str] = None,
        avatar: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[ContactProfile]:
        """Update contact information"""
        if contact_id not in self.contacts:
            return None
        
        contact = self.contacts[contact_id]
        
        if display_name is not None:
            contact.display_name = display_name
        if email is not None:
            contact.email = email
        if phone is not None:
            contact.phone = phone
        if notes is not None:
            contact.notes = notes
        if avatar is not None:
            contact.avatar = avatar
        if tags is not None:
            contact.tags = tags
        
        self._save_contacts()
        return contact
    
    def remove_contact(self, contact_id: str) -> bool:
        """Remove a contact"""
        if contact_id in self.contacts:
            del self.contacts[contact_id]
            
            # Remove from groups
            for group in self.groups.values():
                if contact_id in group.contacts:
                    group.contacts.remove(contact_id)
            
            self._save_contacts()
            self._save_groups()
            return True
        return False
    
    def get_contact(self, contact_id: str) -> Optional[ContactProfile]:
        """Get contact by ID"""
        return self.contacts.get(contact_id)
    
    def get_contact_by_address(self, bluetooth_address: str) -> Optional[ContactProfile]:
        """Get contact by Bluetooth address"""
        contact_id = self._generate_contact_id(bluetooth_address)
        return self.contacts.get(contact_id)
    
    # =========================================================================
    # FAVORITES & BLOCKING
    # =========================================================================
    
    def toggle_favorite(self, contact_id: str) -> bool:
        """Toggle favorite status"""
        if contact_id in self.contacts:
            self.contacts[contact_id].is_favorite = not self.contacts[contact_id].is_favorite
            self._save_contacts()
            return self.contacts[contact_id].is_favorite
        return False
    
    def toggle_block(self, contact_id: str) -> bool:
        """Toggle block status"""
        if contact_id in self.contacts:
            self.contacts[contact_id].is_blocked = not self.contacts[contact_id].is_blocked
            self._save_contacts()
            return self.contacts[contact_id].is_blocked
        return False
    
    def get_favorites(self) -> List[ContactProfile]:
        """Get all favorite contacts"""
        return [c for c in self.contacts.values() if c.is_favorite]
    
    def get_blocked(self) -> List[ContactProfile]:
        """Get all blocked contacts"""
        return [c for c in self.contacts.values() if c.is_blocked]
    
    # =========================================================================
    # GROUPS
    # =========================================================================
    
    def create_group(
        self,
        name: str,
        description: str = "",
        color: str = "#e94560"
    ) -> ContactGroup:
        """Create a contact group"""
        group_id = base64.b64encode(os.urandom(8)).decode()[:8]
        
        group = ContactGroup(
            group_id=group_id,
            name=name,
            description=description,
            color=color
        )
        
        self.groups[group_id] = group
        self._save_groups()
        
        return group
    
    def add_to_group(self, contact_id: str, group_id: str) -> bool:
        """Add contact to group"""
        if contact_id not in self.contacts or group_id not in self.groups:
            return False
        
        if contact_id not in self.groups[group_id].contacts:
            self.groups[group_id].contacts.append(contact_id)
            self._save_groups()
        return True
    
    def remove_from_group(self, contact_id: str, group_id: str) -> bool:
        """Remove contact from group"""
        if group_id not in self.groups:
            return False
        
        if contact_id in self.groups[group_id].contacts:
            self.groups[group_id].contacts.remove(contact_id)
            self._save_groups()
        return True
    
    def get_group_contacts(self, group_id: str) -> List[ContactProfile]:
        """Get all contacts in a group"""
        if group_id not in self.groups:
            return []
        
        return [
            self.contacts[c_id]
            for c_id in self.groups[group_id].contacts
            if c_id in self.contacts
        ]
    
    # =========================================================================
    # SEARCH & FILTER
    # =========================================================================
    
    def search_contacts(self, query: str) -> List[ContactProfile]:
        """Search contacts by name, email, or notes"""
        query = query.lower()
        results = []
        
        for contact in self.contacts.values():
            if (query in contact.display_name.lower() or
                (contact.email and query in contact.email.lower()) or
                (contact.notes and query in contact.notes.lower())):
                results.append(contact)
        
        return results
    
    def get_all_contacts(self) -> List[ContactProfile]:
        """Get all contacts sorted by name"""
        return sorted(
            self.contacts.values(),
            key=lambda c: c.display_name.lower()
        )
    
    # =========================================================================
    # IMPORT/EXPORT
    # =========================================================================
    
    def export_contacts(self, file_path: str, include_keys: bool = True):
        """Export contacts to JSON file"""
        data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "contacts": []
        }
        
        for contact in self.contacts.values():
            contact_data = {
                "display_name": contact.display_name,
                "bluetooth_address": contact.bluetooth_address,
                "email": contact.email,
                "phone": contact.phone,
                "notes": contact.notes,
                "tags": contact.tags,
                "is_favorite": contact.is_favorite
            }
            
            if include_keys:
                contact_data["public_key"] = contact.public_key
            
            data["contacts"].append(contact_data)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def import_contacts(self, file_path: str, merge: bool = True) -> int:
        """Import contacts from JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        imported = 0
        
        for contact_data in data.get("contacts", []):
            try:
                # Check if already exists
                existing = self.get_contact_by_address(contact_data["bluetooth_address"])
                
                if existing and not merge:
                    continue
                
                if not existing:
                    self.add_contact(
                        bluetooth_address=contact_data["bluetooth_address"],
                        display_name=contact_data["display_name"],
                        public_key=contact_data.get("public_key", ""),
                        email=contact_data.get("email"),
                        phone=contact_data.get("phone"),
                        notes=contact_data.get("notes", "")
                    )
                    
                    if contact_data.get("is_favorite"):
                        contact_id = self._generate_contact_id(contact_data["bluetooth_address"])
                        if contact_id in self.contacts:
                            self.contacts[contact_id].is_favorite = True
                    
                    imported += 1
                    
            except Exception as e:
                print(f"Error importing contact: {e}")
        
        return imported
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    def _generate_contact_id(self, bluetooth_address: str) -> str:
        """Generate unique contact ID from Bluetooth address"""
        return hashlib.sha256(bluetooth_address.encode()).hexdigest()[:16]
    
    def _load_contacts(self):
        """Load contacts from file"""
        if not self.contacts_file.exists():
            return
        
        try:
            with open(self.contacts_file, 'r') as f:
                data = json.load(f)
                
            for contact_id, contact_data in data.items():
                self.contacts[contact_id] = ContactProfile(**contact_data)
        except Exception as e:
            print(f"Error loading contacts: {e}")
    
    def _save_contacts(self):
        """Save contacts to file"""
        data = {
            contact_id: asdict(contact)
            for contact_id, contact in self.contacts.items()
        }
        
        with open(self.contacts_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_groups(self):
        """Load contact groups from file"""
        if not self.groups_file.exists():
            return
        
        try:
            with open(self.groups_file, 'r') as f:
                data = json.load(f)
                
            for group_id, group_data in data.items():
                self.groups[group_id] = ContactGroup(**group_data)
        except Exception as e:
            print(f"Error loading groups: {e}")
    
    def _save_groups(self):
        """Save contact groups to file"""
        data = {
            group_id: asdict(group)
            for group_id, group in self.groups.items()
        }
        
        with open(self.groups_file, 'w') as f:
            json.dump(data, f, indent=2)


def demo():
    """Demo contact management"""
    print("=" * 60)
    print("Contact Management Demo")
    print("=" * 60)
    
    # Create contact manager
    manager = ContactManager("/tmp/bt-messenger-test")
    
    # Add contacts
    print("\n1. Adding contacts...")
    
    alice = manager.add_contact(
        bluetooth_address="AA:BB:CC:DD:EE:01",
        display_name="Alice",
        public_key="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
        email="alice@example.com",
        notes="Friend from work"
    )
    print(f"   ✓ Added: {alice.display_name}")
    
    bob = manager.add_contact(
        bluetooth_address="AA:BB:CC:DD:EE:02",
        display_name="Bob",
        public_key="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
        phone="+1234567890"
    )
    print(f"   ✓ Added: {bob.display_name}")
    
    charlie = manager.add_contact(
        bluetooth_address="AA:BB:CC:DD:EE:03",
        display_name="Charlie",
        public_key=""
    )
    print(f"   ✓ Added: {charlie.display_name}")
    
    # Toggle favorite
    print("\n2. Managing favorites...")
    manager.toggle_favorite(alice.contact_id)
    print(f"   ✓ {alice.display_name} is favorite")
    
    # Create group
    print("\n3. Creating groups...")
    friends = manager.create_group("Friends", "Close friends", "#00d26a")
    print(f"   ✓ Created group: {friends.name}")
    
    work = manager.create_group("Work", "Work colleagues", "#3498db")
    print(f"   ✓ Created group: {work.name}")
    
    # Add to groups
    manager.add_to_group(alice.contact_id, friends.group_id)
    manager.add_to_group(bob.contact_id, work.group_id)
    print(f"   ✓ Added contacts to groups")
    
    # List all
    print("\n4. All contacts:")
    for contact in manager.get_all_contacts():
        fav = "⭐" if contact.is_favorite else "  "
        print(f"   {fav} {contact.display_name} ({contact.bluetooth_address})")
    
    # List favorites
    print("\n5. Favorites:")
    for contact in manager.get_favorites():
        print(f"   ⭐ {contact.display_name}")
    
    # Search
    print("\n6. Search for 'Alice':")
    results = manager.search_contacts("Alice")
    for c in results:
        print(f"   Found: {c.display_name}")
    
    # Export
    print("\n7. Exporting contacts...")
    manager.export_contacts("/tmp/contacts_export.json")
    print("   ✓ Exported to /tmp/contacts_export.json")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    demo()
