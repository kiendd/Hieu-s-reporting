## ADDED Requirements

### Requirement: Per-Group Advanced Config Storage
The web UI SHALL store advanced options (`deposit_low`, `deposit_high`, `deadline`, `skip`) independently per group ID in browser localStorage under the key `fpt_group_configs` as a JSON object mapping group hex IDs to their config objects.

Global hardcoded defaults apply when a group has no stored config: `deposit_low=2`, `deposit_high=5`, `deadline="20:00"`, `skip=""`.

#### Scenario: Config saved on single-group run
- **WHEN** only one group is entered and the user sets deadline="19:00" and clicks "Chạy phân tích"
- **THEN** `localStorage["fpt_group_configs"]["<group_id>"]["deadline"]` is set to `"19:00"`

#### Scenario: Config saved on multi-group run — only new groups updated
- **WHEN** group A already has a saved config and group B does not; user runs both
- **THEN** group B's config is saved from the current expander values; group A's existing config is preserved unchanged

#### Scenario: Config not found — hardcoded defaults used
- **WHEN** a group has no entry in `fpt_group_configs`
- **THEN** the expander shows deposit_low=2, deposit_high=5, deadline="20:00", skip="" for that group

---

### Requirement: Per-Group Advanced Config Restore
On page load, the web UI SHALL pre-fill the advanced options expander with the stored config of the first group listed in the group text area. If the first group has no stored config, hardcoded defaults are used.

#### Scenario: Single group with saved config
- **WHEN** the group text area has one entry with group ID `686b517a...` and that group's config has `deadline="18:30"`
- **THEN** the deadline widget shows `"18:30"` when the expander is opened

#### Scenario: Multiple groups — first group's config shown
- **WHEN** the text area has three groups; the first group has `deposit_low=3` saved
- **THEN** the expander pre-fills with `deposit_low=3` (first group's config)

#### Scenario: No group entered yet
- **WHEN** the text area is empty on page load
- **THEN** expander shows hardcoded defaults

---

### Requirement: Per-Group Config Summary in Results
Each result tab SHALL display a collapsed read-only summary of the advanced config that was used for that group's analysis (deposit thresholds, deadline, skip list).

#### Scenario: Tab shows correct config
- **WHEN** group A was run with `deadline="19:00"` and group B with `deadline="20:00"`
- **THEN** tab A's summary shows `deadline: 19:00` and tab B's summary shows `deadline: 20:00`

#### Scenario: Single group result
- **WHEN** only one group is analyzed
- **THEN** its result area shows the config used in the same collapsed summary format
