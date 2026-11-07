# verify.ps1：一条命令验收（mock 单测 + 前端构建 + Playwright E2E + 截图/布局/溢出断言）
# 用法: .\verify.ps1
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPy = Join-Path $root ".venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    $py = $venvPy
} else {
    Write-Host "[verify] 未找到 .venv，使用系统 python（依赖可能未安装，见 README 第 2 步）"
    $py = "python"
}
Push-Location $root
try {
    & $py (Join-Path $root "scripts\verify.py")
    $code = $LASTEXITCODE
} finally {
    Pop-Location
}
if ($code -ne 0) {
    Write-Host "VERIFY FAIL (exit $code)"
    exit $code
}
Write-Host "VERIFY PASS (exit 0)"
exit 0
