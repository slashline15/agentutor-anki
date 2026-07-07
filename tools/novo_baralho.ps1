Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName Microsoft.VisualBasic

# Configura a codificação de saída para UTF-8 (dos dois lados: console e Python,
# senão os acentos da saída do card_agent viram lixo no MessageBox)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONUTF8 = "1"

# 1. Caixa de texto para o tópico
$topico = [Microsoft.VisualBasic.Interaction]::InputBox(
    "Tópico do baralho:",
    "Novo baralho Anki"
)

# Se o usuário cancelar ou deixar vazio, encerra silenciosamente
if ([string]::IsNullOrWhiteSpace($topico)) {
    exit
}

# 2. Determina a raiz do projeto (pai da pasta onde está este script)
$raizProjeto = Split-Path -Parent $PSScriptRoot

# Caminhos para o interpretador Python e o script Python
$pythonExe = Join-Path $raizProjeto ".venv\Scripts\python.exe"
$scriptPy  = Join-Path $raizProjeto "card_agent.py"

# 3. Executa o script Python capturando stdout+stderr e o código de saída
# Usa chamada direta para que o PowerShell trate cada argumento separadamente
$saidaCompleta = & $pythonExe $scriptPy "--topic" $topico "--push" 2>&1
$codigoSaida   = $LASTEXITCODE

# Converte a saída capturada em array de linhas
$linhas = $saidaCompleta -split "`r?`n"

# 4. Prepara a mensagem para o MessageBox
if ($codigoSaida -eq 0) {
    $titulo = "Baralho criado ✓"
    $quantasLinhas = 8
    $icone = [System.Windows.Forms.MessageBoxIcon]::Information
} else {
    $titulo = "Erro ao gerar baralho"
    $quantasLinhas = 12
    $icone = [System.Windows.Forms.MessageBoxIcon]::Error
}

# Seleciona as últimas N linhas (ou menos, se a saída for curta)
if ($linhas.Count -gt $quantasLinhas) {
    $linhasSelecionadas = $linhas[-$quantasLinhas..-1]
} else {
    $linhasSelecionadas = $linhas
}
$textoMensagem = $linhasSelecionadas -join "`r`n"

# Exibe o MessageBox
[System.Windows.Forms.MessageBox]::Show(
    $textoMensagem,
    $titulo,
    [System.Windows.Forms.MessageBoxButtons]::OK,
    $icone
)
