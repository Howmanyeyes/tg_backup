import os

from typing import Optional, List, Union

from pydantic import BaseModel, Field

class Topic(BaseModel):
    topic_id: int = Field(..., description="Unique identifier for the forum topic (thread)")
    name: str = Field(..., description="Name of the forum topic")

class Chat(BaseModel):
    chat_id: int = Field(..., description="Unique identifier for the chat")
    chat_type: str = Field(..., description="Type of chat: 'private', 'group', 'supergroup', or 'channel'")
    title: Optional[str] = Field(None, description="Title of the chat (if applicable)")
    username: Optional[str] = Field(None, description="Username for the chat (if applicable)")
    topics: Optional[List[Topic]] = Field(None, description="List of forum topics for chats that support topics")

class ChatsStorage(BaseModel):
    chats: List[Chat] = Field(default_factory=list, description="List of chats where the bot is present")
    file_path: str
    workchat: Optional[int] = Field(default=None)
    mode: Optional[str] = Field(default=None)

    def add_chat(self, chat: Chat) -> None:
        """
        Add a new chat or update an existing one by chat_id.
        """
        for idx, existing_chat in enumerate(self.chats):
            if existing_chat.chat_id == chat.chat_id:
                self.chats[idx] = chat
                return
        self.chats.append(chat)

    def delete_chat(self, chat_id: int) -> bool:
        """
        Delete a chat by its chat_id.
        
        Returns:
            bool: True if the chat was found and deleted, False otherwise.
        """
        for idx, existing_chat in enumerate(self.chats):
            if existing_chat.chat_id == chat_id:
                del self.chats[idx]
                return True
        return False

    def save(self) -> None:
        """
        Save the storage to a JSON file.
        """
        with open(self.file_path, 'w', encoding='utf-8') as f:
            f.write(self.model_dump_json(indent=2))

    def load(self) -> None:
        """
        Load the storage from a JSON file. If the file does not exist, return an empty storage.
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = f.read()
                loaded_storage = self.__class__.model_validate_json(data)
                self.chats = loaded_storage.chats
                self.workchat = loaded_storage.workchat
                self.mode = loaded_storage.mode
        except FileNotFoundError:
            self.chats=[]

class FileUpload(BaseModel):
    name: str = Field(..., description="Name of the file")
    upload_id: str = Field("", description="Upload identifier for the file (default empty)")

class FolderUpload(BaseModel):
    name: str = Field(..., description="Name of the folder")
    upload_id: str = Field("", description="Upload identifier for the folder (default empty)")
    children: Optional[List[Union["FileUpload", "FolderUpload"]]] = Field(default_factory=list, description="List of files or subfolders contained in the folder")


class BackupStorage(BaseModel):
    backups: List[FolderUpload] = Field(default_factory=list, description="List of root backup folders")
    file_path: str

    def add_backup(self, backup: FolderUpload) -> None:
        """
        Add a new backup or update an existing one by folder name.
        """
        for idx, existing_backup in enumerate(self.backups):
            if existing_backup.name == backup.name:
                self.backups[idx] = backup
                return
        self.backups.append(backup)

    def delete_backup(self, backup_name: str) -> bool:
        """
        Delete a backup by its folder name.
        
        Returns:
            bool: True if the backup was found and deleted, False otherwise.
        """
        for idx, existing_backup in enumerate(self.backups):
            if existing_backup.name == backup_name:
                del self.backups[idx]
                return True
        return False

    def save(self) -> None:
        """
        Save the backup storage to a JSON file.
        """
        with open(self.file_path, 'w', encoding='utf-8') as f:
            f.write(self.model_dump_json(indent=2))

    def load(self) -> None:
        """
        Load the backup storage from a JSON file. If the file does not exist, resets backups to empty.
        """
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = f.read()
                loaded_storage = self.__class__.model_validate_json(data)
                self.backups = loaded_storage.backups
        else:
            self.backups = []