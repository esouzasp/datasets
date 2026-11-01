"""
Scraper do Ranking ENEM (Evolucional Microdados).

Fonte: https://microdados.evolucional.com.br/microdados/ranking-enem-atual?redacao=sim
A tabela é carregada via JavaScript, então usamos Playwright (navegador real).

Saídas (em enem_ranking/data/):
  - ranking_enem_redacao.csv      -> linhas da tabela (DOM), todas as páginas
  - api_responses.jsonl           -> respostas JSON capturadas da rede (dados brutos da API)
  - network_log.json              -> endpoints XHR/fetch vistos (diagnóstico)
  - debug_page.html / debug.png   -> snapshot em caso de falha

Uso:
  python enem_ranking/scrape.py [--max-pages 464] [--headful]
"""
import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

URL = "https://microdados.evolucional.com.br/microdados/ranking-enem-atual?redacao=sim"
OUT = Path(__file__).parent / "data"

NEXT_SELECTORS = [
    "a:has-text('Próximo')", "button:has-text('Próximo')",
    "a:has-text('Próxima')", "button:has-text('Próxima')",
    "a:has-text('Seguinte')", "button:has-text('Seguinte')",
    "li.next:not(.disabled) a", ".paginate_button.next:not(.disabled)",
    "[aria-label='Next']", "[aria-label='Próxima página']", "[aria-label='Próximo']",
    "a:text-is('»')", "button:text-is('»')", "a:text-is('›')", "button:text-is('›')",
    "a:text-is('>')", "button:text-is('>')",
]


def unique(names):
    seen, out = {}, []
    for n in names:
        n = re.sub(r"\s+", " ", n).strip() or "col"
        if n in seen:
            seen[n] += 1
            out.append(f"{n}_{seen[n]}")
        else:
            seen[n] = 1
            out.append(n)
    return out


def table_rows(page):
    """Retorna (headers, rows) da maior tabela da página."""
    return page.evaluate(
        """() => {
        const tables = [...document.querySelectorAll('table')];
        if (!tables.length) return [[], []];
        const t = tables.sort((a,b)=>b.querySelectorAll('tr').length-a.querySelectorAll('tr').length)[0];
        const headRows = [...t.querySelectorAll('thead tr')];
        const head = headRows.length ? [...headRows[headRows.length-1].querySelectorAll('th,td')].map(e=>e.innerText.trim()) : [];
        const body = [...t.querySelectorAll('tbody tr')].map(tr=>[...tr.querySelectorAll('td')].map(td=>td.innerText.replace(/\\s+/g,' ').trim()));
        return [head, body.filter(r=>r.length>1 && !r.join(' ').toLowerCase().includes('carregando'))];
    }"""
    )


def wait_rows(page, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        _, rows = table_rows(page)
        if rows:
            return rows
        time.sleep(0.5)
    raise RuntimeError("Tabela não carregou")


def set_page_size_50(page):
    # tenta <select> primeiro
    for sel in page.query_selector_all("select"):
        opts = [o.inner_text().strip() for o in sel.query_selector_all("option")]
        if "50" in opts:
            sel.select_option(label="50")
            return "select"
    # depois links/botões com texto "50" próximos de "Resultados por página"
    for loc in [
        "xpath=//*[contains(normalize-space(.),'Resultados por página')]/following::*[normalize-space(text())='50'][1]",
        "a:text-is('50')", "button:text-is('50')", "span:text-is('50')", "li:text-is('50')",
    ]:
        try:
            el = page.locator(loc).first
            if el.count():
                el.click(timeout=5000)
                return loc
        except Exception:
            continue
    return None


def click_next(page):
    for s in NEXT_SELECTORS:
        el = page.locator(s).first
        try:
            if el.count() and el.is_visible() and el.is_enabled():
                cls = (el.get_attribute("class") or "") + " " + (el.evaluate("e=>e.parentElement?e.parentElement.className:''") or "")
                if "disabled" in cls:
                    continue
                el.click(timeout=5000)
                return s
        except Exception:
            continue
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pages", type=int, default=1000)
    ap.add_argument("--headful", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    network, api_f = [], open(OUT / "api_responses.jsonl", "w", encoding="utf-8")

    def on_response(resp):
        req = resp.request
        if req.resource_type not in ("xhr", "fetch"):
            return
        entry = {"url": resp.url, "method": req.method, "status": resp.status, "post_data": req.post_data}
        network.append(entry)
        if "json" in (resp.headers.get("content-type") or ""):
            try:
                api_f.write(json.dumps({"url": resp.url, "post_data": req.post_data, "body": resp.json()}, ensure_ascii=False) + "\n")
                api_f.flush()
            except Exception:
                pass

    all_rows, headers, seen = [], None, set()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headful)
        page = browser.new_page(locale="pt-BR", viewport={"width": 1600, "height": 1200})
        page.on("response", on_response)
        try:
            page.goto(URL, wait_until="networkidle", timeout=120000)
            wait_rows(page)
            how = set_page_size_50(page)
            print(f"page-size 50 via: {how}", flush=True)
            time.sleep(2)
            page.wait_for_load_state("networkidle")

            for n in range(1, args.max_pages + 1):
                head, rows = table_rows(page)
                if headers is None:
                    headers = unique(head) if len(head) == len(rows[0]) else [f"col_{i+1}" for i in range(len(rows[0]))]
                new = 0
                for r in rows:
                    k = tuple(r)
                    if k not in seen:
                        seen.add(k)
                        all_rows.append(r)
                        new += 1
                print(f"página {n}: {len(rows)} linhas ({new} novas) total={len(all_rows)}", flush=True)
                if new == 0 and n > 1:
                    print("Sem linhas novas — fim.")
                    break
                first = rows[0]
                if not click_next(page):
                    print("Botão próximo não encontrado/desabilitado — fim.")
                    break
                # espera a tabela mudar
                t0 = time.time()
                while time.time() - t0 < 60:
                    time.sleep(0.4)
                    _, r2 = table_rows(page)
                    if r2 and r2[0] != first:
                        break
                if n % 25 == 0:
                    write_csv(headers, all_rows)
        except Exception as e:
            print("ERRO:", e, file=sys.stderr)
            (OUT / "debug_page.html").write_text(page.content(), encoding="utf-8")
            page.screenshot(path=str(OUT / "debug.png"), full_page=True)
        finally:
            (OUT / "network_log.json").write_text(json.dumps(network, ensure_ascii=False, indent=1), encoding="utf-8")
            api_f.close()
            browser.close()

    if all_rows:
        write_csv(headers, all_rows)
    print(f"TOTAL: {len(all_rows)} linhas")
    return 0 if all_rows else 1


def write_csv(headers, rows):
    with open(OUT / "ranking_enem_redacao.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(headers)
        w.writerows(rows)


if __name__ == "__main__":
    sys.exit(main())
