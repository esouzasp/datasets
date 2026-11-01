# Ranking ENEM — Evolucional Microdados

Fonte: <https://microdados.evolucional.com.br/microdados/ranking-enem-atual?redacao=sim> (com redação, ~464 páginas × 50 escolas).

## Como rodar
- **GitHub Actions:** aba *Actions* → *Scrape Ranking ENEM (Evolucional)* → *Run workflow*. O CSV é commitado em `enem_ranking/data/`.
- **Local:**
  ```bash
  pip install playwright && python -m playwright install chromium
  python enem_ranking/scrape.py
  ```

## Saídas
| Arquivo | Conteúdo |
|---|---|
| `data/ranking_enem_redacao.csv` | Tabela completa (`;`, UTF-8 BOM — abre direto no Excel) |
| `data/api_responses.jsonl` | Respostas JSON brutas da API do site (artefato do Actions) |
| `data/network_log.json` | Endpoints XHR chamados pela página (diagnóstico) |

Colunas: Posição Geral, Posição, Escola, Cidade, Dependência Administrativa, Alunos, LC, CH, CN, MT, RD, Média.
