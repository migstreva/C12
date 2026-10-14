"""Testes rápidos do motor, sem abrir a interface gráfica."""

import time
import unittest
from types import SimpleNamespace

from simulacao import Configuracao, Simulacao, chave_escalonamento


class TestesDoEstacionamento(unittest.TestCase):
    def aguardar(self, simulacao, limite=15):
        inicio = time.monotonic()
        while time.monotonic() - inicio < limite:
            atual = simulacao.snapshot()
            if atual["finalizada"]:
                return atual
            time.sleep(0.025)
        simulacao.parar()
        self.fail("A simulação não terminou dentro do prazo")

    def test_ordem_priority_sjf_fcfs(self):
        candidatos = [
            SimpleNamespace(numero=1, prioridade=3, duracao=3, ordem_chegada=1),
            SimpleNamespace(numero=2, prioridade=1, duracao=8, ordem_chegada=2),
            SimpleNamespace(numero=3, prioridade=2, duracao=4, ordem_chegada=3),
            SimpleNamespace(numero=4, prioridade=1, duracao=4, ordem_chegada=4),
            SimpleNamespace(numero=5, prioridade=1, duracao=4, ordem_chegada=5),
        ]
        ordenados = sorted(candidatos, key=chave_escalonamento)
        self.assertEqual([carro.numero for carro in ordenados], [4, 5, 2, 3, 1])

    def test_24_carros_3_vagas_sem_colisao(self):
        sim = Simulacao(Configuracao(
            quantidade_carros=24, quantidade_vagas=3,
            velocidade=30, intervalo_chegada=0.008, semente=42,
        ))
        sim.iniciar()
        resultado = self.aguardar(sim)
        self.assertEqual(resultado["criados"], 24)
        self.assertEqual(resultado["entraram"], 24)
        self.assertEqual(resultado["concluidos"], 24)
        self.assertEqual(resultado["erros"], 0)
        self.assertEqual(resultado["ocupadas"], 0)
        self.assertEqual(resultado["fila_total"], 0)
        self.assertGreaterEqual(resultado["maior_fila"], 1)

    def test_prioridade_sjf_fcfs_no_scheduler(self):
        # Reserva única vaga; enfileira três carros antes de ela ser liberada.
        sim = Simulacao(Configuracao(
            quantidade_carros=8, quantidade_vagas=1, velocidade=15,
            intervalo_chegada=0.002, semente=3,
        ))
        sim.iniciar()
        resultado = self.aguardar(sim)
        self.assertEqual(resultado["concluidos"], 8)
        self.assertEqual(resultado["erros"], 0)
        logs = []
        while not sim.eventos.empty():
            logs.append(sim.eventos.get_nowait())
        self.assertTrue(any(tipo == "SCHEDULER" for _, tipo, _ in logs))

    def test_cenario_didatico_comprova_priority_sjf_fcfs(self):
        sim = Simulacao(Configuracao(
            quantidade_carros=8, quantidade_vagas=1,
            velocidade=35, modo_demonstracao=True,
        ))
        sim.iniciar()
        resultado = self.aguardar(sim)

        self.assertEqual(resultado["erros"], 0)
        self.assertEqual(resultado["concluidos"], 8)
        self.assertEqual(resultado["max_manobras_simultaneas"], 1)
        self.assertEqual(resultado["semaforo_livres"], 1)
        self.assertEqual(resultado["semaforo_reservadas"], 0)
        self.assertEqual(
            [d["carro"] for d in sim.historico_decisoes],
            [1, 4, 5, 3, 6, 7, 8, 2],
        )
        self.assertEqual(
            [d["criterio"] for d in sim.historico_decisoes[1:4]],
            ["FCFS", "SJF", "PRIORITY"],
        )
        for decisao in sim.historico_decisoes:
            self.assertEqual(
                min(decisao["candidatos"], key=lambda item: item[1:])[0],
                decisao["carro"],
            )

    def test_semaforo_nunca_ultrapassa_capacidade(self):
        sim = Simulacao(Configuracao(
            quantidade_carros=48, quantidade_vagas=3,
            velocidade=30, intervalo_chegada=0.006, semente=77,
        ))
        sim.iniciar()
        limite = time.monotonic() + 15
        while time.monotonic() < limite:
            d = sim.snapshot()
            self.assertLessEqual(d["ocupadas"] + d["semaforo_reservadas"], 3)
            self.assertGreaterEqual(d["semaforo_livres"], 0)
            self.assertLessEqual(d["max_manobras_simultaneas"], 1)
            if d["finalizada"]:
                break
            time.sleep(0.005)
        else:
            sim.parar()
            self.fail("A simulação excedeu o tempo limite")
        self.assertEqual(d["concluidos"], 48)
        self.assertEqual(d["erros"], 0)
        self.assertEqual(d["semaforo_livres"], 3)

    def test_cancelar_nao_prende_threads(self):
        sim = Simulacao(Configuracao(
            quantidade_carros=64, quantidade_vagas=2, velocidade=1,
            intervalo_chegada=0.003,
        ))
        sim.iniciar()
        time.sleep(0.1)
        sim.parar()
        for thread in sim._threads_sistema:
            thread.join(timeout=4)
            self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
