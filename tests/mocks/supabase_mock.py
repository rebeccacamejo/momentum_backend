"""
Mock implementations for Supabase client.
"""
from unittest.mock import Mock, AsyncMock
from typing import Dict, List, Any, Optional


class MockSupabaseTable:
    """Mock Supabase table operations."""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self._data = []
        self._filters = []
        self._select_fields = "*"
        self._order_by = None
        self._limit_count = None

    def select(self, fields: str = "*"):
        """Mock select operation."""
        self._select_fields = fields
        return self

    def insert(self, data: Dict[str, Any]):
        """Mock insert operation."""
        if isinstance(data, list):
            for item in data:
                item["id"] = f"mock-{self.table_name}-{len(self._data)}"
                self._data.append(item)
        else:
            data["id"] = f"mock-{self.table_name}-{len(self._data)}"
            self._data.append(data)
        return self

    def update(self, data: Dict[str, Any]):
        """Mock update operation."""
        for item in self._data:
            if self._matches_filters(item):
                item.update(data)
        return self

    def delete(self):
        """Mock delete operation."""
        self._data = [item for item in self._data if not self._matches_filters(item)]
        return self

    def upsert(self, data: Dict[str, Any]):
        """Mock upsert operation."""
        if isinstance(data, list):
            for item in data:
                existing = next((d for d in self._data if d.get("id") == item.get("id")), None)
                if existing:
                    existing.update(item)
                else:
                    item["id"] = f"mock-{self.table_name}-{len(self._data)}"
                    self._data.append(item)
        else:
            existing = next((d for d in self._data if d.get("id") == data.get("id")), None)
            if existing:
                existing.update(data)
            else:
                data["id"] = f"mock-{self.table_name}-{len(self._data)}"
                self._data.append(data)
        return self

    def eq(self, column: str, value: Any):
        """Mock eq filter."""
        self._filters.append(("eq", column, value))
        return self

    def neq(self, column: str, value: Any):
        """Mock neq filter."""
        self._filters.append(("neq", column, value))
        return self

    def in_(self, column: str, values: List[Any]):
        """Mock in filter."""
        self._filters.append(("in", column, values))
        return self

    def single(self):
        """Mock single result."""
        return self

    def order(self, column: str, desc: bool = False):
        """Mock order operation."""
        self._order_by = (column, desc)
        return self

    def limit(self, count: int):
        """Mock limit operation."""
        self._limit_count = count
        return self

    async def execute(self):
        """Mock execute operation."""
        filtered_data = [item for item in self._data if self._matches_filters(item)]

        if self._order_by:
            column, desc = self._order_by
            filtered_data.sort(key=lambda x: x.get(column, ""), reverse=desc)

        if self._limit_count:
            filtered_data = filtered_data[:self._limit_count]

        # Reset filters after execution
        self._filters = []
        self._order_by = None
        self._limit_count = None

        result = Mock()
        result.data = filtered_data
        return result

    def _matches_filters(self, item: Dict[str, Any]) -> bool:
        """Check if item matches all filters."""
        for filter_type, column, value in self._filters:
            if filter_type == "eq" and item.get(column) != value:
                return False
            elif filter_type == "neq" and item.get(column) == value:
                return False
            elif filter_type == "in" and item.get(column) not in value:
                return False
        return True


class MockSupabaseAuth:
    """Mock Supabase auth operations."""

    def __init__(self):
        self.current_user = None
        self.current_session = None

    async def sign_in_with_otp(self, credentials: Dict[str, Any]):
        """Mock magic link sign in."""
        return {"error": None}

    async def sign_in_with_oauth(self, provider_data: Dict[str, Any]):
        """Mock OAuth sign in."""
        return {"error": None}

    async def sign_out(self):
        """Mock sign out."""
        self.current_user = None
        self.current_session = None
        return {"error": None}

    async def refresh_session(self, refresh_token: str):
        """Mock session refresh."""
        return {
            "session": {
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 3600
            },
            "user": {"id": "test-user-id", "email": "test@example.com"}
        }

    async def set_session(self, access_token: str, refresh_token: str):
        """Mock set session."""
        self.current_session = {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
        self.current_user = {"id": "test-user-id", "email": "test@example.com"}
        return Mock(user=self.current_user)

    async def get_session(self):
        """Mock get session."""
        return {
            "data": {
                "session": self.current_session
            }
        }


class MockSupabaseStorage:
    """Mock Supabase storage operations."""

    def __init__(self):
        self.uploaded_files = {}

    def upload(self, path: str, file_data: bytes, options: Dict[str, Any] = None):
        """Mock file upload."""
        self.uploaded_files[path] = {
            "data": file_data,
            "options": options or {}
        }
        return {"error": None}

    def get_public_url(self, path: str):
        """Mock get public URL."""
        return {
            "data": {"publicUrl": f"http://test.com/{path}"}
        }

    def create_signed_url(self, path: str, expires_in: int):
        """Mock create signed URL."""
        return {
            "signedURL": f"http://test.com/signed/{path}?expires={expires_in}"
        }


class MockSupabaseClient:
    """Mock Supabase client."""

    def __init__(self):
        self.auth = MockSupabaseAuth()
        self._storage = MockSupabaseStorage()
        self._tables = {}

    def table(self, table_name: str):
        """Get or create mock table."""
        if table_name not in self._tables:
            self._tables[table_name] = MockSupabaseTable(table_name)
        return self._tables[table_name]

    @property
    def storage(self):
        """Get storage instance."""
        return Mock(from_=lambda bucket: self._storage)

    def reset_data(self):
        """Reset all mock data."""
        self._tables = {}
        self._storage = MockSupabaseStorage()
        self.auth = MockSupabaseAuth()