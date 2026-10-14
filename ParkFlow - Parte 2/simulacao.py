"""Motor de simulação: threads, fila de espera, escalonamento e sincronização."""

from __future__ import annotations

import queue
import random
import threading
import time
from dataclasses import dataclass
from typing import Any


# Prioridade menor = atendimento primeiro. Os tipos são apenas uma regra da simulação.
PERFIS = (
    ("PCD", 1),
    ("Idoso", 2),
    ("Comum", 3),
)

# Demonstra Priority, SJF e FCFS com uma vaga e oito carros conhecidos.
# (perfil, prioridade, duração simulada em segundos)
CENARIO_DEMONSTRACAO = (
    ("Comum", 3, 9),
    ("Comum", 3, 5),
    ("PCD", 1, 8),
    ("PCD", 1, 4),
    ("PCD", 1, 4),
    ("Idoso", 2, 3),
    ("Idoso", 2, 7),
    ("Comum", 3, 3),
)


def chave_escalonamento(carro):
    """Priority Scheduling, SJF e FCFS, nesta ordem."""
    return (carro.prioridade, carro.duracao, carro.ordem_chegada)


@dataclass(frozen=True)
class Configuracao:
    quantidade_carros: int = 24
    quantidade_vagas: int = 6
    velocidade: float = 3.0
    intervalo_chegada: float = 0.14
    semente: int | None = None
    modo_demonstracao: bool = False


class Estacionamento:
    def __init__(self, quantidade_vagas: int):
        self.vagas: list[Carro | None] = [None] * quantidade_vagas

    def procurar_vaga(self) -> int | None:
        for posicao, ocupante in enumerate(self.vagas):
            if ocupante is None:
                return posicao
        return None


class Carro(threading.Thread):
    def __init__(
        self,
        numero: int,
        perfil: str,
        prioridade: int,
        duracao: int,
        ordem_chegada: int,
        simulacao: Simulacao,
    ):
        super().__init__(name=f"Carro-{numero:03d}", daemon=True)
        self.numero = numero
        self.perfil = perfil
        self.prioridade = prioridade
        self.duracao = duracao
        self.ordem_chegada = ordem_chegada
        self.simulacao = simulacao
        self.chegada_em = time.monotonic()
        self.entrada_em: float | None = None
        self.saida_em: float | None = None
        self.vaga: int | None = None
        self.autorizado = threading.Event()
        self.estacionado = threading.Event()
        self.escolhido = False

    def run(self):
        sim = self.simulacao

        # A thread fica aguardando a autorização do scheduler, sem consumir CPU.
        while not self.autorizado.wait(timeout=0.12):
            if sim.cancelado.is_set():
                return

        if sim.cancelado.is_set():
            if self.escolhido:
                with sim.condicao:
                    sim.reservas_semaforo -= 1
                    sim.vagas_disponiveis.release()
            self.estacionado.set()
            return

        try:
            # A entrada/manobra inteira é protegida por exclusão mútua.
            with sim.mutex_vagas:
                with sim.condicao:
                    posicao = sim.estacionamento.procurar_vaga()
                    if posicao is None:
                        sim.erros += 1
                        sim.registrar("ERRO", "Sem vaga apesar de haver reserva no semáforo")
                        sim.reservas_semaforo -= 1
                        sim.vagas_disponiveis.release()
                        return

                    sim.reservas_semaforo -= 1
                    sim.manobras_ativas += 1
                    sim.max_manobras_simultaneas = max(
                        sim.max_manobras_simultaneas, sim.manobras_ativas
                    )
                    if sim.manobras_ativas > 1:
                        sim.erros += 1
                        sim.registrar("ERRO", "Manobras simultâneas na seção crítica")
                    sim.estacionamento.vagas[posicao] = self
                    self.vaga = posicao
                    self.entrada_em = time.monotonic()
                    sim.entraram += 1
                    sim.em_manobra = self.numero
                    if sim.config.quantidade_carros <= 32:
                        sim.registrar("MUTEX", f"Carro {self.numero:03d} entrou na seção crítica")
                    sim.tempo_espera_total += self.entrada_em - self.chegada_em
                    sim.registrar(
                        "ENTRADA",
                        f"Carro {self.numero:03d} ({self.perfil}) → vaga {posicao + 1:02d}",
                    )

                # Simula a manobra e mantém o mutex até seu fim.
                sim.cancelado.wait(0.27 / sim.config.velocidade)

                with sim.condicao:
                    sim.em_manobra = None
                    sim.manobras_ativas -= 1
                    if sim.config.quantidade_carros <= 32:
                        sim.registrar("MUTEX", f"Carro {self.numero:03d} liberou a seção crítica")
        finally:
            # O dispatcher só escolhe o próximo depois que a manobra terminou.
            self.estacionado.set()

        # O mutex NÃO fica retido durante toda a permanência estacionado.
        if self.vaga is not None:
            sim.cancelado.wait(self.duracao / sim.config.velocidade)

            with sim.mutex_vagas:
                with sim.condicao:
                    if sim.estacionamento.vagas[self.vaga] is self:
                        sim.estacionamento.vagas[self.vaga] = None
                    else:
                        sim.erros += 1
                        sim.registrar("ERRO", f"Vaga inconsistente: carro {self.numero:03d}")
                    self.saida_em = time.monotonic()
                    sim.concluidos += 1
                    if not sim.cancelado.is_set():
                        sim.registrar("SAÍDA", f"Carro {self.numero:03d} liberou vaga {self.vaga + 1:02d}")
                    # A liberação da permissão acompanha a mudança da vaga.
                    sim.vagas_disponiveis.release()
                    if sim.config.quantidade_carros <= 32:
                        sim.registrar("SEMAFORO", f"Carro {self.numero:03d} devolveu permissão da vaga")


class Simulacao:
    def __init__(self, config: Configuracao):
        self.config = config
        self.estacionamento = Estacionamento(config.quantidade_vagas)
        self.mutex_vagas = threading.Lock()
        self.mutex_estado = threading.Lock()
        self.condicao = threading.Condition(self.mutex_estado)
        self.vagas_disponiveis = threading.Semaphore(config.quantidade_vagas)
        self.cancelado = threading.Event()
        self.eventos: queue.SimpleQueue[tuple[str, str, str]] = queue.SimpleQueue()

        self.fila: list[Carro] = []
        self.carros: list[Carro] = []
        self.criados = 0
        self.entraram = 0
        self.concluidos = 0
        self.erros = 0
        self.max_fila = 0
        self.tempo_espera_total = 0.0
        self.em_manobra: int | None = None
        self.reservas_semaforo = 0
        self.manobras_ativas = 0
        self.max_manobras_simultaneas = 0
        self.ultima_decisao: dict[str, Any] | None = None
        self.historico_decisoes: list[dict[str, Any]] = []
        self.producao_concluida = False
        self.finalizada = False
        self.iniciada_em = time.monotonic()
        self._aleatorio = random.Random(config.semente)
        self._threads_sistema: list[threading.Thread] = []

    def registrar(self, categoria: str, mensagem: str):
        hora = time.strftime("%H:%M:%S")
        self.eventos.put((hora, categoria, mensagem))

    def iniciar(self):
        if self.config.modo_demonstracao:
            if (self.config.quantidade_carros != len(CENARIO_DEMONSTRACAO)
                    or self.config.quantidade_vagas != 1):
                raise ValueError("O modo demonstração exige 8 carros e 1 vaga")
            self.registrar("SISTEMA", "Modo demonstração: 8 carros, 1 vaga, tempos definidos")
        self.registrar("SISTEMA", "Simulação iniciada")
        produtor = threading.Thread(target=self._produzir, name="Gerador", daemon=True)
        escalonador = threading.Thread(target=self._escalonar, name="Scheduler", daemon=True)
        supervisor = threading.Thread(target=self._supervisionar, name="Supervisor", daemon=True)
        self._threads_sistema = [produtor, escalonador, supervisor]
        produtor.start()
        escalonador.start()
        supervisor.start()

    def parar(self):
        self.cancelado.set()
        with self.condicao:
            for carro in self.carros:
                carro.autorizado.set()
            self.condicao.notify_all()

    def _produzir(self):
        for numero in range(1, self.config.quantidade_carros + 1):
            if numero > 1 and self.cancelado.wait(self.config.intervalo_chegada / self.config.velocidade):
                break
            if self.cancelado.is_set():
                break

            if self.config.modo_demonstracao:
                perfil, prioridade, duracao = CENARIO_DEMONSTRACAO[numero - 1]
            else:
                perfil, prioridade = self._aleatorio.choices(
                    PERFIS, weights=[22, 26, 52], k=1
                )[0]
                duracao = self._aleatorio.randint(3, 9)
            carro = Carro(numero, perfil, prioridade, duracao, numero, self)

            try:
                carro.start()
            except RuntimeError:
                self.registrar("LIMITE", "O sistema operacional não conseguiu iniciar mais threads")
                break

            with self.condicao:
                self.carros.append(carro)
                self.fila.append(carro)
                self.criados += 1
                self.max_fila = max(self.max_fila, len(self.fila))
                self.condicao.notify_all()

            # No cenário fixo, o primeiro carro inicia a manobra antes que
            # os demais entrem na fila (para demonstrar a ordem prevista).
            if self.config.modo_demonstracao and numero == 1:
                carro.estacionado.wait(timeout=3.0)

            # Limita o log em execuções massivas, não a quantidade de carros.
            if self.config.quantidade_carros <= 128 or numero % 32 == 0:
                self.registrar(
                    "CHEGADA",
                    f"Carro {numero:03d} • {perfil} • {duracao}s previstos",
                )

        with self.condicao:
            self.producao_concluida = True
            self.condicao.notify_all()

    def _escalonar(self):
        while not self.cancelado.is_set():
            with self.condicao:
                while not self.fila and not self.producao_concluida and not self.cancelado.is_set():
                    self.condicao.wait(timeout=0.12)
                if self.cancelado.is_set() or (self.producao_concluida and not self.fila):
                    return

            # Espera uma vaga livre ANTES de escolher o próximo da fila.
            # Assim, novas prioridades podem chegar enquanto a vaga está ocupada.
            if not self.vagas_disponiveis.acquire(timeout=0.12):
                continue

            with self.condicao:
                if self.cancelado.is_set():
                    self.vagas_disponiveis.release()
                    return
                if not self.fila:
                    self.vagas_disponiveis.release()
                    continue

                # Priority é a regra principal; SJF e FCFS são desempates.
                selecionado = min(self.fila, key=chave_escalonamento)
                concorrente = min(
                    (carro for carro in self.fila if carro is not selecionado),
                    key=chave_escalonamento,
                    default=None,
                )
                if concorrente is None:
                    criterio = "Único carro na fila"
                    explicacao = "Nenhum outro carro aguardava"
                elif selecionado.prioridade != concorrente.prioridade:
                    criterio = "PRIORITY"
                    explicacao = f"P{selecionado.prioridade} antes de P{concorrente.prioridade}"
                elif selecionado.duracao != concorrente.duracao:
                    criterio = "SJF"
                    explicacao = f"{selecionado.duracao}s antes de {concorrente.duracao}s"
                else:
                    criterio = "FCFS"
                    explicacao = (
                        f"chegada {selecionado.ordem_chegada} antes de "
                        f"{concorrente.ordem_chegada}"
                    )

                decisao = {
                    "carro": selecionado.numero,
                    "prioridade": selecionado.prioridade,
                    "duracao": selecionado.duracao,
                    "ordem": selecionado.ordem_chegada,
                    "criterio": criterio,
                    "explicacao": explicacao,
                    "concorrente": (
                        {
                            "carro": concorrente.numero,
                            "prioridade": concorrente.prioridade,
                            "duracao": concorrente.duracao,
                            "ordem": concorrente.ordem_chegada,
                        } if concorrente else None
                    ),
                    "candidatos": (
                        [
                            (carro.numero, *chave_escalonamento(carro))
                            for carro in self.fila
                        ] if self.config.modo_demonstracao else None
                    ),
                }
                self.ultima_decisao = decisao
                self.historico_decisoes.append(decisao)

                self.fila.remove(selecionado)
                selecionado.escolhido = True
                self.reservas_semaforo += 1

                if self.config.quantidade_carros <= 128 or selecionado.numero % 32 == 0:
                    comparacao = ""
                    if concorrente is not None:
                        comparacao = (
                            f" | versus {concorrente.numero:03d} "
                            f"(P{concorrente.prioridade}, {concorrente.duracao}s)"
                        )
                    self.registrar(
                        "SCHEDULER",
                        f"Carro {selecionado.numero:03d} (P{selecionado.prioridade}, "
                        f"{selecionado.duracao}s) | {criterio}: "
                        f"{explicacao}{comparacao}",
                    )
                    self.registrar(
                        "SEMAFORO",
                        f"Vaga reservada para o Carro {selecionado.numero:03d}",
                    )
                selecionado.autorizado.set()

            # Garante ordem de admissão e manobras não simultâneas.
            while not selecionado.estacionado.wait(timeout=0.12):
                if self.cancelado.is_set():
                    return

    def _supervisionar(self):
        # Aguarda o produtor e o escalonador terminarem.
        self._threads_sistema[0].join()
        self._threads_sistema[1].join()
        with self.condicao:
            carros = list(self.carros)
        for carro in carros:
            carro.join()
        if not self.cancelado.is_set():
            with self.condicao:
                self.finalizada = True
            self.registrar("SISTEMA", "Todos os carros foram atendidos. Simulação concluída")

    def snapshot(self) -> dict[str, Any]:
        with self.condicao:
            agora = time.monotonic()
            # Ordenação apenas para visualização: a seleção utiliza a mesma chave.
            fila_ordenada = sorted(self.fila, key=chave_escalonamento)
            vagas = []
            for i, carro in enumerate(self.estacionamento.vagas, start=1):
                if carro is None:
                    vagas.append({"numero": i, "carro": None})
                else:
                    restante = max(
                        0.0,
                        carro.duracao - (agora - (carro.entrada_em or agora)) * self.config.velocidade,
                    )
                    vagas.append({
                        "numero": i,
                        "carro": carro.numero,
                        "perfil": carro.perfil,
                        "duracao": carro.duracao,
                        "restante": restante,
                        "manobra": carro.numero == self.em_manobra,
                    })
            ocupadas = sum(item["carro"] is not None for item in vagas)
            return {
                "vagas": vagas,
                "ocupadas": ocupadas,
                "capacidade": self.config.quantidade_vagas,
                "criados": self.criados,
                "entraram": self.entraram,
                "concluidos": self.concluidos,
                "fila_total": len(self.fila),
                "fila": [
                    {
                        "numero": carro.numero,
                        "perfil": carro.perfil,
                        "prioridade": carro.prioridade,
                        "duracao": carro.duracao,
                        "ordem": carro.ordem_chegada,
                    }
                    for carro in fila_ordenada[:12]
                ],
                "espera_media": self.tempo_espera_total / self.entraram if self.entraram else 0.0,
                "maior_fila": self.max_fila,
                "erros": self.erros,
                "manobra": self.em_manobra,
                "producao_concluida": self.producao_concluida,
                "finalizada": self.finalizada,
                "segundos": agora - self.iniciada_em,
                "semaforo_livres": max(
                    0, self.config.quantidade_vagas - ocupadas - self.reservas_semaforo
                ),
                "semaforo_reservadas": self.reservas_semaforo,
                "max_manobras_simultaneas": self.max_manobras_simultaneas,
                "ultima_decisao": self.ultima_decisao,
                "modo_demonstracao": self.config.modo_demonstracao,
            }
