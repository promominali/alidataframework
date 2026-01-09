from __future__ import annotations

"""NoSQL connection helpers (currently MongoDB)."""

from typing import Any, Optional

from .errors import MissingDriverError


def create_mongo_client(uri: str, *, username: Optional[str] = None, password: Optional[str] = None, **kwargs: Any) -> Any:
    """Create a pymongo.MongoClient.

    :param uri: MongoDB URI, e.g. mongodb://localhost:27017
    :param username: Optional username
    :param password: Optional password
    """
    try:
        from pymongo import MongoClient  # type: ignore
    except ImportError as exc:
        raise MissingDriverError("pymongo is required for MongoDB") from exc

    if username and password:
        return MongoClient(uri, username=username, password=password, **kwargs)
    return MongoClient(uri, **kwargs)

# ---------------------------------------------------------------------------
# Usage example
#
# Full CRUD example with MongoDB:
# from aliframework.nosql import create_mongo_client
#
# client = create_mongo_client("mongodb://localhost:27017")
# db = client["mydb"]
# col = db["items"]
#
# # CREATE
# col.insert_one({"_id": 1, "name": "foo"})
# # READ
# print(col.find_one({"_id": 1}))
# # UPDATE
# col.update_one({"_id": 1}, {"$set": {"name": "bar"}})
# # DELETE
# col.delete_one({"_id": 1})
#
# ---------------------------------------------------------------------------
# from aliframework.nosql import create_mongo_client
#
# client = create_mongo_client(
#     "mongodb://localhost:27017",
#     username="mongo_user",
#     password="mongo_pass",
# )
# db = client["mydb"]
# collection = db["items"]
# print(collection.count_documents({}))
