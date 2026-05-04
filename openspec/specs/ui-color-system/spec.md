# Spec: UI Color System

## Purpose

Defines the canonical color mapping for job states and interactive elements in the UI, ensuring visual consistency across all pipeline stages and actions.

## Requirements

### Requirement: State-to-color mapping is consistent and documented
The UI SHALL use a canonical color mapping for job states and actions, defined as CSS custom properties. The mapping SHALL be: match=green, applied=purple, review=amber, favorite-active=yellow, rejected=muted red, discovered=neutral. No interactive element that produces a given state SHALL use a color from a different state.

#### Scenario: Apply button matches applied state color
- **WHEN** a user views the Apply button on a job card
- **THEN** the button uses the same purple hue as the "applied" state badge

#### Scenario: Match badge uses green
- **WHEN** a job is in the "match" state
- **THEN** the state badge and any match-related UI elements use green

#### Scenario: Applied badge uses purple
- **WHEN** a job is in the "applied" state
- **THEN** the state badge uses purple

### Requirement: Favorite button turns yellow when active
The favorite star button SHALL use a yellow color when the job is favorited and a neutral (muted) color when it is not. The color change SHALL be the primary visual signal that the favorite state is active.

#### Scenario: Favorited job shows yellow star
- **WHEN** a job has been favorited
- **THEN** the star button is rendered in yellow (`hsl(45, 95%, 50%)` or equivalent)

#### Scenario: Unfavorited job shows muted star
- **WHEN** a job has not been favorited
- **THEN** the star button is rendered in the secondary text color with no fill

#### Scenario: Dark mode preserves yellow
- **WHEN** dark mode is active and a job is favorited
- **THEN** the star button remains visibly yellow against the dark background
