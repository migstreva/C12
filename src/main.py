import threading
import time
import random


class Estacionamento:
    def __init__(self, quantidade_vagas):
        self.vagas = [None] * quantidade_vagas

    def procurar_vaga(self):
        for i in range(len(self.vagas)):
            if self.vagas[i] is None:
                return i

        return None

    def mostrar_vagas(self):
        print("\n+----------- ESTACIONAMENTO -----------+")

        for i, carro in enumerate(self.vagas):
            if carro is None:
                print(f"| Vaga {i + 1}: LIVRE")
            else:
                print(f"| Vaga {i + 1}: {carro}")

        print("+--------------------------------------+\n")


class Carro(threading.Thread):
    def __init__(self, nome, estacionamento):
        super().__init__()
        self.nome = nome
        self.estacionamento = estacionamento

    def run(self):
        # Simula tempos diferentes de chegada
        time.sleep(random.uniform(0.5, 2))

        print(f"[CHEGADA] {self.nome} chegou ao estacionamento.")

        vaga = self.estacionamento.procurar_vaga()

        if vaga is None:
            print(f"[SEM VAGA] {self.nome} não encontrou vaga e foi embora.")
            return

        print(f"[BUSCA] {self.nome} encontrou a vaga {vaga + 1} livre.")

        # Delay proposital para gerar problemas entre as threads
        time.sleep(random.uniform(0.5, 1.5))

        self.estacionamento.vagas[vaga] = self.nome

        print(f"[ENTRADA] {self.nome} entrou na vaga {vaga + 1}.")

        self.estacionamento.mostrar_vagas()

        # Tempo que o carro permanece estacionado
        tempo_estacionado = random.uniform(2, 4)

        print(
            f"[ESTACIONADO] {self.nome} ficará na vaga {vaga + 1} "
            f"por {tempo_estacionado:.1f} segundos."
        )

        time.sleep(tempo_estacionado)

        # Apenas identifica o erro, mas não impede que ele aconteça
        ocupante_atual = self.estacionamento.vagas[vaga]

        if ocupante_atual != self.nome:
            print("\n********** INCONSISTENCIA **********")
            print(f"{self.nome} acredita estar na vaga {vaga + 1}.")
            print(f"Mas atualmente a vaga contém: {ocupante_atual}")
            print("************************************\n")

        print(f"[SAIDA] {self.nome} está saindo da vaga {vaga + 1}.")

        # Continua propositalmente incorreto
        self.estacionamento.vagas[vaga] = None

        self.estacionamento.mostrar_vagas()


def main():
    quantidade_vagas = 3
    quantidade_carros = 8

    estacionamento = Estacionamento(quantidade_vagas)

    carros = []

    print("========================================")
    print("       SIMULADOR DE ESTACIONAMENTO")
    print("========================================")
    print(f"Quantidade de vagas: {quantidade_vagas}")
    print(f"Quantidade de carros: {quantidade_carros}")
    print("========================================\n")

    estacionamento.mostrar_vagas()

    for i in range(1, quantidade_carros + 1):
        carro = Carro(f"Carro {i}", estacionamento)

        carros.append(carro)
        carro.start()

    for carro in carros:
        carro.join()

    print("\n========================================")
    print("          SIMULACAO FINALIZADA")
    print("========================================")

    estacionamento.mostrar_vagas()


if __name__ == "__main__":
    main()