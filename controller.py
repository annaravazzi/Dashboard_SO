from view import View
from model import Model
import queue

class Controller:
    """
    Controller class to manage the interaction between the View and Model.
    It initializes the model and view, starts the necessary threads, and handles the data flow betweem them.
    """
    def __init__(self):
        # Queue for general process data (from model to view)
        self.process_queue = queue.Queue()
        # Queue for specific process data (from model to view)
        self.specific_process_queue = queue.Queue()
        # Queue for specific process requests (from view to model)
        self.specific_process_req_queue = queue.Queue()
        # Queue for general statistics data (from model to view)
        self.general_stats_queue = queue.Queue()
        # Initialize the view and model
        self.view = View(self.specific_process_req_queue)
        self.model = Model(self.process_queue, self.specific_process_queue, self.specific_process_req_queue, self.general_stats_queue)
        # Start the model's threads to fetch data
        self.model.start_processes_thread()
        self.model.start_specific_processes_thread()
        # self.model.start_general_stats_thread()
        # Schedule the queue check to update the view with data from the model
        self.queue_check()

    def queue_check(self):
        """
        Check the queues using a non-blocking method (so the GUI stays active) to get new data and update the view.
        This method is called periodically (100ms).
        """
        try:
            # Get data from the process queue, specific process queue and general stats queue
            processes = self.process_queue.get_nowait()
            specific_processes = self.specific_process_queue.get_nowait()
            # general_stats = self.general_stats_queue.get_nowait()
            self.view.update_data(processes, specific_processes)
            # self.view.update_data(processes, specific_processes, general_stats)
        except queue.Empty:
            pass
        # Schedule the next queue check
        self.view.root.after(100, self.queue_check)

    def run(self):
        """
        Run the main loop of the view to start the GUI application.
        This method will block until the GUI is closed.
        """
        self.view.run()
        # Stop the model's threads when the GUI is closed
        self.stop_threads()
    
    def stop_threads(self):
        """
        Stop the model's threads gracefully.
        This method is called when the GUI is closed to ensure that all threads are stopped.
        """
        self.model.stop_processes_thread()
        self.model.stop_specific_processes_thread()
        # self.model.stop_general_stats_thread()