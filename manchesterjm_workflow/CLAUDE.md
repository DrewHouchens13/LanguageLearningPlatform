# Git Workflow

## Repository Setup
- **origin**: Personal repository (https://github.com/manchesterjm/claude_code_web_repo)
  - Default destination for all commits and pushes
  - No branch protection - commit freely here
  - Used by Claude Code web interface
- **team**: Team repository (https://github.com/DrewHouchens13/LanguageLearningPlatform)
  - Has branch protection enabled
  - Only push here when ready to create PR
  - Requires pull request for merging

## Development Workflow
1. Work normally and commit to origin (personal repo)
2. Push to origin regularly: `git push origin <branch-name>`
3. When ready to share with team:
   - Ensure all changes are committed to origin first
   - Run: `git push team <branch-name>`
   - Go to https://github.com/DrewHouchens13/LanguageLearningPlatform
   - Create PR from your branch to team's main/master branch

## Important Rules for Claude Code
- **DEFAULT**: Always commit and push to origin unless explicitly told otherwise
- **NEVER** push directly to team remote during development
- **ALWAYS** commit to origin first
- **ONLY** push to team when I explicitly say "push to team" or "ready for team PR"
- When I say "commit" or "push" without specifying, always use origin
- When working in Claude Code web, it will automatically use origin

## Commands Reference
- Check remotes: `git remote -v`
- Commit to personal repo: `git push origin <branch-name>`
- Push to team repo (when ready): `git push team <branch-name>`
- Fetch from team repo: `git fetch team`
- Pull from team repo: `git pull team <branch-name>`

## Claude Code Web Usage
- Claude Code web connects to: https://github.com/manchesterjm/claude_code_web_repo
- All work is done in personal repo first
- After Claude Code web completes work, manually push to team repo using: `git push team <branch-name>`
