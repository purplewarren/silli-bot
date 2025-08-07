# Silli ME Bot – Onboarding & Identification Logic (v1)

## Overview

The new onboarding system implements a structured aiogram-based flow that replaces the previous manual onboarding process. It provides a more professional and secure user experience with proper consent management and family profile creation.

## Key Features

### 🔐 **Consent-First Approach**
- Users must explicitly accept privacy policy before proceeding
- Clear explanation of data processing (derived data only, no raw audio/video)
- Option to decline and return later

### 👨‍👩‍👧‍👦 **Family Profile Management**
- Create new family profiles with custom names
- Join existing families via Family ID
- Automatic profile completion tracking

### 🛡️ **Security & Verification**
- Placeholder for phone number verification (2FA)
- State-based protection of features
- Proper event logging for audit trails

## Implementation Details

### States (`Onboarding` StatesGroup)
```python
waiting_for_consent = State()
waiting_for_family_choice = State()
waiting_for_new_family_name = State()
waiting_for_family_id = State()
verifying_2fa = State()
```

### Flow Sequence

1. **Start Command** (`/start`)
   - Shows welcome message with privacy policy link
   - Presents consent buttons (Accept/Decline)
   - Logs onboarding start event

2. **Consent Handling**
   - **Accept**: Proceeds to family choice
   - **Decline**: Shows exit message, clears state
   - Both actions are logged with appropriate labels

3. **Family Choice**
   - **New Family**: Shows "Create New Family Profile" button
   - **Existing Family**: Accepts Family ID input
   - Both paths lead to verification step

4. **Family Creation/Joining**
   - **New**: Prompts for family name, creates profile
   - **Existing**: Validates ID, links to family
   - Simulates phone verification (placeholder)
   - Marks profile as complete

5. **Completion**
   - Shows available commands
   - Clears onboarding state
   - Logs completion event

### Protection System

The system includes a `check_onboarding_complete()` helper function that:
- Verifies user has completed onboarding
- Checks profile completion status
- Blocks access to features for incomplete users
- Provides clear guidance to complete onboarding

### Event Logging

All onboarding actions are logged with structured events:
- `onboarding_start` - User begins onboarding
- `consent_accepted` - User accepts privacy policy
- `consent_declined` - User declines privacy policy
- `family_created` - New family profile created
- `family_joined` - User joins existing family
- `onboarding_cancelled` - User cancels process

## Integration Points

### Bot Commands Updated
- `/start` - Now triggers new onboarding flow
- `/dyads` - Protected, requires completed onboarding
- `/summon_helper` - Protected, requires completed onboarding
- `/analyze` - Protected, requires completed onboarding

### Removed Commands
- `/onboard` - Replaced by new `/start` flow
- `/yes` - Replaced by inline button callbacks
- `/no` - Replaced by inline button callbacks

### Router Integration
The onboarding router is included first in main.py to ensure proper state management:
```python
dp.include_router(router_onboarding)  # Include first for state management
```

## User Experience

### Welcome Message
```
👋 Welcome. Silli ME helps parents take better care of their children.

To proceed, please review and accept our [Privacy Policy](https://gist.github.com/example-privacy).

🛡️ Silli only processes derived data — never raw audio or video.

Do you accept?

[✅ Accept] [Decline]
```

### Family Choice
```
✅ You're in. Welcome to Silli.

Let's create your Family Profile.

If you're joining an existing family, just send your Silli Family ID now.
Otherwise, tap below to start fresh.

[Create New Family Profile]
```

### Completion
```
✅ Done. You're now the first member of "Barakat Home".

You can now:
• Summon a helper (/summon_helper)
• Send a voice note (/analyze)
• Review sessions (/list)
```

## Technical Implementation

### File Structure
- `bot/onboarding.py` - Main onboarding logic
- `bot/handlers.py` - Updated with protection checks
- `bot/main.py` - Updated router inclusion and commands

### Dependencies
- aiogram FSM for state management
- Inline keyboard buttons for user interaction
- Event logging for audit trails
- Profile management integration

### Error Handling
- Comprehensive try/catch blocks
- User-friendly error messages
- Graceful state recovery
- Detailed logging for debugging

## Future Enhancements

### Phone Verification
- Implement actual 2FA verification
- SMS/Telegram code verification
- Phone number validation

### Family ID Validation
- Validate against existing families
- Prevent duplicate family names
- Family member invitation system

### Enhanced Privacy
- More detailed privacy policy
- Data retention information
- User data export/delete options

## Testing

### Manual Testing Checklist
- [ ] `/start` command shows consent flow
- [ ] Accept consent proceeds to family choice
- [ ] Decline consent shows exit message
- [ ] New family creation works
- [ ] Existing family joining works
- [ ] Protected commands block incomplete users
- [ ] Event logging captures all actions
- [ ] State management works correctly

### Automated Testing
- Unit tests for state transitions
- Integration tests for complete flows
- Event logging validation
- Error handling verification

## Deployment Notes

1. **Database Migration**: Existing users may need to complete new onboarding
2. **Command Updates**: Bot commands updated in Telegram
3. **Event Logging**: New event types added to analytics
4. **State Management**: FSM states may persist across restarts

## Security Considerations

- All user actions are logged for audit
- State-based access control prevents feature bypass
- Privacy policy acceptance is required
- Phone verification placeholder for future 2FA
- Profile completion tracking ensures proper setup

---

*This implementation follows the CTO's specifications and provides a solid foundation for secure, user-friendly onboarding.*
