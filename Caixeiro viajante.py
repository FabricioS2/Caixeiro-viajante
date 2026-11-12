import tkinter as tk


# ---------------------------------------------------------------------
# PARTE 1 — Matemática e aleatoriedade feitas à mão
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


class Aleatorio:
    """Gerador pseudoaleatório linear congruente (Park & Miller)."""

    def __init__(self):
        # semente muda a cada execução (id/hash de objetos variam)
        semente = (id(object()) ^ hash("caixeiro")) % 2147483647
        self.estado = semente if semente > 0 else 1

    def inteiro(self, a, b):
        """Sorteia um inteiro no intervalo fechado [a, b]."""
        self.estado = (16807 * self.estado) % 2147483647
        return a + self.estado % (b - a + 1)


rng = Aleatorio()


# ---------------------------------------------------------------------
# PARTE 2 — Algoritmos do Caixeiro Viajante
# ---------------------------------------------------------------------

def distancia_entre(p, q):
    """Distância euclidiana entre dois pontos (x, y)."""
    dx, dy = p[0] - q[0], p[1] - q[1]
    return sqrt(dx * dx + dy * dy)


def matriz_distancias(cidades):
    """Pré-computa a distância entre todos os pares de cidades."""
    n = len(cidades)
    m = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = distancia_entre(cidades[i], cidades[j])
            m[i][j] = m[j][i] = d
    return m


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
    Um tour que não aceita mais trocas não possui arestas cruzadas.
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
    A cidade 0 fica fixa como início (rotações de um ciclo são iguais).
    Viável só com ~9 cidades ou menos.
    """
    n = len(m)
    melhor, melhor_custo = [0] + list(range(1, n)), 1e18
    for perm in permutacoes(range(1, n)):
        c = custo_total([0] + perm, m)
        if c < melhor_custo:
            melhor, melhor_custo = [0] + perm, c
    return melhor


# ---------------------------------------------------------------------
# PARTE 3 — Interface gráfica (tkinter)
# ---------------------------------------------------------------------

COR_FUNDO    = "#10151f"
COR_GRADE    = "#1b2333"
COR_TOUR     = "#3ddc97"
COR_CIDADE   = "#ffffff"
COR_CONTORNO = "#ff5d5d"
COR_TEXTO    = "#e9edf5"

LARG, ALT, MARG, RAIO = 760, 540, 30, 6

MAX_CIDADES = 2000          # limite do sorteio / do spinbox


class AppCaixeiro:

    def __init__(self):
        self.janela = tk.Tk()
        self.janela.title("Problema do Caixeiro Viajante")
        self.janela.configure(bg="#0a0e16")
        self.janela.resizable(False, False)

        self.cidades = []        # lista de (x, y)
        self.matriz = None       # distâncias pré-computadas
        self.caminho = None      # ordem de visitação (índices)
        self.animando = False
        self.melhorias = 0

        self._montar_interface()
        self.novas_cidades_aleatorias()

    # ------------------------- interface -------------------------

    def _montar_interface(self):
        principal = tk.Frame(self.janela, bg="#0a0e16")
        principal.pack(padx=10, pady=10)

        self.canvas = tk.Canvas(principal, width=LARG, height=ALT,
                                bg=COR_FUNDO, highlightthickness=0)
        self.canvas.grid(row=0, column=0)

        painel = tk.Frame(principal, bg="#0a0e16")
        painel.grid(row=0, column=1, sticky="n", padx=(12, 0))

        def botao(texto, comando):
            tk.Button(painel, text=texto, command=comando, bg="#1f2a3d",
                      fg=COR_TEXTO, activebackground="#2c3b57",
                      activeforeground="white", relief="flat", cursor="hand2",
                      font=("Helvetica", 10, "bold"), padx=10, pady=6,
                      width=24).pack(fill="x", pady=2)

        tk.Label(painel, text="Número de cidades:", bg="#0a0e16", fg=COR_TEXTO,
                 font=("Helvetica", 9)).pack(anchor="w", pady=(8, 2))

        self.spin = tk.Spinbox(painel, from_=4, to=MAX_CIDADES, width=8,
                               justify="center", bg="#1f2a3d", fg=COR_TEXTO,
                               relief="flat", buttonbackground="#2c3b57")
        self.spin.delete(0, "end")
        self.spin.insert(0, "30")
        self.spin.pack(anchor="w")

        botao("Novas cidades", self.novas_cidades_aleatorias)
        botao("Caixeiro viajante", self.resolver)
        botao("Força bruta", self.resolver_exato)
        botao("Limpar tudo", self.limpar)

    # ------------------------- ações -------------------------

    def _sortear_posicao(self, min_dist, tentativas=120):
        """
        Sorteia um (x, y) que fique a pelo menos `min_dist` de qualquer
        cidade existente. Retorna None se não conseguir em `tentativas`.
        """
        for _ in range(tentativas):
            x = rng.inteiro(MARG, LARG - MARG)
            y = rng.inteiro(MARG, ALT - MARG)
            ok = True
            for (cx, cy) in self.cidades:
                dx, dy = x - cx, y - cy
                if dx * dx + dy * dy < min_dist * min_dist:
                    ok = False
                    break
            if ok:
                return (x, y)
        return None

    def novas_cidades_aleatorias(self):
        self.animando = False
        try:
            n = int(self.spin.get())
        except ValueError:
            n = 30
        n = max(3, min(MAX_CIDADES, n))

        # Distância mínima adaptativa: cresce com a área disponível,
        # diminui conforme o número de cidades aumenta.
        area = (LARG - 2 * MARG) * (ALT - 2 * MARG)
        min_dist = 0.55 * sqrt(area / n)
        # Piso baixo (2 px) para que lotes grandes ainda caibam;
        # teto de 60 px para lotes pequenos ficarem bem espalhados.
        min_dist = max(2.0, min(60.0, min_dist))

        self.cidades = []
        for _ in range(n):
            md = min_dist
            pos = self._sortear_posicao(md)
            # Se o critério ficar impossível, vai relaxando aos poucos.
            while pos is None and md > 0.5:
                md *= 0.75
                pos = self._sortear_posicao(md)
            if pos is None:
                # Último recurso: aceita qualquer posição livre óbvia.
                pos = (rng.inteiro(MARG, LARG - MARG),
                       rng.inteiro(MARG, ALT - MARG))
            self.cidades.append(pos)

        self.matriz = matriz_distancias(self.cidades)
        self.caminho = None
        self.melhorias = 0
        self.desenhar()

    def limpar(self):
        self.animando = False
        self.cidades, self.caminho, self.matriz = [], None, None
        self.melhorias = 0
        self.desenhar()

    def resolver(self):
        if len(self.cidades) < 3 or self.animando:
            return
        self.caminho = vizinho_mais_proximo(self.matriz)
        self.melhorias = 0
        self.desenhar()
        self.animando = True
        self.janela.after(300, self._passo_animado)

    def _passo_animado(self):
        if not self.animando:
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
            self.janela.after(20, self._passo_animado)
        else:
            self.animando = False

    def resolver_exato(self):
        if self.animando or len(self.cidades) < 3:
            return
        if len(self.cidades) > 9:
            return
        self.janela.after(60, self._executar_exato)

    def _executar_exato(self):
        self.caminho = forca_bruta(self.matriz)
        self.melhorias = 0
        self.desenhar()

    # ------------------------- desenho -------------------------

    def desenhar(self):
        c = self.canvas
        c.delete("all")

        for gx in range(0, LARG, 40):
            c.create_line(gx, 0, gx, ALT, fill=COR_GRADE)
        for gy in range(0, ALT, 40):
            c.create_line(0, gy, LARG, gy, fill=COR_GRADE)

        if self.caminho and len(self.caminho) > 1:
            n = len(self.caminho)
            # Com muitas cidades, desenha em bloco único (bem mais rápido)
            # do que N chamadas separadas de create_line.
            if n > 300:
                pontos = []
                for k in range(n):
                    x1, y1 = self.cidades[self.caminho[k]]
                    pontos.extend((x1, y1))
                x1, y1 = self.cidades[self.caminho[0]]
                pontos.extend((x1, y1))          # fecha o ciclo
                c.create_line(*pontos, fill=COR_TOUR, width=1)
            else:
                for k in range(n):
                    x1, y1 = self.cidades[self.caminho[k]]
                    x2, y2 = self.cidades[self.caminho[(k + 1) % n]]
                    c.create_line(x1, y1, x2, y2, fill=COR_TOUR, width=2)

        mostrar_num = len(self.cidades) <= 40
        # Reduz o raio em mapas muito cheios para não virar uma mancha só.
        if len(self.cidades) > 600:
            raio = 1
        elif len(self.cidades) > 250:
            raio = 2
        else:
            raio = RAIO
        for i, (x, y) in enumerate(self.cidades):
            c.create_oval(x - raio, y - raio, x + raio, y + raio,
                          fill=COR_CIDADE, outline=COR_CONTORNO, width=1)
            if mostrar_num:
                c.create_text(x, y - RAIO - 8, text=str(i),
                              fill=COR_TEXTO, font=("Helvetica", 7))

    def rodar(self):
        self.janela.mainloop()


if __name__ == "__main__":
    AppCaixeiro().rodar()