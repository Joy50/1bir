# List project files that still contain Git merge conflict markers.
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path (Join-Path $root "manage.py"))) {
    $root = Get-Location
}
Get-ChildItem -Path $root -Recurse -File -Include *.py,*.html,*.css,*.js,*.json |
    Where-Object { $_.FullName -notmatch '\\env\\|\\\.git\\' } |
    ForEach-Object {
        if (Select-String -Path $_.FullName -Pattern '^<<<<<<< ' -Quiet) {
            $_.FullName
        }
    }
