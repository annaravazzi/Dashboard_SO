import tkinter as tk
import ttkbootstrap as ttk

class View:
    """
    View class to create the GUI for the operating system dashboard separated from the data fetching model.
    The view displays general stats data from the OS and the list of processes, and allows the user to see details of a specific process.
    """
    def __init__ (self, specific_process_req_queue):
        # Initialize the main window
        self.root = ttk.Window(themename="darkly")
        self.root.title("Operating System Dashboard")
        self.root.geometry("1120x630")

        # Create a notebook (for tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True)

        # Dictionary to hold general process data {pid: [pid, name, user, memory, cpu, status]}
        self.process_data_dict = {}
        # Dictionary to hold specific process data {pid: [pid, name, user, memory, cpu, status]}
        self.specific_process_data_dict = {}
        # List of general stats data (CPU usage, memory usage, etc.)
        # self.general_stats_data = []

        # Dict to hold the opened tabs for specific processes {pid: tab_id}
        self.processes_opened_tabs = {}
        # Dict to hold the treeviews for threads in opened tabs {tab_id: treeview}
        self.threads_treeviews = {}
        # Dict to hold the treeviews for process data {tab_id: treeview}
        self.process_data_treeviews = {}

        # Queue for specific process requests
        self.specific_process_req_queue = specific_process_req_queue

        # Create process list tab
        self.create_process_list_tab()
        # Create general stats tab
        # self.create_general_stats_tab()

    def create_process_list_tab(self):
        """
        Create a tab for displaying the process list.
        """
        # Create frame
        process_list_tab = ttk.Frame(self.notebook)
        self.notebook.add(process_list_tab, text="All Processes")

        # Create and configure treeview for the table
        self.process_list_tree = ttk.Treeview(process_list_tab, 
                                              columns=('PID', 'Name', 'User', 'Memory', 'CPU(%)', 'State'), 
                                              show='headings', bootstyle='DARK')
        self.process_list_tree.heading('PID', text='PID', anchor='w')
        self.process_list_tree.heading('Name', text='Name', anchor='w')
        self.process_list_tree.heading('User', text='User', anchor='w')
        self.process_list_tree.heading('Memory', text='Memory', anchor='w')
        self.process_list_tree.heading('CPU(%)', text='CPU(%)', anchor='w')
        self.process_list_tree.heading('State', text='State', anchor='w')
        self.process_list_tree.column('PID', width=50)
        self.process_list_tree.column('Name', width=150)
        self.process_list_tree.column('User', width=100)
        self.process_list_tree.column('Memory', width=100)
        self.process_list_tree.column('CPU(%)', width=100)
        self.process_list_tree.column('State', width=100)

        self.process_list_tree.tag_configure("evenrow", background="#222222")
        self.process_list_tree.tag_configure("oddrow", background="#303030")

        # Add scrollbar
        scrollbar = ttk.Scrollbar(process_list_tab, orient=tk.VERTICAL, command=self.process_list_tree.yview)
        self.process_list_tree.configure(yscroll=scrollbar.set)
        self.process_list_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')

        # Configure grid layout
        process_list_tab.grid_columnconfigure(0, weight=1)
        process_list_tab.grid_rowconfigure(0, weight=1)

        # Bind double click event (to open process details)
        self.process_list_tree.bind('<Double-1>', self.create_specific_process_tab)
    
    def create_general_stats_tab(self):
        pass

    def update_data(self, processes_data, specific_process_data, general_stats_data=None):
        """
        Update all data in the view.
        This method is called periodically in the controller to refresh the data displayed in the GUI.
        """
        
        self.process_data_dict = processes_data
        self.specific_process_data_dict = specific_process_data
        # self.general_stats_data = general_stats_data

        # process_data_list = list(self.process_data_dict.values())
        # self.update_process_list_view(process_data_list)

        # Update the tabs
        if self.process_data_dict:
            self.update_process_list_view(list(self.process_data_dict.values()))

        # Check all process-specific tabs
        if self.specific_process_data_dict and self.processes_opened_tabs:
            opened_tabs = self.processes_opened_tabs.copy()
            for pid, tab_id in opened_tabs.items():
                if pid in self.specific_process_data_dict and self.specific_process_data_dict[pid]:
                    if all(data is not None for data in self.specific_process_data_dict[pid]):
                        self.update_specific_process_tab(tab_id, self.specific_process_data_dict[pid])
                    else:
                        # If there's no data for the process, close the tab
                        self.close_tab(tab_id, pid, req=True)
            # if pid in self.specific_process_data_dict:  # Check if there's data for the process
            #     # Update the tab with the new process data
            #     self.update_specific_process_tab(tab_id, self.specific_process_data_dict[pid])
            # else:
                
            #     if self.specific_process_req_queue.empty(): # Check if there's no data because the new request wasn't received yet
            #         self.close_tab(tab_id, pid, req=False)
                # Raise an error if the process is not available anymore
                # self.error_box(tab_id, "Process " + str(pid) + "doesn't exist anymore", pid)


        # if specific_process_data:
        #     # Update the opened tabs for each process
        #     for tab in self.notebook.tabs():
        #         tab_id = self.notebook.tab(tab, "text")
        #         if tab_id.startswith("Process "):
        #             process_id = int(tab_id.split(" ")[1])
        #             if process_id in specific_process_data:
        #                 # Update the tab with the new process data
        #                 self.update_specific_process_tab(self.notebook.nametowidget(tab), specific_process_data[process_id])
        #             else:
        #                 self.close_tab(tab)  # Close the tab if the process is no longer available

    def update_process_list_view(self, process_data):
        """
        Update the general process list tab with the current data.
        """

        # To preserve the scroll position and selected item
        current_position = self.process_list_tree.yview()[0]
        selected_item = self.process_list_tree.focus()
        selected_text = self.process_list_tree.item(selected_item) if selected_item else None

        # Clear existing data
        for item in self.process_list_tree.get_children():
            self.process_list_tree.delete(item)

        # Insert new data
        for idx, process in enumerate(process_data):
            self.process_list_tree.insert('', tk.END, values=process, tags=("evenrow" if idx % 2 == 0 else "oddrow",))
            # Restore the selection
            if selected_text and process[0] == selected_text['values'][0]:
                self.process_list_tree.selection_set(self.process_list_tree.get_children()[idx])
                self.process_list_tree.focus(self.process_list_tree.get_children()[idx])
                self.process_list_tree.see(self.process_list_tree.get_children()[idx])
                
        # Restore the scroll position
        self.process_list_tree.yview_moveto(current_position)

    # TODO: add more specific data
    def update_specific_process_tab(self, tab_id, process_data):
        """
        Update the specific process tab with new data.
        """
        # Clear process treeview
        if tab_id not in self.process_data_treeviews or all(data is None for data in process_data):
            return
        # if tab_id not in self.process_data_threeviews or tab_id not in self.threads_threeviews or not process_data:
        #     return
        
        process_data_treeview = self.process_data_treeviews[tab_id]
        # Clear existing data in the treeview
        for item in process_data_treeview.get_children():
            process_data_treeview.delete(item)
        # Insert new data into the treeview
        fields = ['Name', 'Username', 'CPU(%)', 'Status', 'Number of Threads',
                  'Priority', 'Nice', 'Run Time', 'Resident Set', 'Resident Set (pages)', 
                  'Virtual Memory', 'Virtual Memory (pages)', 'Text Segment Size', 'Data Segment Size',
                  'Stack Segment Size']
        values = [process_data[1], process_data[2], process_data[3], process_data[4], 
                    process_data[5], process_data[6], process_data[7], process_data[8], 
                    process_data[9], process_data[10], process_data[11], process_data[12], 
                    process_data[13], process_data[14], process_data[15]]
        for field, value in zip(fields, values):
            process_data_treeview.insert('', tk.END, values=(field, value), 
                                         tags=("evenrow" if fields.index(field) % 2 == 0 else "oddrow",))
        # Update the process data treeview
        process_data_treeview.pack(fill=tk.BOTH, expand=True)

        # Clear threads treeview
        threads_treeview = self.threads_treeviews[tab_id]
        # Clear existing data in the threads treeview
        for item in threads_treeview.get_children():
            threads_treeview.delete(item)
        # Insert new data into the threads treeview
        for idx, thread in enumerate(process_data[16]):
            threads_treeview.insert('', tk.END, values=(thread[0], thread[1], thread[2], 
                                                        thread[3], thread[4], thread[5]), 
                                                        tags=("evenrow" if idx % 2 == 0 else "oddrow",))
        # Update the threads treeview
        # threads_treeview.pack(fill=tk.BOTH, expand=True)

        # # # Clear existing data in the tab
        # # for widget in tab.winfo_children():
        # #     widget.destroy()

        
        # tab = self.notebook.nametowidget(tab_id)
        # for widget in tab.winfo_children():
        #     if isinstance(widget, tk.Text):
        #         widget.destroy()
        
        # # Clear existing treeview in the tab

        # # Add process details
        # if process_data:
        #     details_text = tk.Text(tab, wrap=tk.WORD)
        #     details_text.insert(tk.END, f"Name: {process_data[1]}\n"
        #                                 f"User: {process_data[2]}\n"
        #                                 f"Memory: {process_data[3]}\n"
        #                                 f"CPU: {process_data[4]}\n"
        #                                 f"Status: {process_data[5]}")
        #     details_text.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        #     details_text.config(state=tk.DISABLED)
        # # else:
        # #     # If the process is not available anymore
        # #     old_pid = self.notebook.tab(tab, ('text')).split(" ")[1]
        # #     self.close_tab(tab, old_pid, req=False)
        # #     # self.error_box(tab, "Process " + str(old_pid) + "doesn't exist anymore", old_pid)

    def create_specific_process_tab(self, event):
        """
        Handle double-click event on the process list.
        Create a new tab with process details.
        """
        # Get the selected process
        selected_process = self.process_list_tree.selection()
        if not selected_process:
            return
        process = self.process_list_tree.item(selected_process)
        process_info = process['values']

        if process_info and process_info[0] in self.processes_opened_tabs:
            # If the tab already exists, select it
            # tab = self.processes_opened_tabs[process_info[0]]
            # print(tab)
            self.notebook.select(self.processes_opened_tabs[process_info[0]])
            return
        
        # Create a new tab for process details
        details_tab = ttk.Frame(self.notebook)
        self.processes_opened_tabs[process_info[0]] = details_tab  # Store the tab for later updates
        self.notebook.add(details_tab, text=f"Process {process_info[0]}")
        self.notebook.select(details_tab)
        close_btn = ttk.Button(details_tab, text="Close Tab", command=lambda: self.close_tab(details_tab, process_info[0], req=True))
        close_btn.pack(side=tk.BOTTOM, pady=10)

        label = tk.Label(details_tab, text=f"Details for Process ID: {process_info[0]}")
        label.pack(pady=10)

        # For the process data
        left_frame = ttk.Frame(details_tab)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        proc_label_frame = ttk.Labelframe(left_frame, text="Process data", padding=(5, 2))
        proc_label_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        process_data_treeview = ttk.Treeview(proc_label_frame, columns=('Field', 'Value'), show='', bootstyle='DARK')

        fields = ['Name', 'Username', 'CPU(%)', 'Status', 'Number of Threads',
                  'Priority', 'Nice', 'Run Time', 'Resident Set', 'Resident Set (pages)', 
                  'Virtual Memory', 'Virtual Memory (pages)', 'Text Segment Size', 'Data Segment Size',
                  'Stack Segment Size']
        for field in fields:
            process_data_treeview.insert('', tk.END, values=(field, ''))

        process_data_treeview.tag_configure("evenrow", background="#222222")
        process_data_treeview.tag_configure("oddrow", background="#303030")
        for idx, field in enumerate(fields):
            process_data_treeview.insert('', tk.END, values=(field, ''), tags=("evenrow" if idx % 2 == 0 else "oddrow",))
        
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(0, weight=1)

        self.process_data_treeviews[details_tab] = process_data_treeview  # Store the treeview for later updates

        # For the threads
        right_frame = ttk.Frame(details_tab)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, expand=True)

        thr_label_frame = ttk.Labelframe(right_frame, text="Threads", padding=(5, 2))
        thr_label_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        # set fixed height for the label
        
        # thr_label.pack(pady=10)

        threads_treeview = ttk.Treeview(thr_label_frame,columns=('TID', 'Name', 'User', 'Mem', 'CPU', 'State'), 
                                                        show='headings', bootstyle='DARK')
        threads_treeview.heading('TID', text='TID', anchor='w')
        threads_treeview.heading('Name', text='Name', anchor='w')
        threads_treeview.heading('User', text='User', anchor='w')
        threads_treeview.heading('Mem', text='Memory', anchor='w')
        threads_treeview.heading('CPU', text='CPU(%)', anchor='w')
        threads_treeview.heading('State', text='State', anchor='w')
        threads_treeview.column('TID', width=60)
        threads_treeview.column('Name', width=130)
        threads_treeview.column('User', width=100)
        threads_treeview.column('Mem', width=90)
        threads_treeview.column('CPU', width=65)
        threads_treeview.column('State', width=100)
        threads_treeview.tag_configure("evenrow", background="#222222")
        threads_treeview.tag_configure("oddrow", background="#303030")

        scrollbar = ttk.Scrollbar(thr_label_frame, orient=tk.VERTICAL, command=threads_treeview.yview)
        threads_treeview.configure(yscroll=scrollbar.set)
        threads_treeview.grid(row=1, column=0, sticky='nsew')
        scrollbar.grid(row=1, column=1, sticky='ns')

        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=1)
        self.threads_treeviews[details_tab] = threads_treeview  # Store the treeview for later updates


        self.specific_process_req_queue.put((process_info[0], 'add'))  # Request specific process details

        # self.update_specific_process_tab(details_tab, process_info)

        # # Add process details
        # details_text = tk.Text(details_tab, wrap=tk.WORD)
        # details_text.insert(tk.END, f"Name: {process_info[1]}\n"
        #                               f"User: {process_info[2]}\n"
        #                               f"Memory: {process_info[3]}\n"
        #                               f"CPU: {process_info[4]}\n"
        #                               f"Status: {process_info[5]}")
        # details_text.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        # details_text.config(state=tk.DISABLED)

        # Add close button

    def close_tab(self, tab, pid, req=True):
        """
        Close the specified tab.
        """
        if req:
            self.specific_process_req_queue.put((pid, 'remove'))
        self.processes_opened_tabs.pop(pid, None)  # Remove the tab from the dictionary
        try:
            self.notebook.forget(tab)
        except tk.TclError:
            # If the tab is already closed or doesn't exist
            return
    
    # def error_box(self, tab, message, pid):
    #     """
    #     Show an error message box.
    #     """
    #     messagebox.showerror("Error", message)
    #     self.close_tab(tab, pid)

    def run(self):
        """
        Run the Tkinter main loop.
        """
        self.root.mainloop()

    # def close(self):
    #     """
    #     Close the Tkinter window.
    #     """
    #     self.root.destroy()