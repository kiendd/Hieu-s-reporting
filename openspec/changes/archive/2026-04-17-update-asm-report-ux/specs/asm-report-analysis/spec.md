## ADDED Requirements

### Requirement: Deposit Threshold Configuration
The deposit count thresholds for shop filtering SHALL be configurable via both `config.json` and CLI flags, following the same precedence pattern as other config keys (CLI > config > built-in default).

Config keys:
- `asm_deposit_low` (int, default `2`): lower threshold
- `asm_deposit_high` (int, default `5`): upper threshold

CLI flags (override config):
- `--deposit-low N`: shops with deposit count strictly less than N appear in the low list
- `--deposit-high N`: shops with deposit count strictly greater than N appear in the high list

The old flags `--coc-low`/`--coc-high` are removed. Internal Python field names `coc_count`, `low_coc_shops`, `high_coc_shops` are renamed to `deposit_count`, `low_deposit_shops`, `high_deposit_shops` respectively. The regex patterns that detect "cọc" in raw message text are unchanged.

The JSON output keys SHALL reflect the new names: `low_deposit_shops`, `high_deposit_shops`, and each shop entry's count field SHALL be `deposit_count`.

#### Scenario: Thresholds from config file
- **WHEN** `config.json` contains `"asm_deposit_low": 3, "asm_deposit_high": 8` and no CLI flags override them
- **THEN** shops with deposit count < 3 appear in the low list and shops with count > 8 appear in the high list

#### Scenario: CLI overrides config
- **WHEN** `config.json` has `"asm_deposit_low": 3` and `--deposit-low 1` is passed
- **THEN** the effective threshold is 1 (CLI takes precedence)

#### Scenario: Low deposit shops
- **WHEN** effective `deposit_low` is 2 and a shop has deposit count 1
- **THEN** that shop appears in `low_deposit_shops` in JSON and "SHOP ĐẶT CỌC THẤP" section in text

#### Scenario: High deposit shops
- **WHEN** effective `deposit_high` is 5 and a shop has deposit count 12
- **THEN** that shop appears in `high_deposit_shops` in JSON and "SHOP ĐẶT CỌC CAO" section in text

#### Scenario: Old flags removed
- **WHEN** `--coc-low` or `--coc-high` is passed
- **THEN** argparse reports an unrecognized argument error

---

### Requirement: Skip Reporters
The compliance check SHALL support excluding specific group members from the "chưa báo cáo" list. Excluded members are managers or leads who are not expected to file daily ASM reports.

Members are excluded if their `displayName` contains any entry in the skip list as a **substring (case-insensitive)**.

The skip list is resolved from two sources (merged, no precedence conflict):
1. Config key `asm_skip_reporters`: array of strings in `config.json`
2. CLI flag `--skip-reporters "Name1,Name2"`: comma-separated names provided at runtime

A member matching any entry in the combined skip list is silently omitted from both the missing list and the compliance check entirely.

#### Scenario: Manager excluded via config
- **WHEN** `config.json` contains `"asm_skip_reporters": ["Nguyen Van Manager"]` and that member is in the group
- **THEN** that member does not appear in "ASM CHƯA BÁO CÁO" regardless of whether they reported

#### Scenario: Manager excluded via CLI flag
- **WHEN** `--skip-reporters "Tran Thi Lead"` is passed and that member is in the group
- **THEN** that member does not appear in "ASM CHƯA BÁO CÁO"

#### Scenario: Both sources merged
- **WHEN** config has `["Manager A"]` and `--skip-reporters "Lead B"` is passed
- **THEN** both "Manager A" and "Lead B" are excluded from compliance check

#### Scenario: Substring match
- **WHEN** skip list contains `"Manager"` and a member's `displayName` is `"Nguyen Van Manager HCM"`
- **THEN** that member is excluded (substring match)

#### Scenario: No skip list configured
- **WHEN** neither `asm_skip_reporters` nor `--skip-reporters` is provided
- **THEN** all group members are checked for compliance (existing behaviour)
