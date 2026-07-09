# Implementation Plan - UI Responsiveness & Auto-Refresh

The goal is to fix responsiveness issues (header overlaps, excessive whitespace) and implement an auto-refresh mechanism so the UI stays in sync with data changes.

## Proposed Changes

### Core Responsiveness
- Use `TyResponsive` utility to scale all hardcoded dimensions.
- Standardize top padding for screens with sticky headers to `MediaQuery.of(context).padding.top + resp.h(85)`.

### Auto-Refresh
- Wrap all major list views in `RefreshIndicator`.
- Listen to `AuthManager` in `AccountScreen` for live user updates.
- Use `.then()` callbacks on navigation to refresh parent screens on return.

### Screens Updated
- `HomeScreen`, `AccountScreen`, `PlansScreen`, `ExploreScreen`, `EventHubScreen`, `BudgetScreen`, `GuestsScreen`.

## Verification Plan

### Automated Tests
- I will check for any compilation errors after the changes using `analyze_file`.

### Manual Verification
- I will use `DevicePreview` (which is already in the project) to verify the UI on different screen sizes like iPhone SE (small) and iPhone 14 Pro Max (large).
- Since I cannot "run" the app and see it live, I will rely on code analysis and the logic of the `TyResponsive` utility which is a standard pattern for Flutter responsiveness.
