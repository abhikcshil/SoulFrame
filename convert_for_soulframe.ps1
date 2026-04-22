param(
    [Parameter(Mandatory=$true)]
    [string]$InputFile,

    [string]$OutputFile = "",

    [int]$TargetVideoBitrateK = 2500,
    [int]$TargetAudioBitrateK = 128
)

if (-not (Test-Path $InputFile)) {
    Write-Error "Input file not found: $InputFile"
    exit 1
}

if ([string]::IsNullOrWhiteSpace($OutputFile)) {
    $base = [System.IO.Path]::GetFileNameWithoutExtension($InputFile)
    $dir  = Split-Path $InputFile -Parent
    if ([string]::IsNullOrWhiteSpace($dir)) { $dir = "." }
    $OutputFile = Join-Path $dir "${base}_pi_under50mb.mp4"
}

$ffmpegArgs = @(
    "-y",
    "-i", $InputFile,
    "-vf", "scale='min(1920,iw)':'min(1080,ih)':force_original_aspect_ratio=decrease",
    "-c:v", "libx264",
    "-preset", "medium",
    "-profile:v", "high",
    "-level", "4.1",
    "-pix_fmt", "yuv420p",
    "-b:v", "${TargetVideoBitrateK}k",
    "-maxrate", "$([int]($TargetVideoBitrateK * 1.2))k",
    "-bufsize", "$([int]($TargetVideoBitrateK * 2.4))k",
    "-c:a", "aac",
    "-b:a", "${TargetAudioBitrateK}k",
    "-movflags", "+faststart",
    $OutputFile
)

Write-Host "Converting: $InputFile"
Write-Host "Output:     $OutputFile"
& ffmpeg @ffmpegArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "ffmpeg conversion failed."
    exit $LASTEXITCODE
}

if (Test-Path $OutputFile) {
    $sizeMB = [math]::Round((Get-Item $OutputFile).Length / 1MB, 2)
    Write-Host "Done. Output size: $sizeMB MB"
}

# .\convert-for-soulframe.ps1 -InputFile ".\test.mp4"

# for smaller sizes
# .\convert-for-soulframe.ps1 -InputFile ".\test.mp4" -TargetVideoBitrateK 1800 -TargetAudioBitrateK 96
# .\convert-for-soulframe.ps1 -InputFile ".\test.mp4" -TargetVideoBitrateK 1400 -TargetAudioBitrateK 96