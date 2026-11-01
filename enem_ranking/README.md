# Ranking ENEM 2025 — Evolucional Microdados

Fonte: <https://microdados.evolucional.com.br/microdados/ranking-enem-atual?redacao=sim>

A página exibe 50 escolas por página (464 páginas), mas a tabela é montada no navegador a partir de um único
endpoint JSON, `https://microdados.evolucional.com.br/microdados/ranked-schools/2025`. O scraper consulta esse
endpoint diretamente e recebe todas as escolas (23.164) em uma só requisição. Se falhar, usa o Playwright
(navegador real) como alternativa.

## Arquivos (`data/`)
| Arquivo | Conteúdo |
|---|---|
| `ranking_enem_2025.csv` | CSV padrão (`,`, ponto decimal, UTF-8), ordenado pela posição com redação |
| `ranking_enem_2025_excel.csv` | Mesmos dados para Excel PT-BR (`;`, vírgula decimal, UTF-8 BOM) |
| `ranked_schools_2025_raw.json` | Resposta original da API |

## Dicionário
| Coluna | Campo API | Descrição |
|---|---|---|
| posicao_com_redacao | PC | Posição geral no ranking com redação (o desta página). Empates dividem a posição (ranking denso: 23.164 escolas, 13.364 posições) |
| posicao_sem_redacao | P | Posição geral sem redação |
| codigo_inep | I | Código INEP da escola |
| escola | SH | Nome |
| cidade / uf | C / S | Município / estado |
| dependencia_administrativa | D | Municipal, Estadual, Federal, Privada |
| localizacao | L | Urbana / Rural |
| alunos | A | Participantes considerados |
| nota_lc, nota_ch, nota_cn, nota_mt, nota_redacao | LC, CH, CN, MT, RD | Médias por área |
| media_com_redacao | GC | Média das 5 notas |
| media_sem_redacao | G | Média das 4 objetivas |

## Atualizar
Aba *Actions* → **Scrape Ranking ENEM (Evolucional)** → *Run workflow* (parâmetro `ano`).
Local: `pip install requests playwright && python enem_ranking/scrape.py --ano 2025`
