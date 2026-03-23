$sandbox = "C:\BAS_Ransomware_Test"
$notePath = "$sandbox\RANSOM_NOTE.txt"
if (Test-Path $notePath) { Remove-Item $notePath -Force }
$files = Get-ChildItem -Path $sandbox -Filter "*.bas_locked"
foreach ($file in $files) {
    try {
        $locked = Get-Content $file.FullName -Raw
        $bytes = [Convert]::FromBase64String($locked)
        $content = [System.Text.Encoding]::UTF8.GetString($bytes)
        $origName = $file.FullName -replace '\.bas_locked$', ''
        Set-Content -Path $origName -Value $content
        Remove-Item $file.FullName -Force
    } catch {}
}
