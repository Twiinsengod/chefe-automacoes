# chefe-automacoes

Scripts somente leitura para o perfil @_Fcruz no X. Nenhum deles publica nada.

- `x_profile_check.py`: salva um snapshot do perfil (nome, bio, link, post fixado, números) em `snapshots/` e mostra o que mudou desde o último.
  `python3 x_profile_check.py --from-json fixtures/fcruz_profile.json` (ou com `X_BEARER_TOKEN` no ambiente).
- `x_best_hours.py`: ranking de horários e dias com mais engajamento (horário de Brasília), com tamanho da amostra; faixas com poucos posts aparecem como hipótese.
  `python3 x_best_hours.py fixtures/fcruz_posts.json [--sem-respostas] [--min-amostra 5]`

Testes: `python3 -m pytest`. `fixtures/` tem dados públicos reais de 05/11/2026; `snapshots/` fica fora do git.
