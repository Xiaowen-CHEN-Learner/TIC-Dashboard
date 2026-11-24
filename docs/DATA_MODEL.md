# Data model

All content is in `data/`. Six files, each plain JSON. `tools/check.py` validates every rule on this page.

## meta.json

| Field | Meaning |
|---|---|
| `as_of` | The date the dashboard describes, `YYYY-MM-DD`. The one place this date is set. |
| `banner` | The notice at the top of every screen, in parts: `intro`, then one of `none`, `part` or `all`, then `outro`. The middle part is chosen by how much a person has signed off. `{as_of}`, `{checked}`, `{sourced}`, `{px_done}`, `{px_total}`, `{who}` and `{when}` are filled in by the build. |
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
| `reviewed_by`, `reviewed_on`, `reviewed_sum` | A person's sign-off: who compared every figure that cites the source, on which day, and a checksum of those figures. Written by `tools/signoff.py`, never by hand. The check fails when the figures no longer match the checksum, and the sign-off is then removed. |

The kind sets the evidence label:

| Kind | Label |
|---|---|
| `filing` | `verified_public_record` |
| `company` | `company_claim` |
| `news`, `transcript`, `aggregator`, `advisory` | `secondary_report` |

## companies.json

`order` is the sequence used on every screen. It also sets the section numbers on Company financials: the first company is 3.1, the second 3.2. Each company has:

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
| `ytd_order` | Labels of the year-to-date periods the Latest column reads, newest first, for example `["9M 2026", "H1 2026"]`. Each row takes the first period that has a value for it. Use `[]` after a full-year release until the next interim one; the column is then left out. |
| `status` | `raised`, `mixed`, `confirmed` or `lowered`: what the company did to its full-year outlook. |
| `status_text` | One line saying so. |

### annual

`columns` are the year labels: five fiscal years where they were found. `reported` is the date the latest year was published. `column_notes` explains unusual columns. The table also prints a Latest column, which is not stored here: it is read from the interim periods named in `latest.ytd_order`, for every row whose `key` matches an interim metric or an `extra` value. Each row has:

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
| `extra` | Optional. Year-to-date values for annual rows that are not interim columns, by annual row key, for example cash flow or net debt. They show only in the Latest column of the annual table. |
| `srcs` | Optional. A different source for single values in `v` or `extra`. |
| `computed` | Optional. Formula by metric key for values derived here. |
| `note` | Optional. Shown under the row. |

An interim metric that shares its key with an annual row must be the same measure and the same `kind`, because the Latest column prints it in that row. Give a different measure its own key, as ALS does with `interim_dps`.

Where a period gives profit, revenue and margin, the margin is recomputed. `sums` declares periods that must add up, for example Q1 + Q2 + Q3 = 9M, with a tolerance. Do not declare a sum where the company changed its reporting basis.

### segments

A list of tables. Each has `title`, `src`, `columns`, `rows` and an optional `note`. With `share_of` and `total`, the rows must add up to the total and a share bar is drawn. A row can carry `text` for a non-numeric cell, for example "Stable".

### outlook

`title`, `as_of`, `src` and `items`. Each item has `text`, `change` (`raised`, `lowered`, `confirmed`, `narrowed` or `null`), an optional `was`, and an optional `src` when it differs. `targets` holds longer-term targets with their own `title`, `src` and `items`.

### notes and charts

`notes` are the reading notes for the company. By default the company gets a revenue chart and a margin chart from the annual table. The charts show full years only, never the Latest column. Set `auto_charts` to `false` and list `charts` to replace them, as TIC Solutions does to show quarters, because it has three annual columns and one is a non-GAAP combination.

## news.json

| Part | Meaning |
|---|---|
| `types` | The news types and their labels. Type `result` is earnings news; every other type is industry news. |
| `news` | Items newest first: `id` (unique slug), `date`, `company` (a company key or `industry`), `type`, `headline`, `summary`, `sources`. The first source sets the evidence label. Items of type `result` show on the TIC earnings news screen and the rest on the Industry news screen. |
| `calls` | The latest earnings call or results update per company: `company`, `event`, `date`, `time`, `points`, `links` (where to read or hear it), `sources` (what the points rest on). Investor days and strategy events are news items of type `strategy`. |
| `earlier_calls` | Other call records from the year: `company`, `event`, `date`, `link`. |
| `calendar` | Confirmed future dates only: `date`, `company`, `kind`, `event`, `src`. `kind` is `earnings` for results dates, which show on TIC earnings news, or `other`, which shows on Industry news. |
| `calendar_windows` | Timing given as a window, not a date, with the same `kind`. |
| `calendar_note` | Says which companies have no confirmed date. |

## prices.json

Month-end share prices and market caps for the TIC stock price screen. Index levels, returns and weights are not stored: `tools/stockindex.py` computes them for the screen, the chart and the checks.

| Field | Meaning |
|---|---|
| `base` | The month both indexes are set to 100, `YYYY-MM`. |
| `last` | The last complete month, `YYYY-MM`. Every series ends here. |
| `last_date` | The last trading day of that month, `YYYY-MM-DD`. Not after the as-of date. |
| `read_on` | The day the price and market-cap pages were read. |
| `series` | One entry per company, keyed as in `companies.json`. |
| `market_caps` | One entry per company: `src`, `values` as `[month, USD billion]` pairs, and an optional `note` shown under the weights table. |
| `method`, `limits` | The two lists printed on the screen. Rewrite the first `limits` line when `last` moves. |

Each series has:

| Field | Meaning |
|---|---|
| `symbol`, `market`, `currency` | As the price source lists the share. |
| `price_prefix`, `price_suffix`, `price_dp` | How the latest price is printed, for example `CHF ` and 2, or `p` and 0 for pence. |
| `src` | The source of the prices. |
| `last_close` | The unadjusted closing price on `last_date`, as printed on the screen. |
| `adj` | `[month, price]` pairs: the month-end close adjusted for dividends and splits, in the share's own currency. Months run in order with no gap and end at `last`. All the pairs come from one reading of the source, because a source restates its earlier adjusted prices after each dividend. |
| `ret`, `ret_src` | Optional. Published monthly total returns in percent, as `[month, return]` pairs, for months the price source does not cover. Where a month has both a return and prices, they must agree. |

How the numbers are used:

- A share's return for a month is `adj[month] / adj[previous month] - 1`. Where either price is missing, the published return in `ret` is used.
- A share joins both indexes at the first month end it has data for. Its first return is the month after.
- The equal-weighted index averages the returns of the shares in it each month.
- The market-cap-weighted index weights each return by the share's market cap at the previous month end. At a month listed in `market_caps` the published figure is used. In between, the last published figure is moved by the share's own return. Before a share's first published figure, the value is worked back from it.
- Nothing is converted here. The market caps are in US dollars because the source publishes them that way, and they are used only as weights.

The checks fail on a gap in the months, a missing source, a monthly move above 70%, a published return that disagrees with the prices, or weights that do not add up to 100%.
