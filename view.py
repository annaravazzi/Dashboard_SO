import tkinter as tk
import ttkbootstrap as ttk

class View:
    def __init__ (self, specific_process_req_queue):
        # Initialize the main window
        self.root = ttk.Window(themename="darkly")
        self.root.title("Operating System Dashboard")
        self.root.geometry("800x600")

        # Create a notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True)

        # Dictionary to hold general process data {pid: [pid, name, user, memory, cpu, status]}
        self.process_data_dict = {}

        # Queue for specific process requests
        self.specific_process_req_queue = specific_process_req_queue

        # Create main tab
        self.create_process_list_tab()

    def create_process_list_tab(self):
        """
        Create a tab for displaying the process list.
        """
        # Create frame for process list tab
        process_list_tab = ttk.Frame(self.notebook)
        self.notebook.add(process_list_tab, text="All Processes")

        # Create and configure treeview for the table
        self.process_list_tree = ttk.Treeview(process_list_tab, 
                                              columns=('PID', 'Name', 'User', 'Memory', 'CPU', 'Status'), 
                                              show='headings', bootstyle='DARK')
        self.process_list_tree.heading('PID', text='PID')
        self.process_list_tree.heading('Name', text='Name')
        self.process_list_tree.heading('User', text='User')
        self.process_list_tree.heading('Memory', text='Memory')
        self.process_list_tree.heading('CPU', text='CPU')
        self.process_list_tree.heading('Status', text='Status')
        self.process_list_tree.column('PID', width=50)
        self.process_list_tree.column('Name', width=150)
        self.process_list_tree.column('User', width=100)
        self.process_list_tree.column('Memory', width=100)
        self.process_list_tree.column('CPU', width=100)
        self.process_list_tree.column('Status', width=100)

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
        self.process_list_tree.bind('<Double-1>', self.on_double_click)

    def update_data(self, processes_data, specific_process_data=None):
        """
        Update the process data dictionary and refresh the process list views.
        """
        self.process_data_dict = {process[0]: process for process in processes_data}

        # Update the process list view (main tab) with the new data
        process_data_list = list(self.process_data_dict.values())
        self.update_process_list_view(process_data_list)

        if specific_process_data:
            # Update the opened tabs for each process
            for tab in self.notebook.tabs():
                tab_id = self.notebook.tab(tab, "text")
                if tab_id.startswith("Process "):
                    process_id = int(tab_id.split(" ")[1])
                    if process_id in specific_process_data:
                        # Update the tab with the new process data
                        self.update_specific_process_tab(self.notebook.nametowidget(tab), specific_process_data[process_id])
                    else:
                        self.close_tab(tab)  # Close the tab if the process is no longer available

    def update_process_list_view(self, process_data):
        """
        Update the treeview with the current process data.
        """

        current_position = self.process_list_tree.yview()[0]
        selected_item = self.process_list_tree.focus()  # Get the focused item's ID
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
                
                

    def update_specific_process_tab(self, tab, process_data):
        """
        Update the specific process tab with new data.
        """
        # # Clear existing data in the tab
        # for widget in tab.winfo_children():
        #     widget.destroy()

        for widget in tab.winfo_children():
            if isinstance(widget, tk.Text):
                widget.destroy()

        # Add process details
        details_text = tk.Text(tab, wrap=tk.WORD)
        details_text.insert(tk.END, f"Name: {process_data[1]}\n"
                                      f"User: {process_data[2]}\n"
                                      f"Memory: {process_data[3]}\n"
                                      f"CPU: {process_data[4]}\n"
                                      f"Status: {process_data[5]}")
        details_text.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        details_text.config(state=tk.DISABLED)

        # # Add close button
        # close_btn = ttk.Button(tab, text="Close Tab", command=lambda: self.close_tab(tab))
        # close_btn.pack(side=tk.BOTTOM, pady=10)


    def on_double_click(self, event):
        """
        Handle double-click event on the process list treeview.
        Create a new tab with process details.
        """
        selected_process = self.process_list_tree.selection()
        if not selected_process:
            return
        process = self.process_list_tree.item(selected_process)
        process_info = process['values']

        # Create a new tab for process details
        details_tab = ttk.Frame(self.notebook)
        self.notebook.add(details_tab, text=f"Process {process_info[0]}")
        self.notebook.select(details_tab)

        label = tk.Label(details_tab, text=f"Details for Process ID: {process_info[0]}")
        label.pack(pady=10)

        self.specific_process_req_queue.put(process_info[0])  # Request specific process details

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
        close_btn = ttk.Button(details_tab, text="Close Tab", command=lambda: self.close_tab(details_tab))
        close_btn.pack(side=tk.BOTTOM, pady=10)

        

    def close_tab(self, tab):
        """
        Close the specified tab.
        """
        pid = int(self.notebook.tab(tab, "text").split(" ")[1])
        self.specific_process_req_queue.put(pid)  # Request to close the specific process
        self.notebook.forget(tab)

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
    
if __name__ == "__main__":
    pass