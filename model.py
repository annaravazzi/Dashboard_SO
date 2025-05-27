from ctypes import CDLL, Structure, c_char, c_char_p, c_int, c_void_p, c_ulonglong, c_ushort, c_ubyte, POINTER
from ctypes.util import find_library
import threading
import time

class CtypesFunctions:
    """
    This class contains ctypes functions for directory operations.
    """
    # Define dirent struct (directory entry)
    class Dirent(Structure):
        _fields_ = [
            ("d_ino", c_ulonglong),
            ("d_off", c_ulonglong),
            ("d_reclen", c_ushort),
            ("d_type", c_ubyte),
            ("d_name", c_char * 256),
        ]
    def __init__(self):
        # Load libc functions
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
        List all entries in a directory.
        """
        entries = []
        dir_ptr = self.opendir(path.encode("utf-8"))    # Pointer to the directory stream
        if not dir_ptr:
            return []
        try:
            while True:            
                entry_ptr = self.readdir(dir_ptr)   # Read the next directory entry
                if not entry_ptr:
                    break

                entry = entry_ptr.contents
                # Extract filename
                name_bytes = bytes(entry.d_name)
                null_pos = name_bytes.find(b'\x00') # find null terminator
                if null_pos != -1:
                    name_bytes = name_bytes[:null_pos]  # Truncate name at null terminator
                name = name_bytes.decode("utf-8", errors="replace")     # Decode bytes to string, replacing invalid characters
                if name not in (".", ".."): # Exclude current and parent directory entries
                    entries.append(name)
        finally:
            self.closedir(dir_ptr)
        return entries


class Model:
    """
    This class is responsible for managing the data gathering for the system dashboard.
    It retrieves process information, specific process information, and general statistics.
    It uses separate threads to continuously gather data and communicate with the main thread.
    """
    def __init__(self, process_queue, specific_processes_queue, specific_processes_req_queue, general_stats_queue=None):
        self.ctypes_functions = CtypesFunctions()
        # Threading
        self._processes_thread_running = False
        self._processes_thread = None
        self._specific_processes_thread_running = False
        self._specific_processes_thread = None
        # self._general_stats_thread_running = False
        # self._general_stats_thread = None
        # Queues (to communicate with the main thread)
        self.process_queue = process_queue
        self.specific_processes_queue = specific_processes_queue
        self.specific_processes_req_queue = specific_processes_req_queue
        # self.general_stats_queue = general_stats_queue

        self.processes_dict = {}
        self.specific_processes_dict = {}
        # self.general_stats_list = []

        # To calculate CPU usage
        self.CLK_TCK_PS = 100  # Default value for clock ticks per second in Linux
        self.prev_proc_data = {}
        self.prev_thrd_data = {}

    def start_processes_thread(self):
        """
        Start the thread for process listing.
        """
        self._processes_thread_running = True
        self._processes_thread = threading.Thread(target=self._list_processes, daemon=True)
        self._processes_thread.start()

    def stop_processes_thread(self):
        """
        Stop the thread for process listing.
        """
        self._processes_thread_running = False
        if self._processes_thread:
            self._processes_thread.join()
    
    def start_specific_processes_thread(self):
        """
        Start the thread for specific process listing.
        """
        self._specific_processes_thread_running = True
        self._specific_processes_thread = threading.Thread(target=self._list_specific_processes, daemon=True)
        self._specific_processes_thread.start()

    def stop_specific_processes_thread(self):
        """
        Stop the thread for specific process listing.
        """
        self._specific_processes_thread_running = False
        if self._specific_processes_thread:
            self._specific_processes_thread.join()

    def start_general_stats_thread(self):
        pass
    
    def stop_general_stats_thread(self):
        pass

    def _list_processes(self):
        """
        Continuously list general processes in a separate thread.
        """
        while self._processes_thread_running:
            self.process_queue.put(self._get_processes_data())
            time.sleep(1)

    def _list_specific_processes(self):
        """
        List data for specific processes in a separate thread.
        This method continuously checks the specific_processes_req_queue for new PIDs to start/stop monitoring.
        """
        while self._specific_processes_thread_running:
            while not self.specific_processes_req_queue.empty():
                pid, req = self.specific_processes_req_queue.get()
                if req == 'add':
                    self.specific_processes_dict[pid] = ()   # Add the PID to the dictionary to start monitoring
                elif req == 'remove':
                    try:
                        del self.specific_processes_dict[pid]  # Remove the PID from the dictionary to stop monitoring
                    except KeyError:
                        pass

            # Return the data for the specific processes currently being monitored
            self.specific_processes_queue.put(self._get_specific_processes_data())
            time.sleep(1)

    def _list_general_stats(self):
        pass

    def _get_processes_data(self):
        """
        List all processes general data on the system.
        """
        self.processes_dict = {}
        # List all entries in the /proc directory
        entries = self.ctypes_functions.list_directory("/proc")
        for entry in entries:
            if entry.isdigit(): # Check if the entry is a digit (PID)
                try:
                    with open(f"/proc/{entry}/status", "r") as f:
                        pid = int(entry)
                        for line in f:
                            if line.startswith("Name:"):
                                name = line.split(":")[1].strip()
                            elif line.startswith("State:"):
                                status = line.split(":")[1].strip().split()[0]
                                status = self._get_process_status(status)
                            elif line.startswith("VmRSS:"):
                                memory = line.split(":")[1].strip().split()[0]
                                memory = self._kb_to_mb(int(memory))  # Convert memory to MB or KB
                            elif line.startswith("Uid:"):
                                userid = line.split(":")[1]
                                userid = userid.split()[0]
                                username = self._uid_to_username(userid)

                    with open(f"/proc/{entry}/stat", "r") as f:
                        data = f.read().split()
                        # Get total time spent in user and kernel mode (in jiffies)
                        total_time = int(data[13]) + int(data[14])
                        cpu_usage = self._get_cpu_usage_process(int(entry), total_time)

                    self.processes_dict[pid] = (pid, name, username, memory, cpu_usage, status)
                except FileNotFoundError:
                    # Process have terminated, it won't be included in the list
                    continue
        return self.processes_dict
    
    def _get_specific_processes_data(self):
        """
        List specific processes data on the system.
        """
        pids = list(self.specific_processes_dict.keys())
        self.specific_processes_dict = {}
        for pid in pids:
            try:
                with open(f"/proc/{pid}/status", "r") as f:
                    for line in f:
                        if line.startswith("Name:"):
                            name = line.split(":")[1].strip()
                        elif line.startswith("State:"):
                            status = line.split(":")[1].strip().split()[0]
                            status = self._get_process_status(status)
                        elif line.startswith("VmRSS:"):
                            memory = line.split(":")[1].strip().split()[0]
                            memory = self._kb_to_mb(int(memory))  # Convert memory to MB or KB
                        elif line.startswith("Uid:"):
                            userid = line.split(":")[1]
                            userid = userid.split()[0]
                            username = self._uid_to_username(userid)
                        elif line.startswith("Threads:"):
                            num_threads = line.split(":")[1].strip()
                            num_threads = int(num_threads) if num_threads.isdigit() else 0
                        elif line.startswith("VmSize:"):
                            vmsize = line.split(":")[1].strip().split()[0]  # Get VmSize in KB
                            vmsize = self._kb_to_mb(int(vmsize))  # Convert VmSize to MB or KB
                        elif line.startswith("VmExe:"):
                            textsize = line.split(":")[1].strip().split()[0]  # Get VmExe in KB
                            textsize = self._kb_to_mb(int(textsize))  # Convert VmExe to MB or KB
                        elif line.startswith("VmData:"):
                            datasize = line.split(":")[1].strip().split()[0]
                            datasize = self._kb_to_mb(int(datasize))  # Convert VmData to MB or KB
                        elif line.startswith("VmStk:"):
                            stacksize = line.split(":")[1].strip().split()[0]
                            stacksize = self._kb_to_mb(int(stacksize))
                    
                with open(f"/proc/{pid}/statm", "r") as f:
                    data = f.read().split()
                    vmsize_pages, mem_pages = data[0], data[1]  # VmSize and VmRSS in pages
                
                with open(f"/proc/{pid}/stat", "r") as f:
                    data = f.read().split()
                    total_time = int(data[13]) + int(data[14])  # Total time spent in user and kernel mode (in jiffies)
                    cpu_usage = self._get_cpu_usage_process(int(pid), total_time)
                    priority = int(data[17])
                    nice = int(data[18])
                    start_time = int(data[21]) / self.CLK_TCK_PS  # Start time in seconds (since system boot)
                    run_time = time.time() - start_time  # Runtime in seconds
                    run_time = time.strftime("%H:%M:%S", time.gmtime(run_time))  # Format runtime as HH:MM:SS

                threads = self._get_threads_data(pid)
                
                self.specific_processes_dict[pid] = (int(pid), name, username, cpu_usage, status, num_threads, priority, nice, run_time,
                                                        memory, mem_pages, vmsize, vmsize_pages, textsize, datasize, stacksize,
                                                        threads)
            except FileNotFoundError:
                # Process have terminated, data will be null
                self.specific_processes_dict[pid] = (None, None, None, None, None, None, None, None, None,
                                                        None, None, None, None, None, None, None, None)
                continue

        # Return the data for the specific processes currently being monitored
        return self.specific_processes_dict
    
    def _get_general_stats_data(self):
        pass

    def _uid_to_username(self, uid):
        """
        Convert UID to username.
        """
        try:
            with open(f"/etc/passwd", "r") as f:
                for line in f:
                    if str(uid) in line:
                        return line.split(":")[0]
            return str(uid)  # If UID not found, return UID as string
        except FileNotFoundError:
            return str(uid)
    
    def _get_process_status(self, status):
        """
        Convert process status code to human-readable format.
        """
        status_map = {
            "R": "Running",
            "S": "Sleeping",
            "D": "Uninterruptible Sleep",
            "T": "Stopped",
            "Z": "Zombie"
        }
        return status_map.get(status, "Unknown")

    def _kb_to_mb(self, kb):
        """
        Convert kilobytes to megabytes.
        """
        if kb > 1024:
            return f"{kb / 1024:.2f} MB"
        else:
            return f"{kb} KB"
    
    def _get_cpu_usage_process(self, id, total_time, is_thread=False):
        """
        Get (instantaneous) CPU usage for a specific process.
        """
        # try:
        #     with open(f"/proc/{pid}/stat", "r") as f:
        #         data = f.read().split()
        #         utime = int(data[13])  # Time the process spent in user mode
        #         stime = int(data[14])  # Time the process spent in kernel mode
        #         total_time = utime + stime  # Total time spent in user and kernel mode (in jiffies)
        # except:
        #     return 0.0
        
        current_time = time.time()
        if is_thread:
            # For threads, we use the previous thread data
            prev_total_time, prev_time = self.prev_thrd_data.get(id, (0, current_time))
        else:
            prev_total_time, prev_time = self.prev_proc_data.get(id, (0, current_time))

        delta_cpu_time = (total_time - prev_total_time)/self.CLK_TCK_PS  # Variation in CPU time since last check (in seconds)
        elapsed_time = current_time - prev_time     # Elapsed time since last check (in seconds)

        if is_thread:
            self.prev_thrd_data.update({id: (total_time, current_time)})
        else:
            self.prev_proc_data.update({id: (total_time, current_time)})   # Update previous data for the process

        # Prevent division by zero
        if elapsed_time <= 0:
            return 0.0
        
        cpu_usage = (delta_cpu_time / elapsed_time) * 100.0
        return round(cpu_usage, 2)
    
    def _get_threads_data(self, pid):
        """
        Get threads data for a specific process.
        """
        threads = []
        try:
            entries = self.ctypes_functions.list_directory(f"/proc/{pid}/task")
            for entry in entries:
                if entry.isdigit():  # Check if the entry is a digit (TID)
                    tid = int(entry)
                    with open(f"/proc/{pid}/task/{tid}/status", "r") as f:
                        for line in f:
                            if line.startswith("Name:"):
                                name = line.split(":")[1].strip()
                            elif line.startswith("State:"):
                                status = line.split(":")[1].strip().split()[0]
                                status = self._get_process_status(status)
                            elif line.startswith("Uid:"):
                                userid = line.split(":")[1].split()[0]
                                username = self._uid_to_username(userid)
                            elif line.startswith("VmRSS:"):
                                memory = line.split(":")[1].strip().split()[0]
                                memory = self._kb_to_mb(int(memory))  # Convert memory to MB or KB
                    
                    with open(f"/proc/{pid}/task/{tid}/stat", "r") as f:
                        data = f.read().split()
                        total_time = int(data[13]) + int(data[14])
                        cpu_usage = self._get_cpu_usage_process(tid, total_time, is_thread=True)

                    threads.append((tid, name, username, memory, cpu_usage, status))
        except FileNotFoundError:
            pass
        return threads