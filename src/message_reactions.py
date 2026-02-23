#!/usr/bin/env python3
"""
Message Reactions Module
=====================
Emoji reactions and message interactions for Bluetooth Messenger.

Features:
- Emoji reactions (like, love, laugh, etc.)
- Reply to messages
- Edit sent messages
- Delete messages
- Message status (sent, delivered, read)
- Message reactions with custom emojis
"""

import os
import json
import base64
import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path


class ReactionType(Enum):
    """Predefined reaction types"""
    LIKE = "👍"
    LOVE = "❤️"
    LAUGH = "😂"
    SURPRISE = "😮"
    SAD = "😢"
    ANGRY = "😠"
    THINK = "🤔"
    FIRE = "🔥"
    CLAP = "👏"
    HUNDRED = "💯"


class MessageStatus(Enum):
    """Message delivery status"""
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


@dataclass
class MessageReaction:
    """Message reaction"""
    reaction_id: str
    message_id: str
    user_id: str
    user_name: str
    emoji: str
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class MessageReply:
    """Reply to a message"""
    reply_id: str
    message_id: str
    original_message_id: str
    user_id: str
    user_name: str
    content: str
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class ChatMessage:
    """Enhanced chat message with reactions and replies"""
    message_id: str
    chat_id: str
    sender_id: str
    sender_name: str
    content: str
    timestamp: str
    message_type: str = "text"  # text, image, file, system
    status: str = "sent"
    
    # Reactions and replies
    reactions: List[Dict] = field(default_factory=list)
    reply_to: Optional[str] = None
    is_edited: bool = False
    edit_timestamp: Optional[str] = None
    is_deleted: bool = False
    
    # Metadata
    attachments: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class MessageReactions:
    """
    Message Reactions and Interactions Manager
    
    Features:
    - Add/remove emoji reactions
    - Reply to messages
    - Edit messages
    - Delete messages (soft delete)
    - Message status tracking
    - Reaction notifications
    """
    
    REACTION_EMOJIS = {
        "like": "👍",
        "love": "❤️",
        "laugh": "😂",
        "surprise": "😮",
        "sad": "😢",
        "angry": "😠",
        "think": "🤔",
        "fire": "🔥",
        "clap": "👏",
        "hundred": "💯"
    }
    
    def __init__(self, storage_dir: Optional[str] = None, user_id: str = "me", user_name: str = "Me"):
        # Default storage
        if storage_dir is None:
            storage_dir = Path.home() / ".bt-messenger"
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.user_id = user_id
        self.user_name = user_name
        
        self.messages_file = self.storage_dir / "messages.json"
        
        # Load messages
        self.messages: Dict[str, ChatMessage] = {}
        self.reactions: Dict[str, List[MessageReaction]] = {}
        self.replies: Dict[str, List[MessageReply]] = {}
        
        self._load_messages()
    
    # =========================================================================
    # MESSAGE OPERATIONS
    # =========================================================================
    
    def send_message(
        self,
        chat_id: str,
        content: str,
        message_type: str = "text",
        reply_to: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> ChatMessage:
        """
        Send a new message.
        
        Args:
            chat_id: Chat ID
            content: Message content
            message_type: Type of message
            reply_to: Message ID to reply to
            attachments: Optional attachments
            
        Returns:
            Created ChatMessage
        """
        message_id = self._generate_message_id(chat_id)
        
        message = ChatMessage(
            message_id=message_id,
            chat_id=chat_id,
            sender_id=self.user_id,
            sender_name=self.user_name,
            content=content,
            timestamp=datetime.now().isoformat(),
            message_type=message_type,
            status=MessageStatus.SENT.value,
            reply_to=reply_to,
            attachments=attachments or []
        )
        
        self.messages[message_id] = message
        
        # If.messages[message_id replying, add to replies
        if reply_to and reply_to in self.messages:
            reply = MessageReply(
                reply_id=self._generate_reply_id(message_id),
                message_id=message_id,
                original_message_id=reply_to,
                user_id=self.user_id,
                user_name=self.user_name,
                content=content
            )
            
            if reply_to not in self.replies:
                self.replies[reply_to] = []
            self.replies[reply_to].append(reply)
        
        self._save_messages()
        
        return message
    
    def edit_message(self, message_id: str, new_content: str) -> Optional[ChatMessage]:
        """
        Edit a sent message.
        
        Args:
            message_id: Message to edit
            new_content: New content
            
        Returns:
            Updated ChatMessage or None
        """
        if message_id not in self.messages:
            return None
        
        message = self.messages[message_id]
        
        # Can only edit own messages
        if message.sender_id != self.user_id:
            return None
        
        if message.is_deleted:
            return None
        
        message.content = new_content
        message.is_edited = True
        message.edit_timestamp = datetime.now().isoformat()
        
        self._save_messages()
        
        return message
    
    def delete_message(self, message_id: str) -> bool:
        """
        Delete a message (soft delete).
        
        Args:
            message_id: Message to delete
            
        Returns:
            True if successful
        """
        if message_id not in self.messages:
            return False
        
        # Can only delete own messages
        message = self.messages[message_id]
        if message.sender_id != self.user_id:
            return False
        
        message.is_deleted = True
        message.content = "[Message deleted]"
        
        self._save_messages()
        
        return True
    
    def get_message(self, message_id: str) -> Optional[ChatMessage]:
        """Get message by ID"""
        return self.messages.get(message_id)
    
    def get_chat_messages(
        self, 
        chat_id: str, 
        limit: int = 50,
        include_deleted: bool = False
    ) -> List[ChatMessage]:
        """Get messages for a chat"""
        messages = [
            m for m in self.messages.values()
            if m.chat_id == chat_id and (include_deleted or not m.is_deleted)
        ]
        
        # Sort by timestamp
        messages.sort(key=lambda m: m.timestamp, reverse=True)
        
        return messages[:limit]
    
    # =========================================================================
    # REACTIONS
    # =========================================================================
    
    def add_reaction(
        self,
        message_id: str,
        emoji: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> Optional[MessageReaction]:
        """
        Add reaction to a message.
        
        Args:
            message_id: Message to react to
            emoji: Emoji or reaction type
            user_id: User ID (default: current user)
            user_name: User name
            
        Returns:
            Created MessageReaction or None
        """
        if message_id not in self.messages:
            return None
        
        # Normalize emoji
        if emoji.lower() in self.REACTION_EMOJIS:
            emoji = self.REACTION_EMOJIS[emoji.lower()]
        
        if user_id is None:
            user_id = self.user_id
        if user_name is None:
            user_name = self.user_name
        
        # Check if already reacted with same emoji
        if message_id in self.reactions:
            existing = [
                r for r in self.reactions[message_id]
                if r.user_id == user_id and r.emoji == emoji
            ]
            if existing:
                return None  # Already reacted
        
        # Remove existing reaction from this user (different emoji)
        if message_id in self.reactions:
            self.reactions[message_id] = [
                r for r in self.reactions[message_id]
                if not (r.user_id == user_id)
            ]
        
        reaction = MessageReaction(
            reaction_id=self._generate_reaction_id(message_id),
            message_id=message_id,
            user_id=user_id,
            user_name=user_name,
            emoji=emoji
        )
        
        if message_id not in self.reactions:
            self.reactions[message_id] = []
        
        self.reactions[message_id].append(reaction)
        
        # Update message
        self.messages[message_id].reactions = [
            asdict(r) for r in self.reactions[message_id]
        ]
        
        self._save_messages()
        
        return reaction
    
    def remove_reaction(self, message_id: str, user_id: Optional[str] = None) -> bool:
        """
        Remove reaction from a message.
        
        Args:
            message_id: Message ID
            user_id: User ID (default: current user)
            
        Returns:
            True if removed
        """
        if user_id is None:
            user_id = self.user_id
        
        if message_id not in self.reactions:
            return False
        
        original_count = len(self.reactions[message_id])
        self.reactions[message_id] = [
            r for r in self.reactions[message_id]
            if r.user_id != user_id
        ]
        
        if len(self.reactions[message_id]) < original_count:
            # Update message
            self.messages[message_id].reactions = [
                asdict(r) for r in self.reactions[message_id]
            ]
            self._save_messages()
            return True
        
        return False
    
    def get_reactions(self, message_id: str) -> List[MessageReaction]:
        """Get all reactions for a message"""
        return self.reactions.get(message_id, [])
    
    def get_reaction_summary(self, message_id: str) -> Dict[str, int]:
        """Get reaction summary (emoji -> count)"""
        summary = {}
        
        for reaction in self.reactions.get(message_id, []):
            summary[reaction.emoji] = summary.get(reaction.emoji, 0) + 1
        
        return summary
    
    # =========================================================================
    # MESSAGE STATUS
    # =========================================================================
    
    def update_status(self, message_id: str, status: str) -> bool:
        """Update message status"""
        if message_id not in self.messages:
            return False
        
        if status in [s.value for s in MessageStatus]:
            self.messages[message_id].status = status
            self._save_messages()
            return True
        
        return False
    
    def mark_delivered(self, message_id: str) -> bool:
        """Mark message as delivered"""
        return self.update_status(message_id, MessageStatus.DELIVERED.value)
    
    def mark_read(self, message_id: str) -> bool:
        """Mark message as read"""
        return self.update_status(message_id, MessageStatus.READ.value)
    
    # =========================================================================
    # REPLIES
    # =========================================================================
    
    def get_replies(self, message_id: str) -> List[MessageReply]:
        """Get all replies to a message"""
        return self.replies.get(message_id, [])
    
    def get_reply_chain(self, message_id: str, max_depth: int = 5) -> List[ChatMessage]:
        """
        Get full reply chain for a message.
        
        Args:
            message_id: Starting message
            max_depth: Maximum depth to traverse
            
        Returns:
            List of messages in chain
        """
        chain = []
        current_id = message_id
        depth = 0
        
        while current_id and depth < max_depth:
            if current_id in self.messages:
                chain.append(self.messages[current_id])
                
                # Check if this message is a reply
                reply_to = self.messages[current_id].reply_to
                if reply_to and reply_to in self.messages:
                    current_id = reply_to
                else:
                    break
            else:
                break
            
            depth += 1
        
        return chain
    
    # =========================================================================
    # UTILITY
    # =========================================================================
    
    def search_messages(
        self,
        chat_id: Optional[str] = None,
        query: Optional[str] = None,
        sender_id: Optional[str] = None,
        has_reactions: bool = False
    ) -> List[ChatMessage]:
        """Search messages with filters"""
        results = []
        
        for message in self.messages.values():
            if message.is_deleted:
                continue
            
            if chat_id and message.chat_id != chat_id:
                continue
            
            if sender_id and message.sender_id != sender_id:
                continue
            
            if has_reactions and not message.reactions:
                continue
            
            if query:
                if query.lower() not in message.content.lower():
                    continue
            
            results.append(message)
        
        results.sort(key=lambda m: m.timestamp, reverse=True)
        return results
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    def _generate_message_id(self, chat_id: str) -> str:
        """Generate unique message ID"""
        data = f"{chat_id}{datetime.now().isoformat()}{self.user_id}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _generate_reaction_id(self, message_id: str) -> str:
        """Generate unique reaction ID"""
        data = f"{message_id}{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:12]
    
    def _generate_reply_id(self, message_id: str) -> str:
        """Generate unique reply ID"""
        data = f"reply{message_id}{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:12]
    
    def _load_messages(self):
        """Load messages from file"""
        if not self.messages_file.exists():
            return
        
        try:
            with open(self.messages_file, 'r') as f:
                data = json.load(f)
                
            # Load messages
            for msg_id, msg_data in data.get("messages", {}).items():
                self.messages[msg_id] = ChatMessage(**msg_data)
            
            # Load reactions
            for msg_id, reactions_data in data.get("reactions", {}).items():
                self.reactions[msg_id] = [
                    MessageReaction(**r) for r in reactions_data
                ]
            
            # Load replies
            for msg_id, replies_data in data.get("replies", {}).items():
                self.replies[msg_id] = [
                    MessageReply(**r) for r in replies_data
                ]
                
        except Exception as e:
            print(f"Error loading messages: {e}")
    
    def _save_messages(self):
        """Save messages to file"""
        data = {
            "messages": {
                msg_id: asdict(msg)
                for msg_id, msg in self.messages.items()
            },
            "reactions": {
                msg_id: [asdict(r) for r in reactions]
                for msg_id, reactions in self.reactions.items()
            },
            "replies": {
                msg_id: [asdict(r) for r in replies]
                for msg_id, replies in self.replies.items()
            }
        }
        
        with open(self.messages_file, 'w') as f:
            json.dump(data, f, indent=2)


def demo():
    """Demo message reactions"""
    print("=" * 60)
    print("Message Reactions Demo")
    print("=" * 60)
    
    # Create reactions manager
    reactions = MessageReactions("/tmp/bt-messenger-test", user_id="user1", user_name="Alice")
    
    # Send messages
    print("\n1. Sending messages...")
    msg1 = reactions.send_message("chat1", "Hello, world!")
    print(f"   ✓ Sent: {msg1.message_id[:8]}... - '{msg1.content}'")
    
    msg2 = reactions.send_message("chat1", "How are you?", reply_to=msg1.message_id)
    print(f"   ✓ Sent reply to msg1")
    
    msg3 = reactions.send_message("chat1", "This is great! 🔥")
    print(f"   ✓ Sent: {msg3.message_id[:8]}... - '{msg3.content}'")
    
    # Add reactions
    print("\n2. Adding reactions...")
    reactions.add_reaction(msg1.message_id, "like")
    print(f"   ✓ Like on msg1")
    
    reactions.add_reaction(msg1.message_id, "love")
    print(f"   ✓ Love on msg1")
    
    reactions.add_reaction(msg1.message_id, "fire")
    print(f"   ✓ Fire on msg1")
    
    reactions.add_reaction(msg3.message_id, "fire")
    print(f"   ✓ Fire on msg3")
    
    # Get reaction summary
    print("\n3. Reaction summary:")
    summary = reactions.get_reaction_summary(msg1.message_id)
    for emoji, count in summary.items():
        print(f"   {emoji}: {count}")
    
    # Get all reactions
    print("\n4. All reactions on msg1:")
    for r in reactions.get_reactions(msg1.message_id):
        print(f"   {r.emoji} from {r.user_name}")
    
    # Edit message
    print("\n5. Editing message...")
    edited = reactions.edit_message(msg3.message_id, "This is absolutely amazing! 🔥🚀")
    if edited:
        print(f"   ✓ Edited: '{edited.content}'")
    
    # Delete message
    print("\n6. Deleting message...")
    deleted = reactions.delete_message(msg2.message_id)
    if deleted:
        print(f"   ✓ Deleted msg2")
    
    # List messages
    print("\n7. Chat messages:")
    for msg in reactions.get_chat_messages("chat1"):
        status = "✓" if not msg.is_deleted else "✗"
        edited = " (edited)" if msg.is_edited else ""
        print(f"   {status} [{msg.status}] {msg.sender_name}: {msg.content}{edited}")
        if msg.reactions:
            reaction_str = " ".join([r['emoji'] for r in msg.reactions])
            print(f"       Reactions: {reaction_str}")
    
    # Search
    print("\n8. Searching for 'great':")
    results = reactions.search_messages(query="great")
    for m in results:
        print(f"   Found: {m.content[:50]}...")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    demo()
