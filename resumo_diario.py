#!/usr/bin/env python3
"""Manda todo dia às 9h um resumo do site para o e-mail de contato.

Conta o que aconteceu ontem (matérias publicadas, descartadas, pedidos de remoção,
rodadas do robô), o que está em alta agora e os atalhos para Analytics, Search
Console e AdSense. Usa a mesma senha de app do Gmail do atendimento de e-mails.
"""
import html
import json
import os
import smtplib
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
TESTE = "--teste" in sys.argv
sys.argv = [sys.argv[0]]  # o build.py lê os argumentos ao ser importado
import build as b  # noqa: E402  (reaproveita as regras do site: temperatura, categorias, datas)

BRT = timezone(timedelta(hours=-3))
AGORA = datetime.now(timezone.utc)
# RESUMO_DE=hoje serve para testar com o dia corrente
ONTEM = (AGORA.astimezone(BRT) - timedelta(days=0 if os.environ.get("RESUMO_DE") == "hoje" else 1)).date()
E = html.escape
CUSTO_POR_MATERIA = 0.0024  # dólares, Haiku com revisão (estimativa)


def no_dia(iso, dia):
    return datetime.fromisoformat(iso).astimezone(BRT).date() == dia


def rodadas_de_ontem():
    """Quantas atualizações automáticas rodaram ontem e quantas falharam (API do GitHub)."""
    token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        return None
    inicio = datetime.combine(ONTEM, datetime.min.time(), BRT).astimezone(timezone.utc)
    fim = inicio + timedelta(days=1)
    url = (f"https://api.github.com/repos/{repo}/actions/workflows/atualizar.yml/runs"
           f"?per_page=100&created={inicio:%Y-%m-%dT%H:%M:%SZ}..{fim:%Y-%m-%dT%H:%M:%SZ}")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}",
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        runs = json.load(r).get("workflow_runs", [])
    return len(runs), sum(1 for x in runs if x.get("conclusion") not in ("success", None))


GA_PROPRIEDADE = "564027803"


def metricas():
    """Visitas (Google Analytics) e buscas (Search Console) de ontem, pelo usuário-robô só de leitura."""
    import google.auth
    from google.auth.transport.requests import AuthorizedSession

    cred, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/analytics.readonly",
                                          "https://www.googleapis.com/auth/webmasters.readonly"])
    bruta = AuthorizedSession(cred)

    class Sessao:  # resposta com erro vira exceção, em vez de virar "zero visitas"
        def post(self, url, **kw):
            r = bruta.post(url, **kw)
            d = r.json()
            if r.status_code >= 400 or "error" in d:
                raise RuntimeError(f"{url.split('/')[2]}: {d.get('error', {}).get('message', r.status_code)}")
            return type("R", (), {"json": lambda _s: d})()

    sessao = Sessao()
    dia = ONTEM.isoformat()
    ga = f"https://analyticsdata.googleapis.com/v1beta/properties/{GA_PROPRIEDADE}:runReport"
    faixa = [{"startDate": dia, "endDate": dia}]
    total = sessao.post(ga, json={"dateRanges": faixa, "metrics": [
        {"name": "activeUsers"}, {"name": "screenPageViews"}, {"name": "sessions"}]}, timeout=30).json()
    vals = [int(v["value"]) for v in (total.get("rows") or [{"metricValues": [{"value": 0}] * 3}])[0]["metricValues"]]
    paginas = sessao.post(ga, json={"dateRanges": faixa, "dimensions": [{"name": "pageTitle"}],
                                    "metrics": [{"name": "screenPageViews"}], "limit": 5,
                                    "orderBys": [{"metric": {"metricName": "screenPageViews"}, "desc": True}]}, timeout=30).json()
    origens = sessao.post(ga, json={"dateRanges": faixa, "dimensions": [{"name": "sessionSource"}],
                                    "metrics": [{"name": "sessions"}], "limit": 5,
                                    "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}]}, timeout=30).json()
    linha = lambda r: (r["dimensionValues"][0]["value"], int(r["metricValues"][0]["value"]))
    site = urllib.parse.quote(b.BASE + "/", safe="")
    sc = sessao.post(f"https://searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query",
                     json={"startDate": dia, "endDate": dia, "dimensions": ["query"], "rowLimit": 5}, timeout=30).json()
    sc_total = sessao.post(f"https://searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query",
                           json={"startDate": dia, "endDate": dia}, timeout=30).json()
    t = (sc_total.get("rows") or [{}])[0]
    return {
        "usuarios": vals[0], "visualizacoes": vals[1], "sessoes": vals[2],
        "paginas": [linha(r) for r in paginas.get("rows", [])],
        "origens": [linha(r) for r in origens.get("rows", [])],
        "cliques": int(t.get("clicks", 0)), "impressoes": int(t.get("impressions", 0)),
        "buscas": [(r["keys"][0], int(r.get("clicks", 0)), int(r.get("impressions", 0))) for r in sc.get("rows", [])],
    }


def montar():
    resumos = json.loads(b.RESUMOS.read_text(encoding="utf-8")) if b.RESUMOS.exists() else {}
    noticias = json.loads(b.DADOS.read_text(encoding="utf-8")) if b.DADOS.exists() else []
    remover_arq = RAIZ / "data" / "remover.json"
    remocoes = json.loads(remover_arq.read_text(encoding="utf-8")) if remover_arq.exists() else []

    publicadas = [r for r in resumos.values() if r.get("slug") and no_dia(r["criado"], ONTEM)]
    descartadas = [r for r in resumos.values() if not r.get("slug") and no_dia(r["criado"], ONTEM)]
    removidas = [x for x in remocoes if x.get("quando") and no_dia(x["quando"], ONTEM)]
    coletadas = [n for n in noticias if no_dia(n["data"], ONTEM)]

    itens = b.montar_itens(noticias, resumos)
    calor = b.calcular_calor(itens)
    quentes, vistos = [], set()
    for i in sorted(itens, key=lambda i: -calor[id(i)][0]):
        chave = i.titulo.split(":")[0].lower()[:30]
        if chave in vistos:
            continue
        vistos.add(chave)
        quentes.append(i)
        if len(quentes) == 5:
            break

    try:
        rodadas = rodadas_de_ontem()
    except Exception:
        rodadas = None
    try:
        m = metricas()
    except Exception as e:
        print(f"  ! Métricas do Google indisponíveis: {e}")
        m = None

    base = b.BASE
    dia = ONTEM.strftime("%d/%m")
    linhas_pub = "".join(
        f'<li><a href="{base}/noticia/{E(r["slug"])}.html">{E(r["titulo"])}</a> '
        f'<span style="color:#888">· {E(b.CATS.get(r["categoria"], ""))}</span></li>'
        for r in sorted(publicadas, key=lambda r: r["criado"], reverse=True)[:10])
    linhas_quentes = "".join(
        f'<li><a href="{E(i.href(base + "/"))}">{E(i.titulo)}</a>'
        + (f' <b style="color:#ff1f5a">· {E(b.selo_calor(i, calor))}</b>' if b.selo_calor(i, calor) else "")
        + "</li>" for i in quentes)
    linhas_rem = "".join(f"<li>{E(x.get('slug', ''))}</li>" for x in removidas) or "<li>Nenhum pedido</li>"
    saude = ("sem dados" if rodadas is None else
             f"{rodadas[0]} atualizações, {'nenhuma falha' if not rodadas[1] else str(rodadas[1]) + ' com falha'}")
    gasto = len(publicadas) * CUSTO_POR_MATERIA + len(descartadas) * CUSTO_POR_MATERIA / 2

    cartao_v = lambda num, rotulo: (
        f'<td style="background:#16181d;border-radius:12px;padding:14px;text-align:center">'
        f'<div style="font-size:28px;font-weight:800;color:#fff">{num}</div>'
        f'<div style="font-size:12px;color:#bbb">{rotulo}</div></td>')
    if m:
        lista_pag = "".join(f"<li>{E(p)} <b>· {v}</b></li>" for p, v in m["paginas"]) or "<li>Sem dados ainda</li>"
        lista_org = "".join(f"<li>{E(o)} <b>· {v}</b></li>" for o, v in m["origens"]) or "<li>Sem dados ainda</li>"
        lista_bus = "".join(f"<li>{E(q)} <b>· {c} cliques, {i} aparições</b></li>" for q, c, i in m["buscas"]) \
            or "<li>O Google costuma levar 2 a 3 dias para mostrar as buscas</li>"
        bloco_visitas = f"""<table width="100%" cellspacing="8"><tr>
{cartao_v(m["usuarios"], "visitantes")}{cartao_v(m["visualizacoes"], "páginas vistas")}
{cartao_v(m["cliques"], "cliques no Google")}{cartao_v(m["impressoes"], "aparições no Google")}
</tr></table>
<h2 style="font-size:18px;margin:22px 0 6px">📈 Mais lidas ontem</h2><ol>{lista_pag}</ol>
<h2 style="font-size:18px;margin:22px 0 6px">De onde vieram as visitas</h2><ul>{lista_org}</ul>
<h2 style="font-size:18px;margin:22px 0 6px">🔎 O que buscaram no Google</h2><ul>{lista_bus}</ul>"""
    else:
        bloco_visitas = '<p style="color:#888">Números de visitas indisponíveis hoje.</p>'
    cartao = lambda num, rotulo: (
        f'<td style="background:#fff3f6;border-radius:12px;padding:14px;text-align:center">'
        f'<div style="font-size:28px;font-weight:800;color:#ff1f5a">{num}</div>'
        f'<div style="font-size:12px;color:#555">{rotulo}</div></td>')
    corpo = f"""<div style="font-family:Arial,Helvetica,sans-serif;max-width:640px;margin:auto;color:#16181d">
<h1 style="font-size:26px;margin:0 0 4px"><span style="color:#ff1f5a">tá fervendo</span> · resumo de {dia}</h1>
<p style="color:#666;margin:0 0 18px">O que o site fez sozinho ontem e o que está bombando agora.</p>
{bloco_visitas}
<table width="100%" cellspacing="8"><tr>
{cartao(len(publicadas), "matérias publicadas")}{cartao(len(coletadas), "manchetes coletadas")}
{cartao(len(descartadas), "barradas pela revisão")}{cartao(len(removidas), "remoções a pedido")}
</tr></table>
<h2 style="font-size:18px;margin:22px 0 6px">🔥 Em alta agora</h2><ol>{linhas_quentes}</ol>
<h2 style="font-size:18px;margin:22px 0 6px">Matérias publicadas ontem</h2><ul>{linhas_pub or "<li>Nenhuma</li>"}</ul>
<h2 style="font-size:18px;margin:22px 0 6px">Pedidos de remoção atendidos</h2><ul>{linhas_rem}</ul>
<h2 style="font-size:18px;margin:22px 0 6px">Saúde do robô</h2>
<p>{E(saude)} · gasto estimado com a IA: US$ {gasto:.2f} (limite de US$ 2 por mês)</p>
<h2 style="font-size:18px;margin:22px 0 6px">Ver os números</h2>
<p><a href="https://analytics.google.com/">Visitas no Google Analytics</a> ·
<a href="https://search.google.com/search-console?resource_id={E(base)}%2F">Buscas no Search Console</a> ·
<a href="https://adsense.google.com/">Ganhos no AdSense</a> · <a href="{base}/">Abrir o site</a></p>
<p style="color:#999;font-size:12px;margin-top:26px">Resumo automático enviado todo dia às 9h.</p></div>"""
    texto = (f"Tá Fervendo, resumo de {dia}: {len(publicadas)} matérias publicadas, {len(coletadas)} manchetes, "
             f"{len(descartadas)} barradas, {len(removidas)} remoções. {saude}. Site: {base}/")
    visitas = f"{m['usuarios']} visitantes, " if m else ""
    return f"Tá Fervendo · resumo de {dia}: {visitas}{len(publicadas)} matérias, {len(removidas)} remoções", texto, corpo


def main():
    senha = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "")
    assunto, texto, corpo = montar()
    if not senha or TESTE:
        print(assunto)
        return
    conta = b.CFG["contato_email"]
    msg = EmailMessage()
    msg["From"] = f"Robô Tá Fervendo <{conta}>"
    msg["To"] = conta
    msg["Subject"] = assunto
    msg.set_content(texto)
    msg.add_alternative(corpo, subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(conta, senha)
        smtp.send_message(msg)
    print("Resumo enviado:", assunto)


if __name__ == "__main__":
    main()
