# Weekly Report — Structured Metrics Design

**Date:** 2026-04-20
**Author:** brainstorming session
**Status:** approved for planning

## Goal

Make the weekly report surface structured KPIs the same way the daily report does, covering both weekly report shapes (Shop Vệ Tinh and TTTC). Today the weekly page shows compliance + raw text dumps only; after this change it shows parsed metrics, aggregates, and daily-style tables alongside the raw text.

## Problem

The current daily parser (`parse_asm_report`) matches 7 of 8 weekly templates poorly:

| Template | Shape | Daily parser gap |
|---|---|---|
| W1, W4, W5, W6, W8 | TTTC (doanh thu %, TB bill, %HT) | misses venue (`TTTC:` not `shop:`), no cọc, sections numbered or dashless |
| W2, W3 | VX narrative | misses venue, sections ambiguous |
| W7 | Shop VT (weekday) | gets cọc/ra tiêm, but section labels have no leading `-` so `_extract_sections` returns empty |

Consequence: weekly UI has no structured data to render, so managers read 200 expanders manually.

## Scope — user-selected option C

Two parsers, dispatched by content classification. No unified schema; each shape keeps its own fields and its own aggregator. Daily page is untouched.

## Non-goals

- No TTTC support on the daily page.
- No per-TVV breakdown parsing (W3 has per-TVV analysis — captured as raw text only).
- No change to `_score_weekly_message` (the qualifier classifier) — this design adds a separate `classify_report` step that runs *after* qualification.
- No Fsell / Tỉ lệ cài sổ / Tỉ trọng Gói extraction (appear on ≤2 templates — not worth the regex complexity).
- No new Python dependencies.

## Architecture

```
qualifying weekly message
        │
        ▼
classify_report(content) ──► "shop_vt" | "tttc" | "unknown"
        │
        ├── shop_vt ──► parse_asm_report  ──► analyze_asm_reports  ──► asm_data
        ├── tttc    ──► parse_tttc_report ──► analyze_tttc_reports ──► tttc_data
        └── unknown ──► (raw text only; appears in Nội dung expander)
```

`analyze_weekly` returns both `asm_data` and `tttc_data` alongside existing compliance fields. Render layer picks which blocks to show.

## Components

### 1. `classify_report(content: str) -> str`
Location: `fpt_chat_stats.py`, alongside `_score_weekly_message`.

Rules (evaluated in order — first match wins):
1. If content matches `\d+\s*cọc` or `cọc\s*\d+` → `"shop_vt"`.
2. Else if content matches `\bTTTC\b` or `TB\s*bill` or `%\s*HT` or `doanh\s*thu` (case-insensitive) → `"tttc"`.
3. Else → `"unknown"`.

`N cọc` is the decisive Shop VT marker (present on all daily templates and W7). TTTC cues are deliberately broad because templates 1–8 vary wildly.

### 2. Relaxed `_extract_sections`
Current regex requires a leading bullet character (`- – •`). Broaden to also accept bare `Label:` at start-of-line and numbered `N. Label:` form. Applies to *both* parsers (Shop VT and TTTC) and is backward-compatible with all daily templates.

New pattern (illustrative):
```python
# Match on either: bullet-prefixed label, bare label at line start, or "N. Label"
pattern = re.compile(
    r'(?:^|\n)\s*(?:[-–•]|\d+\.)?\s*'
    r'([A-ZÀ-Ỵa-zà-ỵ][^:\n]{2,40}?)\s*[:：]\s*'
    r'(.*?)(?=\n\s*(?:[-–•]|\d+\.)|\n\s*[A-ZÀ-Ỵ][^:\n]{2,40}[:：]|\Z)',
    re.DOTALL,
)
```
Implementation detail refined during plan writing; spec commitment is "accepts the three forms above, still lowercases the label, keys unchanged downstream."

### 3. `parse_tttc_report(msg: dict) -> dict`
Location: `fpt_chat_stats.py`, after `parse_asm_report`.

Returns:

| Key | Type | Source | Null when |
|---|---|---|---|
| `venue` | `str \| None` | first occurrence of `(TTTC\|VX\|LC)\s*[:\-]?\s*[^\n]+` **scoped to the first 3 non-empty lines** so mentions inside section bodies (e.g. "đã làm: thăm TTTC Cầu Giấy") aren't picked up | no venue keyword in header lines |
| `revenue_pct` | `float \| None` | `(?:HT\|đạt\|về)\s*[:=]?\s*(\d[\d.,]*)\s*%` on a doanh-thu-adjacent line | absent |
| `hot_pct` | `float \| None` | same pattern near `HOT` / `Hot` | absent |
| `hot_ratio` | `float \| None` | `[Tt]ỉ\s*trọng.{0,15}HOT.{0,8}(\d[\d.,]*)\s*%` | absent |
| `tb_bill` | `int \| None` (VND) | `TB\s*[Bb]ill[^\d]*([\d.,]+)\s*(tr\|M\|triệu)?` — normalized: `2,2tr` → 2_200_000; `1.625,000` → 1_625_000 | absent |
| `customer_count` | `int \| None` | `(?:[Ll]ượt\s*)?(?:KH\|khách)\s*mua[^\d]*(\d+)` | absent |
| `tich_cuc` / `van_de` / `da_lam` / `giai_phap` | `str \| None` | relaxed `_extract_sections`, keys matched on substrings (`"tích cực"`, `"vấn đề"`, `"đã làm"`, `"giải pháp"`) | section absent |
| `sender`, `sender_id`, `sent_at`, `message_id` | — | same as `parse_asm_report` | — |

All metric fields are nullable. Per-template expected coverage (planning reference only — not enforced by tests):

| | W1 | W2 | W3 | W4 | W5 | W6 | W8 |
|---|---|---|---|---|---|---|---|
| venue | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| revenue_pct | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| hot_pct | ✓ | — | — | ✓ | — | ✓ | — |
| hot_ratio | ✓ | — | ✓ | — | ✓ | — | ✓ |
| tb_bill | ✓ | ✓ | — | — | ✓ | ✓ | ✓ |
| customer_count | ✓ | ✓ | — | — | ✓ | — | ✓ |

### 4. `analyze_tttc_reports(parsed: list) -> dict`
Location: `fpt_chat_stats.py`, after `analyze_asm_reports`.

Returns:
```python
{
    "total_reports":   int,
    "avg_tb_bill":     float | None,      # mean of non-null; None if all null
    "avg_revenue_pct": float | None,
    "avg_hot_pct":     float | None,
    "avg_hot_ratio":   float | None,
    "top_centers":     [...],             # sorted desc by revenue_pct, top 5, nulls last
    "bottom_centers":  [...],             # sorted asc,                bottom 5, nulls last
    "ideas":           [{sender, venue, da_lam}, ...],        # da_lam non-null only
    "highlights": {
        "tich_cuc": [{sender, venue, content}, ...],
        "han_che":  [{sender, venue, content}, ...],          # from van_de
    },
}
```
Shape intentionally mirrors `asm_data["ideas"]` / `asm_data["highlights"]` so the same render helper works.

### 5. Updated `analyze_weekly` return
Additive:
```python
{
    # existing:
    "target_date": ..., "deadline": ...,
    "reports": [...], "late_list": [...], "missing_list": [...],
    # new:
    "asm_data":        dict | None,     # None if no shop_vt reports
    "tttc_data":       dict | None,     # None if no tttc reports
    "parsed_shop_vt":  [dict, ...],
    "parsed_tttc":     [dict, ...],
}
```

### 6. Streamlit — `_render_weekly_result`
Render order:
1. Compliance header (4 metrics + progress bar) — unchanged.
2. Action panels Chưa báo cáo / Muộn — unchanged.
3. **If `asm_data`:** Shop VT block (chart cọc by shop, 🚫 0-cọc, 📉 cọc thấp, 🏆 cọc tốt, 🏪 Shop đặt cọc table, 💡 Ý tưởng, ⭐ Điểm nổi bật) — rendered by shared helper `_render_shop_vt_sections` extracted from current `_render_result`.
4. **If `tttc_data`:** TTTC block — new helper `_render_tttc_sections`:
   - Metric row (4 columns): `Trung tâm báo cáo · TB bill TB · %HT TB · %HOT TB` — nulls render as `—`.
   - 🏆 Top trung tâm (by `revenue_pct` desc) — table: Trung tâm / %HT / %HOT / TB bill.
   - ⚠️ Trung tâm cần chú ý (by `revenue_pct` asc) — same columns.
   - 💡 Ý tưởng / ⭐ Điểm nổi bật — reused helper (shape matches Shop VT).
5. Nội dung báo cáo — tabs + search + expanders + avatars — unchanged. "unknown"-kind reports still land here.

`_render_result` refactored only to extract `_render_shop_vt_sections` — daily page behavior unchanged.

### 7. CLI — `print_weekly_report`
Additive sections printed between compliance block and raw-text list:
- Shop VT block via existing `print_asm_report` body if `asm_data` is non-None.
- TTTC block (new inline printing of top/bottom centers, averages, ý tưởng, điểm nổi bật) if `tttc_data` is non-None.

### 8. Excel — `write_weekly_excel`
Additive sheets:
- `Shop VT` — reuses daily's column builders (`Shop`, `Số cọc`, `Ra tiêm`, `Mức`, `ASM`).
- `TTTC` — new columns: `Trung tâm`, `%HT ngày`, `%HOT`, `TB bill`, `Tỉ trọng HOT`, `Lượt KH mua`, `ASM`.
Existing `Compliance` + `Nội dung` sheets unchanged.

## Data flow

```
fetch_all_messages → filter_by_date (VN half-open day)
                   → _score_weekly_message ≥ 3  (qualifying messages)
                   → classify_report
                   ├─► shop_vt msgs ─► parse_asm_report  ─► analyze_asm_reports  ─► asm_data
                   └─► tttc msgs    ─► parse_tttc_report ─► analyze_tttc_reports ─► tttc_data
                   + compliance  (late_list, missing_list from group_members)
                   → render / print / excel
```

## Error handling

- **Parse failure inside `parse_tttc_report`:** individual metric regex misses → field set to `None`; whole report still returned (so its raw text still surfaces). Never raises.
- **Empty `parsed_tttc` / `parsed_shop_vt`:** corresponding `tttc_data` / `asm_data` set to `None`; renderer skips that block.
- **Number normalization ambiguity.** Single helper `_parse_vnd_amount(raw, unit_suffix)`. Rules, in order:
  1. If `unit_suffix ∈ {tr, M, triệu}`: treat `,` as decimal separator when followed by 1-2 digits (e.g. `2,2tr → 2_200_000`, `2,3M → 2_300_000`); treat `.` as decimal separator when followed by 1-2 digits (e.g. `1.625tr → 1_625_000`).
  2. Without a unit suffix: treat both `.` and `,` as thousand separators (e.g. `134.927.000 → 134_927_000`, `1.625,000 → 1_625_000`).
  3. If the resulting string still contains separators after normalization or has a fractional part that doesn't fit these rules: return `None` rather than guess.
- **Classifier "unknown":** report is dropped from both structured pipelines but still present in `reports[]` and therefore in the raw-text tabs. No warning — this is expected for messages that qualify as reports but don't match either shape.

## Testing

Standalone verifier scripts under `scripts/` (no pytest in this repo — matches existing convention):

1. `verify_classify_report.py` — feeds the 8 weekend templates + 7 daily templates + 5 negatives through `classify_report`. Asserts:
   - All daily templates and W7 → `shop_vt`
   - W1/W2/W3/W4/W5/W6/W8 → `tttc`
   - Negatives → `unknown`
2. `verify_parse_tttc.py` — per-template expected field matrix (from the table above). Every non-null expectation must match; null expectations must yield `None`.
3. `verify_analyze_tttc.py` — synthetic inputs exercising: empty list, single report, mixed nulls, top/bottom ordering with nulls-last stability, average computed only over non-null values.
3a. `verify_vnd_parsing.py` — dedicated verifier for `_parse_vnd_amount`: cases `2,2tr → 2_200_000`, `2,3M → 2_300_000`, `1.625tr → 1_625_000`, `134.927.000 → 134_927_000`, `1.625,000 → 1_625_000`, plus ambiguous inputs that must return `None`.
4. Updated `verify_analyze_weekly.py` — adds cases for `asm_data` / `tttc_data` presence/absence and mixed weekly days.
5. Existing `verify_weekly_classifier.py` / `verify_analyze_weekly.py` / `verify_weekly_excel.py` must still pass 100%.

Manual validation (UI — single path only, matches repo convention):
```
streamlit run app.py
```
- Weekly mode on a weekend day with known TTTC reports: confirm TTTC block renders; averages look right; top/bottom sort correctly.
- Weekly mode on a weekday with Shop VT reports: confirm Shop VT block renders like daily; TTTC block absent.
- Weekly mode on a day mixing shapes: confirm both blocks render independently.
- Weekly mode on zero-reports day: both blocks absent; compliance + raw-text tabs still render with empty states.

## Risks

- **Regex fragility on TTTC metrics.** Templates are inconsistent (e.g. `%HT ngày: 145%` vs `HT: 133%` vs `đạt 128,18%`). Mitigation: tests pin expected capture per template; fields are nullable so partial capture degrades gracefully.
- **Number parsing edge cases** (`2,3M`, `134.927.000`, `1.625,000`). Mitigation: single `_parse_vnd_amount` helper with explicit precedence rules; unresolvable input returns `None`, never a wrong number.
- **Relaxed `_extract_sections` breaking daily.** Mitigation: verifier replays all daily templates through the new regex; daily page is otherwise untouched.
- **Classifier false positives on TTTC branch** — a Shop VT report that also mentions "doanh thu" ends up as shop_vt (correct, because `N cọc` wins). A TTTC report that happens to contain "cọc" word anywhere would misclassify — but the regex requires `\d+\s*cọc`, so bare mentions are safe.

## Open questions — resolved

1. *Nullable fields OK?* — **Yes** (user approved).
2. *Two analyzer outputs vs merged?* — **Two** (user approved).
3. *Metrics omitted (Fsell, cài sổ, Tỉ trọng Gói)?* — **Omit** (user approved).
