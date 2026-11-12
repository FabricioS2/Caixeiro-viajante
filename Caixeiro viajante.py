# -*- coding: utf-8 -*-
"""
Caixeiro viajante em um TERMINAL CRT RETRÔ.
Tkinter puro + som 8-bit gerado na hora (WAV de onda quadrada, sem
bibliotecas externas). Os grafos da imagem ficam embutidos no código.
"""
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import wave

import tkinter as tk
import tkinter.font as tkfont


# ---------------------------------------------------------------------
# PARTE 1 — Os dois grafos da imagem, embutidos no código
# ---------------------------------------------------------------------
# Nada é sorteado: as posições (x%, y% da área de desenho) e as arestas
# (nó_a, nó_b, peso) foram transcritas da figura enviada, mantendo a
# numeração 1..n dos círculos. Todos os nós são desenhados iguais.

GRAFO_1 = {
    "titulo": "grafo_01.dat · 5 nós / 8 arestas",
    "posicoes": [(10, 45), (50, 15), (90, 45), (28, 78), (72, 78)],
    "arestas": [(1, 2, 2), (1, 4, 3), (1, 5, 6), (2, 3, 4),
                (2, 4, 3), (3, 4, 7), (3, 5, 3), (4, 5, 3)],
}

GRAFO_2 = {
    "titulo": "grafo_02.dat · 18 nós / 44 arestas",
    "posicoes": [(20, 43), (25, 25), (40, 19), (58, 16), (78, 31), (79, 16),
                 (88, 8), (36, 47), (51, 38), (67, 43), (85, 43), (28, 65),
                 (46, 65), (61, 67), (72, 57), (53, 79), (70, 77), (81, 75)],
    "arestas": [
        (1, 2, 20), (1, 8, 29), (1, 12, 29), (1, 13, 37),
        (2, 3, 25), (2, 8, 28), (2, 12, 39),
        (3, 4, 25), (3, 8, 30), (3, 13, 54),
        (4, 5, 39), (4, 6, 32), (4, 7, 42), (4, 9, 23), (4, 10, 33), (4, 14, 56),
        (5, 6, 12), (5, 10, 19), (5, 11, 30),
        (6, 7, 17), (6, 10, 35), (6, 11, 26),
        (7, 11, 38),
        (8, 12, 25), (8, 13, 22),
        (9, 10, 26), (9, 13, 34), (9, 16, 43),
        (10, 11, 24), (10, 14, 30), (10, 15, 19),
        (11, 15, 26), (11, 18, 36),
        (12, 13, 27), (12, 16, 43),
        (13, 14, 24), (13, 16, 19),
        (14, 15, 20), (14, 16, 19), (14, 17, 17),
        (15, 17, 18), (15, 18, 21),
        (16, 17, 26),
        (17, 18, 15),
    ],
}

GRAFOS = [GRAFO_1, GRAFO_2]

INF = float("inf")


# ---------------------------------------------------------------------
# PARTE 2 — Algoritmos feitos à mão
# ---------------------------------------------------------------------

def sqrt(x):
    """Raiz quadrada pelo método de Newton: r <- (r + x/r) / 2."""
    if x <= 0.0:
        return 0.0
    r = x
    for _ in range(30):                 # converge em ~6 passos
        novo = (r + x / r) / 2.0
        if abs(novo - r) < 1e-12:
            return novo
        r = novo
    return r


def dijkstra(adj, origem):
    """
    Menores caminhos a partir de `origem` — versão clássica com busca
    linear do próximo nó (sem heapq, sem bibliotecas).
    Devolve (distancias, predecessores); pred[v] é o nó anterior no
    menor caminho origem -> v.
    """
    n = len(adj)
    dist = [INF] * n
    pred = [-1] * n
    dist[origem] = 0.0
    fechados = [False] * n
    for _ in range(n):
        # escolhe o nó ainda aberto com a menor distância conhecida
        melhor, menor = -1, INF
        for v in range(n):
            if not fechados[v] and dist[v] < menor:
                melhor, menor = v, dist[v]
        if melhor == -1:
            break                          # o resto é inalcançável
        fechados[melhor] = True
        for viz, peso in adj[melhor]:
            if dist[melhor] + peso < dist[viz]:
                dist[viz] = dist[melhor] + peso
                pred[viz] = melhor
    return dist, pred


def matriz_distancias(n, arestas):
    """
    Distância entre dois nós = peso da aresta quando ela existe; para
    pares SEM aresta direta usa o menor caminho passando por outros nós
    (Dijkstra). A matriz fica completa — a 'clausura métrica' do grafo —
    e o caixeiro pode viajar entre qualquer par de nós.
    Devolve (matriz, predecessores de cada origem).
    """
    adj = [[] for _ in range(n)]
    for a, b, peso in arestas:
        adj[a - 1].append((b - 1, float(peso)))
        adj[b - 1].append((a - 1, float(peso)))

    m = [[0.0] * n for _ in range(n)]
    preds = []
    for u in range(n):
        dist, pred = dijkstra(adj, u)
        m[u] = dist
        preds.append(pred)
    return m, preds


def custo_total(caminho, m):
    """Comprimento total do ciclo, incluindo a volta à cidade inicial."""
    total, n = 0.0, len(caminho)
    for i in range(n):
        total += m[caminho[i]][caminho[(i + 1) % n]]
    return total


def vizinho_mais_proximo(m, inicio=0):
    """Heurística construtiva: sempre vai à cidade mais próxima não visitada."""
    n = len(m)
    visitadas = [False] * n
    caminho, visitadas[inicio] = [inicio], True
    while len(caminho) < n:
        atual, melhor, melhor_d = caminho[-1], -1, 1e18
        for j in range(n):
            if not visitadas[j] and m[atual][j] < melhor_d:
                melhor, melhor_d = j, m[atual][j]
        caminho.append(melhor)
        visitadas[melhor] = True
    return caminho


def troca_2opt(m, caminho):
    """
    Aplica UMA melhoria 2-opt (a primeira que encontrar).

    Escolhe duas arestas (a-b) e (c-d) do tour e as troca por (a-c) e
    (b-d), invertendo o trecho entre b e c. Se o tour encurtar, aceita.
    """
    n = len(caminho)
    for i in range(n - 2):
        a, b = caminho[i], caminho[i + 1]
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue                      # seria a mesma aresta
            c, d = caminho[j], caminho[(j + 1) % n]
            if m[a][c] + m[b][d] < m[a][b] + m[c][d] - 1e-9:
                trecho = caminho[i + 1:j + 1]
                trecho.reverse()
                caminho[i + 1:j + 1] = trecho
                return True
    return False


def permutacoes(itens):
    """Gera todas as permutações — algoritmo de Heap (sem itertools)."""
    a = list(itens)
    n = len(a)
    contadores = [0] * n
    yield a[:]
    i = 0
    while i < n:
        if contadores[i] < i:
            if i % 2 == 0:
                a[0], a[i] = a[i], a[0]
            else:
                a[contadores[i]], a[i] = a[i], a[contadores[i]]
            yield a[:]
            contadores[i] += 1
            i = 0
        else:
            contadores[i] = 0
            i += 1


def forca_bruta(m):
    """
    Solução EXATA: testa todos os (n-1)! ciclos possíveis.
    A cidade 0 (o nó 1 da figura) fica fixa como início.
    Viável só com ~9 nós ou menos.
    """
    n = len(m)
    melhor, melhor_custo = [0] + list(range(1, n)), 1e18
    for perm in permutacoes(range(1, n)):
        c = custo_total([0] + perm, m)
        if c < melhor_custo:
            melhor, melhor_custo = [0] + perm, c
    return melhor


def escalar_posicoes(posicoes, larg, alt, marg):
    """
    Converte as posições em % para pixels, esticando a figura para
    ocupar bem a área útil — sem distorcer as proporções originais.
    """
    xs = [p[0] for p in posicoes]
    ys = [p[1] for p in posicoes]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w, h = max(x1 - x0, 1e-9), max(y1 - y0, 1e-9)
    escala = min((larg - 2 * marg) / w, (alt - 2 * marg) / h)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return [(larg / 2 + (x - cx) * escala, alt / 2 + (y - cy) * escala)
            for x, y in posicoes]


# ---------------------------------------------------------------------
# PARTE 2.5 — Som 8-bit (WAV sintetizado na hora, sem bibliotecas)
# ---------------------------------------------------------------------

class Som:
    """
    Efeitos sonoros estilo console retrô: notas de onda quadrada com
    envelope, gravadas como WAV em uma pasta temporária e tocadas pelo
    player de áudio do sistema (winsound no Windows, aplay/afplay etc.).
    Som é enfeite: qualquer falha é engolida em silêncio.
    """
    TAXA = 22050
    ESCALA = [440.0, 494.0, 554.0, 659.0, 740.0, 880.0, 988.0, 1046.5]

    def __init__(self):
        self.ligado = True
        self.volume = 0.35
        self.player = self._detectar()
        self.pasta = tempfile.mkdtemp(prefix="caixeiro_som_")
        self.arquivos = {}          # nome do efeito -> caminho do WAV

    # ---------- infraestrutura ----------

    @staticmethod
    def _detectar():
        if sys.platform.startswith("win"):
            return "winsound"
        for comando in ("aplay", "paplay", "afplay", "ffplay"):
            caminho = shutil.which(comando)
            if caminho:
                return caminho
        return None

    def _amostras(self, freq, dur, volume=None):
        """Uma nota: onda quadrada (chip) com ataque/cauda suaves."""
        vol = self.volume if volume is None else volume * self.volume
        n = int(self.TAXA * dur)
        amostras = []
        for i in range(n):
            t = i / float(self.TAXA)
            env = min(1.0, t / 0.004)                 # ataque de 4 ms
            if i > n * 0.72:                           # cauda final
                env *= 1.0 - (i - n * 0.72) / (n * 0.28)
            fase = (freq * t) % 1.0
            onda = 0.9 if fase < 0.5 else -0.9
            amostras.append(onda * env * vol)
        return amostras

    def _gravar(self, nome, trechos):
        """Grava a lista de notas como um WAV mono de 16 bits."""
        silencio = [0.0] * int(self.TAXA * 0.02)
        amostras = []
        for i, trecho in enumerate(trechos):
            amostras += trecho
            if i < len(trechos) - 1:
                amostras += silencio
        dados = b"".join(
            struct.pack("<h", max(-32767, min(32767, int(a * 32767.0))))
            for a in amostras)
        caminho = os.path.join(self.pasta, nome + ".wav")
        with wave.open(caminho, "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.TAXA)
            w.writeframes(dados)
        return caminho

    def _tocar(self, nome, trechos):
        if not (self.ligado and self.player):
            return
        caminho = self.arquivos.get(nome)
        if caminho is None:
            try:
                caminho = self._gravar(nome, trechos)
            except Exception:
                return                 # sem disco temporário? fica mudo
            self.arquivos[nome] = caminho
        threading.Thread(target=self._executar, args=(caminho,),
                         daemon=True).start()

    def _executar(self, caminho):
        try:
            if self.player == "winsound":
                import winsound
                winsound.PlaySound(caminho,
                                    winsound.SND_FILENAME | winsound.SND_ASYNC)
                return
            nome = os.path.basename(self.player)
            if nome == "aplay":
                args = [self.player, "-q", caminho]
            elif nome == "ffplay":
                args = [self.player, "-nodisp", "-autoexit",
                        "-loglevel", "quiet", caminho]
            else:                      # paplay, afplay
                args = [self.player, caminho]
            subprocess.Popen(args, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        except Exception:
            pass                       # nunca derruba o programa por som

    # ---------- efeitos ----------

    def conexao(self, indice):
        """Bipe de conexão — a nota sobe pela escala a cada ligação."""
        freq = self.ESCALA[indice % len(self.ESCALA)]
        self._tocar("beep_%d" % int(freq), [self._amostras(freq, 0.055)])

    def melhora(self):
        """Blip grave: uma troca 2-opt aceita."""
        self._tocar("blip", [self._amostras(300.0, 0.045)])

    def concluido(self):
        """Din-don curto: fim de uma montagem (grafo carregado)."""
        self._tocar("ok", [self._amostras(784.0, 0.07),
                           self._amostras(1046.5, 0.14)])

    def vitoria(self):
        """Fanfarra de vitória: C5-E5-G5-C6 em onda quadrada."""
        notas = [(523.25, 0.09), (659.25, 0.09),
                 (783.99, 0.09), (1046.5, 0.30)]
        self._tocar("vitoria",
                    [self._amostras(f, d, 1.4) for f, d in notas])


SOM = Som()


# ---------------------------------------------------------------------
# PARTE 3 — Interface gráfica: terminal CRT retrô (tkinter)
# ---------------------------------------------------------------------

# paleta do fósforo: preto quase puro + verde brilhante
COR_FUNDO         = "#020602"   # tela apagada
COR_GRADE         = "#0a1a0e"   # grade discreta
COR_SCAN          = "#031008"   # scanlines: 1/3 do efeito (a cada 15 px)
COR_MOLDURA       = "#1e7a3c"   # moldura do "monitor"
COR_ARESTA        = "#1f9152"   # arestas em verde apagado
COR_PESO          = "#6fd98f"   # pesos das arestas
COR_TOUR          = "#39ff6e"   # verde-fósforo: rota do caixeiro
COR_TOUR_BRILHO   = "#0c3a1e"   # halo da rota
COR_CAMINHO       = "#ffb000"   # âmbar (fósforo P3): melhor caminho
COR_CAMINHO_BRILHO = "#3a2a08"  # halo do caminho
COR_DESTINO       = "#4dc3ff"   # anel azul do nó de chegada
COR_NO            = "#020602"   # nós "buracos" na tela
COR_CONTORNO      = "#39ff6e"   # contorno verde-fósforo dos nós
COR_NUMERO        = "#39ff6e"   # número do nó
COR_TEXTO         = "#39ff6e"   # texto do painel
COR_TITULO        = "#8fffaf"   # título no topo do canvas

LARG, ALT, MARG = 760, 540, 50
LIMITE_EXATO = 9             # nº máximo de nós para a força bruta

MONO_CANDIDATOS = ("DejaVu Sans Mono", "Liberation Mono", "Menlo",
                   "Consolas", "Courier New", "Courier")


class AppCaixeiro:

    def __init__(self):
        self.janela = tk.Tk()
        self.janela.title("caixeiro_viajante.exe · terminal CRT")
        self.janela.configure(bg=COR_FUNDO)
        self.janela.resizable(True, True)      # janela esticável
        self.janela.minsize(780, 500)

        self.mono = self._escolher_mono()

        # tamanho atual do canvas (muda ao esticar/entrar em tela cheia)
        self.w, self.h = LARG, ALT
        self.tela_cheia = False

        self.titulo = ""
        self.arestas = []      # arestas da figura (1-based), p/ desenho
        self.pos_pct = []      # posições em % (guardadas p/ reescalar)
        self.pos_px = []       # posições dos nós em pixels
        self.matriz = None     # distâncias (peso ou menor caminho)
        self.preds = None      # predecessores de Dijkstra (p/ desenhar rotas)
        self.caminho = None    # ordem de visitação (índices 0-based)
        self.melhorias = 0
        self.selecao = []            # nós clicados p/ o melhor caminho
        self.caminho_dijkstra = None  # trilha do melhor caminho (0-based)

        # máquina de animação: None (parado) | "arestas" | "rota"
        # | "2opt" | "caminho"
        self.fase = None
        self.timer = None
        self.timer_pisca = None
        self.cursor = True              # cursor "_" piscando no título
        self.arestas_vis = None          # None = todas; int = reveladas
        self.segs_rota_vis = None
        self.segs_caminho_vis = None
        self.rota_exata = False         # revelação termina em vitória
        self._passo_ms = 60             # intervalo da montagem do grafo

        self._montar_interface()
        self.janela.bind("<F11>", self._alternar_tela_cheia)
        self.janela.bind("<Escape>", self._sair_tela_cheia)
        self.carregar_grafo(0)
        self.timer_pisca = self.janela.after(530, self._pisca)

    # ------------------------- interface -------------------------

    def _escolher_mono(self):
        """Uma fonte monoespaçada que exista nesta máquina."""
        try:
            familias = set(tkfont.families(self.janela))
        except Exception:
            return "Courier"
        for candidata in MONO_CANDIDATOS:
            if candidata in familias:
                return candidata
        return "Courier"

    def _f(self, tam, negrito=False):
        return (self.mono, tam, "bold") if negrito else (self.mono, tam)

    def _montar_interface(self):
        principal = tk.Frame(self.janela, bg=COR_FUNDO)
        principal.pack(padx=10, pady=10, fill="both", expand=True)
        principal.columnconfigure(0, weight=1)   # só o canvas estica
        principal.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(principal, width=LARG, height=ALT,
                                bg=COR_FUNDO, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Button-1>", self._clicar)   # escolher os 2 nós
        self.canvas.bind("<Motion>", self._mover)    # cursor sobre um nó
        self.canvas.bind("<Leave>", self._sair)
        self.canvas.bind("<Configure>", self._redimensionou)

        painel = tk.Frame(principal, bg=COR_FUNDO)
        painel.grid(row=0, column=1, sticky="n", padx=(12, 0))

        def rotulo(texto):
            tk.Label(painel, text=texto, bg=COR_FUNDO, fg=COR_PESO,
                     font=self._f(9, True), anchor="w"
                     ).pack(anchor="w", pady=(8, 2))

        def botao(texto, comando):
            return tk.Button(painel, text=texto, command=comando,
                             bg="#062010", fg=COR_TOUR,
                             activebackground="#0c3a22",
                             activeforeground=COR_TOUR,
                             relief="flat", cursor="hand2",
                             font=self._f(9, True), padx=10, pady=6,
                             width=24, highlightthickness=1,
                             highlightbackground=COR_MOLDURA,
                             highlightcolor=COR_TOUR).pack(fill="x", pady=2)

        rotulo("> grafos da imagem")
        botao("grafo_01 · 5 nós", lambda: self.carregar_grafo(0))
        botao("grafo_02 · 18 nós", lambda: self.carregar_grafo(1))

        rotulo("> resolver")
        botao("caixeiro viajante", self.resolver)
        botao("força bruta", self.resolver_exato)
        botao("limpar tudo", self.limpar)

        rotulo("> opções")
        self.botao_som = tk.Button(
            painel, text="som: ligado", command=self.alternar_som,
            bg="#062010", fg=COR_TOUR, activebackground="#0c3a22",
            activeforeground=COR_TOUR, relief="flat", cursor="hand2",
            font=self._f(9, True), padx=10, pady=6, width=24,
            highlightthickness=1, highlightbackground=COR_MOLDURA,
            highlightcolor=COR_TOUR)
        self.botao_som.pack(fill="x", pady=2)
        botao("tela cheia (F11)", self._alternar_tela_cheia)

        self.info = tk.Label(painel, text="", bg=COR_FUNDO, fg=COR_PESO,
                             font=self._f(8), wraplength=190,
                             justify="left", anchor="w")
        self.info.pack(anchor="w", pady=(12, 0), fill="x")

    # ------------------------- animação (agenda) -------------------------

    def _agenda(self, ms, funcao):
        self._cancelar()
        self.timer = self.janela.after(ms, funcao)

    def _cancelar(self):
        if self.timer is not None:
            try:
                self.janela.after_cancel(self.timer)
            except Exception:
                pass
            self.timer = None

    def _abortar_anim(self):
        """Interrompe qualquer animação e revela tudo na hora."""
        if self.fase == "2opt" and self.caminho:
            self._info("Rota final: %s\nCusto: %s  ·  melhorias 2-opt: %d"
                       % (self._rota_txt(), self._fmt(self.custo()),
                          self.melhorias))
        self._cancelar()
        self.fase = None
        self.arestas_vis = None
        self.segs_rota_vis = None
        self.segs_caminho_vis = None
        if self.pos_px:
            self.desenhar()

    def _pisca(self):
        """Cursor '_' piscando depois do título, como num terminal."""
        self.cursor = not self.cursor
        if self.fase is None:
            self.desenhar()
        self.timer_pisca = self.janela.after(530, self._pisca)

    # ------------------ tela cheia / redimensionamento ------------------

    def _alternar_tela_cheia(self, _evento=None):
        """F11 (ou botão): entra/sai da tela cheia."""
        self.tela_cheia = not self.tela_cheia
        try:
            self.janela.attributes("-fullscreen", self.tela_cheia)
        except Exception:
            pass                       # gerenciador sem suporte: ignora

    def _sair_tela_cheia(self, _evento=None):
        """Esc: sai da tela cheia (fora dela, Esc não faz nada)."""
        if self.tela_cheia:
            self._alternar_tela_cheia()

    def _redimensionou(self, evento):
        """O canvas mudou de tamanho: reescala o grafo (mantém as proporções)."""
        if abs(evento.width - self.w) < 2 and abs(evento.height - self.h) < 2:
            return
        self.w, self.h = evento.width, evento.height
        self._remontar()

    def _remontar(self):
        """Recalcula as posições dos nós para o tamanho atual e redesenha."""
        if not self.pos_pct:
            return
        marg = max(24, min(MARG, self.w // 8, self.h // 8))
        self.pos_px = escalar_posicoes(self.pos_pct, self.w, self.h, marg)
        self.desenhar()

    # ------------------------- ações -------------------------

    def carregar_grafo(self, indice):
        self._abortar_anim()
        g = GRAFOS[indice]
        n = len(g["posicoes"])

        self.titulo = g["titulo"]
        self.arestas = g["arestas"]
        self.pos_pct = g["posicoes"]
        # zera o estado do grafo ANTERIOR antes de redesenhar com as
        # novas posições (senão rotas velhas indexam nós inexistentes)
        self.caminho = None
        self.caminho_dijkstra = None
        self.selecao = []
        self.melhorias = 0
        self._remontar()
        self.matriz, self.preds = matriz_distancias(n, g["arestas"])
        self._info(self._texto_padrao())

        # animação de montagem: arestas se conectando uma a uma
        self._passo_ms = max(45, min(110, 2500 // max(1, len(self.arestas))))
        self.fase = "arestas"
        self.arestas_vis = 0
        self.desenhar()
        self._agenda(180, self._passo_aresta)

    def _passo_aresta(self):
        if self.fase != "arestas":
            return
        self.arestas_vis += 1
        SOM.conexao(self.arestas_vis - 1)
        self.desenhar()
        if self.arestas_vis < len(self.arestas):
            self._agenda(self._passo_ms, self._passo_aresta)
        else:
            self.fase = None
            self.arestas_vis = None
            SOM.concluido()
            self.desenhar()

    def limpar(self):
        self._abortar_anim()
        self.caminho = None
        self.caminho_dijkstra = None
        self.selecao = []
        self.melhorias = 0
        self._info(self._texto_padrao())
        self.desenhar()

    def alternar_som(self):
        SOM.ligado = not SOM.ligado
        estado = "ligado" if SOM.ligado else "desligado"
        self.botao_som.config(text="som: " + estado)
        if SOM.ligado:
            SOM.concluido()

    def resolver(self):
        if len(self.pos_px) < 3:
            return
        self._abortar_anim()
        self.selecao, self.caminho_dijkstra = [], None
        self.caminho = vizinho_mais_proximo(self.matriz)
        self.melhorias = 0
        self.rota_exata = False
        self.fase = "rota"
        self.segs_rota_vis = 0
        self.desenhar()
        self._info("Traçando a rota do caixeiro...")
        self._agenda(180, self._passo_rota)

    def _passo_rota(self):
        if self.fase != "rota":
            return
        total = len(self._segmentos_rota())
        self.segs_rota_vis += 1
        SOM.conexao(self.segs_rota_vis - 1)
        self.desenhar()
        if self.segs_rota_vis < total:
            self._agenda(70, self._passo_rota)
        elif self.rota_exata:
            self.rota_exata = False
            self.fase = None
            self.segs_rota_vis = None
            SOM.vitoria()
            self.desenhar()
        else:
            self.segs_rota_vis = None
            self.fase = "2opt"
            self._info("Custo inicial: %s — melhorando com 2-opt..."
                       % self._fmt(self.custo()))
            self._agenda(280, self._passo_2opt)

    def _passo_2opt(self):
        if self.fase != "2opt" or not self.caminho:
            return
        por_quadro = 1 + len(self.caminho) // 20   # acelera com muitas cidades
        melhorou = False
        for _ in range(por_quadro):
            if troca_2opt(self.matriz, self.caminho):
                self.melhorias += 1
                melhorou = True
            else:
                break
        self.desenhar()
        if melhorou:
            if self.melhorias % 4 == 0:
                SOM.melhora()
            self._info("Custo atual: %s  ·  melhorias 2-opt: %d"
                       % (self._fmt(self.custo()), self.melhorias))
            self._agenda(20, self._passo_2opt)
        else:
            self.fase = None
            SOM.vitoria()
            self._info("Rota final: %s\nCusto: %s  ·  melhorias 2-opt: %d"
                       % (self._rota_txt(), self._fmt(self.custo()),
                          self.melhorias))
            self.desenhar()

    def resolver_exato(self):
        if len(self.pos_px) < 3:
            return
        n = len(self.pos_px)
        if n > LIMITE_EXATO:
            self._abortar_anim()
            self._info("Força bruta inviável: com %d nós seriam %d rotas\n"
                       "(o limite prático é %d nós)."
                       % (n, self._fatorial(n - 1), LIMITE_EXATO))
            return
        self._abortar_anim()
        self.selecao, self.caminho_dijkstra = [], None
        self.caminho = forca_bruta(self.matriz)
        self.melhorias = 0
        self._info("Ótimo exato: %s\nCusto: %s"
                   % (self._rota_txt(), self._fmt(self.custo())))
        self.rota_exata = True
        self.fase = "rota"
        self.segs_rota_vis = 0
        self.desenhar()
        self._agenda(180, self._passo_rota)

    # -------------- melhor caminho entre dois nós --------------

    def _clicar(self, evento):
        """
        Clique no canvas: acerta um nó -> ele entra na seleção. Com dois nós
        escolhidos, os Dijkstras já calculados revelam o melhor caminho
        entre eles. Clicar num nó marcado ou no fundo desmarca tudo.
        """
        if not self.pos_px:
            return
        self._abortar_anim()                    # cliques têm prioridade
        alvo = self._no_proximo(evento.x, evento.y)
        if alvo is None:                        # clique no vazio: desmarca
            if self.selecao or self.caminho_dijkstra:
                self.selecao, self.caminho_dijkstra = [], None
                self._info(self._texto_padrao())
                self.desenhar()
            return
        if alvo in self.selecao:                # clicou num marcado: desmarca
            self.selecao.remove(alvo)
            self.caminho_dijkstra = None
            self._info(self._texto_padrao())
            self.desenhar()
            return
        if len(self.selecao) >= 2:              # 3º clique: recomeça a dupla
            self.selecao, self.caminho_dijkstra = [alvo], None
        else:
            self.selecao.append(alvo)
            self.caminho_dijkstra = None
        if len(self.selecao) == 2:
            u, v = self.selecao
            self.caminho = None                 # caminho substitui rota verde
            trilha = self._trilha(u, v)
            if trilha[0] != u:
                self._info("Não existe caminho entre %d e %d."
                           % (u + 1, v + 1))
            else:
                self.caminho_dijkstra = trilha
                self._info("Melhor caminho %d -> %d:\n%s\nCusto total: %s"
                           % (u + 1, v + 1, self._trilha_txt(),
                              self._fmt(self.matriz[u][v])))
                # animação: ligações do caminho aparecendo uma a uma
                self.fase = "caminho"
                self.segs_caminho_vis = 0
                self._agenda(160, self._passo_caminho)
                self.desenhar()
                return
        else:
            self._info("Origem: nó %d. Clique em outro nó para ver o melhor "
                       "caminho até ele." % (self.selecao[0] + 1))
        self.desenhar()

    def _passo_caminho(self):
        if self.fase != "caminho" or not self.caminho_dijkstra:
            return
        total = len(self.caminho_dijkstra) - 1
        self.segs_caminho_vis += 1
        SOM.conexao(self.segs_caminho_vis - 1)
        self.desenhar()
        if self.segs_caminho_vis < total:
            self._agenda(90, self._passo_caminho)
        else:
            self.fase = None
            self.segs_caminho_vis = None
            SOM.vitoria()
            self.desenhar()

    def _mover(self, evento):
        """Cursor de mãozinha quando passa sobre um nó clicável."""
        if self.pos_px and self._no_proximo(evento.x, evento.y) is not None:
            self.canvas.config(cursor="hand2")
        else:
            self.canvas.config(cursor="")

    def _sair(self, _evento):
        self.canvas.config(cursor="")

    def _no_proximo(self, x, y):
        """Índice do nó a um clique do ponto clicado (ou None)."""
        limite = self._raio() + 5
        melhor, melhor_d = None, 1e18
        for i, (nx, ny) in enumerate(self.pos_px):
            d = sqrt((x - nx) ** 2 + (y - ny) ** 2)
            if d <= limite and d < melhor_d:
                melhor, melhor_d = i, d
        return melhor

    # ------------------------- desenho -------------------------

    def _raio(self):
        return 17 if len(self.pos_px) <= 6 else 12

    def _segmentos_rota(self):
        """
        Transforma a rota em segmentos REAIS do grafo: cada par
        consecutivo é percorrido pelo menor caminho entre eles (quando
        há aresta direta e ela é o menor caminho, é só a própria aresta).
        """
        if not self.caminho:
            return []
        segmentos = []
        n = len(self.caminho)
        for i in range(n):
            trilha = self._trilha(self.caminho[i], self.caminho[(i + 1) % n])
            for k in range(len(trilha) - 1):
                segmentos.append((trilha[k], trilha[k + 1]))
        return segmentos

    def _trilha(self, u, v):
        """Nós do menor caminho u -> v (0-based), pelos predecessores."""
        pred = self.preds[u]
        trilha = [v]
        while trilha[-1] != u and pred[trilha[-1]] != -1:
            trilha.append(pred[trilha[-1]])
        trilha.reverse()                          # u -> ... -> v
        return trilha

    def _linha(self, u, v, cor, brilho, largura, seta=False):
        """Desenha um segmento com halo de fósforo (e seta no meio)."""
        c = self.canvas
        x1, y1 = self.pos_px[u]
        x2, y2 = self.pos_px[v]
        c.create_line(x1, y1, x2, y2, fill=brilho, width=largura + 4)
        if seta:
            mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            c.create_line(x1, y1, mx, my, fill=cor, width=largura,
                          arrow=tk.LAST, arrowshape=(9, 10, 4))
            c.create_line(mx, my, x2, y2, fill=cor, width=largura)
        else:
            c.create_line(x1, y1, x2, y2, fill=cor, width=largura)

    def desenhar(self):
        c = self.canvas
        c.delete("all")

        # grade discreta do monitor (do tamanho atual da tela)
        for gx in range(0, self.w, 40):
            c.create_line(gx, 0, gx, self.h, fill=COR_GRADE)
        for gy in range(0, self.h, 40):
            c.create_line(0, gy, self.w, gy, fill=COR_GRADE)

        if not self.pos_px:
            return

        # título de terminal, com cursor piscando
        c.create_text(12, 10, anchor="nw",
                      text="> " + self.titulo + ("_" if self.cursor else ""),
                      fill=COR_TITULO, font=self._f(9, True))

        # arestas da figura (durante a montagem, só as já conectadas),
        # com os pesos escritos ao lado do meio
        visiveis = self.arestas
        if self.arestas_vis is not None:
            visiveis = self.arestas[:self.arestas_vis]
        for a, b, peso in visiveis:
            x1, y1 = self.pos_px[a - 1]
            x2, y2 = self.pos_px[b - 1]
            c.create_line(x1, y1, x2, y2, fill=COR_ARESTA, width=1)
            dx, dy = x2 - x1, y2 - y1
            compr = sqrt(dx * dx + dy * dy)
            if compr > 1e-9:
                ox, oy = -dy / compr * 10.0, dx / compr * 10.0
            else:
                ox, oy = 0.0, -10.0
            mx, my = (x1 + x2) / 2 + ox, (y1 + y2) / 2 + oy
            texto = str(peso)
            # placa escura atrás do número para destacar sobre as linhas
            w = 5.4 * len(texto)
            c.create_rectangle(mx - w / 2 - 2, my - 6, mx + w / 2 + 2, my + 6,
                               fill=COR_FUNDO, outline="")
            c.create_text(mx, my, text=texto, fill=COR_PESO,
                          font=self._f(8, True))

        # rota do caixeiro por cima, seguindo as arestas do grafo — em
        # AMBAR como todo resultado exibido (heurística, força bruta ou
        # melhor caminho), mesmo sem nenhum nó selecionado
        if self.caminho and len(self.caminho) > 1:
            largura = 3 if len(self.pos_px) <= 8 else 2
            segs = self._segmentos_rota()
            if self.segs_rota_vis is not None:
                segs = segs[:self.segs_rota_vis]
            for u, v in segs:
                self._linha(u, v, COR_CAMINHO, COR_CAMINHO_BRILHO, largura)

        # melhor caminho entre os dois nós clicados, com seta de sentido
        if self.caminho_dijkstra and len(self.caminho_dijkstra) > 1:
            largura = 4 if len(self.pos_px) <= 8 else 3
            nos = self.caminho_dijkstra
            limite = len(nos) - 1
            if self.segs_caminho_vis is not None:
                limite = self.segs_caminho_vis
            for k in range(min(limite, len(nos) - 1)):
                self._linha(nos[k], nos[k + 1], COR_CAMINHO,
                            COR_CAMINHO_BRILHO, largura, seta=True)

        # nós: "buracos" pretos com contorno verde-fósforo
        r = self._raio()
        nos = self.caminho_dijkstra or ()
        limite = len(nos) - 1 if self.segs_caminho_vis is None \
            else self.segs_caminho_vis
        em_trilha = set(nos[:limite + 1]) if nos else set()
        for i, (x, y) in enumerate(self.pos_px):
            c.create_oval(x - r, y - r, x + r, y + r, fill=COR_NO,
                          outline=COR_CONTORNO, width=2)
            # anéis: âmbar = partida/caminho, azul-claro = chegada
            anel, espessura = None, 0
            if self.selecao and i == self.selecao[0]:
                anel, espessura = COR_CAMINHO, 3
            elif len(self.selecao) >= 2 and i == self.selecao[1]:
                anel, espessura = COR_DESTINO, 3
            elif i in em_trilha:
                anel, espessura = COR_CAMINHO, 2
            if anel:
                c.create_oval(x - r - 3, y - r - 3, x + r + 3, y + r + 3,
                              outline=anel, width=espessura)
            c.create_text(x, y, text=str(i + 1), fill=COR_NUMERO,
                          font=self._f(9, True))

        # scanlines do CRT por cima de tudo — apenas 1/3 do efeito:
        # a cada 15 px (antes 5) e cor quase do fundo, para não
        # atrapalhar a leitura dos pesos e das rotas
        for y in range(0, self.h, 15):
            c.create_line(0, y, self.w, y, fill=COR_SCAN, tags="scan")

        # moldura do monitor + "led" de energia aceso no canto
        c.create_rectangle(3, 3, self.w - 3, self.h - 3,
                           outline=COR_MOLDURA, width=2)
        c.create_rectangle(self.w - 26, self.h - 18, self.w - 18, self.h - 10,
                            fill=COR_TOUR, outline=COR_MOLDURA)

    # ------------------------- utilidades -------------------------

    def custo(self):
        return custo_total(self.caminho, self.matriz) if self.caminho else 0.0

    @staticmethod
    def _fmt(v):
        return str(int(v)) if abs(v - round(v)) < 1e-9 else ("%.1f" % v)

    def _rota_txt(self):
        return "-".join(str(no + 1) for no in self.caminho)

    def _trilha_txt(self):
        return " -> ".join(str(no + 1) for no in self.caminho_dijkstra)

    def _texto_padrao(self):
        return ("> grafo com %d nós e %d arestas\n"
                "> clique em dois nós para ver o melhor caminho (dijkstra)"
                % (len(self.pos_px), len(self.arestas)))

    @staticmethod
    def _fatorial(k):
        f = 1
        for i in range(2, k + 1):
            f *= i
        return f

    def _info(self, texto):
        self.info.config(text=texto)

    def rodar(self):
        self.janela.mainloop()


if __name__ == "__main__":
    AppCaixeiro().rodar()
