#!/bin/sh
# Gera os PDFs dos entregáveis (classe abnTeX2, normas ABNT) em docs/.
# Requer o Tectonic (brew install tectonic); na primeira execução ele baixa os pacotes usados.
# Uso: ./gerar_pdf.sh [arquivo.tex ...]   (sem argumentos, gera os três documentos)
set -e
cd "$(dirname "$0")"
if [ $# -eq 0 ]; then
  set -- 01_documento_requisitos.tex 02_modelagem.tex 04_relatorio_tecnico.tex
fi
for arquivo in "$@"; do
  echo "[*] $arquivo"
  tectonic -X compile "$arquivo" --outdir .. 
  echo "[OK] ../${arquivo%.tex}.pdf"
done
