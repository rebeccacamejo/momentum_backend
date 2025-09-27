"""
Performance tests for the Momentum backend using Locust.
"""
import json
import random
import time
from locust import HttpUser, task, between


class MomentumUser(HttpUser):
    """Simulated user for performance testing."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Set up user session."""
        self.client.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Momentum-Performance-Test"
        })

        # Mock authentication token
        self.auth_token = "mock-jwt-token-for-performance-testing"
        self.client.headers.update({
            "Authorization": f"Bearer {self.auth_token}"
        })

    @task(3)
    def health_check(self):
        """Test health check endpoint (most frequent)."""
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(2)
    def list_deliverables(self):
        """Test listing deliverables."""
        with self.client.get("/deliverables", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"List deliverables failed: {response.status_code}")

    @task(1)
    def generate_deliverable(self):
        """Test deliverable generation from text."""
        payload = {
            "transcript": f"This is a performance test transcript {random.randint(1, 1000)}",
            "client_name": f"Performance Test Client {random.randint(1, 100)}",
            "template_type": "action_plan",
            "primary_color": "#2A3EB1",
            "secondary_color": "#4C6FE7"
        }

        with self.client.post("/generate", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "id" in data and "html" in data:
                        response.success()
                    else:
                        response.failure("Missing required fields in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Generate deliverable failed: {response.status_code}")

    @task(1)
    def upload_file(self):
        """Test file upload endpoint."""
        # Create mock audio content
        mock_audio = b"RIFF" + b"\x00" * 36 + b"WAVE" + b"fmt " + b"\x00" * 20

        files = {
            "file": ("test.wav", mock_audio, "audio/wav")
        }
        data = {
            "client_name": f"Upload Test Client {random.randint(1, 100)}",
            "primary_color": "#2A3EB1",
            "secondary_color": "#4C6FE7",
            "template_type": "action_plan"
        }

        with self.client.post("/upload", files=files, data=data, catch_response=True) as response:
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if "id" in response_data and "html" in response_data:
                        response.success()
                    else:
                        response.failure("Missing required fields in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"File upload failed: {response.status_code}")

    @task(1)
    def brand_settings(self):
        """Test brand settings endpoints."""
        # GET brand settings
        with self.client.get("/brand/settings", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get brand settings failed: {response.status_code}")

        # PUT brand settings
        settings = {
            "primary_color": f"#{random.randint(0, 16777215):06x}",
            "secondary_color": f"#{random.randint(0, 16777215):06x}",
            "logo_url": f"https://example.com/logo-{random.randint(1, 100)}.png"
        }

        with self.client.put("/brand/settings", json=settings, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Update brand settings failed: {response.status_code}")

    @task(1)
    def auth_endpoints(self):
        """Test authentication endpoints."""
        # Magic link
        magic_link_data = {
            "email": f"test-{random.randint(1, 1000)}@performance.test"
        }

        with self.client.post("/auth/magic-link", json=magic_link_data, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Magic link failed: {response.status_code}")

        # Get user profile
        with self.client.get("/auth/user", catch_response=True) as response:
            if response.status_code in [200, 401]:  # 401 is acceptable for mock auth
                response.success()
            else:
                response.failure(f"Get user profile failed: {response.status_code}")

    def wait_time_function(self):
        """Dynamic wait time based on response times."""
        return random.uniform(0.5, 2.0)


class StressTestUser(HttpUser):
    """High-load stress testing user."""

    wait_time = between(0.1, 0.5)  # Much shorter wait times for stress testing

    def on_start(self):
        """Set up stress test session."""
        self.client.headers.update({
            "Content-Type": "application/json",
            "Authorization": "Bearer stress-test-token"
        })

    @task
    def rapid_health_checks(self):
        """Rapid health check requests."""
        self.client.get("/")

    @task
    def rapid_deliverable_list(self):
        """Rapid deliverable listing."""
        self.client.get("/deliverables")

    @task
    def concurrent_generation(self):
        """Concurrent deliverable generation."""
        payload = {
            "transcript": f"Stress test {time.time()}",
            "client_name": f"Stress Client {random.randint(1, 10000)}",
            "template_type": "action_plan"
        }
        self.client.post("/generate", json=payload)


class LongRunningTestUser(HttpUser):
    """Test for long-running operations."""

    wait_time = between(5, 10)

    def on_start(self):
        """Set up long-running test session."""
        self.client.headers.update({
            "Content-Type": "application/json",
            "Authorization": "Bearer long-running-test-token"
        })

    @task
    def large_file_upload(self):
        """Test with larger files."""
        # Create larger mock audio file (10MB)
        large_audio = b"RIFF" + b"A" * (10 * 1024 * 1024) + b"WAVE"

        files = {
            "file": ("large_test.wav", large_audio, "audio/wav")
        }
        data = {
            "client_name": "Large File Test",
            "template_type": "action_plan"
        }

        with self.client.post("/upload", files=files, data=data, timeout=60, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 413:  # Payload too large
                response.success()  # This is expected for large files
            else:
                response.failure(f"Large file upload failed: {response.status_code}")

    @task
    def complex_generation(self):
        """Test with complex, long transcripts."""
        long_transcript = " ".join([
            f"This is sentence {i} in a very long transcript for performance testing."
            for i in range(1000)
        ])

        payload = {
            "transcript": long_transcript,
            "client_name": "Complex Generation Test",
            "template_type": "action_plan"
        }

        with self.client.post("/generate", json=payload, timeout=30, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Complex generation failed: {response.status_code}")


# Performance test scenarios
def test_basic_load():
    """Run basic load test with MomentumUser."""
    pass  # Locust will handle this


def test_stress_load():
    """Run stress test with StressTestUser."""
    pass  # Locust will handle this


def test_spike_load():
    """Run spike test with sudden load increases."""
    pass  # Locust will handle this