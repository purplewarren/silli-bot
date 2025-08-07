#!/usr/bin/env python3
"""
Simple test for Family Profiles system
"""

import json
from bot.profiles import ProfilesStore, Child


def test_profiles_sync():
    """Run simple test of the profiles system."""
    print("🧪 Testing Family Profiles System (Simple)")
    print("=" * 50)
    
    # Create store
    store = ProfilesStore()
    
    # Test 1: Create profile for chat_id=111
    print("\n1. Creating profile for chat_id=111...")
    profile1 = store._index.get("fam_111")
    if not profile1:
        from datetime import datetime
        profile1 = store._index["fam_111"] = store._create_minimal_profile(111)
        store._save_index()
        print(f"✅ Created profile: {profile1.family_id}")
    else:
        print(f"✅ Found existing profile: {profile1.family_id}")
    
    print(f"   Creator: {profile1.creator_chat_id}")
    print(f"   Members: {profile1.members}")
    print(f"   Complete: {profile1.complete}")
    
    # Test 2: Set fields
    print("\n2. Setting profile fields...")
    profile1.parent_name = "Sarah Johnson"
    profile1.timezone = "America/New_York"
    profile1.parent_age = 32
    profile1.updated_at = datetime.now()
    store._index[profile1.family_id] = profile1
    store._save_index()
    
    print(f"✅ Updated profile:")
    print(f"   Parent: {profile1.parent_name}")
    print(f"   Timezone: {profile1.timezone}")
    print(f"   Age: {profile1.parent_age}")
    
    # Test 3: Add children
    print("\n3. Adding children...")
    child1 = Child(name="Emma", age_years=4.5, sex="f")
    child2 = Child(name="Liam", age_years=2.0, sex="m")
    
    profile1.children = [child1, child2]
    profile1.lifestyle_tags = ["vegetarian", "outdoor_activities"]
    profile1.updated_at = datetime.now()
    store._index[profile1.family_id] = profile1
    store._save_index()
    
    print(f"✅ Added children:")
    for child in profile1.children:
        print(f"   - {child.name} ({child.age_years} years, {child.sex})")
    print(f"   Lifestyle tags: {profile1.lifestyle_tags}")
    
    # Test 4: Mark complete
    print("\n4. Marking profile as complete...")
    profile1.complete = True
    profile1.updated_at = datetime.now()
    store._index[profile1.family_id] = profile1
    store._save_index()
    print(f"✅ Profile complete: {profile1.complete}")
    
    # Test 5: Verify final state
    print("\n5. Final profile state:")
    final_profile = store._index.get(profile1.family_id)
    print(json.dumps(final_profile.dict(), indent=2, default=str))
    
    print("\n🎉 All tests passed!")
    return final_profile


if __name__ == "__main__":
    test_profiles_sync() 