# CODEX DEPLOYMENT PROMPT - SHA-LAI BERENDS GITHUB PROFILE README

Act as a senior GitHub release engineer and repository-maintenance specialist.

## Objective

Publish the supplied repository-ready package as the GitHub profile repository for:

```text
GitHub username: berendsshalai
Required repository: berendsshalai/berendsshalai
Visibility: public
Default branch: main
```

When this repository exists and contains a root `README.md`, GitHub displays that README directly on the user's public profile.

## Package contents

The current folder contains:

```text
README.md
SETUP-LIVE-STATS.md
ascii-portrait.txt
assets/github-stats.svg
data/github-stats.json
scripts/generate_profile_stats.py
.github/workflows/update-profile-stats.yml
```

These files form one complete GitHub profile system.

## Non-negotiable requirements

1. Preserve the directory structure exactly.
2. Keep `README.md` at the repository root.
3. Keep `.github/workflows/update-profile-stats.yml` at that exact path.
4. Keep `assets/github-stats.svg` and `data/github-stats.json`.
5. Keep all clickable contact links unchanged unless the user explicitly supplies replacements.
6. Do not add employer names, client names, branch/location names, internal system names, private addresses, secrets, tokens or confidential data.
7. Do not commit any local `.env`, authentication file, editor settings, cache folder or operating-system metadata.
8. Never print or commit GitHub authentication tokens.
9. Use the existing GitHub account authentication already available to Codex or the GitHub CLI.
10. Do not create a paid service or paid GitHub feature.

## Contact-link acceptance criteria

Verify that every badge and table entry in the `Contact` section is wrapped in a valid Markdown or HTML hyperlink and opens the correct external page:

- LinkedIn: `https://www.linkedin.com/in/sha-lai-berends`
- X: `https://x.com/berendsshalai`
- Facebook: `https://www.facebook.com/p/Sha-Lai-Berends-61591546301365/`
- Instagram: `https://www.instagram.com/berendsshalai`
- EasyEquities: `https://bit.ly/3sA5312`
- Website: `https://sha-lai-be-2a6c6108-shalaiberends.wix-site-host.com`

Do not convert these to plain text.

## Deployment sequence

### 1. Inspect and validate

- Confirm the current folder contains every required file.
- Parse `README.md`.
- Confirm that the live-stat image points to:

```text
./assets/github-stats.svg
```

- Confirm that all six contact links are clickable.
- Confirm Python syntax:

```bash
python -m py_compile scripts/generate_profile_stats.py
```

- Confirm the YAML workflow is present and readable.
- Scan the complete folder for:
  - secrets;
  - API keys;
  - private tokens;
  - passwords;
  - private organisation names;
  - local user paths;
  - accidental personal contact details not intended for publication.

Stop before publication if a real secret or private organisational identifier is detected.

### 2. Prepare the GitHub repository

Check whether `berendsshalai/berendsshalai` exists.

If it does not exist, create it as:

```text
Name: berendsshalai
Owner: berendsshalai
Visibility: public
Description: GitHub profile README for Sha-Lai Berends
Initial branch: main
```

Do not add a generated README, licence or `.gitignore` during remote creation if that would conflict with this package.

If it already exists:

- fetch the current repository;
- preserve unrelated user-authored content unless it conflicts with the requested profile system;
- create a backup branch before replacing the profile files;
- never force-push over unknown work without preserving it.

### 3. Initialise or update locally

Use standard Git commands or GitHub CLI.

For a new repository:

```bash
git init
git branch -M main
git add .
git commit -m "feat(profile): publish live GitHub profile README"
git remote add origin https://github.com/berendsshalai/berendsshalai.git
git push -u origin main
```

For an existing repository:

```bash
git fetch origin
git checkout main
git pull --ff-only origin main
git checkout -b backup/profile-before-live-stats
git push -u origin backup/profile-before-live-stats
git checkout main
```

Then copy or update only the package files, review the diff and commit:

```bash
git add README.md SETUP-LIVE-STATS.md ascii-portrait.txt assets data scripts .github
git commit -m "feat(profile): add live statistics and contact links"
git push origin main
```

Use a different commit message only when it is more accurate.

### 4. Activate workflow permissions

The workflow requires:

```yaml
permissions:
  contents: write
```

Verify repository Actions settings permit workflow write access.

When GitHub blocks automated commits:

- open repository Settings;
- open Actions -> General;
- set Workflow permissions to "Read and write permissions";
- save;
- rerun the workflow.

Do not create a personal access token unless the standard repository `GITHUB_TOKEN` is demonstrably insufficient.

### 5. Run the live-stat workflow

Run:

```text
Actions -> Refresh profile statistics -> Run workflow
```

Or with GitHub CLI:

```bash
gh workflow run "Refresh profile statistics" --repo berendsshalai/berendsshalai
```

Wait for completion.

Confirm that the workflow updates and commits:

```text
README.md
assets/github-stats.svg
data/github-stats.json
```

### 6. Verify the public profile

Open:

```text
https://github.com/berendsshalai
```

Confirm:

- the README appears on the profile page;
- the ASCII portrait is visible;
- the live GitHub statistics card renders;
- repositories, stars, followers, contributions, commits and source-line estimate contain values;
- every contact badge is clickable;
- every contact-table link is clickable;
- the layout works in GitHub dark and light themes;
- there are no broken image references;
- no confidential names or data appear.

### 7. Report

Create or update `DEPLOYMENT_REPORT.md` locally with:

- repository URL;
- commit SHA;
- deployment date and time;
- workflow run URL;
- workflow result;
- live-stat values generated;
- contact links verified;
- public-profile verification result;
- any remaining limitations.

Do not publish `DEPLOYMENT_REPORT.md` unless it contains no sensitive information and the user benefits from it being public.

## Live-stat definitions

The displayed values must remain accurately labelled:

- `Repositories`: currently owned public repositories.
- `Stars`: current stars summed across owned public repositories.
- `Followers`: current follower count.
- `Contributions`: trailing 365-day GitHub contribution total.
- `Commits`: trailing 365-day commit contributions.
- `Source lines`: estimated current tracked source-code lines across owned public non-fork repositories.

Do not describe the source-line count as exact historical lines of code.

## Completion condition

The task is complete only when:

1. the repository is public and named `berendsshalai/berendsshalai`;
2. the root README renders on the GitHub profile;
3. the live-stat workflow passes;
4. the generated statistics card displays current values;
5. all contact links are clickable;
6. no secrets or private organisational identifiers are present;
7. the final commit has been pushed to `main`.
