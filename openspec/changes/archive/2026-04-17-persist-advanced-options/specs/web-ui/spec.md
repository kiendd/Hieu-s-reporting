## ADDED Requirements

### Requirement: Web UI Advanced Options Persistence
The web UI SHALL persist the four advanced-options fields in browser localStorage and restore them on page load.

localStorage keys and defaults:

| Key                | Widget                        | Default  |
|--------------------|-------------------------------|----------|
| `fpt_deposit_low`  | Ngưỡng cọc thấp (<)           | `2`      |
| `fpt_deposit_high` | Ngưỡng cọc cao (>)            | `5`      |
| `fpt_deadline`     | Deadline (giờ VN)             | `20:00`  |
| `fpt_skip`         | Bỏ qua khỏi compliance check  | `""`     |

Values SHALL be written to localStorage when the user clicks "Chạy phân tích". Values SHALL be read and pre-filled into the widgets on page load.

#### Scenario: Restore non-default values on reload
- **WHEN** the user previously set deposit_low=3, deposit_high=8, deadline="18:00", skip="Giám đốc" and reloads the page
- **THEN** all four widgets show those saved values instead of the defaults

#### Scenario: Save on run
- **WHEN** the user changes deadline to "19:30" and clicks "Chạy phân tích"
- **THEN** `localStorage["fpt_deadline"]` is set to `"19:30"`

#### Scenario: Default when localStorage empty
- **WHEN** the user opens the app for the first time with no stored values
- **THEN** deposit_low=2, deposit_high=5, deadline="20:00", skip="" (unchanged from current behaviour)
