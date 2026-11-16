# README.md

```markdown
# 🖥️ Caixeiro Viajante em Terminal CRT Retrô

Resolvedor do **Problema do Caixeiro Viajante (TSP)** com estética de terminal
CRT dos anos 80 — em **Python puro**, sem dependências externas, com som 8-bit
sintetizado em tempo real.

![Python](https://img.shields.io/badge/Python-3.8%2B-39ff6e?style=flat-square)
![Dependências](https://img.shields.io/badge/dependências-zero-39ff6e?style=flat-square)

---

## 🚀 Como executar

```bash
python3 caixeiro_viajante.py
```

Requisitos: **Python 3.8+** com Tkinter (já incluso na instalação padrão).
No Linux, se faltar: `sudo apt install python3-tk`.

> Áudio é opcional — se nenhum player (`aplay`, `paplay`, `afplay`, `ffplay`)
> for encontrado, o programa roda mudo.

---

## 🎮 Como usar

| Botão | Ação |
|---|---|
| **grafo_01 · 5 nós** | Carrega o grafo pequeno |
| **grafo_02 · 18 nós** | Carrega o grafo grande |
| **caixeiro viajante** | Heurística (Vizinho + 2-opt) animada |
| **força bruta** | Solução exata (até 9 nós) |
| **limpar tudo** | Zera rotas e seleções |
| **som** | Liga/desliga áudio |
| **tela cheia (F11)** | Alterna tela cheia (`Esc` sai) |

**No canvas:** clique em dois nós para ver o **melhor caminho** (Dijkstra)
entre eles, com setas de sentido.

| Cor | Significado |
|---|---|
| 🟢 Verde | Arestas, nós, textos |
| 🟡 Âmbar | Rota do caixeiro, melhor caminho, origem |
| 🔵 Azul | Destino |

---

## 🧠 O que tem dentro

- **2 grafos embutidos** (5 e 18 nós), transcritos de figura
- **Dijkstra** clássico (sem `heapq`) → matriz completa de distâncias
- **Heurística:** vizinho mais próximo + 2-opt (*first-improvement*)
- **Exato:** força bruta com permutações de Heap (sem `itertools`)
- **Interface CRT:** Tkinter puro, animações via `after()`, sem travar a GUI
- **Som 8-bit:** onda quadrada gravada em WAV temporário e tocada em thread

---

## 📁 Estrutura

```
caixeiro_viajante.py
├── Parte 1   → Grafos (dados)
├── Parte 2   → Algoritmos (sqrt, dijkstra, 2-opt, força bruta)
├── Parte 2.5 → Som 8-bit (classe Som)
└── Parte 3   → Interface CRT (classe AppCaixeiro)
```
