"""
Tests for the Mergington High School API

Tests cover:
- Getting all activities
- Signing up for activities
- Unregistering from activities
- Error cases and edge conditions
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {}
    for name, details in activities.items():
        original_activities[name] = {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
    
    yield
    
    # Restore original state after test
    for name in activities:
        activities[name]["participants"] = original_activities[name]["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root endpoint redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_200(self, client):
        """Test that getting activities returns 200 status"""
        response = client.get("/activities")
        assert response.status_code == 200
    
    def test_get_activities_returns_dict(self, client):
        """Test that activities are returned as a dictionary"""
        response = client.get("/activities")
        data = response.json()
        assert isinstance(data, dict)
    
    def test_get_activities_has_expected_keys(self, client):
        """Test that each activity has expected keys"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)
    
    def test_get_activities_contains_expected_activities(self, client):
        """Test that response contains some expected activities"""
        response = client.get("/activities")
        data = response.json()
        
        # Check for a few known activities
        assert "Soccer Team" in data
        assert "Programming Class" in data
        assert "Chess Club" in data


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Soccer%20Team/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Soccer Team" in data["message"]
    
    def test_signup_adds_participant(self, client):
        """Test that signup actually adds the participant to the activity"""
        email = "newstudent@mergington.edu"
        client.post(f"/activities/Basketball%20Club/signup?email={email}")
        
        # Verify the participant was added
        response = client.get("/activities")
        data = response.json()
        assert email in data["Basketball Club"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_duplicate_email(self, client):
        """Test that signing up twice with the same email fails"""
        email = "duplicate@mergington.edu"
        activity = "Drama Club"
        
        # First signup should succeed
        response1 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_multiple_students_same_activity(self, client):
        """Test that multiple students can sign up for the same activity"""
        activity = "Art Workshop"
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for email in emails:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all participants were added
        response = client.get("/activities")
        data = response.json()
        for email in emails:
            assert email in data["Art Workshop"]["participants"]


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        # First sign up
        email = "unregister.test@mergington.edu"
        activity = "Science Club"
        client.post(f"/activities/{activity}/signup?email={email}")
        
        # Then unregister
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Unregistered" in data["message"]
    
    def test_unregister_removes_participant(self, client):
        """Test that unregister actually removes the participant"""
        email = "remove.me@mergington.edu"
        activity = "Math Olympiad"
        
        # Sign up
        client.post(f"/activities/{activity}/signup?email={email}")
        
        # Verify participant was added
        response = client.get("/activities")
        data = response.json()
        assert email in data[activity]["participants"]
        
        # Unregister
        client.delete(f"/activities/{activity}/unregister?email={email}")
        
        # Verify participant was removed
        response = client.get("/activities")
        data = response.json()
        assert email not in data[activity]["participants"]
    
    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregister from an activity that doesn't exist"""
        response = client.delete(
            "/activities/Fake%20Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_unregister_not_signed_up(self, client):
        """Test unregister when student is not signed up"""
        response = client.delete(
            "/activities/Soccer%20Team/unregister?email=notsignedup@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"].lower()
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering a pre-existing participant"""
        # Chess Club has pre-existing participants
        email = "michael@mergington.edu"
        activity = "Chess Club"
        
        # Verify participant exists
        response = client.get("/activities")
        data = response.json()
        assert email in data[activity]["participants"]
        
        # Unregister
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        
        # Verify participant was removed
        response = client.get("/activities")
        data = response.json()
        assert email not in data[activity]["participants"]


class TestIntegrationScenarios:
    """Integration tests for complete workflows"""
    
    def test_full_signup_unregister_cycle(self, client):
        """Test complete cycle: signup then unregister"""
        email = "cycle.test@mergington.edu"
        activity = "Basketball Club"
        
        # Initial check
        response = client.get("/activities")
        data = response.json()
        initial_count = len(data[activity]["participants"])
        
        # Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify added
        response = client.get("/activities")
        data = response.json()
        assert len(data[activity]["participants"]) == initial_count + 1
        assert email in data[activity]["participants"]
        
        # Unregister
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        
        # Verify removed
        response = client.get("/activities")
        data = response.json()
        assert len(data[activity]["participants"]) == initial_count
        assert email not in data[activity]["participants"]
    
    def test_multiple_activities_same_student(self, client):
        """Test that a student can sign up for multiple activities"""
        email = "multi.activity@mergington.edu"
        activities_list = ["Soccer Team", "Drama Club", "Art Workshop"]
        
        # Sign up for multiple activities
        for activity in activities_list:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify student is in all activities
        response = client.get("/activities")
        data = response.json()
        for activity in activities_list:
            assert email in data[activity]["participants"]
