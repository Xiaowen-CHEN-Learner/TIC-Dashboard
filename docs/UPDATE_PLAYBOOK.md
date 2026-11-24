# Update playbook

What to do when a company reports, and when a month ends. Allow about twenty minutes per release.

## After a results release or trading update

1. **Find the primary document.** Use the regulatory filing or exchange announcement: SEC EDGAR for UL Solutions and TIC Solutions, the ASX announcement for ALS, the RNS for Intertek, the company's regulated press release for SGS, Bureau Veritas and Eurofins.
2. **Add the source** to `data/sources.json` with its exact link, date and kind.
3. **Add the period** at the top of `interim.periods` in `data/financials.json`. Enter only what the release states. For anything you derive, add the formula under `computed`. Year-to-date values for annual rows that are not interim columns, such as cash flow or net debt, go in the period's `extra`.
4. **Point `latest` at it.** Set `latest.period`, put the newest year-to-date period first in `latest.ytd_order`, and update `status` and `status_text` if the outlook changed. A single quarter is not year to date; list the nine-month or half-year period.
5. **Update the outlook.** Replace the items, set `as_of` and `src`, and record the previous wording in `was`.
6. **Full-year results only:** add a column to `annual.columns`, add a cell to every row, and set `annual.reported`. Drop the oldest column to keep five years. Set `latest.ytd_order` to `[]`, so that the Latest column does not show a period older than the new full year. Check whether the release restates earlier years, and note it in the cell if so.
7. **Add the news item** at the top of `news` in `data/news.json`, with the primary source first. Give a results release or trading update the type `result`, which puts it on the TIC earnings news screen.
8. **Update the call** for that company in `calls`: the main points in your own words, and links to the transcript or a summary. Move the old call to `earlier_calls` if it has a third-party record.
9. **Update the calendar** if the release confirms the next date, with `kind` set to `earnings`.
10. **Move the as-of date** in `data/meta.json`, and `accessed` in `data/sources.json`.
11. **Review `known_gaps`** in `data/meta.json`. Remove what you filled and add what you could not find.
12. **Run** `python tools/check.py` and `python tools/build_static.py`. Open `site/index.html` and read the company's section from top to bottom.

## After a month end: share prices

Do this once the month is complete. A part-month price never goes in.

1. **Open each price source** listed under Price and market-cap sources on the TIC stock price screen. Read the month-end adjusted close for each share.
2. **Replace each share's `adj` list** in `data/prices.json` with the series as the page shows it now, up to the new month end. Do not just add the new month: after a dividend the source restates every earlier adjusted price, so prices from two readings do not belong in one list.
3. **UL Solutions** is the exception. Its price page shows about a year of daily prices, so earlier months are held in `ret` as published monthly returns. Extend `ret` so that it reaches the first month of the new `adj` list.
4. **Set `last`, `last_date` and `read_on`**, and each share's `last_close`, the unadjusted close on the last trading day.
5. **After a year end,** add the year-end US dollar market cap for each share to `market_caps`.
6. **Rewrite the first line of `limits`**, which names the last month and anything notable that happened after it.
7. **Run** `python tools/check.py` and `python tools/build_static.py`. Open the TIC stock price screen and compare the latest month with the price pages.

Do not enter an index level or a weight. They are computed. If a month is missing for a share, stop and find it; do not fill it in.

## Replacing a secondary source

When a figure labelled `secondary_report` can be read in the company's own document:

1. Add the company document as a source.
2. Change the cell's source id, and correct the value if it differs.
3. Remove the matching line from `known_gaps` when the last such figure is replaced.

The first candidates are listed under Known gaps on the Sources screen.

## Signing off figures

A person, not an AI assistant, does this.

1. Open a source from the register on the Sources screen.
2. On the Company financials screen, find the figures that cite it. The numbered marks beside each row point to the source.
3. Compare each figure with the document.
4. Add two fields to the source in `data/sources.json`:

```json
"reviewed_by": "XC",
"reviewed_on": "2026-11-30"
```

The count on the Sources screen rises by the number of figures that cite the source. When every source is signed off, change the banner in `data/meta.json`.

## Adding a company

1. Add the profile to `data/companies.json` and its key to `order`. The order sets the section numbers on Company financials.
2. Add the same key to `data/financials.json` with `latest`, `annual`, `interim`, `segments`, `outlook` and `notes`.
3. The annual table needs rows with the roles `revenue`, `profit` and `margin`.
4. Add the same key to `series` and `market_caps` in `data/prices.json`, with a price source and at least one market cap. The share joins the indexes at its first month end.
5. Run the checks. They list anything missing.
