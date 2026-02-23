#!/usr/bin/env python3
"""
Read Receipts Module
===================
Message read status tracking for Bluetooth Messenger.

Features:
- Send read receipts
- Track message read status
- Read receipt notifications
- Multiple recipients
- Read timestamp
- Read by count
- Thread-safe operations
"""

import threading
import time
import json
from datetime import datetime
from typing import Dict, Optional, List, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict


class ReadReceiptStatus(Enum):
    """Read receipt status values"""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"


@dataclass
class ReadReceipt:
    """Read receipt for a message"""
    receipt_id: str
    message_id: str
    chat_id: str
    user_id: str
    user_name: str
    status: str
    timestamp: str
    read_at: Optional[str] = None


class ReadReceipts:
    """
    Read Receipts Manager
    
    Features:
    - Track sent/delivered/read status
    - Multiple receipts per message
    - Read timestamp tracking
    - Callback handlers
    - Message read history
    """
    
    def __init__(self, user_id: str = "me", user_name: str = "Me"):
        self.user_id = user_id
        self.user_name = user_name
        
        # Track receipts: message_id -> list of ReadReceipt
        self.receipts: Dict[str, List[ReadReceipt]] = defaultdict(list)
        
        # Track user's own sent messages: chat_id -> set of message_ids
        self.sent_messages: Dict[str, Set[str]] = defaultdict(set)
        
        # Callbacks
        self.on_status_change: Optional[Callable] = None
        self.on_all_read: Optional[Callable] = None
        
        # Lock for thread safety
        self._lock = threading.Lock()
    
    # =========================================================================
    # MARK MESSAGES AS READ
    # =========================================================================
    
    def mark_as_read(
        self,
        message_ids: List[str],
        chat_id: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> List[ReadReceipt]:
        """
        Mark messages as read.
        
        Args:
            message_ids: List of message IDs
            chat_id: Chat ID
            user_id: User ID (default: current user)
            user_name: User name
            
        Returns:
            List of created ReadReceipts
        """
        if user_id is None:
            user_id = self.user_id
        if user_name is None:
            user_name = self.user_name
        
        receipts = []
        timestamp = datetime.now().isoformat()
        
        with self._lock:
            for message_id in message_ids:
                receipt = ReadReceipt(
                    receipt_id=self._generate_receipt_id(message_id, user_id),
                    message_id=message_id,
                    chat_id=chat_id,
                    user_id=user_id,
                    user_name=user_name,
                    status=ReadReceiptStatus.READ.value,
                    timestamp=timestamp,
                    read_at=timestamp
                )
                
                # Add to receipts
                self.receipts[message_id].append(receipt)
                
                receipts.append(receipt)
                
                # Notify callback
                if self.on_status_change:
                    self.on_status_change(message_id, user_id, ReadReceiptStatus.READ.value)
        
        return receipts
    
    def mark_as_delivered(
        self,
        message_ids: List[str],
        chat_id: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> List[ReadReceipt]:
        """Mark messages as delivered"""
        if user_id is None:
            user_id = self.user_id
        if user_name is None:
            user_name = self.user_name
        
        receipts = []
        timestamp = datetime.now().isoformat()
        
        with self._lock:
            for message_id in message_ids:
                receipt = ReadReceipt(
                    receipt_id=self._generate_receipt_id(message_id, user_id),
                    message_id=message_id,
                    chat_id=chat_id,
                    user_id=user_id,
                    user_name=user_name,
                    status=ReadReceiptStatus.DELIVERED.value,
                    timestamp=timestamp
                )
                
                self.receipts[message_id].append(receipt)
                receipts.append(receipt)
                
                if self.on_status_change:
                    self.on_status_change(message_id, user_id, ReadReceiptStatus.DELIVERED.value)
        
        return receipts
    
    # =========================================================================
    # SEND READ RECEIPTS (for outgoing messages)
    # =========================================================================
    
    def send_read_receipt(
        self,
        message_id: str,
        chat_id: str,
        recipient_id: str,
        recipient_name: str
    ) -> ReadReceipt:
        """
        Send a read receipt (for your sent message).
        
        Args:
            message_id: The message that was read
            chat_id: Chat ID
            recipient_id: Person who read it
            recipient_name: Person's name
            
        Returns:
            ReadReceipt
        """
        receipt = ReadReceipt(
            receipt_id=self._generate_receipt_id(message_id, recipient_id),
            message_id=message_id,
            chat_id=chat_id,
            user_id=recipient_id,
            user_name=recipient_name,
            status=ReadReceiptStatus.READ.value,
            timestamp=datetime.now().isoformat(),
            read_at=datetime.now().isoformat()
        )
        
        with self._lock:
            self.receipts[message_id].append(receipt)
        
        return receipt
    
    # =========================================================================
    # QUERY RECEIPTS
    # =========================================================================
    
    def get_receipts(self, message_id: str) -> List[ReadReceipt]:
        """Get all receipts for a message"""
        with self._lock:
            return self.receipts.get(message_id, []).copy()
    
    def get_read_count(self, message_id: str) -> int:
        """Get number of people who read a message"""
        with self._lock:
            receipts = self.receipts.get(message_id, [])
            return sum(1 for r in receipts if r.status == ReadReceiptStatus.READ.value)
    
    def get_delivery_count(self, message_id: str) -> int:
        """Get number of people who received a message"""
        with self._lock:
            receipts = self.receipts.get(message_id, [])
            delivered = sum(
                1 for r in receipts 
                if r.status in [ReadReceiptStatus.DELIVERED.value, ReadReceiptStatus.READ.value]
            )
            return delivered
    
    def has_been_read_by(self, message_id: str, user_id: str) -> bool:
        """Check if a message was read by a specific user"""
        with self._lock:
            receipts = self.receipts.get(message_id, [])
            return any(
                r.user_id == user_id and r.status == ReadReceiptStatus.READ.value
                for r in receipts
            )
    
    def get_read_by(self, message_id: str) -> List[Dict]:
        """Get list of users who read a message"""
        with self._lock:
            receipts = self.receipts.get(message_id, [])
            return [
                {
                    "user_id": r.user_id,
                    "user_name": r.user_name,
                    "read_at": r.read_at
                }
                for r in receipts
                if r.status == ReadReceiptStatus.READ.value
            ]
    
    def is_fully_read(self, message_id: str, expected_readers: int) -> bool:
        """Check if all expected readers have read the message"""
        return self.get_read_count(message_id) >= expected_readers
    
    # =========================================================================
    # CHAT-LEVEL READ STATUS
    # =========================================================================
    
    def get_chat_unread_count(self, chat_id: str, all_message_ids: List[str]) -> int:
        """Get count of unread messages in a chat"""
        with self._lock:
            unread = 0
            for msg_id in all_message_ids:
                # Check if current user has read this message
                receipts = self.receipts.get(msg_id, [])
                user_read = any(
                    r.user_id == self.user_id and r.status == ReadReceiptStatus.READ.value
                    for r in receipts
                )
                if not user_read:
                    unread += 1
            return unread
    
    def get_chat_read_status(self, chat_id: str, all_message_ids: List[str]) -> str:
        """
        Get overall read status for a chat.
        
        Returns:
            "all_read" - All messages read
            "partial" - Some messages read
            "none" - No messages read
        """
        with self._lock:
            if not all_message_ids:
                return "none"
            
            read_count = 0
            for msg_id in all_message_ids:
                receipts = self.receipts.get(msg_id, [])
                if any(
                    r.user_id == self.user_id and r.status == ReadReceiptStatus.READ.value
                    for r in receipts
                ):
                    read_count += 1
            
            if read_count == 0:
                return "none"
            elif read_count == len(all_message_ids):
                return "all_read"
            else:
                return "partial"
    
    # =========================================================================
    # TRACK SENT MESSAGES
    # =========================================================================
    
    def track_sent_message(self, message_id: str, chat_id: str):
        """Track a message you sent"""
        with self._lock:
            self.sent_messages[chat_id].add(message_id)
    
    def get_sent_message_ids(self, chat_id: str) -> Set[str]:
        """Get all message IDs you've sent in a chat"""
        with self._lock:
            return self.sent_messages.get(chat_id, set()).copy()
    
    # =========================================================================
    # RECEIVE READ RECEIPTS (from network)
    # =========================================================================
    
    def receive_receipt(
        self,
        message_id: str,
        chat_id: str,
        user_id: str,
        user_name: str,
        status: str,
        read_at: Optional[str] = None
    ) -> ReadReceipt:
        """Process a received read receipt"""
        receipt = ReadReceipt(
            receipt_id=self._generate_receipt_id(message_id, user_id),
            message_id=message_id,
            chat_id=chat_id,
            user_id=user_id,
            user_name=user_name,
            status=status,
            timestamp=datetime.now().isoformat(),
            read_at=read_at
        )
        
        with self._lock:
            # Remove existing receipt from same user
            self.receipts[message_id] = [
                r for r in self.receipts[message_id]
                if r.user_id != user_id
            ]
            # Add new receipt
            self.receipts[message_id].append(receipt)
        
        # Notify callback
        if self.on_status_change:
            self.on_status_change(message_id, user_id, status)
        
        return receipt
    
    # =========================================================================
    # MESSAGE READ HISTORY
    # =========================================================================
    
    def get_read_history(
        self,
        chat_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get read receipt history.
        
        Args:
            chat_id: Optional chat filter
            limit: Maximum entries
            
        Returns:
            List of receipt events
        """
        history = []
        
        with self._lock:
            for message_id, receipts in self.receipts.items():
                for receipt in receipts:
                    if receipt.status == ReadReceiptStatus.READ.value:
                        if chat_id is None or receipt.chat_id == chat_id:
                            history.append({
                                "message_id": message_id,
                                "chat_id": receipt.chat_id,
                                "user_id": receipt.user_id,
                                "user_name": receipt.user_name,
                                "read_at": receipt.read_at
                            })
        
        # Sort by read_at descending
        history.sort(key=lambda x: x.get("read_at", ""), reverse=True)
        
        return history[:limit]
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    def _generate_receipt_id(self, message_id: str, user_id: str) -> str:
        """Generate unique receipt ID"""
        import hashlib
        data = f"{message_id}{user_id}{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:12]
    
    # =========================================================================
    # CALLBACK HANDLERS
    # =========================================================================
    
    def set_status_change_handler(self, callback: Callable):
        """Set callback for status changes"""
        self.on_status_change = callback
    
    def set_all_read_handler(self, callback: Callable):
        """Set callback when all messages are read"""
        self.on_all_read = callback
    
    # =========================================================================
    # SERIALIZATION
    # =========================================================================
    
    def to_json(self) -> str:
        """Serialize to JSON"""
        with self._lock:
            data = {
                message_id: [asdict(r) for r in receipts]
                for message_id, receipts in self.receipts.items()
            }
            return json.dumps(data)
    
    def from_json(self, json_str: str):
        """Deserialize from JSON"""
        data = json.loads(json_str)
        
        with self._lock:
            self.receipts = defaultdict(list)
            for message_id, receipts_data in data.items():
                self.receipts[message_id] = [
                    ReadReceipt(**r) for r in receipts_data
                ]


def demo():
    """Demo read receipts"""
    print("=" * 60)
    print("Read Receipts Demo")
    print("=" * 60)
    
    # Create read receipts manager
    receipts = ReadReceipts(user_id="alice", user_name="Alice")
    
    # Set up callback
    def on_status_change(msg_id, user, status):
        print(f"  🔔 Status changed: {user} {status} message {msg_id[:8]}...")
    
    receipts.set_status_change_handler(on_status_change)
    
    # Alice sends messages
    print("\n1. Alice sends 3 messages in chat1...")
    msg1 = "msg_001"
    msg2 = "msg_002"
    msg3 = "msg_003"
    
    receipts.track_sent_message(msg1, "chat1")
    receipts.track_sent_message(msg2, "chat1")
    receipts.track_sent_message(msg3, "chat1")
    print(f"   Sent messages: {receipts.get_sent_message_ids('chat1')}")
    
    # Bob receives messages (delivered)
    print("\n2. Bob receives messages...")
    receipts.receive_receipt(msg1, "chat1", "bob", "Bob", "delivered")
    receipts.receive_receipt(msg2, "chat1", "bob", "Bob", "delivered")
    receipts.receive_receipt(msg3, "chat1", "bob", "Bob", "delivered")
    
    print(f"   msg1 delivery count: {receipts.get_delivery_count(msg1)}")
    
    # Bob reads messages
    print("\n3. Bob reads messages...")
    receipts.receive_receipt(
        msg1, "chat1", "bob", "Bob", "read", 
        read_at=datetime.now().isoformat()
    )
    print(f"   msg1 read count: {receipts.get_read_count(msg1)}")
    
    receipts.receive_receipt(
        msg2, "chat1", "bob", "Bob", "read",
        read_at=datetime.now().isoformat()
    )
    
    receipts.receive_receipt(
        msg3, "chat1", "bob", "Bob", "read",
        read_at=datetime.now().isoformat()
    )
    
    # Check status
    print("\n4. Message status:")
    print(f"   msg1 read by: {receipts.get_read_by(msg1)}")
    print(f"   msg1 read count: {receipts.get_read_count(msg1)}")
    print(f"   msg1 delivered count: {receipts.get_delivery_count(msg1)}")
    print(f"   msg1 fully read by 1 reader: {receipts.is_fully_read(msg1, 1)}")
    
    # Charlie also reads
    print("\n5. Charlie also reads msg1...")
    receipts.receive_receipt(
        msg1, "chat1", "charlie", "Charlie", "read",
        read_at=datetime.now().isoformat()
    )
    print(f"   msg1 read count now: {receipts.get_read_count(msg1)}")
    print(f"   msg1 fully read by 2 readers: {receipts.is_fully_read(msg1, 2)}")
    
    # Chat-level status
    print("\n6. Chat-level read status:")
    all_msgs = [msg1, msg2, msg3]
    print(f"   Chat read status: {receipts.get_chat_read_status('chat1', all_msgs)}")
    print(f"   Unread count: {receipts.get_chat_unread_count('chat1', all_msgs)}")
    
    # History
    print("\n7. Read history:")
    history = receipts.get_read_history("chat1")
    for h in history:
        print(f"   {h['user_name']} read {h['message_id'][:8]}... at {h['read_at']}")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    demo()
