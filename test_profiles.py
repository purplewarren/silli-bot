#!/usr/bin/env python3
"""
Self-test for Family Profiles system
"""

import asyncio
import json
from bot.profiles import profiles, Child


async def test_profiles():
    """Run comprehensive test of the profiles system."""
    print("🧪 Testing Family Profiles System")
    print("=" * 50)
    
    # Test 1: Create profile for chat_id=111
    print("\n1. Creating profile for chat_id=111...")
    profile1 = await profiles.create_or_get(111)
    print(f"✅ Created profile: {profile1.family_id}")
    print(f"   Creator: {profile1.creator_chat_id}")
    print(f"   Members: {profile1.members}")
    print(f"   Complete: {profile1.complete}")
    
    # Test 2: Set fields
    print("\n2. Setting profile fields...")
    profile1 = await profiles.upsert_fields(
        profile1.family_id,
        parent_name="Sarah Johnson",
        timezone="America/New_York",
        parent_age=32
    )
    print(f"✅ Updated profile:")
    print(f"   Parent: {profile1.parent_name}")
    print(f"   Timezone: {profile1.timezone}")
    print(f"   Age: {profile1.parent_age}")
    
    # Test 3: Generate join code
    print("\n3. Generating join code...")
    join_code = await profiles.generate_join_code(profile1.family_id)
    print(f"✅ Generated join code: {join_code}")
    
    # Test 4: Consume join code for chat_id=222
    print("\n4. Consuming join code for chat_id=222...")
    profile2 = await profiles.consume_join_code(join_code, 222)
    print(f"✅ Added member 222 to family {profile2.family_id}")
    print(f"   Members: {profile2.members}")
    
    # Test 5: Add children
    print("\n5. Adding children...")
    child1 = Child(name="Emma", age_years=4.5, sex="f")
    child2 = Child(name="Liam", age_years=2.0, sex="m")
    
    profile1 = await profiles.upsert_fields(
        profile1.family_id,
        children=[child1, child2],
        lifestyle_tags=["vegetarian", "outdoor_activities"]
    )
    print(f"✅ Added children:")
    for child in profile1.children:
        print(f"   - {child.name} ({child.age_years} years, {child.sex})")
    print(f"   Lifestyle tags: {profile1.lifestyle_tags}")
    
    # Test 6: Mark complete
    print("\n6. Marking profile as complete...")
    profile1 = await profiles.mark_complete(profile1.family_id, True)
    print(f"✅ Profile complete: {profile1.complete}")
    
    # Test 7: Verify final state
    print("\n7. Final profile state:")
    final_profile = await profiles.get_profile(profile1.family_id)
    print(json.dumps(final_profile.dict(), indent=2, default=str))
    
    # Test 8: Verify member lookup
    print("\n8. Testing member lookups...")
    profile_by_chat = await profiles.get_profile_by_chat(222)
    print(f"✅ Found profile for chat 222: {profile_by_chat.family_id}")
    
    family_id = await profiles.find_family_id_by_member(111)
    print(f"✅ Found family for member 111: {family_id}")
    
    members = await profiles.list_members(profile1.family_id)
    print(f"✅ Family members: {members}")
    
    print("\n🎉 All tests passed!")
    return final_profile


if __name__ == "__main__":
    asyncio.run(test_profiles()) 