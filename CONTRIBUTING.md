# Contributing

Thanks for helping grow this collection of open-source Android apps! 🎉

## How to Add an App

You have three options, in order of simplicity:

### 1. Use the GitHub Actions workflow (easiest)
Go to **Actions → Add New App → Run workflow**, fill in the category, app name,
and GitHub repo URL. The workflow fetches stars/language/license automatically
and opens the row in the right category. No local setup needed.

### 2. Use the helper script
```bash
pip install -r requirements.txt
export GITHUB_TOKEN=ghp_xxx   # optional, raises the API rate limit
python scripts/add_app.py
```
The script walks you through category selection and writes a correctly
formatted row in alphabetical position.

### 3. Manual PR
Edit the relevant file under [`categories/`](categories/) and add a row that
follows the format below. This is also how you fix metadata or remove archived
projects.

## Row Format

Every app is one row in a 6-column Markdown table, kept in **alphabetical order
by app name** (case-insensitive):

```
| [**App Name**](https://github.com/owner/repo) | Short description. | `Kotlin` | `GPL-3.0` | 1.2k | [![Google Play](https://upload.wikimedia.org/wikipedia/commons/7/78/Google_Play_Store_badge_EN.svg)](https://play.google.com/store/apps/details?id=...) |
```

| Column | Notes |
| :--- | :--- |
| App Name | Bolded link to the GitHub repo. |
| Description | One concise sentence. Append `(Archived)` if the repo is archived. |
| Language | Primary language in backticks (e.g. `` `Kotlin` ``). |
| License | SPDX identifier in backticks (e.g. `` `GPL-3.0` ``). Use `` `Not specified` `` if none. |
| ⭐ Stars | Display form: `1.2k` for ≥1000, raw number otherwise. Auto-updated by the maintenance script. |
| Download | A badge for Google Play / F-Droid, a releases link, or `—` if unavailable. |

## Rules

1. **Open-source only.** Every entry must link to a public source repository.
   Non-open-source references belong under a `### Non-Open-Source` sub-section
   (3-column table) and are not counted toward the category total.
2. **Don't repeat yourself.** Each app should have one primary category. Listing
   an app in a second category is allowed only when it genuinely fits both
   (e.g. NewPipe under *Multi-Media* and *News & Magazines*). Run
   `python scripts/check_repo.py` to spot accidental duplicates.
3. **One change per commit.** Keep commits focused so they're easy to review.
4. **Don't be evil.** 🙃

## Keeping Data Fresh

A scheduled GitHub Action (`maintenance.yml`) runs daily to refresh star counts,
follow repo renames, and flag dead links. It also keeps the README category
counts and the "Total Apps" badge in sync — so you do **not** need to update
those numbers by hand when adding an app.

You can validate the repo locally before opening a PR:

```bash
python scripts/check_repo.py
```

It exits non-zero if counts have drifted or an app is duplicated within a file.
