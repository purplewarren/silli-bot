# Changelog

All notable changes to this project will be documented in this file.

## [v0.2.1-beta] - 2025-08-07

### Added
- **New Onboarding System**: Complete rewrite of user onboarding with aiogram FSM
  - Consent-first approach with privacy policy acceptance
  - Family profile creation and joining via Family ID
  - State-based feature protection for incomplete users
  - Comprehensive event logging for audit trails
  - Inline keyboard buttons for better UX
- **i18n System**: Full internationalization support for PWA
  - English and Portuguese (Brazil) translations
  - Language detection and switching
  - Structured translation keys matching YAML source
  - Language selector component
- **PWA Improvements**: Enhanced Meal Mood Companion
  - Camera capture and photo upload functionality
  - Interactive star rating system
  - Distinct "question" and "patterns" modes for insights
  - Proper data flow between screens
  - Export functionality with bot integration
- **Documentation**: Comprehensive guides and documentation
  - QuickStart guide for v0.2.1-beta
  - Loom script outline for demo video
  - Onboarding system documentation
  - Architecture and deployment guides

### Changed
- **Bot Commands**: Updated command structure
  - `/start` now triggers new onboarding flow
  - Removed `/onboard`, `/yes`, `/no` commands
  - Protected commands require completed onboarding
  - Updated command descriptions and help text
- **PWA Routing**: Fixed dyad-specific routing
  - Proper hash-based navigation for different dyads
  - Correct screen rendering based on URL parameters
  - Fixed meal and tantrum companion routing
- **i18n Structure**: Aligned with YAML source of truth
  - Moved badge translations under `pwa.badges`
  - Moved tip translations under `pwa.tips`
  - Added disclaimer section with non-medical notice
  - Updated all translation keys to match specification

### Fixed
- **PWA Functionality**: Multiple bug fixes
  - Camera access and photo capture working
  - Interactive star ratings in meal logging
  - Proper data passing between screens
  - Export functionality sending data to bot
  - Gallery and navigation buttons working
- **TypeScript Errors**: Resolved compilation issues
  - Fixed import/export statements
  - Removed unused variables and imports
  - Updated type declarations for i18n
- **Storage Issues**: Fixed import problems
  - Corrected storage instance creation
  - Fixed onboarding module dependencies
  - Resolved circular import issues

### Technical
- **Architecture**: Improved system structure
  - Modular onboarding with proper state management
  - Enhanced error handling and logging
  - Better separation of concerns
  - Improved code organization
- **Security**: Enhanced user protection
  - State-based access control
  - Privacy policy enforcement
  - Audit trail logging
  - Profile completion validation

### Documentation
- Added `docs/Onboarding-System-v1.md` with complete implementation details
- Updated `docs/QuickStart-v0.2.1-beta.md` with new setup instructions
- Created `docs/Loom-Script-v0.2.1-beta.md` for demo video
- Enhanced existing documentation with new features

---

## [v0.2.0-beta] - 2025-08-01

### Added
- Initial beta release with core functionality
- Basic bot commands and PWA integration
- Reasoner service with Ollama integration
- JSONL storage system
- Basic event logging and analytics
