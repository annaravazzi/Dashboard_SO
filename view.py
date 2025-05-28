import tkinter as tk
import ttkbootstrap as ttk

class View:
    """
    Classe View para criar a GUI para o dashboard, separado do Model de fetching de dados.
    A view mostra: stats gerais do sistema operacional, a lista de processos e detalhes específicos de cada um, se o usuário quiser.
    """
    def __init__ (self, specific_process_req_queue):
        # Inicializa a janela principal
        self.root = ttk.Window(themename="darkly")
        self.root.title("Operating System Dashboard")
        self.root.geometry("1120x630")

        # Cria notebook (abas)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True)

        # Dict para dados gerais da lista de processos {pid: [pid, name, user, priority, memory_usage, cpu_usage, status]}
        self.process_data_dict = {}
        # Dict para dados específicos de processos
        # {pid: [pid, ppid, name, user, cpu, status, num_threads, priority, nice, processor_time, command,
        # virtual_memory, resident_memory, shared_memory, text_segment_size, 
        # data_segment_size, stack_segment_size, threads]}
        self.specific_process_data_dict = {}
        # Lista de dados gerais de sistema [total_memory, used_memory, memory_usage, total_swap, used_swap, swap_usage,
        # load_avg, uptime, cpu_usage, num_processes, num_threads]
        self.general_stats_data = []

        # Dict das abas abertas dos processos especificos {pid: tab_id}
        self.processes_opened_tabs = {}
        # Dict com as treeviews das threads em cada aba {tab_id: treeview}
        self.threads_treeviews = {}
        # Dict com as treeviews dos dados dos processos em cada aba {tab_id: treeview}
        self.process_data_treeviews = {}

        # Queue de requests para processos especificos
        self.specific_process_req_queue = specific_process_req_queue

        # Se a row do uso de CPU foi expandida
        self.cpu_usage_expanded = False

        # Criar aba dos processos
        self.create_process_list_tab()
        # Criar aba dos dados gerais de sistema
        self.create_general_stats_tab()

    ###########################
    # Métodos para criar abas #
    ###########################
    def create_process_list_tab(self):
        """
        Cria a aba para mostrar a lista geral de processos
        """
        process_list_tab = ttk.Frame(self.notebook)
        self.notebook.add(process_list_tab, text="All Processes")

        # Treeview para a tabela
        self.process_list_tree = ttk.Treeview(process_list_tab, 
                                              columns=('PID', 'Name', 'User', 'Priority', 'Memory', 'CPU', 'State'), 
                                              show='headings', bootstyle='DARK')
        self.process_list_tree.heading('PID', text='PID', anchor='w')
        self.process_list_tree.heading('Name', text='Name', anchor='w')
        self.process_list_tree.heading('User', text='User', anchor='w')
        self.process_list_tree.heading('Priority', text='Priority', anchor='w')
        self.process_list_tree.heading('Memory', text='Memory', anchor='w')
        self.process_list_tree.heading('CPU', text='CPU(%)', anchor='w')
        self.process_list_tree.heading('State', text='State', anchor='w')
        self.process_list_tree.column('PID', width=50)
        self.process_list_tree.column('Name', width=150)
        self.process_list_tree.column('User', width=100)
        self.process_list_tree.column('Priority', width=80)
        self.process_list_tree.column('Memory', width=100)
        self.process_list_tree.column('CPU', width=100)
        self.process_list_tree.column('State', width=100)

        # Linhas cores alternadas
        self.process_list_tree.tag_configure("evenrow", background="#222222")
        self.process_list_tree.tag_configure("oddrow", background="#303030")

        # Scrollbar
        scrollbar = ttk.Scrollbar(process_list_tab, orient=tk.VERTICAL, command=self.process_list_tree.yview)
        self.process_list_tree.configure(yscroll=scrollbar.set)
        self.process_list_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')

        # Setando a grid
        process_list_tab.grid_columnconfigure(0, weight=1)
        process_list_tab.grid_rowconfigure(0, weight=1)

        # Bind do evento de double click (abrir aba de processo especifico)
        self.process_list_tree.bind('<Double-1>', self.create_specific_process_tab)
    
    def create_general_stats_tab(self):
        """
        Cria a aba para mostrar os dados gerais do sistema operacional.
        """
        general_stats_tab = ttk.Frame(self.notebook)
        self.notebook.add(general_stats_tab, text="General System Data")

        # Cria a tabela de uso de CPU
        cpu_frame = ttk.Frame(general_stats_tab)
        cpu_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        cpu_label_frame = ttk.Labelframe(cpu_frame, text="CPU Usage", padding=(10, 10))
        cpu_label_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)

        self.cpu_usage_treeview = ttk.Treeview(cpu_label_frame, columns=('CPU', 'Usage (%)', 'Graph'), show='headings', bootstyle='DARK', height=5)
        self.cpu_usage_treeview.heading('CPU', text='CPU', anchor='w')
        self.cpu_usage_treeview.heading('Usage (%)', text='Usage (%)', anchor='w')
        self.cpu_usage_treeview.heading('Graph', text='', anchor='w')
        self.cpu_usage_treeview.column('CPU', width=100, stretch=tk.NO)
        self.cpu_usage_treeview.column('Usage (%)', width=150, stretch=tk.NO)
        self.cpu_usage_treeview.column('Graph', stretch=tk.YES)
        self.cpu_usage_treeview.tag_configure("evenrow", background="#222222")
        self.cpu_usage_treeview.tag_configure("oddrow", background="#303030")

        self.cpu_usage_treeview.pack(fill=tk.BOTH, expand=True)

        # Bind do evento de click (expandir/colapsar a linha de uso de CPU)
        self.cpu_usage_treeview.bind('<Button-1>', self.toggle_cpu_row)

        # Cria a tabela de uso de memória
        memory_frame = ttk.Frame(general_stats_tab)
        memory_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        memory_label_frame = ttk.Labelframe(memory_frame, text="Memory and Swap", padding=(10, 10))
        memory_label_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
        self.memory_usage_treeview = ttk.Treeview(memory_label_frame, columns=('Field', 'Value', 'Graph'), show='', bootstyle='DARK', height=2)
        self.memory_usage_treeview.heading('Field', text='Field', anchor='w')
        self.memory_usage_treeview.heading('Value', text='Value', anchor='w')
        self.memory_usage_treeview.heading('Graph', text='Graph', anchor='w')
        self.memory_usage_treeview.column('Field', width=100, stretch=tk.NO)
        self.memory_usage_treeview.column('Value', width=150, stretch=tk.NO)
        self.memory_usage_treeview.column('Graph', stretch=tk.YES)
        self.memory_usage_treeview.tag_configure("evenrow", background="#222222")
        self.memory_usage_treeview.tag_configure("oddrow", background="#303030")

        self.memory_usage_treeview.insert('', tk.END, values=('Memory', ''), tags=("evenrow",))
        self.memory_usage_treeview.insert('', tk.END, values=('Swap', ''), tags=("oddrow",))

        self.memory_usage_treeview.pack(fill=tk.BOTH, expand=True)

        # Cria a tabela de outros dados gerais do sistema
        general_stats_frame = ttk.Frame(general_stats_tab)
        general_stats_frame.pack(side=tk.TOP, fill=tk.BOTH, padx=10, pady=10)
        general_stats_label_frame = ttk.Labelframe(general_stats_frame, text="Other System Stats", padding=(10, 10))
        general_stats_label_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.general_stats_treeview = ttk.Treeview(general_stats_label_frame,
                                                  columns=('Field', 'Value'), show='', bootstyle='DARK', height=4)
        self.general_stats_treeview.heading('Field', text='Field', anchor='w')
        self.general_stats_treeview.heading('Value', text='Value', anchor='w')
        self.general_stats_treeview.column('Field', width=150)
        self.general_stats_treeview.column('Value', width=100)
        self.general_stats_treeview.tag_configure("evenrow", background="#222222")
        self.general_stats_treeview.tag_configure("oddrow", background="#303030")

        fields = ['Number of Processes', 'Number of Threads', 'Load Average', 'Uptime']
        for field in fields:
            self.general_stats_treeview.insert('', tk.END, values=(field, ''), 
                                          tags=("evenrow" if fields.index(field) % 2 == 0 else "oddrow",))
        
        self.general_stats_treeview.pack(fill=tk.BOTH, expand=True)

    def create_specific_process_tab(self, event):
        """
        Cria uma aba para mostrar os detalhes de um processo específico.
        Chamado ao dar double-click em um processo na lista de processos.
        """
        # Get do processo selecionado
        selected_process = self.process_list_tree.selection()
        if not selected_process:
            return
        process = self.process_list_tree.item(selected_process)
        process_info = process['values']

        if process_info and process_info[0] in self.processes_opened_tabs:
            # Se a aba ja existe, apenas seleciona ela
            self.notebook.select(self.processes_opened_tabs[process_info[0]])
            return
        
        # Criar a tab para o processo
        details_tab = ttk.Frame(self.notebook)
        self.processes_opened_tabs[process_info[0]] = details_tab
        self.notebook.add(details_tab, text=f"Process {process_info[0]}")
        self.notebook.select(details_tab)
        close_btn = ttk.Button(details_tab, text="Close Tab", command=lambda: self.close_tab(details_tab, process_info[0], req=True))
        close_btn.pack(side=tk.BOTTOM, pady=10)
        label = tk.Label(details_tab, text=f"Details for Process ID: {process_info[0]}")
        label.pack(pady=10)

        # Para os dados do processo, criar duas treeviews: uma para os dados do processo e outra para o uso de memória dele
        left_frame = ttk.Frame(details_tab)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        proc_label_frame = ttk.Labelframe(left_frame, text="Process data", padding=(10, 10))
        proc_label_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        process_data_treeview = ttk.Treeview(proc_label_frame, columns=('Field', 'Value'), show='', bootstyle='DARK', height=10)
        process_data_treeview.tag_configure("evenrow", background="#222222")
        process_data_treeview.tag_configure("oddrow", background="#303030")
        fields = ['PPID', 'Name', 'Username', 'CPU(%)', 'Status', 'Number of Threads',
                  'Priority', 'Nice', 'Processor Time', 'Command']
        for idx, field in enumerate(fields):
            process_data_treeview.insert('', tk.END, values=(field, ''), tags=("evenrow" if idx % 2 == 0 else "oddrow",))
        
        proc_mem_label_frame = ttk.Labelframe(left_frame, text="Memory Usage", padding=(10, 10))
        proc_mem_label_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        process_mem_treeview = ttk.Treeview(proc_mem_label_frame, columns=('Field', 'Value'), show='', bootstyle='DARK', height=6)
        process_mem_treeview.tag_configure("evenrow", background="#222222")
        process_mem_treeview.tag_configure("oddrow", background="#303030")
        mem_fields = ['Virtual Memory', 'Resident Memory', 'Shared Memory',
                      'Text Segment Size', 'Data Segment Size', 'Stack Segment Size']
        for idx, field in enumerate(mem_fields):
            process_mem_treeview.insert('', tk.END, values=(field, ''), 
                                        tags=("evenrow" if idx % 2 == 0 else "oddrow",))
        
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(0, weight=1)

        # Armazenar as treeviews para atualizações futuras
        self.process_data_treeviews[details_tab] = (process_data_treeview, process_mem_treeview)


        # Criar a tabela de threads
        right_frame = ttk.Frame(details_tab)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, expand=True)

        thr_label_frame = ttk.Labelframe(right_frame, text="Threads", padding=(10, 10))
        thr_label_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

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

        # Armazenar a treeview de threads para atualizações futuras
        self.threads_treeviews[details_tab] = threads_treeview

        # Fazer request para dados do processo
        self.specific_process_req_queue.put((process_info[0], 'add'))

    ##########################################
    # Métodos para atualizar os dados da GUI #
    ##########################################
    def update_data(self, processes_data, specific_process_data, general_stats_data):
        """
        Atualiza todos os dados na view.
        Chamado periodicamente no controller para atualizar os dados exibidos na GUI.
        """
        # Armazena os dados recebidos
        self.process_data_dict = processes_data
        self.specific_process_data_dict = specific_process_data
        self.general_stats_data = general_stats_data

        # Pega a aba ativa do notebook
        active_tab = self.notebook.select()

        # Atualiza a lista de processos
        if active_tab == self.notebook.tabs()[0] and self.process_data_dict:
            # Se a aba ativa for a lista de processos, atualiza a view
            self.update_process_list_view(list(self.process_data_dict.values()))
        
        # Atualiza a aba de dados gerais do sistema
        if active_tab == self.notebook.tabs()[1] and self.general_stats_data:
            # Se a aba ativa for a aba de dados gerais do sistema, atualiza a view
            self.update_general_stats_view(self.general_stats_data)

        # Checa as abas abertas dos processos especificos
        if self.specific_process_data_dict and self.processes_opened_tabs:
            # Copia o dict para evitar problemas de iteração durante a atualização
            opened_tabs = self.processes_opened_tabs.copy()
            for pid, tab_id in opened_tabs.items():
                # Verifica se a entry no dict não é vazia (pode ser uma chave que existe, mas com tupla vazia)
                # Se a entrada for uma tupla vazia, significa que o processo foi adicionado mas ainda não recebeu dados, então espera
                if str(active_tab) == str(tab_id) and pid in self.specific_process_data_dict and self.specific_process_data_dict[pid]:
                    # Se a entry for uma tupla com dados, atualiza a aba
                    if all(data is not None for data in self.specific_process_data_dict[pid]):
                        self.update_specific_process_tab(tab_id, self.specific_process_data_dict[pid])
                    else:
                        # Se a entry for uma tupla com dados None, significa que o processo foi terminado (confirmado pelo Model)
                        self.close_tab(tab_id, pid, req=True)

    def update_process_list_view(self, process_data):
        """
        Atualiza a aba de lista de processos com os dados atuais.
        """
        if not process_data:
            return
        
        # Preservar a posição de rolagem e seleção
        current_position = self.process_list_tree.yview()[0]
        selected_item = self.process_list_tree.focus()
        selected_text = self.process_list_tree.item(selected_item) if selected_item else None

        # Limpar dados existentes na treeview
        for item in self.process_list_tree.get_children():
            self.process_list_tree.delete(item)

        # Inserir novos dados na treeview
        for idx, process in enumerate(process_data):
            self.process_list_tree.insert('', tk.END, values=process, tags=("evenrow" if idx % 2 == 0 else "oddrow",))
            # Se o processo selecionado for o mesmo que o texto selecionado, manter a seleção
            if selected_text and process[0] == selected_text['values'][0]:
                self.process_list_tree.selection_set(self.process_list_tree.get_children()[idx])
                self.process_list_tree.focus(self.process_list_tree.get_children()[idx])
                self.process_list_tree.see(self.process_list_tree.get_children()[idx])
                
        # Atualizar a posição de rolagem
        self.process_list_tree.yview_moveto(current_position)

    def update_general_stats_view(self, general_data):
        """
        Atualiza a aba de dados globais do sistema com dados atuais.
        """
        if not general_data:
            return
        
        # Limpar dados existentes nas treeviews
        for item in self.cpu_usage_treeview.get_children():
            self.cpu_usage_treeview.delete(item)
        for item in self.memory_usage_treeview.get_children():
            self.memory_usage_treeview.delete(item)
        for item in self.general_stats_treeview.get_children():
            self.general_stats_treeview.delete(item)

        # Atualizar a tabela de uso de CPU
        self.cpu_usage_treeview.insert('', tk.END, values=('Total CPU', f"{general_data[6][0][1]:.2f}%", self.plot_graph_string(100, general_data[6][0][1])),
                                       tags=("evenrow",))
        # Adicionar uso de CPU por núcleo
        if self.cpu_usage_expanded:
            for idx, usage in enumerate(general_data[6][1:]):
                self.cpu_usage_treeview.insert('', tk.END, values=(f"    Core {idx}", f"    {usage[1]:.2f}%", self.plot_graph_string(100, usage[1])),
                                               tags=("oddrow" if idx % 2 == 0 else "evenrow",))
        
        self.cpu_usage_treeview.pack(fill=tk.BOTH, expand=True)

        # Atualizar a tabela de uso de memória
        total_memory = general_data[0]
        used_memory = general_data[1]
        memory_usage = general_data[2]
        total_swap = general_data[3]
        used_swap = general_data[4]
        swap_usage = general_data[5]
        self.memory_usage_treeview.insert('', tk.END, values=('Memory', used_memory + "/" + total_memory, 
                                                              self.plot_graph_string(100, memory_usage)), 
                                                              tags=("evenrow",))
        self.memory_usage_treeview.insert('', tk.END, values=('Swap', used_swap + "/" + total_swap, 
                                                              self.plot_graph_string(100, swap_usage)), 
                                                              tags=("oddrow",))

        self.memory_usage_treeview.pack(fill=tk.BOTH, expand=True)

        # Atualizar a tabela de outros dados gerais do sistema
        fields = ['Number of Processes', 'Number of Threads', 'Load Average', 'Uptime']
        values = [general_data[7], general_data[8], f"{general_data[9][0]:.2f}, {general_data[9][1]:.2f}, {general_data[9][2]:.2f}",
                  general_data[10]]
        for field, value in zip(fields, values):
            self.general_stats_treeview.insert('', tk.END, values=(field, value), 
                                               tags=("evenrow" if fields.index(field) % 2 == 0 else "oddrow",))

        self.general_stats_treeview.pack(fill=tk.BOTH, expand=True)

    def update_specific_process_tab(self, tab_id, process_data):
        """
        Atualiza a aba de processo específico com os dados atuais.
        """
        if tab_id not in self.process_data_treeviews or all(data is None for data in process_data):
            return
        
        # Get das treeviews associadas ao tab_id
        process_data_treeview, process_mem_treeview = self.process_data_treeviews[tab_id]
        
        # Limpar dados existentes na treeview de dados do processo
        for item in process_data_treeview.get_children():
            process_data_treeview.delete(item)
        for item in process_mem_treeview.get_children():
            process_mem_treeview.delete(item)

        # Inserir novos dados na treeview de dados do processo
        fields = ['PPID', 'Name', 'Username', 'CPU(%)', 'Status', 'Number of Threads',
                  'Priority', 'Nice', 'Processor Time', 'Command']
        values = [process_data[1], process_data[2], process_data[3], f"{process_data[4]:.2f}%",
                  process_data[5], process_data[6], process_data[7], process_data[8],
                  process_data[9], process_data[10]]
        for idx, (field, value) in enumerate(zip(fields, values)):
            process_data_treeview.insert('', tk.END, values=(field, value), 
                                         tags=("evenrow" if idx % 2 == 0 else "oddrow",))
        process_data_treeview.pack(fill=tk.BOTH, expand=True)

        # Inserir novos dados na treeview de uso de memória do processo
        mem_fields = ['Virtual Memory', 'Resident Memory', 'Shared Memory',
                      'Text Segment Size', 'Data Segment Size', 'Stack Segment Size']
        mem_values = [process_data[11], process_data[12], process_data[13],
                      process_data[14], process_data[15], process_data[16]]
        for idx, (field, value) in enumerate(zip(mem_fields, mem_values)):
            process_mem_treeview.insert('', tk.END, values=(field, value if value is not None else 'N/A'), 
                                        tags=("evenrow" if idx % 2 == 0 else "oddrow",))
        process_mem_treeview.pack(fill=tk.BOTH, expand=True)

        # Limpar dados existentes na treeview de threads
        threads_treeview = self.threads_treeviews[tab_id]
        for item in threads_treeview.get_children():
            threads_treeview.delete(item)

        # Inserir novos dados na treeview de threads
        for idx, thread in enumerate(process_data[17]):
            threads_treeview.insert('', tk.END, values=(thread[0], thread[1], thread[2], 
                                                        thread[3], thread[4], thread[5]), 
                                                        tags=("evenrow" if idx % 2 == 0 else "oddrow",))
        threads_treeview.grid(row=1, column=0, sticky='nsew')


    def close_tab(self, tab, pid, req=True):
        """
        Fechar uma aba de processo específico.
        Se req for True, envia um request para o controller remover o processo da lista de processos.
        Se req for False, apenas remove a aba sem enviar o request.
        """
        if req:
            self.specific_process_req_queue.put((pid, 'remove'))
        self.processes_opened_tabs.pop(pid, None)
        try:
            self.notebook.forget(tab)
        except:
            return
        
    def toggle_cpu_row(self, event):
        """
        Toggle entre expandir e colapsar a linha de uso de CPU.
        Se a linha de uso de CPU for expandida, insere os dados de uso de CPU por núcleo.
        """
        region = self.cpu_usage_treeview.identify_region(event.x, event.y)
        item = self.cpu_usage_treeview.identify_row(event.y)

        if item and (region == 'cell' or region == 'heading'):
                # Toggle do estado de expansão da linha de uso de CPU
                if not self.cpu_usage_expanded:
                    self.cpu_usage_expanded = True
                    self.cpu_usage_treeview.item(item, open=True)          
                else:
                    self.cpu_usage_expanded = False
                    # Removeer os filhos da linha de uso de CPU
                    for child in self.cpu_usage_treeview.get_children(item):
                        self.cpu_usage_treeview.delete(child)
                    self.cpu_usage_treeview.item(item, open=False)

    def plot_graph_string(self, total, used, blocks=100):
        """
        Gera uma representação em string de um gráfico para uso de memória.
        """
        total_blocks = blocks
        used_blocks = round((used / total) * total_blocks)
        graph = "▰" * used_blocks + "▱" * (total_blocks - used_blocks)
        return graph
                
    def run(self):
        """
        Mainloop do tkinter para manter a janela aberta.
        """
        self.root.mainloop()