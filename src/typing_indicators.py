#!/usr/bin/env python3
"""
Typing Indicators Module
======================
Real-time typing status for Bluetooth Messenger.

Features:
- Start/stop typing indicators
- Typing timeout (auto-stop after inactivity)
- Broadcast typing status to contacts
- Multiple chat support
- Thread-safe operations
"""

import threading
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict


class TypingStatus(Enum):
    """Typing status values"""
    TYPING = "typing"
    STOPPED = "stopped"
    STARTED = "started"


@dataclass
class TypingEvent:
    """Typing event"""
    chat_id: str
    user_id: str
    user_name: str
    status: str
    timestamp: str


class TypingIndicators:
    """
    Real-time Typing Indicators Manager
    
    Features:
    - Start/stop typing
    - Auto-timeout (stop after N seconds)
    - Broadcast to multiple users
    - Callback handlers for UI updates
    """
    
    DEFAULT_TIMEOUT = 5  # seconds before auto-stop
    
    def __init__(self, user_id: str = "me", user_name: str = "Me"):
        self.user_id = user_id
        self.user_name = user_name
        
        # Track typing status per chat
        self.typing_users: Dict[str, Dict[str, TypingEvent]] = defaultdict(dict)
        
        # Callbacks
        self.on_typing_started: Optional[Callable] = None
        self.on_typing_stopped: Optional[Callable] = None
        self.on_broadcast: Optional[Callable] = None
        
        # Lock for thread safety
        self._lock = threading.Lock()
    
    # =========================================================================
    # TYPING OPERATIONS
    # =========================================================================
    
    def start_typing(self, chat_id: str) -> TypingEvent:
        """
        Start typing in a chat.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            TypingEvent
        """
        with self._lock:
            event = TypingEvent(
                chat_id=chat_id,
                user_id=self.user_id,
                user_name=self.user_name,
                status=TypingStatus.STARTED.value,
                timestamp=datetime.now().isoformat()
            )
            
            self.typing_users[chat_id][self.user_id] = event
            
            # Notify callback
            if self.on_typing_started:
                self.on_typing_started(chat_id, self.user_id, self.user_name)
            
            # Schedule auto-stop
            self._schedule_auto_stop(chat_id, self.user_id)
            
            return event
    
    def stop_typing(self, chat_id: str) -> Optional[TypingEvent]:
        """
        Stop typing in a chat.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            TypingEvent or None
        """
        with self._lock:
            if chat_id in self.typing_users and self.user_id in self.typing_users[chat_id]:
                event = self.typing_users[chat_id][self.user_id]
                event.status = TypingStatus.STOPPED.value
                event.timestamp = datetime.now().isoformat()
                
                # Notify callback
                if self.on_typing_stopped:
                    self.on_typing_stopped(chat_id, self.user_id, self.user_name)
                
                # Remove from active typing
                del self.typing_users[chat_id][self.user_id]
                
                if not self.typing_users[chat_id]:
                    del self.typing_users[chat_id]
                
                return event
            
            return None
    
    def is_typing(self, chat_id: str, user_id: Optional[str] = None) -> bool:
        """
        Check if someone is typing.
        
        Args:
            chat_id: Chat ID
            user_id: Specific user ID (optional)
            
        Returns:
            True if typing
        """
        with self._lock:
            if chat_id not in self.typing_users:
                return False
            
            if user_id:
                return user_id in self.typing_users[chat_id]
            
            return len(self.typing_users[chat_id]) > 0
    
    def get_typing_users(self, chat_id: str) -> list:
        """
        Get all users currently typing in a chat.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            List of typing users
        """
        with self._lock:
            if chat_id not in self.typing_users:
                return []
            
            return [
                {
                    "user_id": user_id,
                    "user_name": event.user_name,
                    "timestamp": event.timestamp
                }
                for user_id, event in self.typing_users[chat_id].items()
            ]
    
    def get_typing_text(self, chat_id: str) -> str:
        """
        Get human-readable typing status text.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            Formatted typing text
        """
        users = self.get_typing_users(chat_id)
        
        if not users:
            return ""
        
        if len(users) == 1:
            return f"{users[0]['user_name']} is typing..."
        
        if len(users) == 2:
            return f"{users[0]['user_name']} and {users[1]['user_name']} are typing..."
        
        return f"{users[0]['user_name']} and {len(users)-1} others are typing..."
    
    def clear_typing(self, chat_id: str):
        """Clear all typing status for a chat"""
        with self._lock:
            if chat_id in self.typing_users:
                self.typing_users[chat_id].clear()
                del self.typing_users[chat_id]
    
    # =========================================================================
    # RECEIVE TYPING STATUS
    # =========================================================================
    
    def receive_typing_status(
        self,
        chat_id: str,
        user_id: str,
        user_name: str,
        status: str
    ) -> Optional[TypingEvent]:
        """
        Receive typing status from another user.
        
        Args:
            chat_id: Chat ID
            user_id: User ID
            user_name: User name
            status: "started" or "stopped"
            
        Returns:
            TypingEvent
        """
        # Don't process own typing events
        if user_id == self.user_id:
            return None
        
        with self._lock:
            if status == TypingStatus.STARTED.value:
                event = TypingEvent(
                    chat_id=chat_id,
                    user_id=user_id,
                    user_name=user_name,
                    status=status,
                    timestamp=datetime.now().isoformat()
                )
                self.typing_users[chat_id][user_id] = event
                
                # Notify callback
                if self.on_typing_started:
                    self.on_typing_started(chat_id, user_id, user_name)
                
                # Schedule auto-cleanup
                self._schedule_auto_stop(chat_id, user_id)
                
                return event
                
            elif status == TypingStatus.STOPPED.value:
                if chat_id in self.typing_users and user_id in self.typing_users[chat_id]:
                    del self.typing_users[chat_id][user_id]
                    
                    if not self.typing_users[chat_id]:
                        del self.typing_users[chat_id]
                    
                    # Notify callback
                    if self.on_typing_stopped:
                        self.on_typing_stopped(chat_id, user_id, user_name)
                    
                    return TypingEvent(
                        chat_id=chat_id,
                        user_id=user_id,
                        user_name=user_name,
                        status=status,
                        timestamp=datetime.now().isoformat()
                    )
        
        return None
    
    # =========================================================================
    # SERIALIZATION
    # =========================================================================
    
    def to_json(self) -> str:
        """Serialize to JSON"""
        with self._lock:
            data = {
                chat_id: {
                    user_id: asdict(event)
                    for user_id, event in users.items()
                }
                for chat_id, users in self.typing_users.items()
            }
            return json.dumps(data)
    
    def from_json(self, json_str: str):
        """Deserialize from JSON"""
        data = json.loads(json_str)
        
        with self._lock:
            self.typing_users = defaultdict(dict)
            for chat_id, users in data.items():
                for user_id, event_data in users.items():
                    self.typing_users[chat_id][user_id] = TypingEvent(**event_data)
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    def _schedule_auto_stop(self, chat_id: str, user_id: str):
        """Schedule auto-stop after timeout"""
        def stop_after_timeout():
            time.sleep(self.DEFAULT_TIMEOUT)
            
            with self._lock:
                # Check if still typing
                if (chat_id in self.typing_users and 
                    user_id in self.typing_users[chat_id]):
                    # Auto-stop
                    event = self.typing_users[chat_id][user_id]
                    event.status = TypingStatus.STOPPED.value
                    event.timestamp = datetime.now().isoformat()
                    
                    del self.typing_users[chat_id][user_id]
                    
                    if not self.typing_users[chat_id]:
                        del self.typing_users[chat_id]
                    
                    # Notify callback
                    if self.on_typing_stopped:
                        self.on_typing_stopped(chat_id, user_id, event.user_name)
        
        thread = threading.Thread(target=stop_after_timeout, daemon=True)
        thread.start()
    
    # =========================================================================
    # CALLBACK HANDLERS
    # =========================================================================
    
    def set_typing_started_handler(self, callback: Callable):
        """Set callback for typing started"""
        self.on_typing_started = callback
    
    def set_typing_stopped_handler(self, callback: Callable):
        """Set callback for typing stopped"""
        self.on_typing_stopped = callback
    
    def set_broadcast_handler(self, callback: Callable):
        """Set callback for broadcasting to network"""
        self.on_broadcast = callback


def demo():
    """Demo typing indicators"""
    print("=" * 60)
    print("Typing Indicators Demo")
    print("=" * 60)
    
    # Create typing manager
    typing = TypingIndicators(user_id="alice", user_name="Alice")
    
    # Set up callbacks
    def on_started(chat, user, name):
        print(f"  🔔 {name} started typing in {chat}")
    
    def on_stopped(chat, user, name):
        print(f"  🔔 {name} stopped typing in {chat}")
    
    typing.set_typing_started_handler(on_started)
    typing.set_typing_stopped_handler(on_stopped)
    
    # Start typing
    print("\n1. Alice starts typing in chat1...")
    typing.start_typing("chat1")
    print(f"   Is typing: {typing.is_typing('chat1')}")
    print(f"   Typing users: {typing.get_typing_users('chat1')}")
    
    # Wait for auto-stop
    print("\n2. Waiting for auto-timeout (5 seconds)...")
    time.sleep(6)
    print(f"   Is typing: {typing.is_typing('chat1')}")
    
    # Start and manually stop
    print("\n3. Alice starts typing again...")
    typing.start_typing("chat1")
    print(f"   Text: {typing.get_typing_text('chat1')}")
    
    print("\n4. Alice stops typing manually...")
    typing.stop_typing("chat1")
    print(f"   Is typing: {typing.is_typing('chat1')}")
    
    # Simulate receiving from another user
    print("\n5. Receiving typing status from Bob...")
    typing.receive_typing_status("chat1", "bob", "Bob", "started")
    print(f"   Text: {typing.get_typing_text('chat1')}")
    
    typing.receive_typing_status("chat1", "bob", "Bob", "stopped")
    print(f"   Text after stop: '{typing.get_typing_text('chat1')}'")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    demo()
