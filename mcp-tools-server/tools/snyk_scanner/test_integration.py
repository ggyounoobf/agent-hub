#!/usr/bin/env python3
"""
Snyk Scanner Integration Test

Simple test script to verify Snyk scanner functionality.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add the tools directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.snyk_scanner.services.snyk_service import SnykService, SnykConfig
from tools.snyk_scanner.utils.path_validator import is_valid_github_url, extract_repo_info
from tools.snyk_scanner.utils.output_formatter import format_scan_report


async def test_snyk_installation():
    """Test Snyk CLI installation and authentication."""
    print("🔍 Testing Snyk CLI installation...")
    
    service = SnykService()
    result = await service.check_snyk_installation()
    
    print(f"✅ Installation check result:")
    print(json.dumps(result, indent=2))
    
    return result.get("installed", False) and result.get("authenticated", False)


async def test_path_validation():
    """Test path validation utilities."""
    print("\n🔍 Testing path validation...")
    
    # Test valid GitHub URLs
    test_urls = [
        "https://github.com/owner/repo",
        "https://github.com/microsoft/typescript",
        "https://github.com/invalid",
        "not-a-url"
    ]
    
    for url in test_urls:
        is_valid = is_valid_github_url(url)
        repo_info = extract_repo_info(url) if is_valid else None
        print(f"  {url}: {'✅' if is_valid else '❌'} {repo_info}")


async def test_project_scan():
    """Test scanning a local project."""
    print("\n🔍 Testing project scanning...")
    
    # Try to scan the current project directory
    current_dir = str(Path(__file__).parent.parent.parent.parent)
    
    service = SnykService()
    result = await service.scan_project(current_dir, "test")
    
    print(f"✅ Scan result for {current_dir}:")
    if result.success:
        print(f"  Found {len(result.vulnerabilities)} vulnerabilities")
        print(f"  Summary: {result.summary}")
    else:
        print(f"  Error: {result.error}")
    
    return result


async def main():
    """Run all tests."""
    print("🚀 Starting Snyk Scanner Integration Tests")
    print("=" * 50)
    
    try:
        # Test 1: Installation check
        installation_ok = await test_snyk_installation()
        
        # Test 2: Path validation
        await test_path_validation()
        
        # Test 3: Project scan (only if Snyk is properly installed)
        if installation_ok:
            await test_project_scan()
        else:
            print("\n⚠️  Skipping project scan test - Snyk CLI not properly configured")
            print("   Please run 'snyk auth' to authenticate")
        
        print("\n" + "=" * 50)
        print("✅ Integration tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
