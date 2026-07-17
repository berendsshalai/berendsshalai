# Live profile-statistics setup

## Repository requirement

The GitHub profile repository must be public and named exactly:

```text
berendsshalai/berendsshalai
```

Upload the entire bundle without flattening its directories.

## First activation

1. Open the repository's **Actions** tab.
2. Open **Refresh profile statistics**.
3. Select **Run workflow**.
4. Confirm that the workflow commits:
   - `assets/github-stats.svg`
   - `data/github-stats.json`
   - the README cache key.
5. Open the profile page and verify all six statistics.

## Workflow permissions

The workflow declares `contents: write`. When repository policy still blocks the commit:

1. Open **Settings -> Actions -> General**.
2. Locate **Workflow permissions**.
3. Select **Read and write permissions**.
4. Save and rerun the workflow.

## Update model

- Scheduled once daily at `04:17 UTC`.
- Manual refresh is available through `workflow_dispatch`.
- Current repositories, stars and followers come from GitHub's REST API.
- Trailing-365-day contributions and commits come from GitHub's GraphQL API.
- Source lines are estimated by shallow-cloning owned public repositories and counting current source files.
- Bot-authored refresh commits do not use the profile owner's commit identity.

## Measurement boundary

"Source lines" is not historical lines added or removed. It is a present-state estimate. The counter excludes common dependency, generated, binary, documentation, asset and build-output paths.
