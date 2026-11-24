# CLAUDE.md — rules for any Claude editing this repo

This repo is the TIC Industry Dashboard: news, financials and two share-price indexes for seven listed testing, inspection and certification companies, for managers in that industry. The repository is public, so everything committed here is public.

Read `docs/DATA_MODEL.md` before changing data and `docs/UPDATE_PLAYBOOK.md` before adding a results release or a month of share prices.

## How the repo works

- Content lives in `data/*.json`. The pages in `site/` are generated; never edit them by hand and never commit them.
- `screens/` holds one template per screen. Templates carry headings and short fixed text, with `{{slots}}` that `tools/render.py` fills.
- `tools/check.py` is the gate. `tools/build_static.py` builds the site.
- `tools/stockindex.py` computes the two indexes on the TIC stock price screen from `data/prices.json`. Index levels and weights are never stored.
- The order in `data/companies.json` sets the order on every screen and the section numbers on Company financials: 3.1, 3.2 and so on.

## Workflow

1. Branch from `main`. Open a pull request; the owner merges, or asks you to merge once the checks pass.
2. Edit `data/` for content, or `screens/` and `tools/` for presentation.
3. Run `python tools/check.py`, then `python tools/build_static.py`. Open `site/index.html` and look at your change.
4. In the pull request, say what changed and name the source behind every new or changed figure.
5. Never merge on a red check.

## Hard rules

- **No invented numbers.** Every figure is `[value, source id]`, or `[value, "computed", formula]`, or `[null, reason]`. If a figure is not disclosed or not found, leave it null with `not_found`. Never estimate, interpolate, annualise or convert currency.
- **Sources first.** Add the source to `data/sources.json` before you cite it. Prefer the regulatory filing or exchange announcement, and link to the exact document. A figure taken from news, a call record or a data provider is allowed, is labelled `secondary_report`, and should be replaced when the company document is found.
- **Evidence labels.** The label comes from the source kind: `filing` gives `verified_public_record`; `company` gives `company_claim`; `news`, `transcript`, `aggregator` and `advisory` give `secondary_report`. Outlook statements and targets always show `company_claim`. A company claim is never shown as fact.
- **Restatements.** Show each year as it appears in the most recent release that presents it, and say so in a cell note when the figure differs from the one first reported.
- **Comparability.** The companies use different profit and growth measures. Keep each company's own measure and name it. Do not rank EBITDA margins against operating margins, and do not add or rank revenue across currencies.
- **Charts.** One blue (`#1D4ED8`) for every data mark. Text stays in ink colours. Bars and columns start at zero. Every value is printed beside its mark, and a table with the same numbers sits on the same screen. A monthly line is the one exception: it prints its latest value only, a second line on it is dashed, and its table carries every month. No dual axes, no pie charts, no decoration.
- **Share-price indexes.** A month-end price is `[month, adjusted close]` in the share's own currency, with a source on the series. Never convert a share price and never fill a missing month; the check fails on a gap. US dollar market caps come from a published source and only set the weights of the market-cap-weighted index; between published values a weight moves with the share's own return, and the screen says so. Do not type an index level or a weight into a data file. A monthly return goes in only as a published figure with its source, for a month the price source does not cover. The indexes stop at the last complete month.
- **Copyright.** Summarise in your own words. No quotation of 15 words or more, and at most one short quotation from any source. Never paste paragraphs from articles, releases or transcripts.
- **Public information only.** No material non-public information, no internal company data, and no personal data beyond executives named in public documents.
- **Not investment advice.** No ratings, price targets, or buy and sell language.
- **Human review.** Only a person may add `reviewed_by` and `reviewed_on` to a source. Claude never sets them.
- **Writing.** Plain, short, specific. Avoid "unlock", "seamless", "synergy", "robust", "cutting-edge", "best-in-class" and "world-class". Use "leverage" only as the finance noun for net debt to EBITDA.
- **Self-contained pages.** No external scripts, images, iframes or emoji. Fonts load from Google Fonts; styles and script are inlined by the build.
- **Ids.** Every `id` in a screen is a lower-case slug and unique across all screens, because the one-file build puts every screen on one page.

## Do not

- Change `tools/check.py` to make a failing check pass. Fix the data or the screen, or raise it in the pull request.
- Commit `site/`, secrets, or anything from another repository.
- Update the as-of date in `data/meta.json` without re-checking that the latest period for every company is still the latest.

## Adding things

- **A results release:** follow `docs/UPDATE_PLAYBOOK.md`.
- **A news item:** add it at the top of `news` in `data/news.json`, primary source first. Type `result` shows on TIC earnings news; every other type shows on Industry news.
- **A month of share prices:** follow "After a month end" in `docs/UPDATE_PLAYBOOK.md`.
- **A company:** add it to `companies.json` (and to `order`), to `financials.json` and to `series` and `market_caps` in `prices.json`, with the same key. The annual table needs rows with the roles `revenue`, `profit` and `margin`.
- **A screen:** add the template to `screens/`, an entry to `screens/screens.json`, and any new slot to `slots()` in `tools/render.py`.
