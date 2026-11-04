"""
Backend tests for the Mergington High School Activities API.

All tests follow the AAA (Arrange-Act-Assert) pattern.
"""

import copy

import pytest
from fastapi.testclient import TestClient

from src.app import app, activities


@pytest.fixture(autouse=True)
def restore_activities():
    """Snapshot and restore the in-memory activities state around each test."""
    # Arrange (shared): preserve a deep copy of the original state
    snapshot = copy.deepcopy(activities)
    yield
    # Cleanup: restore the original state so tests stay isolated
    activities.clear()
    activities.update(snapshot)


@pytest.fixture
def client():
    return TestClient(app)


class TestRoot:
    def test_root_redirects_to_static_index(self, client):
        # Act
        response = client.get("/", follow_redirects=False)

        # Assert
        assert response.status_code in (302, 307)
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    def test_returns_all_activities(self, client):
        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data.keys() == activities.keys()

    def test_activity_has_expected_structure(self, client):
        # Arrange
        expected_fields = {"description", "schedule", "max_participants", "participants"}

        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        for name, details in response.json().items():
            assert expected_fields <= details.keys(), f"Missing fields in {name}"
            assert isinstance(details["participants"], list)
            assert isinstance(details["max_participants"], int)


class TestSignup:
    def test_signup_success_adds_participant(self, client):
        # Arrange
        activity_name = "Chess Club"
        email = "newstudent@mergington.edu"
        initial_count = len(activities[activity_name]["participants"])

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup", params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        assert email in response.json()["message"]
        assert email in activities[activity_name]["participants"]
        assert len(activities[activity_name]["participants"]) == initial_count + 1

    def test_signup_duplicate_returns_400(self, client):
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # already signed up in initial data
        assert email in activities[activity_name]["participants"]
        initial_count = len(activities[activity_name]["participants"])

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup", params={"email": email}
        )

        # Assert
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]
        assert len(activities[activity_name]["participants"]) == initial_count

    def test_signup_unknown_activity_returns_404(self, client):
        # Arrange
        activity_name = "Nonexistent Club"
        email = "student@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup", params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"


class TestUnregister:
    def test_unregister_success_removes_participant(self, client):
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # already signed up in initial data
        assert email in activities[activity_name]["participants"]
        initial_count = len(activities[activity_name]["participants"])

        # Act
        response = client.delete(
            f"/activities/{activity_name}/unregister", params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        assert email in response.json()["message"]
        assert email not in activities[activity_name]["participants"]
        assert len(activities[activity_name]["participants"]) == initial_count - 1

    def test_unregister_not_signed_up_returns_404(self, client):
        # Arrange
        activity_name = "Chess Club"
        email = "ghost@mergington.edu"
        assert email not in activities[activity_name]["participants"]

        # Act
        response = client.delete(
            f"/activities/{activity_name}/unregister", params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        assert "not signed up" in response.json()["detail"]

    def test_unregister_unknown_activity_returns_404(self, client):
        # Arrange
        activity_name = "Nonexistent Club"
        email = "student@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/unregister", params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"


class TestSignupUnregisterRoundtrip:
    def test_signup_then_unregister_restores_state(self, client):
        # Arrange
        activity_name = "Art Club"
        email = "roundtrip@mergington.edu"
        original_participants = list(activities[activity_name]["participants"])

        # Act
        signup_response = client.post(
            f"/activities/{activity_name}/signup", params={"email": email}
        )
        unregister_response = client.delete(
            f"/activities/{activity_name}/unregister", params={"email": email}
        )

        # Assert
        assert signup_response.status_code == 200
        assert unregister_response.status_code == 200
        assert activities[activity_name]["participants"] == original_participants
