## ADDED Requirements

### Requirement: Report Detail Drill-Down
The web UI SHALL provide a **Xem chi tiết** expander at the bottom of each group's result section. The expander contains two independent selectors:

**Theo shop**: a selectbox listing all `shop_ref` values from parsed reports. When a shop is selected, a detail card is shown containing:
- ASM (sender name), Số cọc, Cọc D-1 (when D-1 data is available), Ra tiêm, Giờ gửi
- Tích cực, Vấn đề, Đã làm (full text from the parsed report)

**Theo nhân viên**: a selectbox listing all unique `sender` values. When an ASM is selected, one detail card per shop that ASM reported is shown (an ASM may report multiple shops).

The two selectors are independent — selecting one does not clear or affect the other.

#### Scenario: User selects a shop
- **WHEN** the user opens the "Xem chi tiết" expander and selects a shop_ref
- **THEN** a detail card appears showing that shop's ASM, deposit count, ra tiêm count, send time, tich_cuc, van_de, and da_lam

#### Scenario: User selects an ASM with multiple shops
- **WHEN** the user selects an ASM who reported two shops
- **THEN** two detail cards appear, one per shop

#### Scenario: Cọc D-1 shown in detail card when available
- **WHEN** D-1 data is available and the selected shop appeared in D-1
- **THEN** the detail card includes the D-1 deposit count

#### Scenario: No selection made
- **WHEN** the expander is open but neither selector has a value chosen
- **THEN** no detail card is shown
