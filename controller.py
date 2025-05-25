from view import View
from model import Model
import queue

class Controller:
    def __init__(self):
        self.process_queue = queue.Queue()
        self.specific_process_queue = queue.Queue()
        self.specific_process_req_queue = queue.Queue()
        self.view = View(self.specific_process_req_queue)
        self.model = Model(self.process_queue, self.specific_process_queue, self.specific_process_req_queue)
        self.model.start_processes_thread()
        self.model.start_specific_processes_thread()
        self.queue_check()

    def queue_check(self):
        try:
            processes = self.process_queue.get_nowait()
            specific_processes = self.specific_process_queue.get_nowait()
            self.view.update_data(processes, specific_processes)
        except queue.Empty:
            pass
        self.view.root.after(1000, self.queue_check)

    # def get_data(self):
    #     print("Fetching data from model...")
    #     self.data = self.model.get_pids()
    
    # def update_view(self):
    #     print("Starting update view thread...")
    #     while True:
    #         self.view.update_process_list(self.data)

    def run(self):
        self.view.run()
        self.model.stop_processes_thread()
        self.model.stop_specific_processes_thread()
    
if __name__ == "__main__":
    controller = Controller()
    controller.run()