from view import View
from model import Model
import queue

class Controller:
    """
    Classe Controller para intermediar a interação entre View e Model.
    Inicializa o Model e a View, inicia as threads e lida com o fluxo de dados.
    """
    def __init__(self):
        # Queue para lista de processos (Model -> View)
        self.process_queue = queue.Queue()
        # Queue para processos especificos (Model -> View)
        self.specific_process_queue = queue.Queue()
        # Queue para requests de processos específicos (View -> Model)
        self.specific_process_req_queue = queue.Queue()
        # Queue para dados gerais de sistema (Model -> View)
        self.general_stats_queue = queue.Queue()

        # Inicializa View e Model
        self.view = View(self.specific_process_req_queue)
        self.model = Model(self.process_queue, self.specific_process_queue, self.specific_process_req_queue, self.general_stats_queue)

        # Inicia threads de data gathering
        self.model.start_processes_thread()
        self.model.start_specific_processes_thread()
        self.model.start_general_stats_thread()

        # Agendar a checagem das queues para atualizar a View com os dados do Model
        self.queue_check()

    def queue_check(self):
        """
        Checa as queues usando um método não-bloqueante (para a GUI permanecer ativa).
        O método é chamado periodicamente (100ms).
        """
        try:
            processes = self.process_queue.get_nowait()
        except queue.Empty:
            processes = None
        try:
            specific_processes = self.specific_process_queue.get_nowait()
        except queue.Empty:
            specific_processes = None
        try:
            general_stats = self.general_stats_queue.get_nowait()
        except queue.Empty:
            general_stats = None
        
        # Se houver dados em pelo menos uma das queues, atualiza a View
        # (se algum for nulo, a View toma conta de não atualizar a tela com ele)
        if processes or specific_processes or general_stats:
        # Atualiza a View com os dados recebidos do Model
            self.view.update_data(processes, specific_processes, general_stats)

        # Agenda próxima checagem das queues
        self.view.root.after(100, self.queue_check)

    def run(self):
        """
        Roda o loop principal da View. Fica bloqueado até a GUI ser fechada, então as threads do Model são fechadas.
        """
        self.view.run()
        self.stop_threads()
    
    def stop_threads(self):
        """
        Para as threads do Model.
        É chamado quando a GUI é fechada.
        """
        self.model.stop_processes_thread()
        self.model.stop_specific_processes_thread()
        self.model.stop_general_stats_thread()