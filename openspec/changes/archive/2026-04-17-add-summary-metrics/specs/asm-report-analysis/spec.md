## ADDED Requirements

### Requirement: Aggregate Summary Metrics
The analysis SHALL compute and expose the following aggregate fields in the `asm_data` dict:
- `total_deposits`: sum of `deposit_count` across all parsed reports (skipping `None`)
- `total_ra_tiem`: sum of `ra_tiem_count` across all parsed reports (skipping `None`)
- `no_deposit_shops`: list of `{sender, shop_ref}` where `deposit_count == 0`

#### Scenario: Deposits summed
- **WHEN** three ASM reports have deposit_count 5, 3, 0
- **THEN** `total_deposits` is 8 and `no_deposit_shops` contains the shop with 0 deposits

#### Scenario: ra_tiem summed with None
- **WHEN** two reports have ra_tiem_count 1 and None respectively
- **THEN** `total_ra_tiem` is 1 (None entries skipped)

---

### Requirement: Day-over-Day Comparison
The web UI SHALL display `total_deposits` and `total_ra_tiem` as `st.metric` tiles with a delta showing the difference vs. the previous calendar day (D-1).

D-1 data SHALL be fetched as a separate API call for the calendar day immediately before the target date, using the same group and token. D-1 comparison is shown only when the analysis covers exactly one calendar day (including "Hôm nay" mode). For multi-day date ranges, the delta is omitted.

#### Scenario: Single-day run with D-1 available
- **WHEN** the user runs analysis for a single day and D-1 messages exist
- **THEN** the Tổng cọc metric tile shows today's total with a +/- delta vs. D-1

#### Scenario: Multi-day range
- **WHEN** the user selects a date range of more than one day
- **THEN** no D-1 delta is shown

---

### Requirement: No-Deposit and High-Deposit Shop Lists
The web UI SHALL display two dedicated sections after the summary metrics:

**Nhân viên không phát sinh cọc** — two sub-tables:
- Sub-table A: shops from parsed reports with `deposit_count == 0`, columns: ASM, Shop
- Sub-table B: group members with no report on the target date (using `check_asm_compliance` with deadline `"23:59"`), column: Tên thành viên

**Nhân viên cọc tốt** — shops where `deposit_count > deposit_high`, columns: ASM, Shop, Số cọc

#### Scenario: Shop with 0 deposits appears in sub-table A
- **WHEN** an ASM report contains `0 cọc` for a shop
- **THEN** that shop appears in the "không phát sinh cọc" sub-table A

#### Scenario: Member with no report appears in sub-table B
- **WHEN** a group member has sent no ASM report on the target date
- **THEN** their name appears in sub-table B (subject to skip list)

---

### Requirement: Reporter Timing Metrics
The web UI SHALL display two timing metrics in the summary section:

- **Báo cáo muộn**: count of ASMs whose report on the target date was sent after the configured deadline; clicking/expanding shows the list with timestamps
- **Chưa báo cáo**: count of group members with no report as of the run time (deadline = current VN time at the moment of the run)

#### Scenario: Late reporter counted
- **WHEN** an ASM sends their report at 21:05 and deadline is "20:00"
- **THEN** the "Báo cáo muộn" count includes that ASM

#### Scenario: Unreported as of now
- **WHEN** a member has not sent any report by the time the analysis runs
- **THEN** the "Chưa báo cáo" count includes that member
