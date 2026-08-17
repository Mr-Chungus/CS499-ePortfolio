"""MongoDB data-access layer for the CS-340 Animal Shelter dashboard.

This class keeps all database-specific logic in one place. The dashboard does
not need to know how MongoDB connections, ObjectIds, indexes, validation, or
audit records are handled; it simply calls the CRUD methods defined here.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from bson.objectid import ObjectId
from pymongo import ASCENDING, MongoClient
from pymongo.errors import PyMongoError

# Validation is kept in its own module so the same rules can be reused and tested
# independently from the MongoDB connection code.
from validation import normalize_animal_document, validate_animal_document

LOGGER = logging.getLogger(__name__)


class AnimalShelter:
    """Provide safer CRUD operations for the AAC animals collection."""

    def __init__(
        self,
        username: str,
        password: str,
        host: str,
        port: int,
        database: str,
        collection: str,
    ) -> None:
        """Create the MongoDB client, select collections, and verify access."""
        # Required connection values are checked before building the URI so a
        # configuration problem produces a clear error as early as possible.
        if not all((username, password, host, database, collection)):
            raise ValueError("MongoDB connection values cannot be empty.")

        # authSource=admin matches the AAC environment's authentication setup.
        # A five-second selection timeout prevents the application from hanging
        # indefinitely when the MongoDB server cannot be reached.
        uri = f"mongodb://{username}:{password}@{host}:{int(port)}/?authSource=admin"
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)

        # Store references to the main animal collection and a separate audit
        # collection used to record create/update/delete activity.
        self.database = self.client[database]
        self.collection = self.database[collection]
        self.audit_collection = self.database["animal_audit"]

        # Fail fast so configuration, authentication, or network problems are
        # visible at startup instead of appearing during a later query.
        self.client.admin.command("ping")

        # Ensure the indexes expected by the application exist. MongoDB safely
        # reuses indexes with the same names instead of creating duplicates.
        self._ensure_indexes()

    @classmethod
    def from_config(cls, config: Any) -> "AnimalShelter":
        """Create the data layer from an AppConfig-like configuration object."""
        # This factory keeps app.py from needing to know the constructor order.
        return cls(
            username=config.db_user,
            password=config.db_password,
            host=config.db_host,
            port=config.db_port,
            database=config.db_name,
            collection=config.db_collection,
        )

    def _ensure_indexes(self) -> None:
        """Create indexes used by dashboard filtering and audit lookups."""
        # Single-field indexes support common lookups in the animal collection.
        self.collection.create_index(
            [("animal_type", ASCENDING)], name="idx_animal_type"
        )
        self.collection.create_index([("breed", ASCENDING)], name="idx_breed")

        # The compound index follows the fields commonly involved in rescue
        # candidate filtering and can reduce collection scans as data grows.
        self.collection.create_index(
            [
                ("animal_type", ASCENDING),
                ("breed", ASCENDING),
                ("sex_upon_outcome", ASCENDING),
                ("age_upon_outcome_in_weeks", ASCENDING),
            ],
            name="idx_rescue_filter",
        )

        # Audit indexes support finding changes by time or by affected document.
        self.audit_collection.create_index(
            [("timestamp", ASCENDING)], name="idx_audit_timestamp"
        )
        self.audit_collection.create_index(
            [("document_id", ASCENDING)], name="idx_audit_document"
        )

    @staticmethod
    def _normalize_id(value: Any) -> Any:
        """Convert valid string ObjectIds back into BSON ObjectId instances."""
        # Dash needs IDs represented as serializable strings, while MongoDB uses
        # ObjectId values. This converts IDs back before database operations.
        if isinstance(value, str) and ObjectId.is_valid(value):
            return ObjectId(value)
        return value

    def _normalize_filter(
        self, query: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Return a copy of a query with a normalized MongoDB _id when present."""
        normalized = dict(query or {})
        if "_id" in normalized:
            normalized["_id"] = self._normalize_id(normalized["_id"])
        return normalized

    def _audit(
        self,
        operation: str,
        document_id: Any,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Write a best-effort audit record for a database modification."""
        # Store a UTC timestamp so audit events are unambiguous across systems.
        record = {
            "operation": operation,
            "document_id": str(document_id) if document_id is not None else None,
            "timestamp": datetime.now(timezone.utc),
            "details": details or {},
        }

        try:
            self.audit_collection.insert_one(record)
        except PyMongoError:
            # An audit failure is logged but does not undo the primary operation.
            # For this project, keeping the application usable takes priority.
            LOGGER.exception("Unable to write audit record")

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and insert one animal record, returning the new record ID."""
        try:
            # Reject incomplete/invalid records before sending them to MongoDB.
            validate_animal_document(data)
            document = normalize_animal_document(data)

            # insert_one is intentionally used because the dashboard creates one
            # animal at a time and should return that document's unique ID.
            result = self.collection.insert_one(document)

            # Record which fields were created without copying the full document
            # into the audit collection.
            self._audit("create", result.inserted_id, {"fields": sorted(document)})

            return {"success": True, "inserted_id": str(result.inserted_id)}
        except (ValueError, PyMongoError) as exc:
            # Validation and MongoDB failures are both reported to the caller and
            # logged with a traceback for troubleshooting.
            LOGGER.exception("Insert failed")
            return {"success": False, "error": str(exc)}

    def read(
        self,
        query: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, int]] = None,
        limit: int = 0,
        sort: Optional[Iterable[Tuple[str, int]]] = None,
    ) -> List[Dict[str, Any]]:
        """Read matching records with optional projection, sorting, and limit."""
        try:
            # Normalize any _id value before sending the query to MongoDB.
            cursor = self.collection.find(self._normalize_filter(query), projection)

            # Let MongoDB perform sorting when requested instead of sorting the
            # complete result set later in application code.
            if sort:
                cursor = cursor.sort(list(sort))

            # A positive limit helps callers avoid loading an unnecessarily large
            # result set. Zero preserves MongoDB's default of no explicit limit.
            if limit and limit > 0:
                cursor = cursor.limit(int(limit))

            return list(cursor)
        except PyMongoError:
            LOGGER.exception("Query failed")
            return []

    def update(
        self,
        query: Dict[str, Any],
        new_data: Dict[str, Any],
        many: bool = False,
    ) -> Dict[str, Any]:
        """Update one record by default, or many only when explicitly requested."""
        # An empty MongoDB filter matches every document. Reject it to prevent an
        # accidental bulk update caused by missing filter criteria.
        if not query:
            return {"success": False, "error": "Update filter cannot be empty."}

        try:
            # Partial validation allows an update to contain only changed fields.
            validate_animal_document(new_data, partial=True)
            normalized_data = normalize_animal_document(new_data)
            normalized_query = self._normalize_filter(query)

            # The data layer adds $set so dashboard code does not need to know
            # MongoDB update-operator syntax.
            update_doc = {"$set": normalized_data}

            # update_one is the safer default. Bulk changes require many=True so
            # they must be requested intentionally by the caller.
            result = (
                self.collection.update_many(normalized_query, update_doc)
                if many
                else self.collection.update_one(normalized_query, update_doc)
            )

            # Keep an audit trail of the filter and fields involved in the change.
            self._audit(
                "update_many" if many else "update",
                normalized_query.get("_id"),
                {
                    "filter": str(normalized_query),
                    "updated_fields": sorted(normalized_data),
                },
            )

            # matched_count distinguishes "record not found" from "record found
            # but values were unchanged," which modified_count alone cannot do.
            return {
                "success": True,
                "matched_count": result.matched_count,
                "modified_count": result.modified_count,
            }
        except (ValueError, PyMongoError) as exc:
            LOGGER.exception("Update failed")
            return {"success": False, "error": str(exc)}

    def delete(self, query: Dict[str, Any], many: bool = False) -> Dict[str, Any]:
        """Delete one record by default, or many only when explicitly requested."""
        # Empty filters are rejected because delete_many({}) would remove every
        # document in the collection.
        if not query:
            return {"success": False, "error": "Delete filter cannot be empty."}

        try:
            normalized_query = self._normalize_filter(query)

            # delete_one is the safe default. many=True is required for an
            # intentional bulk-delete operation.
            result = (
                self.collection.delete_many(normalized_query)
                if many
                else self.collection.delete_one(normalized_query)
            )

            # Record what was deleted and how many records matched the operation.
            self._audit(
                "delete_many" if many else "delete",
                normalized_query.get("_id"),
                {"filter": str(normalized_query), "deleted_count": result.deleted_count},
            )

            return {"success": True, "deleted_count": result.deleted_count}
        except PyMongoError as exc:
            LOGGER.exception("Delete failed")
            return {"success": False, "error": str(exc)}

    def count(self, query: Optional[Dict[str, Any]] = None) -> int:
        """Return the number of documents matching an optional query."""
        try:
            # count_documents asks MongoDB for a count without transferring all
            # matching records to Python just to calculate len(...).
            return self.collection.count_documents(self._normalize_filter(query))
        except PyMongoError:
            LOGGER.exception("Count failed")
            return 0

    def close(self) -> None:
        """Close the MongoDB client and release its connection resources."""
        self.client.close()
