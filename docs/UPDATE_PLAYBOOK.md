# Update playbook

What to do when a company reports. Allow about twenty minutes per release.

## After a results release or trading update

1. **Find the primary document.** Use the regulatory filing or exchange announcement: SEC EDGAR for UL Solutions and TIC Solutions, the ASX announcement for ALS, the RNS for Intertek, the company's regulated press release for SGS, Bureau Veritas and Eurofins.
2. **Add the source** to `data/sources.json` with its exact link, date and kind.
3. **Add the period** at the top of `interim.periods` in `data/financials.json`. Enter only what the release states. For anything you derive, add the formula under `computed`.
4. **Point `latest` at it.** Set `latest.period`, and update `status` and `status_text` if the outlook changed.
5. **Update the outlook.** Replace the items, set `as_of` and `src`, and record the previous wording in `was`.
6. **Full-year results only:** add a column to `annual.columns`, add a cell to every row, and set `annual.reported`. Drop the oldest column if you want to keep four years. Check whether the release restates earlier years, and note it in the cell if so.
7. **Add the news item** at the top of `news` in `data/news.json`, with the primary source first.
8. **Update the call** for that company in `calls`: the main points in your own words, and links to the transcript or a summary. Move the old call to `earlier_calls` if it has a third-party record.
9. **Update the calendar** if the release confirms the next date.
10. **Move the as-of date** in `data/meta.json`, and `accessed` in `data/sources.json`.
11. **Review `known_gaps`** in `data/meta.json`. Remove what you filled and add what you could not find.
12. **Run** `python tools/check.py` and `python tools/build_static.py`. Open `site/index.html` and read the company's section from top to bottom.

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

1. Add the profile to `data/companies.json` and its key to `order`.
2. Add the same key to `data/financials.json` with `latest`, `annual`, `interim`, `segments`, `outlook` and `notes`.
3. The annual table needs rows with the roles `revenue`, `profit` and `margin`.
4. Run the checks. They list anything missing.
