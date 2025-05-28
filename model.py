from ctypes import CDLL, Structure, c_char, c_char_p, c_int, c_void_p, c_ulonglong, c_ushort, c_ubyte, POINTER
from ctypes.util import find_library
import threading
import time

class CtypesFunctions:
    """
    Classe Ctypesfunctions para usar funções do libc para manipulação de diretórios.
    Esta classe define métodos para listar diretórios usando a biblioteca C padrão.
    """
    # Dirent struct (directory entry)
    class Dirent(Structure):
        _fields_ = [
            ("d_ino", c_ulonglong),
            ("d_off", c_ulonglong),
            ("d_reclen", c_ushort),
            ("d_type", c_ubyte),
            ("d_name", c_char * 256),
        ]
    def __init__(self):
        # Carrega libc functions
        self.libc = CDLL(find_library("c"))
        self.opendir = self.libc.opendir
        self.opendir.argtypes = [c_char_p]
        self.opendir.restype = c_void_p
        self.readdir = self.libc.readdir
        self.readdir.argtypes = [c_void_p]
        self.readdir.restype = POINTER(self.Dirent)
        self.closedir = self.libc.closedir
        self.closedir.argtypes = [c_void_p]
        self.closedir.restype = c_int

    def list_directory(self, path):
        """
        Listar o conteúdo de um diretório.
        """
        entries = []
        dir_ptr = self.opendir(path.encode("utf-8"))    # Ponteiro para o diretório aberto
        if not dir_ptr:
            return []
        try:
            while True:            
                entry_ptr = self.readdir(dir_ptr)   # Ler próximo diretório
                if not entry_ptr:
                    break

                entry = entry_ptr.contents
                # Extrair filename
                name_bytes = bytes(entry.d_name)
                null_pos = name_bytes.find(b'\x00') # null terminator
                if null_pos != -1:
                    name_bytes = name_bytes[:null_pos]  # Truncar nome no null terminator
                name = name_bytes.decode("utf-8", errors="replace")     # Decodificar bytes para string
                if name not in (".", ".."): # Excluir diretorios atual e pai
                    entries.append(name)
        finally:
            self.closedir(dir_ptr)
        return entries


class Model:
    """
    Classe Model para manejar a coleta de dados do dashboard do sistema.
    Ela coleta informações de processos, informações de processos específicos e estatísticas gerais.
    Threads separados são usados para coletar dados continuamente e se comunicar com a thread principal.
    """
    def __init__(self, process_queue, specific_processes_queue, specific_processes_req_queue, general_stats_queue, DT=1):
        self.ctypes_functions = CtypesFunctions()
        # Threading
        self._processes_thread_running = False
        self._processes_thread = None
        self._specific_processes_thread_running = False
        self._specific_processes_thread = None
        self._general_stats_thread_running = False
        self._general_stats_thread = None

        # Queues (para comunicação com a thread principal)
        self.process_queue = process_queue
        self.specific_processes_queue = specific_processes_queue
        self.specific_processes_req_queue = specific_processes_req_queue
        self.general_stats_queue = general_stats_queue

        # Guardam dados coletados
        self._processes_dict = {}
        self._specific_processes_dict = {}
        self._general_stats_list = []

        # Calculo de uso de CPU
        self._CLK_TCK_PS = 100  # Default value for clock ticks per second in Linux
        self._prev_proc_data = {}
        self._prev_thrd_data = {}

        # Intervalo de tempo entre coletas (em segundos)
        self._DT = DT

    ################################################
    # Metodos de inicialização e parada de threads #
    ################################################
    def start_processes_thread(self):
        """
        Inicia a thread para listar processos.
        """
        self._processes_thread_running = True
        self._processes_thread = threading.Thread(target=self._list_processes, daemon=True)
        self._processes_thread.start()
    def stop_processes_thread(self):
        """
        Encerra a thread para listar processos.
        """
        self._processes_thread_running = False
        if self._processes_thread:
            self._processes_thread.join()
    def start_specific_processes_thread(self):
        """
        Inicia a thread para listar processos específicos.
        """
        self._specific_processes_thread_running = True
        self._specific_processes_thread = threading.Thread(target=self._list_specific_processes, daemon=True)
        self._specific_processes_thread.start()
    def stop_specific_processes_thread(self):
        """
        Encerra a thread para listar processos específicos.
        """
        self._specific_processes_thread_running = False
        if self._specific_processes_thread:
            self._specific_processes_thread.join()
    def start_general_stats_thread(self):
        """
        Inicia a thread para listar estatísticas gerais do sistema.
        """
        self._general_stats_thread_running = True
        self._general_stats_thread = threading.Thread(target=self._list_general_stats, daemon=True)
        self._general_stats_thread.start()
    def stop_general_stats_thread(self):
        """
        Encerra a thread para listar estatísticas gerais do sistema.
        """
        self._general_stats_thread_running = False
        if self._general_stats_thread:
            self._general_stats_thread.join()

    ###################################################
    # Metodos de coleta de dados em threads separadas #
    ###################################################
    def _list_processes(self):
        """
        Rodando na thread _list_processes_thread.
        Coleta dados gerais sobre todos os processos do sistema.
        """
        while self._processes_thread_running:
            self.process_queue.put(self._get_processes_data())
            time.sleep(self._DT)

    def _list_specific_processes(self):
        """
        Rodando na thread _list_specific_processes_thread.
        Coleta dados sobre processos específicos que estão sendo monitorados.
        Se um PID for adicionado ou removido da fila specific_processes_req_queue, ele será monitorado ou não.
        """
        while self._specific_processes_thread_running:
            while not self.specific_processes_req_queue.empty():
                pid, req = self.specific_processes_req_queue.get()
                if req == 'add':
                    # Adiciona o PID ao dicionário para monitoramento
                    if pid not in self._specific_processes_dict:
                        self._specific_processes_dict[pid] = ()  # Inicializa com tupla vazia
                elif req == 'remove':
                    try:
                        # Remove o PID do dicionário
                        del self._specific_processes_dict[pid]
                    except KeyError:
                        pass

            # Retorna os dados dos processos específicos monitorados
            self.specific_processes_queue.put(self._get_specific_processes_data())
            time.sleep(self._DT)

    def _list_general_stats(self):
        """
        Rodando na thread _list_general_stats_thread.
        Coleta estatísticas gerais do sistema, como uso de memória, CPU, carga média, etc.
        """
        while self._general_stats_thread_running:
            self.general_stats_queue.put(self._get_general_stats_data())
            time.sleep(self._DT)

    def _get_processes_data(self):
        """
        Lista todos os processos do sistema e coleta dados gerais sobre eles.
        Return: Dictionary {pid: (pid, name, user, priority, memory, cpu_usage, status)}
        """
        self._processes_dict = {}
        # Lista os diretórios em /proc
        entries = self.ctypes_functions.list_directory("/proc")
        for entry in entries:
            if entry.isdigit(): # Checa se a entrada é um número (PID)
                try:
                    pid = int(entry)
                    name = "N/A"
                    status = "N/A"
                    memory = "N/A"
                    username = "N/A"
                    cpu_usage = 0.0
                    priority = 0

                    with open(f"/proc/{entry}/status", "r") as f:
                        for line in f:
                            if line.startswith("Name:"):
                                name = line.split(":")[1].strip()   # Nome do processo
                            elif line.startswith("State:"):
                                status = line.split(":")[1].strip().split()[0]
                                status = self._get_process_status(status)   # Status do processo
                            elif line.startswith("VmRSS:"):
                                memory = line.split(":")[1].strip().split()[0]
                                memory = self._kb_to_mb_gb(int(memory))    # Uso de memória (RSS) em MB ou KB
                            elif line.startswith("Uid:"):
                                userid = line.split(":")[1].split()[0]
                                username = self._uid_to_username(userid)    # Username (do UID)

                    with open(f"/proc/{entry}/stat", "r") as f:
                        data = f.read().split()
                        priority = int(data[17])    # Prioridade do processo (no kernel)
                        total_time = int(data[13]) + int(data[14])
                        cpu_usage = self._get_cpu_usage_process(int(entry), total_time)   # Uso de CPU em porcentagem

                    # Adiciona os dados do processo ao dicionário
                    self._processes_dict[pid] = (pid, name, username, priority, memory, cpu_usage, status)
                except FileNotFoundError:
                    # Processo foi encerrado, não será incluído
                    continue
        return self._processes_dict
    
    def _get_specific_processes_data(self):
        """
        Lista processos específicos que estão sendo monitorados.
        Se um PID for adicionado ou removido da fila specific_processes_req_queue, ele será monitorado ou não.
        Return: Dictionary {pid: (pid, ppid, name, username, cpu_usage, status, num_threads, priority, nice, processor_time, command,
                virtual_mem, resident_mem, shared_mem, textsize, datasize, stacksize, (threads))}
        """
        # Limpa o dicionário de processos específicos antes de coletar novos dados
        pids = list(self._specific_processes_dict.keys())
        self._specific_processes_dict = {}

        for pid in pids:
            try:
                pid = int(pid)
                ppid = -1
                name = "N/A"
                username = "N/A"
                cpu_usage = 0.0
                status = "N/A"
                num_threads = 0
                priority = 0
                nice = 0
                processor_time = "N/A"
                command = "N/A"
                virtual_mem = "N/A"
                resident_mem = "N/A"
                shared_mem = "N/A"
                textsize = "N/A"
                datasize = "N/A"
                stacksize = "N/A"

                with open(f"/proc/{pid}/cmdline", "r") as f:
                    command = f.read().strip().replace('\x00', ' ')   # Linha de comando do processo
                
                with open(f"/proc/{pid}/status", "r") as f:
                    for line in f:
                        if line.startswith("Name:"):
                            name = line.split(":")[1].strip()   # Nome do processo
                        elif line.startswith("State:"):
                            status = line.split(":")[1].strip().split()[0]
                            status = self._get_process_status(status)   # Status do processo
                        elif line.startswith("VmRSS:"):
                            resident_mem = line.split(":")[1].strip().split()[0]
                            resident_mem = self._kb_to_mb_gb(int(resident_mem))    # Memoria residente (RSS) em MB ou KB
                        elif line.startswith("Uid:"):
                            userid = line.split(":")[1].split()[0]
                            username = self._uid_to_username(userid)    # Username (do UID)
                        elif line.startswith("Threads:"):
                            num_threads = line.split(":")[1].strip()
                            num_threads = int(num_threads) if num_threads.isdigit() else 0  # Número de threads do processo
                        elif line.startswith("VmSize:"):
                            virtual_mem = line.split(":")[1].strip().split()[0]
                            virtual_mem = self._kb_to_mb_gb(int(virtual_mem))    # Memória virtual em MB ou KB
                        elif line.startswith("RssShmem:"):
                            shared_mem = line.split(":")[1].strip().split()[0]
                            shared_mem = self._kb_to_mb_gb(int(shared_mem))    # Memória compartilhada em MB ou KB
                        elif line.startswith("VmExe:"):
                            textsize = line.split(":")[1].strip().split()[0]
                            textsize = self._kb_to_mb_gb(int(textsize))    # Tamanho do segmento text em MB ou KB
                        elif line.startswith("VmData:"):
                            datasize = line.split(":")[1].strip().split()[0]
                            datasize = self._kb_to_mb_gb(int(datasize))    # Tamanho do segmento data em MB ou KB
                        elif line.startswith("VmStk:"):
                            stacksize = line.split(":")[1].strip().split()[0]
                            stacksize = self._kb_to_mb_gb(int(stacksize))   # Tamanho do segmento stack em MB ou KB
                        elif line.startswith("PPid:"):
                            ppid = line.split(":")[1].strip()   # ID do processo pai (PPID)
                
                with open(f"/proc/{pid}/stat", "r") as f:
                    data = f.read().split()
                    total_time = int(data[13]) + int(data[14])
                    cpu_usage = self._get_cpu_usage_process(int(pid), total_time)   # Uso de CPU em porcentagem
                    processor_time = self._seconds_to_hhmmss(total_time/self._CLK_TCK_PS)  # Tempo de processamento formatado como HH:MM:SS
                    priority = int(data[17])    # Prioridade
                    nice = int(data[18])    # Nice
                    
                threads = self._get_threads_data(pid)   # Dados das threads do processo
                
                # Adiciona os dados do processo específico ao dicionário
                self._specific_processes_dict[pid] = (pid, ppid, name, username, cpu_usage, status, num_threads,
                                                        priority, nice, processor_time, command, virtual_mem,
                                                        resident_mem, shared_mem, textsize, datasize, stacksize,
                                                        threads)
                
            except FileNotFoundError:
                # Processo foi encerrado, será preenchido com tupla nula
                self._specific_processes_dict[pid] = (None, None, None, None, None, None, None, None, None, None, 
                                                      None, None, None, None, None, None, None, None)
                continue

        return self._specific_processes_dict

    def _get_threads_data(self, pid):
        """
        Lista as threads de um processo específico e coleta dados sobre elas.
        Return: List [(tid, name, username, memory, cpu_usage, status)]
        """
        threads = []
        entries = self.ctypes_functions.list_directory(f"/proc/{pid}/task")

        for entry in entries:
            if entry.isdigit():  # Checa se a entrada é um número (TID)
                try:
                    with open(f"/proc/{pid}/task/{entry}/status", "r") as f:
                        tid = int(entry)
                        for line in f:
                            if line.startswith("Name:"):
                                name = line.split(":")[1].strip()   # Nome da thread
                            elif line.startswith("State:"):
                                status = line.split(":")[1].strip().split()[0]
                                status = self._get_process_status(status)   # Status da thread
                            elif line.startswith("Uid:"):
                                userid = line.split(":")[1].split()[0]
                                username = self._uid_to_username(userid)    # Username (do UID)
                            elif line.startswith("VmRSS:"):
                                memory = line.split(":")[1].strip().split()[0]
                                memory = self._kb_to_mb_gb(int(memory))  # Uso de memória (RSS) em MB ou KB
                    
                    with open(f"/proc/{pid}/task/{tid}/stat", "r") as f:
                        data = f.read().split()
                        total_time = int(data[13]) + int(data[14])
                        cpu_usage = self._get_cpu_usage_process(tid, total_time, is_thread=True)    # Uso de CPU em porcentagem para a thread

                    # Adiciona os dados da thread à lista
                    threads.append((tid, name, username, memory, cpu_usage, status))
                except FileNotFoundError:
                    # Thread foi encerrada, não será incluída
                    continue
        return threads

    def _get_general_stats_data(self):
        """
        Coleta dados gerais sobre o sistema operacional.
        Return: List [total_memory, used_memory, memory_usage, total_swap, used_swap, swap_usage, cpu_usage,
                        num_procs, num_threads, load_avg, uptime]
        """
        self._general_stats_list = []

        try:
            total_memory = "N/A"
            used_memory = "N/A"
            memory_usage = 0.0
            total_swap = "N/A"
            used_swap = "N/A"
            swap_usage = 0.0
            cpu_usage = []
            num_procs = 0
            num_threads = 0
            load_avg = []
            uptime = "N/A"

            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        total_memory = line.split(":")[1].strip().split()[0]
                    elif line.startswith("MemFree:"):
                        free_memory = line.split(":")[1].strip().split()[0]
                    elif line.startswith("Buffers:"):
                        buffers_memory = line.split(":")[1].strip().split()[0]
                    elif line.startswith("Cached:"):
                        cached_memory = line.split(":")[1].strip().split()[0]
                    elif line.startswith("SwapTotal:"):
                        total_swap = line.split(":")[1].strip().split()[0]
                    elif line.startswith("SwapFree:"):
                        free_swap = line.split(":")[1].strip().split()[0]
            
                used_memory = int(total_memory) - int(free_memory) - int(buffers_memory) - int(cached_memory)
                memory_usage = 100.0 * used_memory / int(total_memory) if int(total_memory) > 0 else 0.0    # Uso de memória em porcentagem
                used_memory = self._kb_to_mb_gb(int(used_memory))   # Uso de memória em MB ou GB
                total_memory = self._kb_to_mb_gb(int(total_memory))   # Memória total em MB ou GB

                used_swap = int(total_swap) - int(free_swap)    
                swap_usage = 100.0 * used_swap / int(total_swap) if int(total_swap) > 0 else 0.0    # Uso de swap em porcentagem
                used_swap = self._kb_to_mb_gb(int(used_swap))   # Uso de swap em MB ou GB
                total_swap = self._kb_to_mb_gb(int(total_swap))   # Swap total em MB ou GB

            with open("/proc/loadavg", "r") as f:
                load_avg = f.read().strip().split()[:3]
                load_avg = [float(x) for x in load_avg]     # Load average
            
            with open("/proc/uptime", "r") as f:
                uptime = float(f.read().strip().split()[0])
                uptime = self._seconds_to_hhmmss(uptime)    # Uptime do sistema formatado como HH:MM:SS

            cpu_usage = self._get_cpu_usage_system()        # Uso de CPU em porcentagem
            num_procs, num_threads = self._get_total_thr_procs()    # Total de processos e threads no sistema
        
            # Adiciona os dados gerais do sistema à lista
            self._general_stats_list = [total_memory, used_memory, memory_usage, total_swap, used_swap,
                                        swap_usage, cpu_usage, num_procs, num_threads, load_avg, uptime]
        except FileNotFoundError:
            pass

        return self._general_stats_list
        
    def _uid_to_username(self, uid):
        """
        Converte um UID em um nome de usuário.
        """
        try:
            with open(f"/etc/passwd", "r") as f:
                for line in f:
                    if str(uid) in line:
                        return line.split(":")[0]
            return str(uid)
        except FileNotFoundError:
            return str(uid)
    
    def _get_process_status(self, status):
        """
        Converte o status do processo em uma string legível.
        """
        status_map = {
            "R": "Running",
            "S": "Sleeping",
            "D": "Uninterruptible Sleep",
            "T": "Stopped",
            "Z": "Zombie",
        }
        return status_map.get(status, "Unknown")

    def _kb_to_mb_gb(self, kb):
        """
        Converte tamanho em KB para MB ou GB (formato string)
        """
        if kb >= 1024:
            if kb >= 1024 * 1024:
                return f"{kb / (1024 * 1024):.2f} GB"
            return f"{kb / 1024:.2f} MB"
        else:
            return f"{kb} KB"
    
    def _get_cpu_usage_process(self, id, total_time, is_thread=False):
        """
        Calcula o uso de CPU de um processo ou thread específico.
        """

        current_time = time.time()
        # Tempo anterior medido
        if is_thread:
            prev_total_time, prev_time = self._prev_thrd_data.get(id, (0, current_time))
        else:
            prev_total_time, prev_time = self._prev_proc_data.get(id, (0, current_time))

        delta_cpu_time = (total_time - prev_total_time)/self._CLK_TCK_PS  # Variação de tempo desde a ultima checagem (em segundos)
        elapsed_time = current_time - prev_time     # Tempo decorrido desde a ultima checagem (em segundos)

        # Atualiza os dados anteriores com o tempo atual e o tempo total
        if is_thread:
            self._prev_thrd_data.update({id: (total_time, current_time)})
        else:
            self._prev_proc_data.update({id: (total_time, current_time)})

        if elapsed_time <= 0:
            return 0.0
        
        cpu_usage = (delta_cpu_time / elapsed_time) * 100.0
        return round(cpu_usage, 2)
    
    def _get_cpu_usage_system(self):
        """
        Coleta o uso de CPU do sistema.
        """
        cpu_usage = []
        cpus = []
        try:
            with open("/proc/stat", "r") as f:
                data = f.read().splitlines()
                for line in data:
                    if line.startswith("cpu"):
                        cpus.append(line.split())
                if not cpus:
                    return []
            for cpu in cpus:
                if len(cpu) < 5:
                    continue
                idle_time = float(cpu[4]) / self._CLK_TCK_PS  # Tempo idle em segundos
                total_time = sum(float(x) for x in cpu[1:]) / self._CLK_TCK_PS  # Tempo total em segundos
                usage = 100.0 * (1 - idle_time / total_time) if total_time > 0 else 0.0  # Uso de CPU em porcentagem
                cpu_usage.append((cpu[0], round(usage, 2)))
                if not cpu_usage:
                    return []
        except FileNotFoundError:
            return []
        
        return cpu_usage

    def _get_total_thr_procs(self):
        """
        Coleta o número total de processos e threads no sistema.
        """
        total_procs = 0
        total_threads = 0
        entries = self.ctypes_functions.list_directory("/proc")
        for entry in entries:
            if entry.isdigit():
                total_procs += 1
                try:
                    with open(f"/proc/{entry}/stat", "r") as f:
                        data = f.read().split()
                        total_threads += int(data[19])
                except FileNotFoundError:
                    continue
        return total_procs, total_threads
    
    def _seconds_to_hhmmss(self, seconds):
        """
        Converte segundos em uma string no formato HH:MM:SS.
        """
        hours = int(seconds // 3600)
        remaining = seconds % 3600
        minutes = int(remaining // 60)
        secs = int(remaining % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"