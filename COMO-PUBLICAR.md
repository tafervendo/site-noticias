# Tá Fervendo — como colocar no ar

Site de celebridades, televisão, curiosidades e virais que se atualiza sozinho a cada 30 minutos. Para cada notícia, a IA lê a matéria original e escreve um resumo com palavras próprias, que vira uma página do site com a fonte citada e o link para a matéria completa.

## Como funciona

1. A cada 30 minutos, o GitHub (de graça) busca as novidades de Quem, Hugo Gloss, Caras, Contigo, Metrópoles (Leo Dias), Gshow, OTV Foco, g1, Terra, Catraca Livre, Superinteressante, Galileu e Agência Brasil
2. Também busca as **buscas em alta do Google no Brasil** e prioriza esses assuntos
3. Cada notícia vai para Celebridades, Televisão, Virais ou Curiosidades pelas palavras do título (lista editável no `config.json`)
4. A IA escreve o resumo das mais recentes, começando pelas que estão em alta
5. O site é publicado com as páginas novas, botões de compartilhar e espaços de anúncio

Notícias que ainda não têm resumo aparecem com o título original e levam direto ao veículo (com a setinha ↗).

## Passo 1 — Domínio

Conferido no registro oficial (rdap.registro.br) em 11/11/2026. Livres tanto em .com.br quanto em .com:

| Nome | Domínio |
|---|---|
| **Tá Fervendo** (usado agora) | tafervendo.com.br |
| Fofocou | fofocou.com.br |
| Fuxicou | fuxicou.com.br |
| Cochichou | cochichou.com.br |
| Babadeiro | babadeiro.com.br |
| Close Certo | closecerto.com.br |
| Quebrou a Net | quebrouanet.com.br |

Já ocupados: ferveu, pipocou, viralizou, fofoquei, fervendo, babadou (.com).

Registre logo em registro.br (cerca de R$ 40 por ano): um domínio livre hoje pode ser registrado por outra pessoa amanhã. Antes, confira se o @ está livre no Instagram e no TikTok.

## Passo 2 — Colocar no ar

1. Crie uma conta em github.com e um repositório público chamado `site-noticias`
2. Envie esta pasta para lá
3. **Settings → Pages → Source: GitHub Actions**
4. Em `config.json`: coloque seu e-mail em `contato_email`, o domínio em `dominio` e `https://seudominio.com.br` em `url`
5. No registro.br, aponte o domínio para o GitHub Pages (instruções em Settings → Pages → Custom domain)

## Passo 3 — Chave da IA (os resumos)

1. Crie uma conta em console.anthropic.com, coloque créditos e gere uma chave de API
2. No GitHub: **Settings → Secrets and variables → Actions → New repository secret**
   - Nome: `ANTHROPIC_API_KEY`
   - Valor: a chave
3. Rode em **Actions → Atualizar notícias → Run workflow**

### Quanto custa (estimativa)

Cada resumo lê a matéria (cerca de 4 mil tokens) e escreve o texto (cerca de mil tokens). Com o limite padrão de 40 resumos por dia:

| Modelo (`ia.modelo` no config) | Por resumo | Por mês |
|---|---|---|
| `claude-opus-5-5` (padrão, melhor texto) | ~US$ 0,04 | ~US$ 48 (~R$ 270) |
| `claude-haiku-5-5` (mais barato) | ~US$ 0,001 | ~US$ 1,50 (~R$ 9) |

As notícias que a IA ainda não resumiu aparecem com a capa própria e levam ao veículo original.

Para gastar menos, baixe `max_por_dia` ou troque o modelo. Sugestão: comece com o Haiku, compare a qualidade e só suba de modelo se o tráfego justificar. Na Anthropic, dá para pôr um limite mensal de gasto na conta.

## Passo 4 — Anúncios

1. Cadastre o site em adsense.google.com (essa parte é sua)
2. Coloque o código `ca-pub-...` em `adsense_cliente` no `config.json`
3. Espere a aprovação

## Cuidados importantes

- **Imagens: o site não copia fotos de outros veículos.** Cada matéria usa, nesta ordem:
  1. foto com licença livre da pessoa citada (Wikimedia Commons) ou da Agência Brasil, com autor e licença na legenda
  2. o post original do Instagram, TikTok, X ou YouTube citado na matéria, incorporado pelo recurso oficial das redes
  3. foto de banco gratuito para temas gerais (Openverse; e Pexels, se você cadastrar o segredo `PEXELS_API_KEY`, que é grátis em pexels.com/api)
  4. capa própria com a cor da categoria, que também vira a prévia no WhatsApp
- **Fofoca exige cuidado jurídico.** A IA foi instruída a atribuir boatos a quem publicou, não especular sobre saúde, sexualidade ou vida íntima e não falar da vida privada de crianças. Mesmo assim, de vez em quando dê uma olhada no que foi publicado
- **Resumo citando a fonte é o caminho certo**, mas não é blindagem total. Atenda pedidos de remoção em até 48 horas (já está prometido na página Sobre)
- **Viralizar depende de divulgação:** cada matéria tem botões de WhatsApp, Facebook, X e Telegram, e a prévia com foto grande já sai pronta quando o link é colado. Crie perfis do site no Instagram, TikTok e X e poste os destaques
- **Nunca clique nos próprios anúncios**

## Testar no seu computador

```bash
cd ~/Projetos/site-noticias && .venv/bin/python build.py --preview
```

Sem a chave, o `--preview` cria 8 páginas de demonstração (com o trecho do feed no lugar do resumo) só para conferir o visual.
