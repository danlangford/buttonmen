# GitHub Actions CI

GitHub Actions runs the same checks as CircleCI (`.circleci/config.yml`), so the two can run side by side until one is chosen. CircleCI is unchanged.

## How it works

- `deploy/ci/steps.sh` holds every CI command, copied from `.circleci/config.yml`. The workflow calls it one step at a time, so both CI systems run identical commands.
- `deploy/ci/Dockerfile` builds an image with the CircleCI puppet setup already applied. It's rebuilt only when `deploy/vagrant/`, `deploy/circleci/manifests/` or the Dockerfile change, and is stored as `ghcr.io/<owner>/buttonmen-ci`.
- Jobs still run puppet against their own checkout (`steps.sh prepare`). Puppet copies the current source into `/var/www` and rebuilds the databases every time, so tests never run against code baked into the image; the image only saves package installs.

## Workflows

`.github/workflows/ci.yml` runs on every push, on pull requests from forks, weekly and on demand:

| Job | What it runs |
|---|---|
| CI image | Reuses or builds the image above |
| Lint and audits | newlines, PHP layout, JS test coverage, grunt, PHP_CodeSniffer |
| Unit tests | database update consistency, PHPUnit, dummy API data, QUnit, python 2 and 3 client tests |
| Code metrics | PHP_Depend, PHPMD, phploc, PHP_CodeBrowser; weekly, on demand and on the default branch only |
| Publish test results | PHPUnit results as a "Test Results" check |

Each run also writes a test summary to its run page, and uploads logs and reports as artifacts.

`.github/workflows/ci-results.yml` publishes test results for pull requests from forks. Their own CI run can't write checks, so this runs separately from the default branch, using only the uploaded results, never the pull request's code.

## Notes

- With the image cached, a run takes about 3 minutes; building the image takes about 8 more.
- GitHub-hosted runners are free for public repositories.
- Actions are pinned to commit SHAs; Dependabot (`.github/dependabot.yml`) proposes updates.
- The image package inherits the repository's visibility, so in a public repository it's public and pull requests from forks can pull it.
- To try this without CircleCI, or remove it again: delete `.github/` and `deploy/ci/`.
