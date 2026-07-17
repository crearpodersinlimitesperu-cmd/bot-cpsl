$downloadsPath = 'C:\Users\josem\Downloads'
$pattern = 'VERSI*N CORREGIDA Terminios y Condiciones del Servicio - Capitulo I - Creaci*n Cu*ntica NA 12.05.26.doc'
$fullPattern = Join-Path $downloadsPath $pattern

# Buscar el archivo exacto para obtener la ruta de sistema real
$file = Get-ChildItem -Path $fullPattern | Select-Object -First 1

if ($file) {
    $path = $file.FullName
    $outputPath = 'C:\Users\josem\Downloads\bot-cpsl-review\terminos_legales_extraidos.txt'

    try {
        $word = New-Object -ComObject Word.Application
        $word.Visible = $false
        $doc = $word.Documents.Open($path, $false, $true)
        $text = $doc.Content.Text
        $text | Out-File -FilePath $outputPath -Encoding utf8
        $doc.Close()
        $word.Quit()
        Write-Host "EXTRACCION EXITOSA: $outputPath"
        Write-Host "ARCHIVO PROCESADO: $path"
    } catch {
        Write-Host "ERROR EN LA EXTRACCION: $_"
    }
} else {
    Write-Host "ERROR: No se encontró el archivo con el patrón especificado en $downloadsPath"
}
