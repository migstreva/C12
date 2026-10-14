# ParkFlow — Estacionamento multithread (etapa 2)

Simulador educacional em **Python + Tkinter**, construído sobre a primeira etapa do projeto de Sistemas Operacionais. Mantém o mapa de vagas com rolagem, a Ready Queue central e os eventos à direita. A interface usa somente a biblioteca padrão do Python.

## Executar no VS Code

Abra a pasta `ParkFlow` e execute no terminal:

```bash
python main.py
```

No Windows, também é possível executar `executar.bat`. Requer Python 3.10+ e Tkinter. Para executar os testes:

```bash
python -m unittest test_simulacao.py -v
```

## Como demonstrar ao professor

### Cenário **Demonstração** (recomendado)

No seletor **CENÁRIO**, escolha **Demonstração**. O programa configura automaticamente **8 carros e 1 vaga**. Clique em **INICIAR SIMULAÇÃO** e observe:

- A Ready Queue mostra a **prioridade P1/P2/P3**, a **duração prevista em segundos simulados** e a **ordem de chegada**.
- O quadro **Última decisão do escalonador** mostra o carro selecionado, o critério decisivo (**PRIORITY**, **SJF** ou **FCFS**) e uma comparação com o segundo candidato.
- Os eventos **SCHEDULER**, **SEMAFORO** e **MUTEX** deixam registrado quando houve escolha, reserva/liberação de permissão e entrada/saída da seção crítica.
- No mapa, **MANOBRANDO** sinaliza que uma thread executa a manobra protegida; o indicador de mutex informa seu estado, e o semáforo exibe permissões livres e reservadas.

**Sequência esperada no cenário demonstrativo:** `001 → 004 → 005 → 003 → 006 → 007 → 008 → 002`.

O Carro 001 começa primeiro e ocupa a única vaga. Enquanto ele permanece estacionado, os outros sete carros entram na fila, com dados fixos:

| Carro | Perfil | Prioridade | Duração prevista | Chegada |
|---|---|---|---|---|
| 001 | Comum | P3 | 9 s | 1 |
| 002 | Comum | P3 | 5 s | 2 |
| 003 | PCD | P1 | 8 s | 3 |
| 004 | PCD | P1 | 4 s | 4 |
| 005 | PCD | P1 | 4 s | 5 |
| 006 | Idoso | P2 | 3 s | 6 |
| 007 | Idoso | P2 | 7 s | 7 |
| 008 | Comum | P3 | 3 s | 8 |

Depois da saída do 001, a escolha do 004 antes do 005 mostra **FCFS** (mesma prioridade e duração); a escolha do 005 antes do 003 mostra **SJF** (ambos P1, mas o 005 tem duração menor); a escolha do 003 antes do 006 mostra **Priority Scheduling** (P1 antes de P2 apesar de durar mais).

A interface mostra o **último critério decisivo**, comparando com o próximo candidato. O escalonamento completo segue sempre a chave `(prioridade, duração prevista, ordem de chegada)`.

### Cenário **Aleatório**

Para voltar ao funcionamento livre, selecione **Aleatório**, escolha o número de carros e de vagas e inicie a simulação. O perfil e a duração de cada carro são sorteados. Testes muito grandes (512–2048 threads reais) podem atingir limites do sistema operacional. Prefira 16–32 carros para demonstrações ao vivo.

## O que cada técnica faz

- **Ready Queue simulada:** lista interna dos carros que chegaram e ainda aguardam. **Não** é a Ready Queue do kernel.
- **Priority Scheduling:** prioridade P1 (PCD) antes de P2 (idoso), antes de P3 (comum). É uma regra **didática** do simulador, não uma regra legal de estacionamento.
- **SJF:** decide entre carros com a mesma prioridade, preferindo a menor **duração simulada de permanência no estacionamento**. Essa duração não é tempo real de CPU (*CPU burst*); é uma aproximação didática. O escalonamento é **não preemptivo**.
- **FCFS:** decide entre carros de prioridade **e duração iguais**, escolhendo aquele de chegada anterior.
- **Semáforo de contagem:** `threading.Semaphore(quantidade_vagas)` limita as permissões de ocupação. Uma permissão é reservada antes de selecionar/admitir o carro e devolvida ao sair.
- **Mutex / seção crítica:** `threading.Lock()` protege as modificações nas vagas, inclusive a manobra; não fica retido enquanto o carro permanece estacionado.
- **Condition / Event:** o escalonador aguarda a chegada de carros e cada carro aguarda sua autorização sem espera ocupada.

### Indicadores e interpretação

**SEMÁFORO X/Y permissões livres** mostra capacidade ainda não ocupada nem reservada; **reservadas** são permissões obtidas pelo escalonador, mas ainda não convertidas em ocupação física.

**MUTEX em uso/livre** e **pico de manobras simultâneas** mostram o estado da região de manobra. O pico esperado é 1. O escalonador também serializa o início das manobras: portanto, o indicador sozinho não prova o efeito isolado do mutex; a proteção aparece no código e é verificada por testes.

**INCONSISTÊNCIAS** deve permanecer em 0. **ESPERA MÉDIA (REAL)** utiliza segundos do relógio real; já a duração prevista e o tempo restante das vagas são **segundos simulados**, acelerados pelo fator selecionado (por exemplo, 9 s simulados levam aproximadamente 3 s reais em 3x).

## Testes de verificação

O arquivo `test_simulacao.py` verifica ordenação Priority/SJF/FCFS, sequência prevista no modo demonstração, respeito à capacidade e às reservas do semáforo, ocupação consistente, manobras não simultâneas e finalização/cancelamento das threads. Esses testes complementam a demonstração visual.

## Arquivos

- `main.py`: interface Tkinter em três colunas e atualização periódica dos estados.
- `simulacao.py`: threads, Ready Queue, escalonador, semáforo, mutex, logs e cenários.
- `test_simulacao.py`: testes automatizados do motor.
- `versao_1.py`: versão original desorganizada, mantida para comparação; usa Matplotlib.
- `preview.png`: captura da interface com o modo demonstração em execução.

Para usar `versao_1.py`, instale `matplotlib` (`pip install matplotlib`). A segunda versão **não precisa de bibliotecas externas**.
