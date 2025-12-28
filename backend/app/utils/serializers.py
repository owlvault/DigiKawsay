"""Data serialization utilities."""

from datetime import datetime, date
from typing import Any, Dict
from bson import ObjectId


def serialize_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize a document for MongoDB storage.
    
    Converts datetime objects to ISO strings and handles ObjectId.
    """
    result = {}
    for key, value in doc.items():
        if key == "_id":
            continue  # Skip MongoDB's _id field
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, date):
            result[key] = value.isoformat()
        elif isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, dict):
            result[key] = serialize_document(value)
        elif isinstance(value, list):
            result[key] = [
                serialize_document(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def deserialize_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Remove _id from MongoDB document."""
    if doc and "_id" in doc:
        doc.pop("_id")
    return doc
