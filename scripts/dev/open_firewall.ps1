# Allow inbound TCP for C2 local dev (run PowerShell as Administrator)
# Usage: .\scripts\dev\open_firewall.ps1

$ErrorActionPreference = "Stop"

$rules = @(
    @{ Name = "C2 API (8000)"; Port = 8000 },
    @{ Name = "C2 Map HTTPS (8090)"; Port = 8090 },
    @{ Name = "C2 Map HTTP redirect (8091)"; Port = 8091 }
)

foreach ($rule in $rules) {
    $existing = netsh advfirewall firewall show rule name=$($rule.Name) 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Rule already exists: $($rule.Name)"
        continue
    }
    netsh advfirewall firewall add rule `
        name=$($rule.Name) `
        dir=in action=allow protocol=TCP localport=$($rule.Port) `
        profile=private,domain
    Write-Host "Added firewall rule: $($rule.Name)"
}

Write-Host "Done. Restart backend with --host 0.0.0.0 and map GUI with --https --port 8090"
