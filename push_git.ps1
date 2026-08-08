$ErrorActionPreference = "Continue"
$token = Get-Content (Join-Path $PSScriptRoot ".github_token") -Raw
$token = $token.Trim()

Set-Location $PSScriptRoot
git rebase --abort 2>$null
git remote set-url origin "https://oauth2:${token}@github.com/your-username/lumilearn.git"
git push -u origin master --force
git remote set-url origin "https://github.com/your-username/lumilearn.git"

Write-Output "PUSH_COMPLETE"