#!/usr/bin/env python3
"""
Test script to verify Supabase connection and database setup
"""

import asyncio
from loguru import logger
from agents.shared.database import (
    health_check,
    create_user,
    get_user_by_phone,
    create_trip,
    get_trip,
    create_vendor,
    get_vendor,
    get_market_rate,
    supabase,
)
from agents.shared.config import settings


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def test_connection() -> bool:
    """Test Supabase connection."""
    print_header("TEST 1: Supabase Connection")
    
    try:
        result = health_check()
        if result:
            print("✓ Supabase connection successful!")
            return True
        else:
            print("✗ Supabase connection failed!")
            return False
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        return False


def test_tables_exist() -> bool:
    """Check if all required tables exist."""
    print_header("TEST 2: Database Tables")
    
    required_tables = [
        "users",
        "trips",
        "vendors",
        "calls",
        "call_events",
        "market_rates",
    ]
    
    try:
        # Try to query each table
        for table_name in required_tables:
            try:
                response = supabase.table(table_name).select("*").limit(1).execute()
                print(f"✓ Table '{table_name}' exists")
            except Exception as e:
                print(f"✗ Table '{table_name}' not found: {str(e)}")
                return False
        
        print("\n✓ All required tables exist!")
        return True
    except Exception as e:
        logger.error(f"Table verification failed: {str(e)}")
        return False


def test_user_operations() -> bool:
    """Test user CRUD operations."""
    print_header("TEST 3: User Operations")
    
    try:
        # Create test user
        test_phone = "+919876543210"
        test_name = "Test User"
        
        print(f"Creating test user: {test_name} ({test_phone})")
        user = create_user(test_phone, test_name, "hinglish")
        
        if not user:
            print("✗ Failed to create user")
            return False
        
        print(f"✓ User created with ID: {user.get('id')}")
        
        # Retrieve user
        retrieved_user = get_user_by_phone(test_phone)
        
        if not retrieved_user:
            print("✗ Failed to retrieve user")
            return False
        
        print(f"✓ User retrieved successfully")
        print(f"  - Name: {retrieved_user.get('name')}")
        print(f"  - Language: {retrieved_user.get('preferred_language')}")
        print(f"  - Trust Score: {retrieved_user.get('trust_score')}")
        
        return True
    except Exception as e:
        logger.error(f"User operations test failed: {str(e)}")
        return False


def test_trip_operations() -> bool:
    """Test trip CRUD operations."""
    print_header("TEST 4: Trip Operations")
    
    try:
        # First create a user
        test_phone = "+919876543211"
        user = create_user(test_phone, "Trip Test User", "english")
        
        if not user:
            print("✗ Failed to create test user for trip")
            return False
        
        user_id = user.get('id')
        print(f"Created test user: {user_id}")
        
        # Create trip
        print("Creating test trip to Goa...")
        trip = create_trip(
            user_id=user_id,
            destination="Goa",
            start_date="2025-03-01",
            end_date="2025-03-05",
            party_size=4,
            budget_min=20000,
            budget_max=30000,
            budget_stretch=40000,
            services=["taxi", "homestay"],
            preferences={
                "vegetarian": False,
                "ac_required": True,
                "hindi_speaking": True,
            }
        )
        
        if not trip:
            print("✗ Failed to create trip")
            return False
        
        trip_id = trip.get('id')
        print(f"✓ Trip created with ID: {trip_id}")
        
        # Retrieve trip
        retrieved_trip = get_trip(trip_id)
        
        if not retrieved_trip:
            print("✗ Failed to retrieve trip")
            return False
        
        print("✓ Trip retrieved successfully")
        print(f"  - Destination: {retrieved_trip.get('destination')}")
        print(f"  - Party Size: {retrieved_trip.get('party_size')}")
        print(f"  - Budget: ₹{retrieved_trip.get('budget_min')} - ₹{retrieved_trip.get('budget_max')}")
        print(f"  - Status: {retrieved_trip.get('status')}")
        
        return True
    except Exception as e:
        logger.error(f"Trip operations test failed: {str(e)}")
        return False


def test_vendor_operations() -> bool:
    """Test vendor CRUD operations."""
    print_header("TEST 5: Vendor Operations")
    
    try:
        # Create test vendor
        test_phone = "+919999999999"
        test_name = "Test Taxi Service"
        
        print(f"Creating test vendor: {test_name}")
        vendor = create_vendor(
            phone_number=test_phone,
            name=test_name,
            category="taxi",
            location="Goa",
            source="google_maps",
            metadata={
                "rating": 4.5,
                "reviews": 120,
            }
        )
        
        if not vendor:
            print("✗ Failed to create vendor")
            return False
        
        vendor_id = vendor.get('id')
        print(f"✓ Vendor created with ID: {vendor_id}")
        
        # Retrieve vendor
        retrieved_vendor = get_vendor(vendor_id)
        
        if not retrieved_vendor:
            print("✗ Failed to retrieve vendor")
            return False
        
        print("✓ Vendor retrieved successfully")
        print(f"  - Name: {retrieved_vendor.get('name')}")
        print(f"  - Category: {retrieved_vendor.get('category')}")
        print(f"  - Trust Score: {retrieved_vendor.get('trust_score')}")
        print(f"  - Location: {retrieved_vendor.get('location')}")
        
        return True
    except Exception as e:
        logger.error(f"Vendor operations test failed: {str(e)}")
        return False


def test_market_rates() -> bool:
    """Test market rates retrieval."""
    print_header("TEST 6: Market Rates")
    
    try:
        print("Fetching market rates for Goa (Taxi)...")
        rate = get_market_rate("taxi", "Goa")
        
        if not rate:
            print("⚠ No market rates found (this is okay if seeding hasn't been done)")
            return True
        
        print("✓ Market rate found:")
        print(f"  - Item: {rate.get('item_description')}")
        print(f"  - Local Rate: ₹{rate.get('local_rate')}")
        print(f"  - Tourist Rate: ₹{rate.get('tourist_rate')}")
        print(f"  - Savings Potential: {((rate.get('tourist_rate', 0) - rate.get('local_rate', 0)) / rate.get('tourist_rate', 1) * 100):.1f}%")
        
        return True
    except Exception as e:
        logger.error(f"Market rates test failed: {str(e)}")
        return False


def run_all_tests():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  DesiYatra Database Connectivity Tests".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    
    print(f"\nConfiguration:")
    print(f"  Supabase URL: {settings.supabase_url}")
    print(f"  Environment: {settings.environment}")
    
    results = []
    
    # Run all tests
    results.append(("Connection", test_connection()))
    results.append(("Tables Exist", test_tables_exist()))
    
    if results[-1][1]:  # Only run operations tests if connection works
        results.append(("User Operations", test_user_operations()))
        results.append(("Trip Operations", test_trip_operations()))
        results.append(("Vendor Operations", test_vendor_operations()))
        results.append(("Market Rates", test_market_rates()))
    
    # Summary
    print_header("TEST SUMMARY")
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name:<30} {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n{'=' * 60}")
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! Database setup is complete.")
        return True
    else:
        print("✗ Some tests failed. Check the output above for details.")
        return False


if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        exit(1)
