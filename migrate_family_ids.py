#!/usr/bin/env python3
"""
Migration script to convert family IDs to sequential format.
Your family: fam_2130406580_20250808_171117 -> Family #000001
"""

import sys
import json
from pathlib import Path

# Add the bot module to path
sys.path.insert(0, '.')

from bot.families import families
from bot.profiles import profiles

def main():
    print("🔄 Starting Family ID Migration")
    print("=" * 50)
    
    # Step 1: Migrate families to sequential IDs
    print("\n📊 Current families:")
    data = families._read()
    for old_id, family_data in data.items():
        print(f"  - {old_id}")
    
    print(f"\n🔄 Migrating {len(data)} families...")
    id_mapping = families.migrate_to_sequential_ids()
    
    print("\n✅ Migration mapping:")
    for old_id, new_id in id_mapping.items():
        print(f"  {old_id} -> {new_id}")
    
    # Step 2: Update profiles to reference new family IDs
    print(f"\n🔄 Updating profile references...")
    
    # Get the current profile
    chat_id = 2130406580
    profile = profiles.get_profile_by_chat_sync(chat_id)
    
    if profile:
        old_family_id = profile.get("family_id")
        if old_family_id in id_mapping:
            new_family_id = id_mapping[old_family_id]
            
            # Update the profile data
            updated_profile = profile.copy()
            updated_profile["family_id"] = new_family_id
            updated_profile["old_family_id"] = old_family_id
            
            # Save the updated profile
            profiles.upsert_profile(chat_id, updated_profile)
            print(f"  Profile {chat_id}: {old_family_id} -> {new_family_id}")
            print(f"✅ Updated profile")
        else:
            print(f"  Profile {chat_id}: No migration needed")
    else:
        print("  No profile found to update")
    
    # Step 3: Verification
    print(f"\n🔍 Verification:")
    chat_id = 2130406580
    profile = profiles.get_profile_by_chat_sync(chat_id)
    if profile:
        family_id = profile.get("family_id")
        family = families.get_family(family_id)
        print(f"  User {chat_id} profile: {profile.get('family_id')}")
        print(f"  Family found: {'✅' if family else '❌'}")
        if family:
            print(f"  Family ID: {family.family_id}")
            print(f"  Parent: {family.parent_name}")
            print(f"  Cloud reasoning: {family.cloud_reasoning}")
    
    print(f"\n🎉 Migration complete!")
    print("Your family is now: Family #000001")

if __name__ == "__main__":
    main()
