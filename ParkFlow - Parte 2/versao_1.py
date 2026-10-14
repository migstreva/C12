import threading
import time
import random
import matplotlib.pyplot as plt


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
    def __init__(self, nome, estacionamento, mostrar_detalhes=False):
        super().__init__()

        self.nome = nome
        self.estacionamento = estacionamento
        self.mostrar_detalhes = mostrar_detalhes

        self.colisao = False
        self.inconsistencia = False
        self.sem_vaga = False

    def run(self):
        time.sleep(random.uniform(0.01, 0.15))

        if self.mostrar_detalhes:
            print(f"[CHEGADA] {self.nome} chegou ao estacionamento.")

        vaga = self.estacionamento.procurar_vaga()

        if vaga is None:
            self.sem_vaga = True

            if self.mostrar_detalhes:
                print(
                    f"[SEM VAGA] {self.nome} "
                    f"não encontrou vaga e foi embora."
                )

            return

        if self.mostrar_detalhes:
            print(
                f"[BUSCA] {self.nome} encontrou "
                f"a vaga {vaga + 1} livre."
            )

        time.sleep(random.uniform(0.05, 0.20))

        if self.estacionamento.vagas[vaga] is not None:
            self.colisao = True

            if self.mostrar_detalhes:
                print(
                    f"[CONFLITO] {self.nome} tentou entrar "
                    f"na vaga {vaga + 1}, mas ela já estava "
                    f"ocupada por {self.estacionamento.vagas[vaga]}."
                )

        self.estacionamento.vagas[vaga] = self.nome

        if self.mostrar_detalhes:
            print(
                f"[ENTRADA] {self.nome} entrou "
                f"na vaga {vaga + 1}."
            )

            self.estacionamento.mostrar_vagas()

        tempo_estacionado = random.uniform(0.1, 0.3)

        if self.mostrar_detalhes:
            print(
                f"[ESTACIONADO] {self.nome} ficará "
                f"na vaga {vaga + 1} por "
                f"{tempo_estacionado:.2f} segundos."
            )

        time.sleep(tempo_estacionado)

        ocupante_atual = self.estacionamento.vagas[vaga]

        if ocupante_atual != self.nome:
            self.inconsistencia = True

            if self.mostrar_detalhes:
                print("\n********** INCONSISTENCIA **********")
                print(
                    f"{self.nome} acredita estar "
                    f"na vaga {vaga + 1}."
                )
                print(
                    f"Mas atualmente a vaga contém: "
                    f"{ocupante_atual}"
                )
                print("************************************\n")

        if self.mostrar_detalhes:
            print(
                f"[SAIDA] {self.nome} está saindo "
                f"da vaga {vaga + 1}."
            )

        self.estacionamento.vagas[vaga] = None

        if self.mostrar_detalhes:
            self.estacionamento.mostrar_vagas()


def executar_simulacao(
    quantidade_vagas,
    quantidade_carros,
    mostrar_detalhes=False
):
    estacionamento = Estacionamento(quantidade_vagas)
    carros = []

    if mostrar_detalhes:
        print("\n========================================")
        print(
            f"      SIMULACAO COM "
            f"{quantidade_carros} THREADS"
        )
        print("========================================")

        estacionamento.mostrar_vagas()

    for i in range(1, quantidade_carros + 1):
        carro = Carro(
            f"Carro {i}",
            estacionamento,
            mostrar_detalhes
        )

        carros.append(carro)

        try:
            carro.start()
        except RuntimeError:
            print(
                f"\n[LIMITE DO SISTEMA] Não foi possível iniciar "
                f"a thread do Carro {i}."
            )
            print(
                "O sistema atingiu o limite de criação de threads."
            )

            carros.remove(carro)
            break

    for carro in carros:
        carro.join()

    colisoes = 0
    inconsistencias = 0
    sem_vaga = 0

    for carro in carros:
        if carro.colisao:
            colisoes += 1

        if carro.inconsistencia:
            inconsistencias += 1

        if carro.sem_vaga:
            sem_vaga += 1

    if mostrar_detalhes:
        print("\nResultado da simulacao:")
        print(f"Colisoes: {colisoes}")
        print(f"Inconsistencias: {inconsistencias}")
        print(f"Carros sem vaga: {sem_vaga}")

    return colisoes, inconsistencias, sem_vaga


def plotar_grafico(resultados):
    threads = []
    colisoes = []
    inconsistencias = []
    sem_vaga = []

    for resultado in resultados:
        (
            quantidade_threads,
            quantidade_colisoes,
            quantidade_inconsistencias,
            quantidade_sem_vaga
        ) = resultado

        threads.append(quantidade_threads)
        colisoes.append(quantidade_colisoes)
        inconsistencias.append(quantidade_inconsistencias)
        sem_vaga.append(quantidade_sem_vaga)

    plt.figure(figsize=(12, 7))

    plt.plot(
        threads,
        colisoes,
        marker="o",
        label="Colisoes"
    )

    plt.plot(
        threads,
        inconsistencias,
        marker="o",
        label="Inconsistencias"
    )

    plt.plot(
        threads,
        sem_vaga,
        marker="o",
        label="Carros sem vaga"
    )

    plt.title(
        "Impacto do aumento de Threads no Estacionamento"
    )

    plt.xlabel("Quantidade de Threads")
    plt.ylabel("Quantidade de ocorrencias")

    plt.xscale("log", base=2)

    plt.xticks(
        threads,
        [str(valor) for valor in threads]
    )

    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    plt.show()


def main():
    quantidade_vagas = 3

    testes = [2 ** i for i in range(1, 12)]

    mostrar_detalhes = False

    resultados = []

    print("==============================================")
    print("      TESTE DE CONCORRENCIA - ESTACIONAMENTO")
    print("==============================================")
    print(f"Quantidade fixa de vagas: {quantidade_vagas}")
    print("Testes com potencias de 2 ate 2048 threads.")
    print("==============================================")

    for quantidade_carros in testes:
        print(
            f"\nExecutando teste com "
            f"{quantidade_carros} threads..."
        )

        colisoes, inconsistencias, sem_vaga = executar_simulacao(
            quantidade_vagas,
            quantidade_carros,
            mostrar_detalhes
        )

        resultados.append(
            (
                quantidade_carros,
                colisoes,
                inconsistencias,
                sem_vaga
            )
        )

    print("\n\n==============================================")
    print("              RESULTADO FINAL")
    print("==============================================")

    print(
        f"{'THREADS':<10}"
        f"{'COLISOES':<12}"
        f"{'INCONSISTENCIAS':<18}"
        f"{'SEM VAGA':<10}"
    )

    print("-" * 50)

    for resultado in resultados:
        threads, colisoes, inconsistencias, sem_vaga = resultado

        print(
            f"{threads:<10}"
            f"{colisoes:<12}"
            f"{inconsistencias:<18}"
            f"{sem_vaga:<10}"
        )

    print("-" * 50)

    plotar_grafico(resultados)


if __name__ == "__main__":
    main()