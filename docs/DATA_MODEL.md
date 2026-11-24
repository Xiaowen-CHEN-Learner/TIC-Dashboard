# Data model

All content is in `data/`. Five files, each plain JSON. `tools/check.py` validates every rule on this page.

## meta.json

| Field | Meaning |
|---|---|
| `as_of` | The date the dashboard describes, `YYYY-MM-DD`. The one place this date is set. |
| `banner` | The notice at the top of every screen. `{as_of}` is replaced with the date. |
| `evidence_labels` | The definition shown for each label on the Sources screen. |
| `comparability` | Why the companies are not like-for-like. |
| `known_gaps` | What is missing or weakly sourced. The first four show on the overview. |

## sources.json

`accessed` is the date the links were last opened. `kinds` describes the six source kinds. `sources` maps an id to:

| Field | Meaning |
|---|---|
| `title` | A description of the document. |
| `publisher` | Who published the copy that is linked, for example "UL Solutions via SEC EDGAR". |
| `date` | `YYYY-MM-DD`, `YYYY-MM`, or `null` for an undated page. |
| `kind` | `filing`, `company`, `news`, `transcript`, `aggregator` or `advisory`. |
| `url` | The exact document, `https` only. |
| `reviewed_by`, `reviewed_on` | Set by a person once they have compared every figure that cites the source. |

The kind sets the evidence label:

| Kind | Label |
|---|---|
| `filing` | `verified_public_record` |
| `company` | `company_claim` |
| `news`, `transcript`, `aggregator`, `advisory` | `secondary_report` |

## companies.json

`order` is the sequence used on every screen. Each company has:

| Field | Meaning |
|---|---|
| `name`, `short`, `ticker`, `listing` | Names as shown. |
| `currency`, `money_prefix`, `unit` | For example `USD`, `$`, `USD million`. |
| `dp` | Decimal places for money, 0 or 1, matching how the company reports. |
| `fy_end`, `hq`, `ceo`, `cfo`, `people`, `ir_url`, `description` | Profile. Use `null` when not known. |
| `profit_measure`, `margin_measure` | The company's own headline measure, by name. |
| `margin_family` | `operating` or `ebitda`. The overview chart keeps the two apart. |
| `organic_label` | "Organic growth" or "Like-for-like growth". |
| `profile_sources` | Source ids for the profile. |
| `status` | Optional notice with `label`, `text` and `sources`, for example a pending takeover. |

## financials.json

One object per company, keyed as in `companies.json`.

### A cell

```
[value, source]            a sourced figure
[value, source, note]      a sourced figure with a note shown under the table
[value, "computed", formula]   derived here; the formula is required
[null, reason]             reason is not_found, not_applicable or not_meaningful
```

### latest

| Field | Meaning |
|---|---|
| `period` | Label of the interim period shown on the overview. |
| `organic_from` | Optional. Label of the period the organic growth figure comes from, when the headline period does not give one. |
| `status` | `raised`, `mixed`, `confirmed` or `lowered`: what the company did to its full-year outlook. |
| `status_text` | One line saying so. |

### annual

`columns` are the year labels. `reported` is the date the latest year was published. `column_notes` explains unusual columns. Each row has:

| Field | Meaning |
|---|---|
| `key`, `label` | Identifier and the text shown. |
| `kind` | `money`, `pct`, `pct_change`, `per_share` (2 decimals), `per_share_1` (1 decimal), `ratio` or `count`. |
| `role` | Optional: `revenue`, `growth`, `organic`, `profit`, `margin`, `net`, `eps`, `fcf`, `netdebt`, `leverage`, `dps`. The overview, tiles and charts find rows by role. `revenue`, `profit` and `margin` are required. |
| `cells` | One cell per column. |
| `check` | Optional. `{"growth_of": "revenue"}` recomputes year-on-year growth from that row. `{"margin_of": ["profit", "revenue"]}` recomputes the margin. Both must agree within 0.15 points. |

### interim

`metrics` lists the columns (`key`, `label`, `kind`). `periods` are listed newest first. Each period has:

| Field | Meaning |
|---|---|
| `label`, `end`, `reported` | For example "Q3 2026", period end date, release date. `reported` is `null` for a derived period. |
| `src` | The main source. |
| `v` | Values by metric key. Leave a metric out when it was not reported. |
| `srcs` | Optional. A different source for single metrics. |
| `computed` | Optional. Formula by metric key for values derived here. |
| `note` | Optional. Shown under the row. |

Where a period gives profit, revenue and margin, the margin is recomputed. `sums` declares periods that must add up, for example Q1 + Q2 + Q3 = 9M, with a tolerance. Do not declare a sum where the company changed its reporting basis.

### segments

A list of tables. Each has `title`, `src`, `columns`, `rows` and an optional `note`. With `share_of` and `total`, the rows must add up to the total and a share bar is drawn. A row can carry `text` for a non-numeric cell, for example "Stable".

### outlook

`title`, `as_of`, `src` and `items`. Each item has `text`, `change` (`raised`, `lowered`, `confirmed`, `narrowed` or `null`), an optional `was`, and an optional `src` when it differs. `targets` holds longer-term targets with their own `title`, `src` and `items`.

### notes and charts

`notes` are the reading notes for the company. By default the company gets a revenue chart and a margin chart from the annual table. Set `auto_charts` to `false` and list `charts` to replace them, as TIC Solutions does because its annual columns are not consecutive years.

## news.json

| Part | Meaning |
|---|---|
| `types` | The news types and their labels. |
| `news` | Items newest first: `id` (unique slug), `date`, `company` (a company key or `industry`), `type`, `headline`, `summary`, `sources`. The first source sets the evidence label. |
| `calls` | The latest call or investor event per company: `company`, `event`, `date`, `time`, `points`, `links` (where to read or hear it), `sources` (what the points rest on). |
| `earlier_calls` | Other call records from the year: `company`, `event`, `date`, `link`. |
| `calendar` | Confirmed future dates only: `date`, `company`, `event`, `src`. |
| `calendar_windows` | Timing given as a window, not a date. |
| `calendar_note` | Says which companies have no confirmed date. |
