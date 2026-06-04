# Sugestões para deixar o app mais bonito

> Revisão de design (UX/UI) do app Streamlit do Observatório de Mobilidade.
> Aqui só estão **ideias e recomendações** — nada no código foi alterado.
> A linguagem é propositalmente simples, sem termos técnicos desnecessários.

---

## Resumo em uma frase

O app **funciona bem**, mas tem cara de "modelo pronto". Mudando **duas coisas**
— as **cores do app** e a **forma de desenhar os gráficos** — ele já fica com
aparência profissional, sem mexer em nada da parte de dados.

---

## O problema, em palavras simples

1. **O app não tem uma identidade visual própria.**
   Hoje ele usa as cores e a fonte que vêm "de fábrica" no Streamlit (aquele
   vermelho genérico). Por isso parece um exemplo, não um produto.

2. **Os gráficos são os mais básicos possíveis.**
   Eles foram feitos com os comandos mais simples (`st.line_chart` e
   `st.bar_chart`). Eles mostram a informação certa, mas não deixam você
   escolher cor, nem colocar o nome dos eixos, nem formatar os números, nem
   melhorar a caixinha que aparece quando passa o mouse. É daí que vem o ar de
   "cru".

3. **O mapa fica todo vermelho e sem legenda.**
   O vermelho em tudo passa sensação de "alerta" o tempo todo, e não há uma
   legenda explicando o que a cor e o tamanho dos pontos significam.

---

## O que fazer — da maior para a menor prioridade

### 🔴 Prioridade alta — muda a aparência do app inteiro

**1. Escolher as cores e a fonte do app (criar um "tema").**
É como pintar as paredes e escolher a tipografia da casa. Define-se uma cor
principal (sugestão: um **azul/petróleo**, que combina com transporte), as cores
de fundo e a fonte. Só isso já tira a cara de "modelo" e dá personalidade.
*Esforço: baixo. Impacto: enorme.*

**2. Desenhar os gráficos com uma ferramenta melhor.**
Trocar os gráficos básicos por gráficos feitos com uma biblioteca mais completa
(Altair ou Plotly). Com isso passa a ser possível:
- usar as **cores do app** em todos os gráficos;
- escrever o **nome dos eixos com a unidade** (ex.: "viagens por dia", "minutos");
- mostrar uma **caixinha bonita e clara** ao passar o mouse (data legível,
  número com ponto de milhar);
- deixar a **linha do tempo mais elegante** (com preenchimento embaixo e pontos
  de destaque).
*Esforço: médio. Impacto: alto. É o que mais resolve a queixa dos gráficos.*

**3. Usar cores com significado e sempre as mesmas.**
Escolher de 3 a 4 cores e usá-las de forma consistente. Melhor ainda quando a
cor "diz" algo. Exemplo: no gráfico de chuva, usar **azul para "com chuva"** e
**amarelo/âmbar para "sem chuva"**. Cor com significado é o que diferencia um
painel amador de um profissional.
*Esforço: baixo. Impacto: alto.*

### 🟡 Prioridade média — bom ganho, esforço moderado

**4. Deixar o mapa mais sofisticado.**
- Trocar o vermelho por uma **escala de cor moderna** (tipo "Viridis"), que é
  mais bonita e também funciona para quem tem daltonismo.
- Colocar um **mapa de fundo mais limpo** (claro ou escuro).
- Adicionar uma **legenda** explicando o que a cor e o tamanho dos pontos
  querem dizer.
- Quando há muitos pontos juntos, usar um **mapa de calor** em vez de bolinhas
  que se sobrepõem e viram manchões.

**5. Melhorar a tabela de "gargalos".**
Em vez de só números, mostrar uma **barrinha colorida** dentro da célula para o
tempo de espera (headway) e formatar os números. Fica muito mais fácil de ler
e mais bonito.

**6. Dar contexto aos números grandes (KPIs).**
Os cartões com os números principais podem mostrar a **variação** em relação ao
período anterior (uma setinha verde ou vermelha). Assim a pessoa entende na hora
se está melhorando ou piorando. Também dá para agrupar esses números em
"cartões" com borda, ficando mais organizado.

### 🟢 Polimento — pouco esforço, acabamento final

- **Organizar a página em abas.** A página de "KPIs & Análises" tem muita coisa
  empilhada (filtros + números + 3 gráficos + tabela). Separar em abas
  ("Tendência", "Sazonalidade", "Gargalos") diminui a rolagem e organiza.
- **Adicionar linhas divisórias** entre as seções para dar respiro.
- **Melhorar a página de Previsões.** Hoje ela mostra só um número solto. Um
  "velocímetro" (gauge) ou um mini-gráfico mostrando como a previsão muda com a
  chuva deixaria a ideia mais clara. *(O aviso de que a demanda é simulada está
  ótimo — isso passa honestidade e deve ser mantido.)*
- **Ordenar os dias da semana** de segunda a domingo no gráfico de sazonalidade
  e colorir dia útil e fim de semana de formas diferentes.

---

## O que já está bom (manter)

- O código separa a parte visual da parte de dados — isso é organizado e raro.
- O app já trata bem os casos de "sem dados" e "carregando".
- O aviso de que a previsão de demanda é simulada é honesto e importante.
- O layout já usa a largura total da tela e tem uma barra lateral com navegação.

---

## Conclusão

Não é preciso refazer nada. Com **duas mudanças principais** — definir as
**cores/fonte do app** e **redesenhar os gráficos** com uma ferramenta melhor —
resolve-se cerca de **80% da sensação de "feio"**. E o melhor: nenhuma dessas
mudanças mexe na lógica dos dados, então não há risco de quebrar o que já
funciona.

**Sugestão de primeiro passo:** aplicar o tema (cores/fonte) e refazer **apenas
um gráfico** como teste. Assim dá para aprovar o visual antes de aplicar nos
demais.
