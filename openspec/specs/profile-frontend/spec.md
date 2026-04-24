# Spec: profile-frontend

## Purpose

Frontend UI for viewing and editing the user profile, integrated into the main navigation as a Profile tab. Supports inline chip editing, range sliders, explicit-save text sections, experience accordion cards, and backup history.

## Requirements

### Requirement: Profile tab in navigation
A `Profile` tab SHALL be added to the main navigation bar alongside `Jobs` and `Companies`. Clicking it SHALL switch to the Profile view and load the profile data via `GET /api/profile` if not already loaded.

#### Scenario: Profile tab switches view
- **WHEN** the user clicks the Profile tab
- **THEN** the Profile view is shown and `GET /api/profile` is called to load data

### Requirement: Profile view sections
The Profile view SHALL be organised into six collapsible sections. The first three (Skills & Domains, Job Targets, Logistics) SHALL be expanded by default; the last three (Narrative, Experience, Education & Certifications) SHALL be collapsed by default.

Sections and their fields:
1. **Skills & Domains**: `skill_tiers` chip groups (super_power, strong, low) + `mission_domains` sliders
2. **Job Targets**: `targets.primary_roles` chips + `scout_filters.positive` chips + `scout_filters.seniority_boost` chips
3. **Logistics**: `location_preferences.accepted` chips + `compensation.minimum` + `compensation.target_range` + `logistics.availability` text
4. **Narrative**: `narrative.headline` text + `narrative.intro` textarea + `narrative.exit_story` textarea + `narrative.superpowers` chips
5. **Experience**: accordion cards, one per experience entry
6. **Education & Certifications**: accordion cards for education entries + certification entries

#### Scenario: Default expanded sections are visible
- **WHEN** the Profile tab is opened
- **THEN** Skills & Domains, Job Targets, and Logistics sections are expanded without user interaction

### Requirement: Chip group interactions
All chip groups (skill_tiers, filters, locations, roles) SHALL support:
- **Remove**: click `×` on a chip to remove it immediately and trigger a profile save
- **Add**: click `[+ add]` to reveal an inline text input; pressing Enter adds the chip and triggers a save; pressing Escape cancels
- **Tier cycling** (skill_tiers only): clicking a chip (not the `×`) cycles it through `super_power → strong → low → (remove)` and triggers a save

#### Scenario: Chip removal triggers immediate save
- **WHEN** the user clicks `×` on a skill chip
- **THEN** the chip is removed, `PUT /api/profile` is called with the updated profile, and a brief "Saved" indicator is shown

#### Scenario: Chip add via Enter triggers immediate save
- **WHEN** the user types a skill name in the inline input and presses Enter
- **THEN** the chip is added to the appropriate group, `PUT /api/profile` is called, and the inline input is hidden

#### Scenario: Tier cycling moves chip between groups
- **WHEN** the user clicks a chip in `super_power`
- **THEN** the chip moves to `strong`; clicking it again moves it to `low`; clicking again removes it entirely; each step triggers a save

### Requirement: Mission domain sliders
Each `mission_domains` entry SHALL render as a labelled range slider (min=1, max=10, step=1) with a numeric readout. Changes to a slider SHALL trigger a profile save after a 500ms debounce. A `[+ add domain]` button SHALL allow adding a new domain name + initial weight. An `×` on a domain row SHALL remove it and trigger a save.

#### Scenario: Slider change triggers debounced save
- **WHEN** the user moves a mission domain slider
- **THEN** `PUT /api/profile` is called 500ms after the last change

#### Scenario: New domain can be added
- **WHEN** the user clicks `[+ add domain]`, enters a name and weight, and confirms
- **THEN** the new domain appears in the list and is saved to the profile

### Requirement: Text field sections use explicit Save button
Sections containing free-text fields (Narrative, Experience, Logistics compensation/availability) SHALL each have a section-level `[Save]` button. Changes to text fields SHALL NOT auto-save. An "unsaved changes" indicator SHALL be shown when a section has pending edits.

#### Scenario: Unsaved changes indicator shown
- **WHEN** the user edits a text field in the Narrative section without saving
- **THEN** an "unsaved changes" badge is shown next to the section header

#### Scenario: Save button persists text changes
- **WHEN** the user edits the headline and clicks [Save]
- **THEN** `PUT /api/profile` is called and the "unsaved changes" indicator is cleared

### Requirement: Experience accordion cards
Each experience entry SHALL render as a collapsible card showing `company` and `role` in the header. When expanded, the card SHALL show editable fields: `company`, `role`, `location`, `period` (all text inputs), `highlights` (list of textareas with add/remove/reorder), and `tech_stack` (chip group with immediate save). Text fields use the section-level Save button; tech_stack chips save immediately. Entries can be reordered with `↑ ↓` buttons. A `[+ Add experience]` button appends a new blank entry.

#### Scenario: Experience tech_stack chip saves immediately
- **WHEN** the user removes a chip from an experience tech_stack
- **THEN** `PUT /api/profile` is called immediately without requiring the Save button

#### Scenario: Experience text fields require Save
- **WHEN** the user edits the company name in an experience card
- **THEN** the change is not persisted until the section [Save] button is clicked

#### Scenario: New experience entry can be added
- **WHEN** the user clicks `[+ Add experience]`
- **THEN** a new blank card is appended and expanded for editing

### Requirement: Backup history UI
A `[🕐 History]` button in the Profile view header SHALL open a panel listing the last 10 backups with their timestamps. Each entry SHALL have a `[Restore]` button that calls `POST /api/profile/backups/restore` and reloads the profile. The panel SHALL close after a successful restore.

#### Scenario: History panel lists backups
- **WHEN** the user clicks [🕐 History]
- **THEN** a panel opens showing available backups with human-readable timestamps

#### Scenario: Restore loads the profile from backup
- **WHEN** the user clicks [Restore] on a backup entry
- **THEN** `POST /api/profile/backups/restore` is called, the profile is reloaded via `GET /api/profile`, and all sections refresh with the restored data
