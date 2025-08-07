# QA Patch Notes - v0.2.1-fix

**Date**: 2025-08-07  
**Branch**: `hotfix/v0.2.1-fix`  
**Target**: `v0.2.1-rc1`  

## Overview

This patch addresses the remaining QA matrix issues from v0.2.1-beta, specifically:
- **C1**: Multilingual switch (PARTIAL → PASS)
- **D2**: Cache hit testing (PENDING → PASS)  
- **G1**: Reasoner disabled fallback (PENDING → PASS)

## Changes Implemented

### 1. Multilingual Support (`/lang` command)

#### Files Modified:
- `bot/i18n.py` (new)
- `bot/handlers_i18n.py` (new)
- `bot/profiles.py` (enhanced)
- `bot/handlers.py` (updated)
- `bot/main.py` (updated)
- `tests/test_i18n.py` (new)

#### Changes:
1. **i18n Module**: Created `bot/i18n.py` with locale management functions
   - `get_locale(chat_id)` - retrieves user's language preference
   - `set_locale(chat_id, locale)` - sets language preference
   - `get_supported_locales()` - returns available languages
   - `is_supported_locale(locale)` - validates locale

2. **Profile Enhancement**: Added `locale` field to `FamilyProfile` model
   - Default: "en"
   - Supported: "en", "pt_br"
   - Persisted in profile index

3. **Command Handler**: Created `/lang` command in `bot/handlers_i18n.py`
   - Usage: `/lang <en|pt_br>`
   - Shows current language and available options
   - Updates profile with new preference
   - Confirms change in selected language

4. **Dyad Integration**: Updated all Dyad invocation handlers to use user's locale
   - `summon_helper_command()` - uses `get_locale()`
   - `handle_dyad_invocation()` - uses `get_locale()`
   - Direct summon commands - use `get_locale()`
   - `/help` command - localized text

5. **Unit Tests**: Comprehensive test suite in `tests/test_i18n.py`
   - 11 test cases covering all functionality
   - Round-trip locale setting/getting
   - Error handling and fallbacks
   - Invalid locale validation

### 2. Cache Hit Testing (D2)

#### Files Modified:
- `qa/reasoner_smoke.py` (enhanced)

#### Changes:
1. **Cache Hit Test Method**: Added `test_cache_hit()`
   - Makes identical requests to reasoner
   - Verifies first call is cache MISS
   - Verifies second call is cache HIT
   - Validates latency < 15ms for cache hits

2. **Enhanced Test Flow**: Updated `run_smoke_test()`
   - Added Test 3: Cache Hit (D2)
   - Validates cache status and latency
   - Reports detailed cache analysis

### 3. Reasoner Disabled Fallback (G1)

#### Files Modified:
- `qa/reasoner_smoke.py` (enhanced)

#### Changes:
1. **Fallback Test Method**: Added `test_reasoner_disabled_fallback()`
   - Temporarily sets `REASONER_ENABLED=0`
   - Makes request to reasoner API
   - Verifies completion without tips
   - Restores original environment

2. **Enhanced Test Flow**: Updated `run_smoke_test()`
   - Added Test 4: Reasoner Disabled Fallback (G1)
   - Validates fallback behavior
   - Ensures no tips are generated

3. **Command Line Support**: Added `--reasoner-off` flag
   - Allows testing with reasoner disabled
   - Useful for G1 test scenarios

## Testing Results

### i18n Tests
```
✅ test_get_supported_locales PASSED
✅ test_is_supported_locale PASSED  
✅ test_get_locale_default PASSED
✅ test_get_locale_custom PASSED
✅ test_get_locale_invalid PASSED
✅ test_set_locale_valid PASSED
✅ test_set_locale_invalid PASSED
✅ test_set_locale_nonexistent_user PASSED
✅ test_round_trip_locale PASSED
✅ test_get_locale_error_handling PASSED
✅ test_set_locale_error_handling PASSED
```

### Reasoner Smoke Tests
```
🧪 Test 1: Tantrum Session: ✅ PASS (latency: 245ms)
🧪 Test 2: Meal Session: ✅ PASS (latency: 198ms)  
🧪 Test 3: Cache Hit (D2): ✅ PASS (cache: HIT, latency: OK)
🧪 Test 4: Reasoner Disabled Fallback (G1): ✅ PASS (completed: YES, tips: EMPTY)
```

## Updated QA Matrix Status

| ID | Scenario | Status | Notes |
|----|----------|--------|-------|
| A1 | Master menu | ✅ PASS | - |
| A2 | Direct commands | ✅ PASS | - |
| B1 | JWT validity | ✅ PASS | - |
| B2 | JWT expiry | ✅ PASS | - |
| **C1** | **Multilingual switch** | **✅ PASS** | **Fixed with `/lang` command** |
| D1 | Reasoner path | ✅ PASS | - |
| **D2** | **Cache hit** | **✅ PASS** | **Fixed with cache hit testing** |
| E1 | Profile gating | ✅ PASS | - |
| F1 | Privacy copy | ✅ PASS | - |
| **G1** | **Reasoner OFF fallback** | **✅ PASS** | **Fixed with fallback testing** |

**Overall Pass Rate**: 10/10 (100% ✅)

## Breaking Changes

None. All changes are backward compatible.

## Migration Notes

- Existing profiles will default to "en" locale
- No database migration required (JSONL storage)
- New `locale` field added to `FamilyProfile` model

## Next Steps

1. **Tag Release**: Create `v0.2.1-rc1` tag
2. **Production Testing**: Validate in staging environment
3. **Documentation**: Update QuickStart guide with `/lang` command
4. **Monitoring**: Watch for any locale-related issues in production

## Files Changed Summary

```
Modified: 6 files
Added: 3 files
Lines added: ~350
Lines modified: ~50
```

### New Files:
- `bot/i18n.py` - i18n functionality
- `bot/handlers_i18n.py` - `/lang` command handler  
- `tests/test_i18n.py` - i18n unit tests

### Modified Files:
- `bot/profiles.py` - Added locale field to FamilyProfile
- `bot/handlers.py` - Updated Dyad handlers to use locale
- `bot/main.py` - Added i18n router and `/lang` command
- `qa/reasoner_smoke.py` - Enhanced with cache hit and fallback tests
