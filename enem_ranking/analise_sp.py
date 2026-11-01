"""
Ranking ENEM 2025 da cidade de São Paulo com unidades da mesma escola/rede agrupadas.

Agrupamento:
  1) Nome normalizado: remove sufixos de unidade/etapa (UNIDADE X, CAMPUS X, UNID, I/II/III/IV,
     EFM, EIFM, EEIFM, ENSINO MEDIO...) -> une INEPs com o mesmo nome (ex.: AMORIM COLEGIO x2).
  2) Regras de marca para redes cujo nome principal é a marca (ETAPA, OBJETIVO, PORTO SEGURO,
     REDE DECISAO, SESI, SENAC, IFSP, ADVENTISTA, POLICIA MILITAR ...).
  Escolas com nome próprio distinto de uma rede (ex.: Arquidiocesano/Marista, ETECs, EEs) ficam separadas.

Média ponderada por aluno: nota_grupo = soma(nota_i * alunos_i) / soma(alunos_i), por área.
Saída: enem_ranking/analise/ranking_sp_agrupado.csv e mapa_agrupamento_sp.csv
"""
import re
from pathlib import Path
import pandas as pd

BASE = Path(__file__).parent
OUT = BASE / "analise"
AREAS = ["nota_lc", "nota_ch", "nota_cn", "nota_mt", "nota_redacao"]

BRANDS = [  # (regex, nome do grupo) — avaliadas em ordem
    (r"\bETAPA\b", "ETAPA (rede)"),
    (r"\bOBJETIVO\b", "OBJETIVO (rede)"),
    (r"VISCONDE DE PORTO SEGURO", "VISCONDE DE PORTO SEGURO (rede)"),
    (r"\bPENTAGONO\b", "PENTÁGONO (rede)"),
    (r"JARDIM SAO PAULO .*COLEGIO|JARDIM SAO PAULO COLEGIO", "JARDIM SÃO PAULO COLÉGIO (rede)"),
    (r"\bVERTICE\b", "VÉRTICE (rede)"),
    (r"REDE DECISAO", "REDE DECISÃO (rede)"),
    (r"\bSESI\b", "SESI (rede)"),
    (r"\bSENAC\b", "SENAC (rede)"),
    (r"^IFSP\b", "IFSP (rede)"),
    (r"ADVENTISTA", "ADVENTISTA (rede)"),
    (r"POLICIA MILITAR", "COLÉGIO DA POLÍCIA MILITAR (rede)"),
    (r"PUERI DOMUS", "PUERI DOMUS (rede)"),
    (r"NOVA LOURENCO", "ESCOLA NOVA LOURENÇO CASTANHO (rede)"),
    (r"LUMINOVA", "LUMINOVA (rede)"),
    (r"^ESCOLA MAIS\b", "ESCOLA MAIS (rede)"),
    (r"^ELITE\b", "ELITE (rede)"),
    (r"GALILEU GALILEI", "GALILEU GALILEI (rede)"),
    (r"^AMORIM\b", "AMORIM (rede)"),
    (r"^ALIADO\b", "ALIADO (rede)"),
    (r"^INOVACAO COLEGIO", "INOVAÇÃO (rede)"),
    (r"^ISAAC NEWTON ESCOLA", "ISAAC NEWTON ESCOLA (rede)"),
    (r"NOSSA SENHORA DE SION", "NOSSA SENHORA DE SION (rede)"),
    (r"PASCHOAL DANTAS", "PASCHOAL DANTAS (rede)"),
    (r"^SAO LUIS COLEGIO", "SÃO LUÍS COLÉGIO (rede)"),
    (r"SAO LUIZ DE GONZAGA", "SÃO LUIZ DE GONZAGA (rede)"),
    (r"^FIAP\b", "FIAP SCHOOL (rede)"),
    (r"DOM FELIPE", "DOM FELIPE (rede)"),
    (r"^VIP COLEGIO", "VIP COLÉGIO (rede)"),
    (r"^MARIA IMACULADA COLEGIO", "MARIA IMACULADA (rede)"),
]

GENERIC = r"\b(UNIDADE|UNID|CAMPUS)\b.*$"
STAGE = r"\b(EFM|EIFM|EEIFM|EIEFEM|EM|ENSINO MEDIO|ENSINO FUNDAMENTAL E MEDIO|I|II|III|IV|V)\b"


def norm(name):
    n = re.sub(GENERIC, "", name)
    n = re.sub(STAGE, "", n)
    return re.sub(r"\s+", " ", n).strip(" -")


def group_name(row):
    if row.dependencia_administrativa == "Privada" or row.dependencia_administrativa == "Federal":
        for rx, g in BRANDS:
            if re.search(rx, row.escola):
                return g
    return norm(row.escola) if row.dependencia_administrativa == "Privada" else row.escola


def wavg(g):
    w = g.alunos
    out = {a: (g[a] * w).sum() / w.sum() for a in AREAS}
    out["media_geral"] = sum(out[a] for a in AREAS) / 5
    out["media_objetivas"] = sum(out[a] for a in AREAS[:4]) / 4
    out["alunos"] = w.sum()
    out["unidades"] = len(g)
    out["dependencia"] = g.dependencia_administrativa.mode()[0]
    out["codigos_inep"] = " ".join(g.codigo_inep)
    out["melhor_unidade_media"] = g.media_com_redacao.max()
    out["pior_unidade_media"] = g.media_com_redacao.min()
    return pd.Series(out)


def benchmarks(d, sp):
    """Médias ponderadas por aluno para recortes de comparação."""
    def w(x, lab):
        r = {"recorte": lab, "escolas_inep": len(x), "alunos": int(x.alunos.sum())}
        for c in AREAS + ["media_com_redacao"]:
            r["media_geral" if c == "media_com_redacao" else c] = (x[c] * x.alunos).sum() / x.alunos.sum()
        return r
    sp_uf = d[d.uf == "São Paulo"]
    est = sp[sp.dependencia_administrativa == "Estadual"]
    rows = [w(d, "Brasil"), w(sp_uf, "Estado de SP"), w(sp, "Cidade de SP"),
            w(sp[sp.dependencia_administrativa == "Privada"], "Privada"),
            w(est, "Estadual"),
            w(est[est.escola.str.startswith("ETEC")], "Estadual: ETECs"),
            w(est[~est.escola.str.startswith("ETEC")], "Estadual: demais (EEs)"),
            w(sp[sp.dependencia_administrativa == "Federal"], "Federal (IFSP)"),
            w(sp[sp.dependencia_administrativa == "Municipal"], "Municipal")]
    return pd.DataFrame(rows)


def main():
    d = pd.read_csv(BASE / "data/ranking_enem_2025.csv", dtype={"codigo_inep": str})
    sp = d[(d.cidade == "São Paulo") & (d.uf == "São Paulo")].copy()
    sp["grupo"] = sp.apply(group_name, axis=1)
    g = sp.groupby("grupo").apply(wavg, include_groups=False).reset_index()
    g["grupo"] = [n.replace(" (rede)", "") if u == 1 else n for n, u in zip(g.grupo, g.unidades)]
    g = g.sort_values("media_geral", ascending=False).reset_index(drop=True)
    g.insert(0, "rank_geral", g.media_geral.rank(ascending=False, method="min").astype(int))
    for a in AREAS:
        g[f"rank_{a.replace('nota_', '')}"] = g[a].rank(ascending=False, method="min").astype(int)
    OUT.mkdir(exist_ok=True)
    g.round(2).to_csv(OUT / "ranking_sp_agrupado.csv", index=False)
    single = set(g.loc[g.unidades == 1, "grupo"])
    sp["grupo"] = [x.replace(" (rede)", "") if x.replace(" (rede)", "") in single else x for x in sp.grupo]
    sp[["codigo_inep", "escola", "dependencia_administrativa", "alunos", "media_com_redacao", "grupo"]] \
        .sort_values(["grupo", "media_com_redacao"], ascending=[True, False]) \
        .to_csv(OUT / "mapa_agrupamento_sp.csv", index=False)
    benchmarks(d, sp).round(2).to_csv(OUT / "benchmarks_sp.csv", index=False)
    print(f"{len(sp)} INEPs -> {len(g)} escolas/redes; {sp.alunos.sum()} alunos")
    return sp, g


if __name__ == "__main__":
    main()
