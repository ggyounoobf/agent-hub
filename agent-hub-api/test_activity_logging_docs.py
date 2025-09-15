import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

def test_activity_logging_api_docs():
    """Test that our activity logging API documentation is comprehensive."""
    
    # Check that the API documentation file exists
    docs_path = "ACTIVITY_LOGGING_API_DOCS.md"
    if not os.path.exists(docs_path):
        print(f"ERROR: {docs_path} not found!")
        return False
    
    # Read the documentation
    with open(docs_path, 'r') as f:
        content = f.read()
    
    # Check for key sections
    required_sections = [
        "Authentication",
        "Base URL",
        "Endpoints",
        "Get Recent Activity",
        "Get Activity by Time Range",
        "Search Activity",
        "Event Types and Examples",
        "User Events",
        "Chat Events",
        "Agent Events",
        "System Events",
        "Error Responses"
    ]
    
    missing_sections = []
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)
    
    if missing_sections:
        print(f"ERROR: Missing sections in documentation: {missing_sections}")
        return False
    
    # Check for endpoint examples
    required_endpoints = [
        "GET /api/v1/admin/activity/recent",
        "GET /api/v1/admin/activity/range",
        "POST /api/v1/admin/activity/search"
    ]
    
    missing_endpoints = []
    for endpoint in required_endpoints:
        if endpoint not in content:
            missing_endpoints.append(endpoint)
    
    if missing_endpoints:
        print(f"ERROR: Missing endpoints in documentation: {missing_endpoints}")
        return False
    
    print("All tests passed! Activity logging API documentation is comprehensive.")
    return True

if __name__ == "__main__":
    success = test_activity_logging_api_docs()
    if not success:
        sys.exit(1)