## MODIFIED Requirements

### Requirement: Per-Group Advanced Config Storage
The web UI SHALL store advanced options (`deposit_low`, `deposit_high`, `deadline`, `skip`) for each group as part of the Group Library entry under `fpt_groups_library` in localStorage. Config is no longer stored separately in `fpt_group_configs`.

Advanced options are set per group in the add/edit form, not via a global expander.

Global hardcoded defaults apply when a new group is created without explicit values: `deposit_low=2`, `deposit_high=5`, `deadline="20:00"`, `skip=""`.

#### Scenario: Config saved when group is added
- **WHEN** the user adds a group with deadline="19:00" and clicks "Lưu"
- **THEN** `fpt_groups_library[n].config.deadline` is `"19:00"`

#### Scenario: Config updated when group is edited
- **WHEN** the user edits group A's deposit_low from 2 to 3 and saves
- **THEN** `fpt_groups_library[n].config.deposit_low` is `3` and other groups are unchanged

#### Scenario: Default config for new group
- **WHEN** the user adds a group without changing the config fields
- **THEN** the entry is created with deposit_low=2, deposit_high=5, deadline="20:00", skip=""

## REMOVED Requirements

### Requirement: Web UI Advanced Options Persistence
**Reason**: Global advanced options expander removed. Settings are now stored per group inside the Group Library entry. The four localStorage keys (`fpt_deposit_low`, `fpt_deposit_high`, `fpt_deadline`, `fpt_skip`) are obsolete.
**Migration**: No action needed — default values are hardcoded and per-group config takes precedence.

### Requirement: Per-Group Advanced Config Restore
**Reason**: Replaced by the Group Library edit form, which always shows each group's current config inline. No need to pre-fill a global expander on page load.
**Migration**: Covered by the library migration from `fpt_group_configs`.

### Requirement: Per-Group Config Summary in Results
**Reason**: Config summary in result tabs is redundant now that users can see each group's config directly in the library before running. Removing to reduce UI clutter.
**Migration**: None needed.
