"""
Scraper do Ranking ENEM (Evolucional Microdados).

Página: https://microdados.evolucional.com.br/microdados/ranking-enem-atual?redacao=sim
A tabela (DataTables, 50/página, ~464 páginas) é montada no navegador a partir de UM endpoint JSON
que traz todas as escolas de uma vez:
    https://microdados.evolucional.com.br/microdados/ranked-schools/<ano>

Estratégia: GET direto no JSON (requests). Se falhar (bloqueio/JS), abre a página com Playwright
e captura a mesma resposta da rede.

Mapeamento de campos (validado contra a tabela exibida):
  SH=Escola  I=Código INEP  C=Cidade  S=UF  D=Dependência  L=Localização  A=Alunos
  LC, CH, CN, MT, RD = notas por área
  G  = média sem redação (4 áreas)   P  = posição sem redação
  GC = média com redação (5 áreas)   PC = posição com redação  (ranking ?redacao=sim)

Uso:  python enem_ranking/scrape.py [--ano 2025]
"""
import argparse
import csv
import json
import sys
from pathlib import Path

PAGE = "https://microdados.evolucional.com.br/microdados/ranking-enem-atual?redacao=sim"
API = "https://microdados.evolucional.com.br/microdados/ranked-schools/{ano}"
OUT = Path(__file__).parent / "data"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"

COLS = [
    ("PC", "posicao_com_redacao"), ("P", "posicao_sem_redacao"),
    ("I", "codigo_inep"), ("SH", "escola"), ("C", "cidade"), ("S", "uf"),
    ("D", "dependencia_administrativa"), ("L", "localizacao"), ("A", "alunos"),
    ("LC", "nota_lc"), ("CH", "nota_ch"), ("CN", "nota_cn"), ("MT", "nota_mt"), ("RD", "nota_redacao"),
    ("GC", "media_com_redacao"), ("G", "media_sem_redacao"),
]
NUM = {"LC", "CH", "CN", "MT", "RD", "G", "GC"}


def via_requests(ano):
    import requests
    r = requests.get(API.format(ano=ano), timeout=120,
                     headers={"User-Agent": UA, "Referer": PAGE, "X-Requested-With": "XMLHttpRequest",
                              "Accept": "application/json"})
    r.raise_for_status()
    return r.json()


def via_playwright(ano):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        with pg.expect_response(lambda r: "/ranked-schools/" in r.url, timeout=120000) as info:
            pg.goto(PAGE, timeout=120000)
        data = info.value.json()
        b.close()
        return data


def to_float(v):
    if v in (None, ""):
        return None
    return float(str(v).replace(".", "").replace(",", ".")) if isinstance(v, str) else float(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ano", default="2025")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    try:
        payload = via_requests(args.ano)
        src = "requests"
    except Exception as e:
        print(f"requests falhou ({e}); usando Playwright", flush=True)
        payload = via_playwright(args.ano)
        src = "playwright"

    rows = payload["data"] if isinstance(payload, dict) else payload
    print(f"{len(rows)} escolas via {src}")
    (OUT / f"ranked_schools_{args.ano}_raw.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    rows.sort(key=lambda r: (r.get("PC") is None, r.get("PC") or 0))
    for name, delim, enc in [(f"ranking_enem_{args.ano}.csv", ",", "utf-8"),
                             (f"ranking_enem_{args.ano}_excel.csv", ";", "utf-8-sig")]:
        with open(OUT / name, "w", newline="", encoding=enc) as f:
            w = csv.writer(f, delimiter=delim)
            w.writerow([c for _, c in COLS])
            for r in rows:
                out = []
                for k, _ in COLS:
                    v = r.get(k)
                    if k in NUM:
                        v = to_float(v)
                        if v is not None and delim == ";":
                            v = f"{v:.2f}".replace(".", ",")
                    out.append(v)
                w.writerow(out)
    extra = set().union(*(r.keys() for r in rows)) - {k for k, _ in COLS}
    if extra:
        print("Campos não mapeados (mantidos no JSON bruto):", extra)
    return 0


if __name__ == "__main__":
    sys.exit(main())
