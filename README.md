# TIC Industry Dashboard

A dashboard for managers in the testing, inspection and certification (TIC) industry. It follows seven listed companies: industry news, earnings results and earnings calls, and five years of financials with the latest year-to-date figures.

The dashboard is a static site built from JSON files. Every figure carries a source and an evidence label, and a check script recomputes the arithmetic before anything is built.

**Live site:** https://xiaowen-chen-learner.github.io/TIC-Dashboard/

> **Status: unverified draft.** Compiled by an AI assistant (Claude) from public sources on 23 November 2026. No figure has yet been checked by a person. Company measures differ and are not like-for-like. This is not investment advice.

## Screens

| # | Screen | What it shows |
|---|---|---|
| 00 | Industry overview | Outlook changes, the latest reported period for each company, two ranked charts, the latest full year and next dates |
| 01 | Industry news | Deals, strategy updates, leadership changes and sector developments, in a feed you can filter by company and type, with deal and meeting dates ahead |
| 02 | TIC earnings news | Earnings results this year, earnings calls with links to transcripts or summaries, confirmed results dates, and the earnings news feed, all filtered by company |
| 03 | Company financials | One section per company to scroll through: key figures, charts, five years of annual figures with the latest year to date beside them, interim tables, segments, outlook and targets, reading notes and numbered sources |
| 04 | Sources and method | How the data is compiled, evidence labels, human-review count, known gaps and the full source register |

## Companies

| Company | Listing | Reports in | Year end |
|---|---|---|---|
| UL Solutions Inc. | NYSE: ULS | USD | 31 December |
| SGS SA | SIX: SGSN | CHF | 31 December |
| Bureau Veritas SA | Euronext Paris: BVI | EUR | 31 December |
| Intertek Group plc | LSE: ITRK | GBP | 31 December |
| Eurofins Scientific SE | Euronext Paris: ERF | EUR | 31 December |
| ALS Limited | ASX: ALQ | AUD | 31 March |
| TIC Solutions, Inc. | NYSE: TIC | USD | 31 December |

## Run it

Python 3.12 or later. There is nothing to install.

```
python tools/check.py                   # rule checks; must pass
python tools/build_static.py            # writes site/
python tools/build_static.py --single   # also writes site/tic-dashboard.html, one file to email or share
```

Open `site/index.html` and click through.

## Where things live

```
data/                 the content; edit these files
  meta.json           as-of date, banner, label definitions, known gaps
  companies.json      profile of each company, and the order they appear in
  financials.json     annual and interim figures, segments, outlook and targets
  news.json           industry and earnings news items, earnings calls, calendar
  sources.json        every source: title, publisher, date, kind, link
screens/              one template per screen, the page shell, styles and script
tools/
  check.py            rule checks (sources, arithmetic, writing, built pages)
  build_static.py     builds site/ from data/ and screens/
  render.py           turns data into the tables, tiles and lists
  charts.py           inline SVG charts
  model.py            loads the data and walks every figure
docs/
  DATA_MODEL.md       what each field means
  UPDATE_PLAYBOOK.md  what to do after a results release
.github/workflows/    check.yml runs on every pull request and push; pages.yml is an optional publish step
Dockerfile            optional container that serves site/
CLAUDE.md             rules for any AI assistant editing this repo
```

`site/` is build output and is not committed.

## The rules in one minute

- **No invented numbers.** A figure has a source, or a formula, or it is left empty with a reason. Nothing is estimated and no currency is converted.
- **Evidence labels.** `verified_public_record` for filings and exchange announcements, `company_claim` for other company statements and for every outlook or target, `secondary_report` for news, call records and data providers, `computed` for figures derived here, `not_found_in_scoped_search` for gaps.
- **Charts follow the data.** Charts are drawn from the same JSON as the tables, so they cannot disagree.
- **Plain writing, no long quotations.** News is summarised in the dashboard's own words.
- **A person signs off.** A figure counts as checked only when a person marks its source as reviewed. See `docs/UPDATE_PLAYBOOK.md`.

The full rules are in `CLAUDE.md`.

## Update it

After a company reports, follow `docs/UPDATE_PLAYBOOK.md`: add the source, add the new period, update the outlook, add the news item, run the checks and build.

## Share or publish it

- **Preview from CI.** Every run of the `check` workflow uploads the built site as an artifact named `dashboard-preview`.
- **One file.** `python tools/build_static.py --single` writes `site/tic-dashboard.html`, which opens from disk or an email attachment.
- **GitHub Pages.** The live site is published by the `pages` workflow on every push to `main`, after the rule checks pass. It is on because the Pages source is "GitHub Actions" and the repository variable `ENABLE_PAGES` is `true`. Set the variable to `false` to stop publishing new versions; to take the site down, unpublish it under Settings, Pages. Anyone with the link can open the site.
- **Container.** `docker build -t tic-dashboard . && docker run -p 8080:8080 tic-dashboard`, then open `http://localhost:8080`. The same image runs on Cloud Run. There is no sign-in, so keep it private unless you mean to publish it.

## Design choices

- **Screens, checks and a build.** Each screen has a template in `screens/`, `tools/check.py` is the gate, and `tools/build_static.py` writes the site. A `check` workflow runs both on every pull request.
- **Data-driven screens.** Content lives in `data/*.json` and the pages are generated, because the figures change every quarter and each one needs its source attached.
- **No backend and no sign-in.** Everything here is public information, so the site is static and opens from disk.
- **One look.** Navy sidebar, white cards on a grey page, one blue accent, Inter for text and IBM Plex Mono for figures.

## Credit

Maintained by the repository owner. Compiled and built with Claude.
