## ADDED Requirements

### Requirement: Today Shortcut
The tool SHALL support a `--today` flag that automatically sets the date range and compliance date to the current date in Vietnam time (UTC+7), eliminating the need to type the date manually.

When `--today` is passed:
- `--from` is set to today's date (start of day, UTC)
- `--to` is set to today's date (end of day, UTC)
- `--date` is set to today's date (for ASM compliance check)

`--today` MUST NOT be combined with `--from`, `--to`, or `--date`; if any of these are also provided, the tool SHALL exit with an error.

#### Scenario: Today shortcut without ASM report
- **WHEN** `--today` is passed without `--asm-report`
- **THEN** only messages from today (VN time) are analyzed; `--from`/`--to` are auto-set and the date range label shows today's date

#### Scenario: Today shortcut with ASM report
- **WHEN** `--today --asm-report` are both passed
- **THEN** messages are filtered to today, AND the compliance check uses today as the target date

#### Scenario: Conflict with explicit date flags
- **WHEN** `--today --from 2026-04-01` are both passed
- **THEN** the tool prints an error to `stderr` and exits with a non-zero code
