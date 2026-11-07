# run.ps1：一条命令启动 mock（8001）+ H5（5173）
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $root
try {
    $venvPy = Join-Path $root ".venv\Scripts\python.exe"
    if (Test-Path $venvPy) {
        $env:CH1807_PYTHON = $venvPy
    } else {
        Write-Host "[run] 未找到 .venv，使用系统 python（建议先按 README 第 2 步安装依赖）"
    }
    node (Join-Path $root "scripts\dev.mjs") @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
