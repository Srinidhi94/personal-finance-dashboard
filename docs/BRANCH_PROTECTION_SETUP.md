# Branch Protection Setup Guide

This guide will help you set up branch protection rules for your `main` branch to ensure code quality and require PR reviews before merging.

## Prerequisites

- You must be the repository owner or have admin permissions
- Your repository must have at least one commit on the `main` branch

## Step-by-Step Setup

### 1. Navigate to Branch Protection Settings

1. Go to your GitHub repository
2. Click on **Settings** tab
3. In the left sidebar, click on **Branches**
4. Click **Add rule** button

### 2. Configure Branch Protection Rule

#### Basic Settings
- **Branch name pattern**: `main`
- Check **Restrict pushes that create matching branches**

#### Pull Request Requirements
Check the following options:

- ✅ **Require a pull request before merging**
  - ✅ **Require approvals**: Set to `1` (minimum 1 reviewer)
  - ✅ **Dismiss stale PR approvals when new commits are pushed**
  - ✅ **Require review from code owners** (if you have a CODEOWNERS file)

#### Status Check Requirements
- ✅ **Require status checks to pass before merging**
- ✅ **Require branches to be up to date before merging**

**Required status checks to add:**
- `test` (from your GitHub Actions workflow)
- `lint` (from your GitHub Actions workflow)

*Note: These status checks will only appear after you've run your GitHub Actions at least once*

#### Additional Restrictions
- ✅ **Restrict pushes that create matching branches**
- ✅ **Do not allow bypassing the above settings**
- ❌ **Allow force pushes** (keep unchecked for security)
- ❌ **Allow deletions** (keep unchecked for security)

### 3. Advanced Settings (Optional but Recommended)

#### For Enhanced Security:
- ✅ **Require signed commits** (if you use commit signing)
- ✅ **Require linear history** (prevents merge commits, forces rebase/squash)
- ✅ **Include administrators** (applies rules to repo admins too)

### 4. Save the Rule

Click **Create** to save your branch protection rule.

## Workflow After Setup

### For Contributors (including yourself):

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes and commit**:
   ```bash
   git add .
   git commit -m "Your commit message"
   git push origin feature/your-feature-name
   ```

3. **Create a Pull Request**:
   - Go to GitHub and create a PR from your feature branch to `main`
   - Wait for status checks (tests and linting) to pass
   - Request review from a team member (or use a second account for personal projects)

4. **Merge after approval**:
   - Once approved and all checks pass, you can merge the PR
   - Delete the feature branch after merging

### Status Checks Configuration

Your `.github/workflows/test.yml` should include these job names that match the required status checks:

```yaml
name: Test and Lint

on:
  pull_request:
    branches: [ main ]
  push:
    branches: [ main ]

jobs:
  test:
    name: test
    runs-on: ubuntu-latest
    # ... test configuration

  lint:
    name: lint
    runs-on: ubuntu-latest
    # ... lint configuration
```

## Troubleshooting

### Status Checks Not Appearing
- Run your GitHub Actions workflow at least once
- The status check names must match exactly (case-sensitive)
- Check that your workflow runs on `pull_request` events

### Can't Push to Main
This is expected! You now need to:
1. Create a feature branch
2. Push changes to the feature branch
3. Create a PR
4. Get approval and pass status checks
5. Merge via GitHub UI

### Emergency Bypass (Repository Owners Only)
If you need to bypass protection rules in an emergency:
1. Go to Settings > Branches
2. Temporarily disable the rule
3. Make your changes
4. Re-enable the rule immediately

## Best Practices

### For Solo Development:
- Use a second GitHub account for reviews, or
- Set up automated reviews with GitHub Apps, or
- Use draft PRs for work-in-progress

### For Team Development:
- Assign specific reviewers for different areas of code
- Use CODEOWNERS file to automatically request reviews
- Set up automated status checks for comprehensive testing

### Code Review Guidelines:
- Review for functionality, security, and code quality
- Check that tests are included for new features
- Ensure documentation is updated when needed
- Verify that the PR description explains the changes

## CODEOWNERS File (Optional)

Create a `.github/CODEOWNERS` file to automatically request reviews:

```
# Global owners
* @your-username

# Specific paths
/app.py @backend-team
/templates/ @frontend-team
/tests/ @qa-team
/.github/ @devops-team
```

## Monitoring and Maintenance

### Regular Tasks:
- Review and update required status checks as your CI/CD evolves
- Monitor PR merge times and adjust approval requirements if needed
- Update branch protection rules when adding new workflows

### Metrics to Track:
- Time from PR creation to merge
- Number of failed status checks
- Code review turnaround time

---

## Quick Setup Checklist

- [ ] Navigate to Settings > Branches
- [ ] Add rule for `main` branch
- [ ] Require pull request before merging
- [ ] Require 1 approval
- [ ] Require status checks: `test` and `lint`
- [ ] Require branches to be up to date
- [ ] Restrict pushes that create matching branches
- [ ] Do not allow bypassing settings
- [ ] Save the rule
- [ ] Test with a sample PR

Your main branch is now protected! 🛡️ 