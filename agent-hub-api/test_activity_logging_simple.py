import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from app.database.models import ActivityLogType, ActivityLogSeverity
from app.models.schemas import ActivityLogCreate

def test_imports():
    """Test that our activity logging models and schemas can be imported."""
    # Test that enums can be imported
    print("ActivityLogType enum values:", list(ActivityLogType))
    print("ActivityLogSeverity enum values:", list(ActivityLogSeverity))
    
    # Test that schema can be imported
    log_data = ActivityLogCreate(
        type=ActivityLogType.USER,
        description="Test log entry",
        severity=ActivityLogSeverity.INFO
    )
    
    print("Log data type:", log_data.type)
    print("Log data type value:", log_data.type.value)
    
    print("All imports and basic tests passed!")

if __name__ == "__main__":
    test_imports()