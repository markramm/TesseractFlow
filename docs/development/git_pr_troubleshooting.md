# Pull Request Troubleshooting

This repository is initialized without a Git remote, so commands such as `git push` or any tooling that relies on a GitHub pull request will fail until you configure one. Even after renaming the working branch to match the project guide (`001-mvp-optimizer`), the automation still cannot open a PR because there is nowhere to push the commits.

## Why PR creation fails

The automation checks for an `origin` remote before attempting to create a pull request. Because the project is bootstrapped locally for implementation work, no remote is defined by default:

```bash
git remote -v
# (no output)
```

Without a remote, Git cannot determine where to push your commits, which is a prerequisite for PR creation on GitHub.

You can verify the current branch separately. After the recent rename the status shows the expected branch but still fails to push:

```bash
git status -sb
## 001-mvp-optimizer
```

If your output shows a different branch name, run `git branch -m <old> 001-mvp-optimizer` to align with the specification. This alone does not fix PR creation; a remote is still required.

## Fix: add your GitHub remote

1. Create an empty repository on GitHub (or use an existing one).
2. Add it as the `origin` remote in this project:

```bash
git remote add origin git@github.com:<your-username>/<your-repo>.git
```

3. Push the current branch:

```bash
git push -u origin 001-mvp-optimizer
```

After the remote exists, the PR automation can push commits and open a pull request as expected.

## Local work is unaffected

You can continue committing locally even without a remote:

```bash
git status
# On branch 001-mvp-optimizer
# nothing to commit, working tree clean

# make your changes, then

git add <files>
git commit -m "feat: describe your change"
```

These commits remain in your local Git history and can be pushed later once a remote is configured.

## Missing pytest plugins

If `pytest` fails with messages about missing coverage or asyncio plugins, install them explicitly:

```bash
pip install pytest-cov pytest-asyncio
```

These packages are already listed in `pyproject.toml`, but they need to be installed into your active environment (e.g., a new virtualenv) before coverage-enabled test runs will succeed.
