# Test file model creation
import uuid
from app.database.models import File, generate_uuid

def test_file_model():
    """Test creating a File instance."""
    try:
        # Test 1: Create with explicit ID
        file_id = generate_uuid()
        file1 = File(
            id=file_id,
            name="test1.pdf",
            path="/tmp/test1.pdf",
            content_type="application/pdf",
            size=1024,
            user_id="user1"
        )
        print("Test 1 passed: File created with explicit ID")
        print(f"  ID: {file1.id}")
        
        # Test 2: Create without ID (should use default)
        file2 = File(
            name="test2.pdf",
            path="/tmp/test2.pdf",
            content_type="application/pdf",
            size=2048,
            user_id="user2"
        )
        print("Test 2 passed: File created without explicit ID")
        print(f"  ID: {file2.id}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_file_model()