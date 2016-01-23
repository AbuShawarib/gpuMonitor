from gi.repository import Gtk, GObject
import pynvml

class MonitorWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="GPU Monitor")
        self.set_border_width(12)
        self.set_resizable(False)
        self.set_icon_name("utilities-system-monitor")
        self.set_position(Gtk.WindowPosition.CENTER)
        
        notebook = Gtk.Notebook()
        
        util_page = Gtk.Box(spacing=24)
        util_page.set_border_width(12)
        procs_page = Gtk.Box(spacing=8)
        procs_page.set_border_width(0)
        
        self.init()
        
        #util_page
        for box in self.gpu_boxes:
            util_page.pack_start(box, True, True, 0)
        util_page.pack_start(self.cpu_box, True, True, 0)
        
        #procs_page
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add_with_viewport(self.tree)
        procs_page.pack_start(scroll, True, True, 0)
        
        #notebook
        notebook.append_page(util_page, Gtk.Label("Utilization"))
        notebook.append_page(procs_page, Gtk.Label("Processes"))
        self.add(notebook)
        
        self.timeout_id = GObject.timeout_add(1000, self.info_refresh)
        
        self.info_refresh()
        
        self.connect("delete-event", self.exit)
        self.show_all()
#
# Refresh stats
#
    def info_refresh(self):
        
        try:
            stat = open("/proc/stat")
            
            self.statlines = stat.read().splitlines()[1:-1]
            stat.close()
            
        except IOError:
            print("Problem opening /proc/stat, exiting..")
            pynvml.nvmlShutdown()
            quit()
        
        for i in range(self.corecount):
            for j in self.statlines[i].split()[1:]: #remove cpu#
               self.total[i]+= int(j)
            self.idle[i] = int(self.statlines[i].split()[4])
        
        for i in range(self.corecount):
            if (self.total[i] - self.prev_total[i]) == 0:
                self.prev_idle[i] = self.idle[i]
                self.prev_total[i] = self.total[i]
                break
            
            self.cpu_prog_bars[i].set_fraction(1 - ((self.idle[i] - self.prev_idle[i]) / (self.total[i] - self.prev_total[i])) )
            self.prev_idle[i] = self.idle[i]
            self.prev_total[i] = self.total[i]
            self.idle[i] = 0
            self.total[i] = 0
        
        for i in range(self.deviceCount):
            
            util = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handles[i])
            temp = pynvml.nvmlDeviceGetTemperature(self.gpu_handles[i], pynvml.NVML_TEMPERATURE_GPU)
            memInfo = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handles[i])
            (encoder_util, sPeriod) = pynvml.nvmlDeviceGetEncoderUtilization(self.gpu_handles[i])
            (decoder_util, sPeriod) = pynvml.nvmlDeviceGetDecoderUtilization(self.gpu_handles[i])
            
            mem_total = memInfo.total / 1024 / 1024
            mem_used = memInfo.used / 1024 / 1024
            
            self.gpu_prog_bars[i*6].set_text("GPU: %d%%" % util.gpu)
            self.gpu_prog_bars[i*6].set_fraction(util.gpu / 100)
            
            self.gpu_prog_bars[i*6 +1].set_text("Memory Utilization: %d%%" % util.memory)
            self.gpu_prog_bars[i*6 +1].set_fraction(util.memory / 100)
            
            self.gpu_prog_bars[i*6 +4].set_text("Encoder: %d%%" % encoder_util)
            self.gpu_prog_bars[i*6 +5].set_text("Decoder: %d%%" % decoder_util)
            self.gpu_prog_bars[i*6 +4].set_fraction(encoder_util / 100)
            self.gpu_prog_bars[i*6 +5].set_fraction(decoder_util / 100)
            
            self.gpu_prog_bars[i*6 +2].set_text("Memory Usage: %d MiB/%d MiB" % (mem_used, mem_total))
            self.gpu_prog_bars[i*6 +2].set_fraction(mem_used / mem_total)
            
            self.gpu_prog_bars[i*6 +3].set_text("Temperature: %d °C" % temp)
            if temp > 100:
               temp = 100
            elif temp < 0:
                temp = 0
            self.gpu_prog_bars[i*6 +3].set_fraction(temp / 100)
            
            
        #--proc--
        procs = pynvml.nvmlDeviceGetGraphicsRunningProcesses(self.gpu_handles[0])
        
        proc_liststore = Gtk.ListStore(int, str, int)
        
        for p in procs:
            pid = p.pid
            path = pynvml.nvmlSystemGetProcessName(p.pid).decode('utf-8')
            if (p.usedGpuMemory == None):
                mem = 0
            else:
                mem = (p.usedGpuMemory / 1024 / 1024)
            proc_liststore.append([pid, path, mem])
        self.tree.set_model(proc_liststore)
        return True
#
# init
#
    def init(self):

        pynvml.nvmlInit()
        self.gpu_handles = []
        self.deviceCount = pynvml.nvmlDeviceGetCount()
        
        for i in range(self.deviceCount):
            self.gpu_handles.append(pynvml.nvmlDeviceGetHandleByIndex(i))
        
        self.cpu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.cpu_prog_bars = []
        self.gpu_boxes = []
        self.gpu_prog_bars = []
        
        self.prev_idle = []
        self.prev_total = []
        self.idle = []
        self.total = []
        
        #---cpu_box---
        try:
            stat = open("/proc/stat")
            
            statlines = stat.read().splitlines()
            stat.close()
            
            self.corecount = -1
            
            for line in statlines:
                if (line[0:2] == "cp"):
                    self.corecount+= 1
                else:
                    break
            
        except IOError:
            print("Problem opening /proc/stat, exiting..")
            pynvml.nvmlShutdown()
            quit()
        
        for i in range(self.corecount):
            self.cpu_prog_bars.append(Gtk.ProgressBar(text="CPU %d" % i, show_text=True))
            self.cpu_box.pack_start(self.cpu_prog_bars[i], True, True, 0)
            
            self.prev_idle.append(0)
            self.prev_total.append(0)
            self.idle.append(0)
            self.total.append(0)
        
        #---gpu_boxes---
        for i in range(self.deviceCount):
            product_name = pynvml.nvmlDeviceGetName(self.gpu_handles[i])
            product_name = product_name.decode('utf-8')
            
            gpu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            
            label = Gtk.Label(product_name)
            
            self.gpu_prog_bars.append(Gtk.ProgressBar(text="GPU", show_text=True))
            self.gpu_prog_bars.append(Gtk.ProgressBar(text="Memory Utilization", show_text=True))
            self.gpu_prog_bars.append(Gtk.ProgressBar(text="Memory Usage", show_text=True))
            self.gpu_prog_bars.append(Gtk.ProgressBar(text="Temperature", show_text=True))
            self.gpu_prog_bars.append(Gtk.ProgressBar(text="Encoder", show_text=True))
            self.gpu_prog_bars.append(Gtk.ProgressBar(text="Decoder", show_text=True))
            
            gpu_box.pack_start(label, True, True, 0)
            gpu_box.pack_start(self.gpu_prog_bars[i*6], True, True, 0)
            gpu_box.pack_start(self.gpu_prog_bars[i*6 +1], True, True, 0)
            gpu_box.pack_start(self.gpu_prog_bars[i*6 +2], True, True, 0)
            gpu_box.pack_start(self.gpu_prog_bars[i*6 +3], True, True, 0)
            gpu_box.pack_start(self.gpu_prog_bars[i*6 +4], True, True, 0)
            gpu_box.pack_start(self.gpu_prog_bars[i*6 +5], True, True, 0)
            
            self.gpu_boxes.append(gpu_box)
        
        #---proc---
        proc_liststore = Gtk.ListStore(int, str, int)
        
        self.tree = Gtk.TreeView(model=proc_liststore)
        
        renderer_pid = Gtk.CellRendererText()
        column_pid = Gtk.TreeViewColumn("Proccess ID", renderer_pid, text=0)
        column_pid.set_resizable(True)
        self.tree.append_column(column_pid)
        
        renderer_path = Gtk.CellRendererText()
        column_path = Gtk.TreeViewColumn("Command Line", renderer_path, text=1)
        column_path.set_resizable(True)
        column_path.set_fixed_width(250)
        self.tree.append_column(column_path)
        
        renderer_mem = Gtk.CellRendererText()
        column_mem = Gtk.TreeViewColumn("Memory (MiB)", renderer_mem, text=2)
        column_mem.set_resizable(True)
        self.tree.append_column(column_mem)
    
    def exit(self, widget, ev):
        pynvml.nvmlShutdown()
        Gtk.main_quit()
        quit()
#
# Instance creation
#       
win = MonitorWindow()
Gtk.main()
