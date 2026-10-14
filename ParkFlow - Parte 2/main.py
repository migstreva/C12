"""ParkFlow — interface gráfica para o projeto de Sistemas Operacionais."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from simulacao import Configuracao, Simulacao

BG = "#0B1220"
PANEL = "#121F31"
PANEL_SOFT = "#19283E"
LINE = "#263751"
TEXT = "#F1F5FC"
MUTED = "#91A3BC"
TEAL = "#57E0C0"
BLUE = "#83B6FF"
AMBER = "#EFC374"
PINK = "#F7A4B3"
BLACK = "#091522"
PRIORITY = {"PCD": PINK, "Idoso": AMBER, "Comum": BLUE}


def arredondar(c, x1, y1, x2, y2, raio, **kwargs):
    r = min(raio, (x2 - x1) / 2, (y2 - y1) / 2)
    coords = [
        x1 + r, y1, x2 - r, y1, x2, y1,
        x2, y1 + r, x2, y2 - r, x2, y2,
        x2 - r, y2, x1 + r, y2, x1, y2,
        x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return c.create_polygon(coords, smooth=True, splinesteps=16, **kwargs)


def rotulo(pai, texto, fonte=11, cor=TEXT, negrito=False, **kwargs):
    return tk.Label(
        pai, text=texto, bg=kwargs.pop("bg", PANEL), fg=cor,
        font=("Segoe UI", fonte, "bold" if negrito else "normal"),
        **kwargs,
    )


class Dashboard:
    def __init__(self, raiz: tk.Tk):
        self.raiz = raiz
        self.raiz.title("ParkFlow | Escalonamento e sincronização")
        self.raiz.geometry("1370x875")
        self.raiz.minsize(1130, 760)
        self.raiz.configure(bg=BG)

        self.simulacao: Simulacao | None = None
        self.final_anunciado = False
        self.dados = self._dados_vazios()

        self.num_carros = tk.StringVar(value="32")
        self.num_vagas = tk.StringVar(value="6")
        self.velocidade = tk.StringVar(value="3x")
        self.modo = tk.StringVar(value="Aleatório")
        self._config_anterior = ("32", "6")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Park.TCombobox", fieldbackground=PANEL_SOFT, background=PANEL_SOFT,
            foreground=TEXT, arrowcolor=TEAL, borderwidth=0, padding=6,
            font=("Segoe UI", 11),
        )
        style.map(
            "Park.TCombobox",
            fieldbackground=[("readonly", PANEL_SOFT)],
            foreground=[("readonly", TEXT)],
            selectbackground=[("readonly", PANEL_SOFT)],
            selectforeground=[("readonly", TEXT)],
        )

        self._montar_interface()
        self.raiz.after(140, self._atualizar)
        self.raiz.protocol("WM_DELETE_WINDOW", self._fechar)

    @staticmethod
    def _dados_vazios():
        return {
            "vagas": [], "ocupadas": 0, "capacidade": 6,
            "criados": 0, "entraram": 0, "concluidos": 0,
            "fila_total": 0, "fila": [], "espera_media": 0.0,
            "maior_fila": 0, "erros": 0, "manobra": None,
            "producao_concluida": False, "finalizada": False, "segundos": 0.0,
            "semaforo_livres": 6, "semaforo_reservadas": 0,
            "max_manobras_simultaneas": 0, "ultima_decisao": None,
            "modo_demonstracao": False,
        }

    def _montar_interface(self):
        principal = tk.Frame(self.raiz, bg=BG)
        principal.pack(fill="both", expand=True, padx=26, pady=(23, 20))

        topo = tk.Frame(principal, bg=BG)
        topo.pack(fill="x", pady=(0, 20))

        marca = tk.Frame(topo, bg=BG)
        marca.pack(side="left")
        logo = tk.Canvas(marca, width=50, height=50, bg=BG, bd=0, highlightthickness=0)
        logo.pack(side="left", padx=(0, 13))
        arredondar(logo, 2, 2, 48, 48, 12, fill=TEAL, outline="")
        logo.create_text(25, 25, text="P", font=("Segoe UI", 26, "bold"), fill=BLACK)

        textos = tk.Frame(marca, bg=BG)
        textos.pack(side="left")
        tk.Label(
            textos, text="PARKFLOW", bg=BG, fg=TEXT,
            font=("Segoe UI", 23, "bold"),
        ).pack(anchor="w")
        tk.Label(
            textos, text="LABORATÓRIO DE SISTEMAS OPERACIONAIS", bg=BG,
            fg=MUTED, font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(1, 0))

        estado = tk.Frame(topo, bg=BG)
        estado.pack(side="right", pady=10)
        self.estado_label = tk.Label(
            estado, text="AGUARDANDO", bg=BG, fg=TEAL,
            font=("Segoe UI", 10, "bold"),
        )
        self.estado_label.pack(side="right", padx=(12, 0))
        tk.Label(
            estado, text="ETAPA 02  /  MULTITHREAD", bg=BG,
            fg=MUTED, font=("Segoe UI", 10),
        ).pack(side="right")

        barra = self._painel(principal, altura=103)
        barra.pack(fill="x", pady=(0, 17))
        controles = tk.Frame(barra, bg=PANEL)
        controles.pack(fill="both", expand=True, padx=19, pady=15)

        self.combo_carros = self._combo(controles, "CARROS / THREADS", self.num_carros,
                                        ["8", "16", "24", "32", "48", "64", "128", "256", "512", "1024", "2048"], 12)
        self.combo_vagas = self._combo(controles, "VAGAS", self.num_vagas,
                                       [str(i) for i in range(1, 13)], 7)
        self.combo_vel = self._combo(controles, "VELOCIDADE", self.velocidade,
                                     ["1x", "2x", "3x", "5x", "8x"], 6)
        self.combo_modo = self._combo(controles, "CENÁRIO", self.modo,
                                      ["Aleatório", "Demonstração"], 14)
        self.combo_modo.bind("<<ComboboxSelected>>", self._modo_alterado)

        ttk.Separator(controles, orient="vertical").pack(side="left", fill="y", padx=17)
        politica = tk.Frame(controles, bg=PANEL)
        politica.pack(side="left", fill="y")
        rotulo(politica, "POLÍTICA DE ESCALONAMENTO", 9, MUTED, True).pack(anchor="w", pady=(1, 8))
        rotulo(politica, "Prioridade  →  SJF  →  FCFS", 12, TEXT, True).pack(anchor="w")

        self.botao_reset = tk.Button(
            controles, text="LIMPAR", font=("Segoe UI", 10, "bold"),
            fg=MUTED, bg=PANEL_SOFT, activeforeground=TEXT,
            activebackground=LINE, relief="flat", cursor="hand2",
            bd=0, padx=15, pady=11, command=self._limpar,
        )
        self.botao_reset.pack(side="right", padx=(8, 0), pady=5)
        self.botao_iniciar = tk.Button(
            controles, text="INICIAR SIMULAÇÃO", font=("Segoe UI", 10, "bold"),
            fg=BLACK, bg=TEAL, activeforeground=BLACK,
            activebackground="#83F0D5", relief="flat", cursor="hand2",
            bd=0, padx=17, pady=11, command=self._iniciar,
        )
        self.botao_iniciar.pack(side="right", pady=5)

        indicadores = tk.Frame(principal, bg=BG)
        indicadores.pack(fill="x", pady=(0, 17))
        self.metricas = {}
        for k, titulo, cor in [
            ("ocupacao", "OCUPAÇÃO ATUAL", TEAL),
            ("fila", "AGUARDANDO NA FILA", BLUE),
            ("atendidos", "CARROS ATENDIDOS", AMBER),
            ("espera", "ESPERA MÉDIA (REAL)", TEXT),
            ("erros", "INCONSISTÊNCIAS", TEAL),
        ]:
            caixa = self._painel(indicadores, altura=98)
            caixa.pack(side="left", fill="both", expand=True, padx=(0, 10) if k != "erros" else 0)
            rotulo(caixa, titulo, 9, MUTED, True).pack(anchor="w", padx=16, pady=(13, 3))
            numero = rotulo(caixa, "0", 22, cor, True)
            numero.pack(anchor="w", padx=16)
            self.metricas[k] = numero

        
        conteudo = tk.Frame(principal, bg=BG)
        conteudo.pack(fill="both", expand=True)

        conteudo.grid_columnconfigure(0, weight=7, uniform="paineis")
        conteudo.grid_columnconfigure(1, weight=4, uniform="paineis")
        conteudo.grid_columnconfigure(2, weight=5, uniform="paineis")
        conteudo.grid_rowconfigure(0, weight=1)

        esquerda = tk.Frame(conteudo, bg=BG)
        esquerda.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        centro = tk.Frame(conteudo, bg=BG)
        centro.grid(row=0, column=1, sticky="nsew", padx=(0, 12))

        direita = tk.Frame(conteudo, bg=BG)
        direita.grid(row=0, column=2, sticky="nsew")

        mapa = self._painel(esquerda)
        mapa.pack(fill="both", expand=True)
        cabecalho_mapa = tk.Frame(mapa, bg=PANEL)
        cabecalho_mapa.pack(fill="x", padx=19, pady=(17, 2))
        rotulo(cabecalho_mapa, "Mapa do estacionamento", 16, TEXT, True).pack(side="left")
        self.rotulo_mapa = rotulo(cabecalho_mapa, "0 / 6 ocupadas", 10, TEAL, True)
        self.rotulo_mapa.pack(side="right")
        rotulo(
            mapa, "Uma manobra por vez • acesso às vagas protegido por mutex",
            10, MUTED,
        ).pack(anchor="w", padx=19, pady=(0, 4))
        self.rotulo_semaforo = rotulo(
            mapa, "SEMÁFORO  6/6 permissões livres  •  0 reservadas", 9, BLUE, True,
        )
        self.rotulo_semaforo.pack(anchor="w", padx=19, pady=(0, 2))
        self.rotulo_mutex = rotulo(
            mapa, "MUTEX  livre  •  pico de manobras simultâneas: 0", 9, MUTED,
        )
        self.rotulo_mutex.pack(anchor="w", padx=19, pady=(0, 7))
        area_vagas = tk.Frame(mapa, bg=PANEL)
        area_vagas.pack(fill="both", expand=True, padx=15, pady=(2, 15))

        self.canvas_vagas = tk.Canvas(
            area_vagas,
            bg=PANEL,
            bd=0,
            highlightthickness=0,
            width=1,
            height=250
        )

        self.canvas_vagas.pack(side="left", fill="both", expand=True)

        barra_vagas = tk.Scrollbar(
            area_vagas,
            orient="vertical",
            command=self.canvas_vagas.yview,
            bg=LINE,
            troughcolor=PANEL,
            activebackground=TEAL,
            width=11,
            bd=0,
            highlightthickness=0
        )

        barra_vagas.pack(side="right", fill="y")

        self.canvas_vagas.configure(yscrollcommand=barra_vagas.set)

        self.canvas_vagas.bind(
            "<Configure>",
            lambda _: self._desenhar_vagas()
        )

        self.canvas_vagas.bind(
            "<MouseWheel>",
            lambda e: self.canvas_vagas.yview_scroll(
                -1 if e.delta > 0 else 1, "units"
            )
        )

        fila = self._painel(centro)
        fila.pack(fill="both", expand=True)
        barra_fila = tk.Frame(fila, bg=PANEL)
        barra_fila.pack(fill="x", padx=18, pady=(17, 1))
        rotulo(barra_fila, "Ready Queue", 16, TEXT, True).pack(side="left")
        self.contagem_fila = rotulo(barra_fila, "0 esperando", 10, BLUE, True)
        self.contagem_fila.pack(side="right")
        rotulo(fila, "P → SJF (segundos previstos) → FCFS", 9, MUTED).pack(
            anchor="w", padx=18, pady=(1, 7)
        )
        decisao_box = tk.Frame(fila, bg=PANEL_SOFT, padx=11, pady=9)
        decisao_box.pack(side="bottom", fill="x", padx=13, pady=(0, 12))
        rotulo(
            decisao_box, "ÚLTIMA DECISÃO DO ESCALONADOR", 8, MUTED, True, bg=PANEL_SOFT,
        ).pack(anchor="w")
        self.rotulo_decisao = rotulo(
            decisao_box, "Aguardando a primeira decisão...", 9, TEAL, True,
            bg=PANEL_SOFT, justify="left", anchor="w", wraplength=215,
        )
        self.rotulo_decisao.pack(anchor="w", fill="x", pady=(4, 0))

        self.canvas_fila = tk.Canvas(fila, bg=PANEL, highlightthickness=0, width=1, height=200)
        self.canvas_fila.pack(fill="both", expand=True, padx=13, pady=(0, 10))
        self.canvas_fila.bind("<Configure>", lambda _: self._desenhar_fila())

        logs = self._painel(direita)
        logs.pack(fill="both", expand=True)
        cabecalho_logs = tk.Frame(logs, bg=PANEL)
        cabecalho_logs.pack(fill="x", padx=18, pady=(15, 9))
        rotulo(cabecalho_logs, "Eventos do sistema", 13, TEXT, True).pack(side="left")
        rotulo(cabecalho_logs, "AO VIVO", 9, TEAL, True).pack(side="right")
        self.texto_logs = tk.Text(
            logs, bg=PANEL, fg=MUTED, font=("Consolas", 9),
            relief="flat", height=10, wrap="word", bd=0,
            insertbackground=TEXT, state="disabled",
            padx=11, pady=5, highlightthickness=0, width=1
        )
        self.texto_logs.pack(fill="both", expand=True, padx=9, pady=(0, 11))
        for categoria, cor in [
            ("CHEGADA", MUTED), ("SCHEDULER", BLUE),
            ("ENTRADA", TEAL), ("SAÍDA", AMBER),
            ("ERRO", PINK), ("LIMITE", PINK), ("SISTEMA", TEXT),
            ("MUTEX", AMBER), ("SEMAFORO", TEAL),
        ]:
            self.texto_logs.tag_config(categoria, foreground=cor)

        rodape = tk.Frame(principal, bg=BG)
        rodape.pack(fill="x", pady=(13, 0))
        tk.Label(
            rodape, text="PRIORIDADES    P1  PCD     •     P2  IDOSO     •     P3  COMUM",
            bg=BG, fg=MUTED, font=("Segoe UI", 9),
        ).pack(side="left")
        tk.Label(
            rodape, text="THREADS  +  READY QUEUE  +  PRIORITY  +  SJF  +  FCFS  +  MUTEX  +  SEMÁFORO",
            bg=BG, fg=MUTED, font=("Segoe UI", 9),
        ).pack(side="right")

        self._desenhar_vagas()
        self._desenhar_fila()

    def _painel(self, pai, altura=None):
        painel = tk.Frame(pai, bg=PANEL, highlightbackground=LINE, highlightthickness=1)
        if altura:
            painel.configure(height=altura)
            painel.pack_propagate(False)
        return painel

    def _combo(self, pai, texto, var, valores, largura):
        frame = tk.Frame(pai, bg=PANEL)
        frame.pack(side="left", padx=(0, 11))
        rotulo(frame, texto, 9, MUTED, True).pack(anchor="w", pady=(0, 6))
        combo = ttk.Combobox(
            frame, textvariable=var, values=valores, width=largura,
            state="readonly", style="Park.TCombobox",
        )
        combo.pack(anchor="w")
        return combo

    def _modo_alterado(self, _evento=None):
        if self.modo.get() == "Demonstração":
            self._config_anterior = (self.num_carros.get(), self.num_vagas.get())
            self.num_carros.set("8")
            self.num_vagas.set("1")
            self.combo_carros.configure(state="disabled")
            self.combo_vagas.configure(state="disabled")
        else:
            self.num_carros.set(self._config_anterior[0])
            self.num_vagas.set(self._config_anterior[1])
            if self.simulacao is None or self.dados["finalizada"]:
                self.combo_carros.configure(state="readonly")
                self.combo_vagas.configure(state="readonly")
        self.dados["capacidade"] = int(self.num_vagas.get())
        self.dados["semaforo_livres"] = int(self.num_vagas.get())
        self._refrescar()

    def _habilitar_controles(self):
        for combo in [self.combo_carros, self.combo_vagas, self.combo_vel, self.combo_modo]:
            combo.configure(state="readonly")
        if self.modo.get() == "Demonstração":
            self.combo_carros.configure(state="disabled")
            self.combo_vagas.configure(state="disabled")

    def _iniciar(self):
        try:
            carros = int(self.num_carros.get())
            vagas = int(self.num_vagas.get())
            velocidade = float(self.velocidade.get().rstrip("x"))
        except ValueError:
            messagebox.showerror("Configuração", "Informe valores válidos.")
            return

        if carros >= 512:
            confirmar = messagebox.askyesno(
                "Teste de estresse",
                f"Iniciar {carros} threads reais?\n\n"
                "Testes muito grandes podem consumir bastante memória e "
                "atingir limites do sistema operacional.",
            )
            if not confirmar:
                return

        self._limpar()
        self.final_anunciado = False
        self.simulacao = Simulacao(Configuracao(
            quantidade_carros=carros,
            quantidade_vagas=vagas,
            velocidade=velocidade,
            modo_demonstracao=self.modo.get() == "Demonstração",
        ))
        self.botao_iniciar.configure(state="disabled", text="EM EXECUÇÃO", bg="#325E59")
        for combo in [self.combo_carros, self.combo_vagas, self.combo_vel, self.combo_modo]:
            combo.configure(state="disabled")
        self.estado_label.configure(text="EM EXECUÇÃO", fg=TEAL)
        self.simulacao.iniciar()

    def _limpar(self):
        if self.simulacao is not None:
            self.simulacao.parar()
            self.simulacao = None
        self.dados = self._dados_vazios()
        self.dados["capacidade"] = int(self.num_vagas.get())
        self.dados["semaforo_livres"] = int(self.num_vagas.get())
        self.final_anunciado = False
        self.estado_label.configure(text="AGUARDANDO", fg=TEAL)
        self.botao_iniciar.configure(state="normal", text="INICIAR SIMULAÇÃO", bg=TEAL)
        self._habilitar_controles()
        self.texto_logs.configure(state="normal")
        self.texto_logs.delete("1.0", "end")
        self.texto_logs.configure(state="disabled")
        self._refrescar()

    def _fechar(self):
        if self.simulacao is not None:
            self.simulacao.parar()
        self.raiz.destroy()

    def _atualizar(self):
        try:
            if self.simulacao is not None:
                self.dados = self.simulacao.snapshot()
                self._ler_eventos()
                if self.dados["finalizada"] and not self.final_anunciado:
                    self.final_anunciado = True
                    self.estado_label.configure(text="CONCLUÍDA", fg=AMBER)
                    self.botao_iniciar.configure(
                        state="normal", text="NOVA SIMULAÇÃO", bg=TEAL
                    )
                    self._habilitar_controles()
            self._refrescar()
        except tk.TclError:
            return
        self.raiz.after(140, self._atualizar)

    def _ler_eventos(self):
        eventos = []
        for _ in range(90):
            try:
                eventos.append(self.simulacao.eventos.get_nowait())
            except Exception:
                break
        if not eventos:
            return
        self.texto_logs.configure(state="normal")
        for hora, tipo, mensagem in eventos:
            self.texto_logs.insert("end", f"{hora}  ", "SISTEMA")
            self.texto_logs.insert("end", f"[{tipo}] ", tipo)
            self.texto_logs.insert("end", mensagem + "\n")
        linhas = int(self.texto_logs.index("end-1c").split(".")[0])
        if linhas > 240:
            self.texto_logs.delete("1.0", f"{linhas - 190}.0")
        self.texto_logs.see("end")
        self.texto_logs.configure(state="disabled")

    def _refrescar(self):
        d = self.dados
        self.metricas["ocupacao"].configure(text=f"{d['ocupadas']} / {d['capacidade']}")
        self.metricas["fila"].configure(text=str(d["fila_total"]))
        self.metricas["atendidos"].configure(text=str(d["concluidos"]))
        self.metricas["espera"].configure(text=f"{d['espera_media']:.2f}s")
        self.metricas["erros"].configure(text=str(d["erros"]))
        self.rotulo_mapa.configure(text=f"{d['ocupadas']} / {d['capacidade']} ocupadas")
        self.contagem_fila.configure(text=f"{d['fila_total']} esperando")
        self.rotulo_semaforo.configure(
            text=(
                f"SEMÁFORO  {d['semaforo_livres']}/{d['capacidade']} permissões livres"
                f"  •  {d['semaforo_reservadas']} reservadas"
            )
        )
        self.rotulo_mutex.configure(
            text=(
                f"MUTEX  {'em uso: Carro ' + format(d['manobra'], '03d') if d['manobra'] else 'livre'}"
                f"  •  pico de manobras simultâneas: {d['max_manobras_simultaneas']}"
            ),
            fg=AMBER if d['manobra'] else MUTED,
        )
        decisao = d.get("ultima_decisao")
        if decisao:
            concorrente = decisao["concorrente"]
            comparacao = (
                f"\nComparado: {concorrente['carro']:03d} "
                f"· P{concorrente['prioridade']} · {concorrente['duracao']}s"
                if concorrente else ""
            )
            self.rotulo_decisao.configure(
                text=(
                    f"Carro {decisao['carro']:03d} · P{decisao['prioridade']} "
                    f"· {decisao['duracao']}s previstos\n"
                    f"{decisao['criterio']}: {decisao['explicacao']}{comparacao}"
                )
            )
        else:
            self.rotulo_decisao.configure(text="Aguardando a primeira decisão...")
        self._desenhar_vagas()
        self._desenhar_fila()

    def _desenhar_vagas(self):
        c = self.canvas_vagas
        c.delete("all")

        w, h = c.winfo_width(), c.winfo_height()

        if w < 160 or h < 100:
            return

        vagas = self.dados["vagas"] or [
            {"numero": i, "carro": None}
            for i in range(1, self.dados["capacidade"] + 1)
        ]

        colunas = 2
        linhas = (len(vagas) + colunas - 1) // colunas

        margem = 10
        folga = 12

        largura = (w - 2 * margem - (colunas - 1) * folga) / colunas

        altura = min(
            210,
            max(
                150,
                (h - 2 * margem - (linhas - 1) * folga) / linhas
            )
        )

        altura_total = 2 * margem + linhas * altura + (linhas - 1) * folga
        y_inicio = margem + max(0, (h - altura_total) / 2)

        for indice, vaga in enumerate(vagas):
            coluna, linha = indice % colunas, indice // colunas
            x = folga + coluna * (largura + folga)
            y = y_inicio + linha * (altura + folga)
            ocupado = vaga["carro"] is not None
            cor_borda = TEAL if ocupado else LINE
            arredondar(c, x, y, x + largura, y + altura, 10,
                       fill=PANEL_SOFT if ocupado else "#152237", outline=cor_borda, width=1)
            c.create_text(x + 14, y + 18, text=f"VAGA {vaga['numero']:02d}",
                          anchor="w", fill=MUTED, font=("Segoe UI", 9, "bold"))

            if ocupado:
                manobra = vaga.get("manobra", False)
                status = "MANOBRANDO" if manobra else "OCUPADA"
                c.create_text(x + largura - 13, y + 18, text=status,
                              anchor="e", fill=AMBER if manobra else TEAL,
                              font=("Segoe UI", 8, "bold"))
                c.create_text(x + 14, y + altura * 0.48, text=f"Carro {vaga['carro']:03d}",
                              anchor="w", fill=TEXT, font=("Segoe UI", 15, "bold"))
                if altura >= 100:
                    c.create_text(x + 14, y + altura * 0.72,
                                  text=f"{vaga['perfil']}   •   {vaga['restante']:.1f}s restantes",
                                  anchor="w", fill=MUTED, font=("Segoe UI", 9))
                progresso = 1 - vaga["restante"] / max(1, vaga["duracao"])
                c.create_rectangle(x + 14, y + altura - 14,
                                   x + largura - 14, y + altura - 10,
                                   fill=LINE, outline="")
                c.create_rectangle(x + 14, y + altura - 14,
                                   x + 14 + (largura - 28) * max(0, min(1, progresso)),
                                   y + altura - 10, fill=TEAL, outline="")
            else:
                c.create_text(x + largura / 2, y + altura / 2,
                              text="DISPONÍVEL", fill="#637C99",
                              font=("Segoe UI", 13, "bold"))
        c.configure(
            scrollregion=(
                0,
                0,
                w,
                max(
                    h,
                    y_inicio + linhas * altura + (linhas - 1) * folga + margem
                )
            )
        )

    def _desenhar_fila(self):
        c = self.canvas_fila
        c.delete("all")
        w, h = max(1, c.winfo_width()), max(150, c.winfo_height())
        fila = self.dados["fila"]
        total = self.dados["fila_total"]
        if not total:
            c.create_text(w / 2, h / 2 - 10, text="Nenhum carro aguardando",
                          fill=MUTED, font=("Segoe UI", 12, "bold"))
            c.create_text(w / 2, h / 2 + 16, text="A fila será atualizada automaticamente",
                          fill="#6D829E", font=("Segoe UI", 9))
            return

        altura_linha = 46
        limite = min(len(fila), max(2, int((h - 12) // altura_linha)))
        for i, carro in enumerate(fila[:limite]):
            y = 5 + i * altura_linha
            arredondar(c, 4, y, w - 6, y + 40, 8,
                       fill=PANEL_SOFT, outline="")
            c.create_rectangle(5, y + 7, 8, y + 33,
                               fill=PRIORITY[carro["perfil"]], outline="")
            c.create_text(21, y + 20, text=f"{i + 1:02d}", anchor="w",
                          fill=MUTED, font=("Consolas", 10))
            c.create_text(54, y + 18, text=f"Carro {carro['numero']:03d}", anchor="w",
                          fill=TEXT, font=("Segoe UI", 11, "bold"))
            c.create_text(54, y + 32, text=f"{carro['perfil']}  •  chegada {carro['ordem']}",
                          anchor="w", fill=MUTED, font=("Segoe UI", 8))
            c.create_text(w - 18, y + 20,
                          text=f"P{carro['prioridade']}  {carro['duracao']}s",
                          anchor="e", fill=PRIORITY[carro["perfil"]],
                          font=("Segoe UI", 10, "bold"))
        restantes = total - limite
        if restantes > 0:
            c.create_text(w / 2, min(h - 9, 8 + limite * altura_linha),
                          text=f"+ {restantes} outros carros na fila", fill=MUTED,
                          font=("Segoe UI", 9))

def main():
    janela = tk.Tk()
    Dashboard(janela)
    janela.mainloop()


if __name__ == "__main__":
    main()
