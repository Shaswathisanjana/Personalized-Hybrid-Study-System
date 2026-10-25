"""Single MongoDB persistence layer shared by the PHSS AI service."""
from pymongo import MongoClient
from pymongo.database import Database
from app.core.config import settings

_client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
_database: Database = _client[settings.database_name]

def get_db() -> Database:
    return _database

def ping_database() -> bool:
    _client.admin.command("ping")
    return True
