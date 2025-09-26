import tkinter as tk
import matplotlib.pyplot as plt
from tkinter import ttk, messagebox, filedialog
import pyvisa
import numpy as np
import threading
import time
import csv
from datetime import datetime
import logging

class KeithleySMUController:
    def __init__(self, root):
        self.root = root
        self.root.title("Keithley SMU Control - Professional Edition with ReRAM Testing")
        self.root.geometry("1400x900")
        
        # Initialize variables
        self.rm = None
        self.smu = None
        self.connected = False
        self.measurement_running = False
        self.data_points = []
        
        # Model identification variables
        self.model = None
        self.series_2400 = False
        self.series_2600 = False
        self.data_format_set = False
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Create the GUI
        self.create_gui()
    
    def create_gui(self):
        """Create the main GUI layout"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Connection Section
        self.create_connection_section(main_frame)
        
        # Control Tabs
        self.create_control_tabs(main_frame)
        
        # Results and plotting area
        self.create_results_section(main_frame)
        
        # Status bar
        self.create_status_bar(main_frame)
    
    def create_connection_section(self, parent):
        """Create connection control section"""
        conn_frame = ttk.LabelFrame(parent, text="Instrument Connection", padding="10")
        conn_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Address entry
        ttk.Label(conn_frame, text="VISA Address:").grid(row=0, column=0, sticky=tk.W)
        self.address_var = tk.StringVar(value="GPIB0::24::INSTR")
        address_entry = ttk.Entry(conn_frame, textvariable=self.address_var, width=30)
        address_entry.grid(row=0, column=1, padx=(5, 10))
        
        # Scan button
        ttk.Button(conn_frame, text="Scan", command=self.scan_instruments).grid(row=0, column=2, padx=(0, 10))
        
        # Connect/Disconnect buttons
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect_instrument)
        self.connect_btn.grid(row=0, column=3, padx=(0, 5))
        
        self.disconnect_btn = ttk.Button(conn_frame, text="Disconnect", command=self.disconnect_instrument, state=tk.DISABLED)
        self.disconnect_btn.grid(row=0, column=4)
        
        # Connection status
        self.conn_status_var = tk.StringVar(value="Disconnected")
        self.conn_status_label = ttk.Label(conn_frame, textvariable=self.conn_status_var, foreground="red")
        self.conn_status_label.grid(row=1, column=0, columnspan=5, pady=(5, 0))
        
        # Model info
        self.model_info_var = tk.StringVar(value="Model: Unknown")
        ttk.Label(conn_frame, textvariable=self.model_info_var, font=("Arial", 8)).grid(row=2, column=0, columnspan=5, pady=(2, 0))
    
    def create_control_tabs(self, parent):
        """Create control tabs for different measurement modes"""
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # I-V Characterization Tab
        self.create_iv_tab()
        
        # DC Bias Tab
        self.create_dc_bias_tab()
        
        # Resistance Measurement Tab
        self.create_resistance_tab()
        
        # Memristor Testing Tab (replacing pulse and battery tabs)
        self.create_memristor_tab()
    
    def create_iv_tab(self):
        """Create I-V characterization tab"""
        iv_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(iv_frame, text="I-V Characterization")
        
        # Sweep parameters
        params_frame = ttk.LabelFrame(iv_frame, text="Sweep Parameters", padding="10")
        params_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Source type
        ttk.Label(params_frame, text="Source Type:").grid(row=0, column=0, sticky=tk.W)
        self.iv_source_type = tk.StringVar(value="Voltage")
        ttk.Combobox(params_frame, textvariable=self.iv_source_type, values=["Voltage", "Current"], state="readonly").grid(row=0, column=1, padx=(5, 0))
        
        # Start value
        ttk.Label(params_frame, text="Start Value:").grid(row=1, column=0, sticky=tk.W)
        self.iv_start = tk.StringVar(value="0")
        ttk.Entry(params_frame, textvariable=self.iv_start, width=15).grid(row=1, column=1, padx=(5, 0))
        
        # Stop value
        ttk.Label(params_frame, text="Stop Value:").grid(row=2, column=0, sticky=tk.W)
        self.iv_stop = tk.StringVar(value="5")
        ttk.Entry(params_frame, textvariable=self.iv_stop, width=15).grid(row=2, column=1, padx=(5, 0))
        
        # Number of points
        ttk.Label(params_frame, text="Points:").grid(row=3, column=0, sticky=tk.W)
        self.iv_points = tk.StringVar(value="101")
        ttk.Entry(params_frame, textvariable=self.iv_points, width=15).grid(row=3, column=1, padx=(5, 0))
        
        # Compliance
        ttk.Label(params_frame, text="Compliance (A):").grid(row=4, column=0, sticky=tk.W)
        self.iv_compliance = tk.StringVar(value="0.1")
        ttk.Entry(params_frame, textvariable=self.iv_compliance, width=15).grid(row=4, column=1, padx=(5, 0))
        
        # Current Range (NEW)
        ttk.Label(params_frame, text="Current Range (A):").grid(row=5, column=0, sticky=tk.W)
        self.iv_current_range = tk.StringVar(value="AUTO")
        current_range_combo = ttk.Combobox(params_frame, textvariable=self.iv_current_range, 
                                         values=["AUTO", "1e-9", "1e-8", "1e-7", "1e-6", "1e-5", "1e-4", "1e-3", "1e-2", "1e-1", "1"], 
                                         width=12)
        current_range_combo.grid(row=5, column=1, padx=(5, 0))
        
        # Delay
        ttk.Label(params_frame, text="Delay (s):").grid(row=6, column=0, sticky=tk.W)
        self.iv_delay = tk.StringVar(value="0.1")
        ttk.Entry(params_frame, textvariable=self.iv_delay, width=15).grid(row=6, column=1, padx=(5, 0))
        
        # Control buttons
        btn_frame = ttk.Frame(iv_frame)
        btn_frame.grid(row=1, column=0, pady=(10, 0))
        
        self.iv_start_btn = ttk.Button(btn_frame, text="Start I-V Sweep", command=self.start_iv_sweep)
        self.iv_start_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.iv_stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_measurement, state=tk.DISABLED)
        self.iv_stop_btn.grid(row=0, column=1)
    
    def create_dc_bias_tab(self):
        """Create DC bias tab"""
        dc_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(dc_frame, text="DC Bias")
        
        # Bias parameters
        params_frame = ttk.LabelFrame(dc_frame, text="Bias Parameters", padding="10")
        params_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Source type
        ttk.Label(params_frame, text="Source Type:").grid(row=0, column=0, sticky=tk.W)
        self.dc_source_type = tk.StringVar(value="Voltage")
        ttk.Combobox(params_frame, textvariable=self.dc_source_type, values=["Voltage", "Current"], state="readonly").grid(row=0, column=1, padx=(5, 0))
        
        # Bias value
        ttk.Label(params_frame, text="Bias Value:").grid(row=1, column=0, sticky=tk.W)
        self.dc_value = tk.StringVar(value="0")
        ttk.Entry(params_frame, textvariable=self.dc_value, width=15).grid(row=1, column=1, padx=(5, 0))
        
        # Compliance
        ttk.Label(params_frame, text="Compliance (A):").grid(row=2, column=0, sticky=tk.W)
        self.dc_compliance = tk.StringVar(value="0.1")
        ttk.Entry(params_frame, textvariable=self.dc_compliance, width=15).grid(row=2, column=1, padx=(5, 0))
        
        # Current Range
        ttk.Label(params_frame, text="Current Range (A):").grid(row=3, column=0, sticky=tk.W)
        self.dc_current_range = tk.StringVar(value="AUTO")
        ttk.Combobox(params_frame, textvariable=self.dc_current_range, 
                    values=["AUTO", "1e-9", "1e-8", "1e-7", "1e-6", "1e-5", "1e-4", "1e-3", "1e-2", "1e-1", "1"], 
                    width=12).grid(row=3, column=1, padx=(5, 0))
        
        # Control buttons
        btn_frame = ttk.Frame(dc_frame)
        btn_frame.grid(row=1, column=0, pady=(10, 0))
        
        self.dc_apply_btn = ttk.Button(btn_frame, text="Apply Bias", command=self.apply_dc_bias)
        self.dc_apply_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.dc_output_btn = ttk.Button(btn_frame, text="Output Off", command=self.toggle_output)
        self.dc_output_btn.grid(row=0, column=1)
    
    def create_resistance_tab(self):
        """Create resistance measurement tab"""
        res_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(res_frame, text="Resistance")
        
        # Measurement parameters
        params_frame = ttk.LabelFrame(res_frame, text="Resistance Parameters", padding="10")
        params_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Wire mode
        ttk.Label(params_frame, text="Wire Mode:").grid(row=0, column=0, sticky=tk.W)
        self.res_wire_mode = tk.StringVar(value="2-Wire")
        ttk.Combobox(params_frame, textvariable=self.res_wire_mode, values=["2-Wire", "4-Wire"], state="readonly").grid(row=0, column=1, padx=(5, 0))
        
        # Test current
        ttk.Label(params_frame, text="Test Current (A):").grid(row=1, column=0, sticky=tk.W)
        self.res_current = tk.StringVar(value="0.001")
        ttk.Entry(params_frame, textvariable=self.res_current, width=15).grid(row=1, column=1, padx=(5, 0))
        
        # Control buttons
        btn_frame = ttk.Frame(res_frame)
        btn_frame.grid(row=1, column=0, pady=(10, 0))
        
        self.res_measure_btn = ttk.Button(btn_frame, text="Measure Resistance", command=self.measure_resistance)
        self.res_measure_btn.grid(row=0, column=0)
    
    def create_memristor_tab(self):
        """Create memristor/ReRAM testing tab"""
        mem_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(mem_frame, text="Memristor/ReRAM Testing")
        
        # Create sub-notebooks for different memristor tests
        mem_notebook = ttk.Notebook(mem_frame)
        mem_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), columnspan=2)
        
        # IV Loop Testing Tab
        self.create_iv_loop_tab(mem_notebook)
        
        # Retention Testing Tab
        self.create_retention_tab(mem_notebook)
        
        # Endurance Testing Tab
        self.create_endurance_tab(mem_notebook)
        
        mem_frame.columnconfigure(0, weight=1)
        mem_frame.rowconfigure(0, weight=1)
    
    def create_iv_loop_tab(self, parent):
        """Create IV loop testing tab for memristors"""
        loop_frame = ttk.Frame(parent, padding="10")
        parent.add(loop_frame, text="IV Loop Testing")
        
        # Parameters frame
        params_frame = ttk.LabelFrame(loop_frame, text="IV Loop Parameters", padding="10")
        params_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Positive voltage limit
        ttk.Label(params_frame, text="Positive Voltage Limit (V):").grid(row=0, column=0, sticky=tk.W)
        self.loop_vpos = tk.StringVar(value="2.0")
        ttk.Entry(params_frame, textvariable=self.loop_vpos, width=15).grid(row=0, column=1, padx=(5, 0))
        
        # Negative voltage limit
        ttk.Label(params_frame, text="Negative Voltage Limit (V):").grid(row=1, column=0, sticky=tk.W)
        self.loop_vneg = tk.StringVar(value="-2.0")
        ttk.Entry(params_frame, textvariable=self.loop_vneg, width=15).grid(row=1, column=1, padx=(5, 0))
        
        # Points per segment
        ttk.Label(params_frame, text="Points per Segment:").grid(row=2, column=0, sticky=tk.W)
        self.loop_points = tk.StringVar(value="50")
        ttk.Entry(params_frame, textvariable=self.loop_points, width=15).grid(row=2, column=1, padx=(5, 0))
        
        # Current compliance
        ttk.Label(params_frame, text="Current Compliance (A):").grid(row=3, column=0, sticky=tk.W)
        self.loop_compliance = tk.StringVar(value="0.01")
        ttk.Entry(params_frame, textvariable=self.loop_compliance, width=15).grid(row=3, column=1, padx=(5, 0))
        
        # Current Range
        ttk.Label(params_frame, text="Current Range (A):").grid(row=4, column=0, sticky=tk.W)
        self.loop_current_range = tk.StringVar(value="AUTO")
        ttk.Combobox(params_frame, textvariable=self.loop_current_range, 
                    values=["AUTO", "1e-9", "1e-8", "1e-7", "1e-6", "1e-5", "1e-4", "1e-3", "1e-2", "1e-1", "1"], 
                    width=12).grid(row=4, column=1, padx=(5, 0))
        
        # Delay between points
        ttk.Label(params_frame, text="Delay (s):").grid(row=5, column=0, sticky=tk.W)
        self.loop_delay = tk.StringVar(value="0.05")
        ttk.Entry(params_frame, textvariable=self.loop_delay, width=15).grid(row=5, column=1, padx=(5, 0))
        
        # Number of loops
        ttk.Label(params_frame, text="Number of Loops:").grid(row=6, column=0, sticky=tk.W)
        self.loop_cycles = tk.StringVar(value="5")
        ttk.Entry(params_frame, textvariable=self.loop_cycles, width=15).grid(row=6, column=1, padx=(5, 0))
        
        # Control buttons
        btn_frame = ttk.Frame(loop_frame)
        btn_frame.grid(row=1, column=0, pady=(10, 0))
        
        self.loop_start_btn = ttk.Button(btn_frame, text="Start IV Loop Test", command=self.start_iv_loop)
        self.loop_start_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.loop_stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_measurement, state=tk.DISABLED)
        self.loop_stop_btn.grid(row=0, column=1)
    
    def create_retention_tab(self, parent):
        """Create retention testing tab for memristors"""
        ret_frame = ttk.Frame(parent, padding="10")
        parent.add(ret_frame, text="Retention Testing")
        
        # Parameters frame
        params_frame = ttk.LabelFrame(ret_frame, text="Retention Test Parameters", padding="10")
        params_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # SET voltage
        ttk.Label(params_frame, text="SET Voltage (V):").grid(row=0, column=0, sticky=tk.W)
        self.ret_vset = tk.StringVar(value="2.0")
        ttk.Entry(params_frame, textvariable=self.ret_vset, width=15).grid(row=0, column=1, padx=(5, 0))
        
        # RESET voltage
        ttk.Label(params_frame, text="RESET Voltage (V):").grid(row=1, column=0, sticky=tk.W)
        self.ret_vreset = tk.StringVar(value="-2.0")
        ttk.Entry(params_frame, textvariable=self.ret_vreset, width=15).grid(row=1, column=1, padx=(5, 0))
        
        # Read voltage
        ttk.Label(params_frame, text="Read Voltage (V):").grid(row=2, column=0, sticky=tk.W)
        self.ret_vread = tk.StringVar(value="0.1")
        ttk.Entry(params_frame, textvariable=self.ret_vread, width=15).grid(row=2, column=1, padx=(5, 0))
        
        # Current compliance
        ttk.Label(params_frame, text="Current Compliance (A):").grid(row=3, column=0, sticky=tk.W)
        self.ret_compliance = tk.StringVar(value="0.01")
        ttk.Entry(params_frame, textvariable=self.ret_compliance, width=15).grid(row=3, column=1, padx=(5, 0))
        
        # Test duration
        ttk.Label(params_frame, text="Test Duration (s):").grid(row=4, column=0, sticky=tk.W)
        self.ret_duration = tk.StringVar(value="300")
        ttk.Entry(params_frame, textvariable=self.ret_duration, width=15).grid(row=4, column=1, padx=(5, 0))
        
        # Read interval
        ttk.Label(params_frame, text="Read Interval (s):").grid(row=5, column=0, sticky=tk.W)
        self.ret_interval = tk.StringVar(value="10")
        ttk.Entry(params_frame, textvariable=self.ret_interval, width=15).grid(row=5, column=1, padx=(5, 0))
        
        # Control buttons
        btn_frame = ttk.Frame(ret_frame)
        btn_frame.grid(row=1, column=0, pady=(10, 0))
        
        self.ret_start_btn = ttk.Button(btn_frame, text="Start Retention Test", command=self.start_retention_test)
        self.ret_start_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.ret_stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_measurement, state=tk.DISABLED)
        self.ret_stop_btn.grid(row=0, column=1)
    
    def create_endurance_tab(self, parent):
        """Create endurance testing tab for memristors"""
        end_frame = ttk.Frame(parent, padding="10")
        parent.add(end_frame, text="Endurance Testing")
        
        # Parameters frame
        params_frame = ttk.LabelFrame(end_frame, text="Endurance Test Parameters", padding="10")
        params_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # SET voltage
        ttk.Label(params_frame, text="SET Voltage (V):").grid(row=0, column=0, sticky=tk.W)
        self.end_vset = tk.StringVar(value="2.0")
        ttk.Entry(params_frame, textvariable=self.end_vset, width=15).grid(row=0, column=1, padx=(5, 0))
        
        # RESET voltage
        ttk.Label(params_frame, text="RESET Voltage (V):").grid(row=1, column=0, sticky=tk.W)
        self.end_vreset = tk.StringVar(value="-2.0")
        ttk.Entry(params_frame, textvariable=self.end_vreset, width=15).grid(row=1, column=1, padx=(5, 0))
        
        # Read voltage
        ttk.Label(params_frame, text="Read Voltage (V):").grid(row=2, column=0, sticky=tk.W)
        self.end_vread = tk.StringVar(value="0.1")
        ttk.Entry(params_frame, textvariable=self.end_vread, width=15).grid(row=2, column=1, padx=(5, 0))
        
        # Current compliance
        ttk.Label(params_frame, text="Current Compliance (A):").grid(row=3, column=0, sticky=tk.W)
        self.end_compliance = tk.StringVar(value="0.01")
        ttk.Entry(params_frame, textvariable=self.end_compliance, width=15).grid(row=3, column=1, padx=(5, 0))
        
        # Number of cycles
        ttk.Label(params_frame, text="Number of Cycles:").grid(row=4, column=0, sticky=tk.W)
        self.end_cycles = tk.StringVar(value="1000")
        ttk.Entry(params_frame, textvariable=self.end_cycles, width=15).grid(row=4, column=1, padx=(5, 0))
        
        # Pulse width
        ttk.Label(params_frame, text="Pulse Width (s):").grid(row=5, column=0, sticky=tk.W)
        self.end_pulse_width = tk.StringVar(value="0.001")
        ttk.Entry(params_frame, textvariable=self.end_pulse_width, width=15).grid(row=5, column=1, padx=(5, 0))
        
        # Control buttons
        btn_frame = ttk.Frame(end_frame)
        btn_frame.grid(row=1, column=0, pady=(10, 0))
        
        self.end_start_btn = ttk.Button(btn_frame, text="Start Endurance Test", command=self.start_endurance_test)
        self.end_start_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.end_stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_measurement, state=tk.DISABLED)
        self.end_stop_btn.grid(row=0, column=1)
    
    def create_results_section(self, parent):
        """Create results and plotting section"""
        results_frame = ttk.LabelFrame(parent, text="Measurement Results", padding="10")
        results_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Create notebook for results
        results_notebook = ttk.Notebook(results_frame)
        results_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Data table tab - Updated with more columns
        table_frame = ttk.Frame(results_notebook)
        results_notebook.add(table_frame, text="Data Table")
        
        # Create treeview for data
        columns = ('Time', 'Voltage', 'Current', 'Resistance', 'Cycle', 'State', 'Extra')
        self.data_tree = ttk.Treeview(table_frame, columns=columns, show='headings')
        for col in columns:
            self.data_tree.heading(col, text=col)
            if col == 'Time':
                self.data_tree.column(col, width=100)
            elif col in ['Voltage', 'Current', 'Resistance']:
                self.data_tree.column(col, width=120)
            else:
                self.data_tree.column(col, width=80)
        
        self.data_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbars for treeview
        v_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.data_tree.yview)
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.data_tree.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.data_tree.xview)
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.data_tree.configure(xscrollcommand=h_scrollbar.set)
        
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # Plot info tab
        plot_frame = ttk.Frame(results_notebook)
        results_notebook.add(plot_frame, text="Plot Info")
        
        plot_info = ttk.Label(plot_frame, text="Plotting Information:\n\n" +
                             "Data visualization can be added using matplotlib.\n" +
                             "Current version saves data to CSV for external analysis.\n\n" +
                             "To add live plotting:\n" +
                             "1. Install matplotlib: pip install matplotlib\n" +
                             "2. Import FigureCanvasTkAgg\n" +
                             "3. Create embedded plots in this tab\n\n" +
                             "Memristor-specific plots:\n" +
                             "- IV loop hysteresis curves\n" +
                             "- Retention vs time plots\n" +
                             "- Endurance resistance vs cycle plots",
                             justify=tk.LEFT)
        plot_info.grid(row=0, column=0, padx=20, pady=20, sticky=tk.W)
        
        # Data export controls
        export_frame = ttk.Frame(results_frame)
        export_frame.grid(row=1, column=0, pady=(10, 0))
        
        ttk.Button(export_frame, text="Export CSV", command=self.export_csv).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(export_frame, text="Clear Data", command=self.clear_data).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(export_frame, text="Plot Data (External)", command=self.plot_external).grid(row=0, column=2)
    
    def create_status_bar(self, parent):
        """Create status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var).grid(row=0, column=0, sticky=tk.W)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=1, padx=(20, 0), sticky=(tk.W, tk.E))
        status_frame.columnconfigure(1, weight=1)
    
    def scan_instruments(self):
        """Scan for available VISA instruments"""
        try:
            if self.rm is None:
                self.rm = pyvisa.ResourceManager()
            
            resources = self.rm.list_resources()
            if resources:
                # Create a simple selection dialog
                selection_window = tk.Toplevel(self.root)
                selection_window.title("Select Instrument")
                selection_window.geometry("500x350")
                
                ttk.Label(selection_window, text="Available Instruments:").pack(pady=10)
                
                listbox = tk.Listbox(selection_window)
                listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                for resource in resources:
                    listbox.insert(tk.END, resource)
                
                def select_instrument():
                    if listbox.curselection():
                        selected = listbox.get(listbox.curselection()[0])
                        self.address_var.set(selected)
                        selection_window.destroy()
                
                ttk.Button(selection_window, text="Select", command=select_instrument).pack(pady=10)
            else:
                messagebox.showinfo("Scan Results", "No VISA instruments found")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error scanning instruments: {str(e)}")
    
    def connect_instrument(self):
        """Connect to the SMU instrument"""
        try:
            if self.rm is None:
                self.rm = pyvisa.ResourceManager()
            
            address = self.address_var.get()
            self.smu = self.rm.open_resource(address)
            self.smu.timeout = 30000  # 30 second timeout
            
            # Test connection
            idn = self.smu.query("*IDN?")
            self.connected = True
            
            # Identify model family
            self.model = idn.strip()
            m = self.model.lower()
            self.series_2400 = ('keithley' in m and any(x in m for x in ['2400', '2450', '2460', '2470']))
            self.series_2600 = ('keithley' in m and any(x in m for x in ['2601', '2602', '2612', '2636']))
            
            self.conn_status_var.set(f"Connected: {idn.strip()[:50]}...")
            self.conn_status_label.config(foreground="green")
            self.model_info_var.set(f"Model: {self.model[:60]}...")
            
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            self.status_var.set("Instrument connected successfully")
            
            # Configure instrument
            self._configure_instrument()
            
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            self.status_var.set("Connection failed")
    
    def _configure_instrument(self):
        """Configure the instrument after connection"""
        try:
            # Reset instrument
            self.smu.write("*RST")
            time.sleep(1)
            
            # Clear errors
            try:
                self.smu.write("*CLS")
                if self.series_2400:
                    self.smu.write(":SYST:CLE")
            except Exception:
                pass
            
            # Set consistent data format for :READ?
            try:
                if self.series_2400:
                    self.smu.write(":FORM:ELEM VOLT,CURR,TIME")
                    self.data_format_set = True
                elif self.series_2600:
                    self.smu.write("format.data = format.ASCII")
                    self.data_format_set = True
            except Exception:
                self.logger.warning("Could not set data format, using default parsing")
                self.data_format_set = False
            
            # Initialize source to voltage mode, 0V
            self.smu.write(":SOUR:FUNC VOLT")
            self.smu.write(":SOUR:VOLT:LEV 0")
            self.smu.write(":OUTP OFF")
            
            self.logger.info("Instrument configured successfully")
            
        except Exception as e:
            self.logger.error(f"Configuration error: {e}")
            messagebox.showwarning("Configuration Warning", 
                                 f"Instrument connected but some configuration failed: {str(e)}")
    
    def disconnect_instrument(self):
        """Disconnect from the SMU instrument"""
        try:
            # Stop any running measurement first
            self.measurement_running = False
            time.sleep(0.2)
            
            if self.smu:
                # Always turn off output before disconnecting
                self.smu.write(":OUTP OFF")
                time.sleep(0.1)
                self.smu.close()
                self.smu = None
            
            self.connected = False
            self.conn_status_var.set("Disconnected")
            self.conn_status_label.config(foreground="red")
            self.model_info_var.set("Model: Unknown")
            
            self.connect_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.DISABLED)
            self.status_var.set("Instrument disconnected")
            
        except Exception as e:
            self.logger.error(f"Disconnect error: {e}")
            messagebox.showerror("Disconnect Error", f"Error disconnecting: {str(e)}")
    
    def _safe_parse_reading(self, reading_str):
        """Safely parse instrument reading"""
        try:
            if self.data_format_set and self.series_2400:
                # Expected format: voltage,current,time
                parts = reading_str.strip().split(',')
                if len(parts) >= 2:
                    voltage = float(parts[0])
                    current = float(parts[1])
                    return voltage, current
            
            # Fallback parsing
            parts = reading_str.strip().split(',')
            if len(parts) >= 2:
                values = []
                for part in parts[:4]:
                    try:
                        val = float(part)
                        values.append(val)
                    except ValueError:
                        continue
                
                if len(values) >= 2:
                    return values[0], values[1]
            
            # If all else fails, return single value twice
            val = float(parts[0])
            return val, val
            
        except Exception as e:
            self.logger.error(f"Parse error for reading '{reading_str}': {e}")
            raise ValueError(f"Could not parse reading: {reading_str}")
    
    def _set_current_compliance_and_range(self, compliance_current, current_range="AUTO"):
        """Set both compliance current and measurement range properly - THIS IS THE KEY FIX"""
        try:
            # CRITICAL: Set both compliance and range for proper current measurement
            
            # 1. Set the source function to voltage
            self.smu.write(":SOUR:FUNC VOLT")
            
            # 2. Set current compliance (limit)
            if self.series_2400:
                self.smu.write(f":SOUR:VOLT:ILIM {compliance_current}")
                
                # 3. CRITICAL: Set current measurement range
                if current_range == "AUTO":
                    # Set range to accommodate the compliance current, but allow auto-ranging
                    self.smu.write(":SENS:CURR:RANG:AUTO ON")
                    # Set the upper limit of auto-ranging to include compliance current
                    range_value = max(compliance_current * 1.2, 1e-9)  # At least 1 nA range
                    self.smu.write(f":SENS:CURR:RANG:UPP {range_value}")
                else:
                    # Use fixed range
                    self.smu.write(":SENS:CURR:RANG:AUTO OFF")
                    range_value = float(current_range)
                    self.smu.write(f":SENS:CURR:RANG {range_value}")
                
                # 4. Set current protection level (additional safety)
                self.smu.write(f":SENS:CURR:PROT {compliance_current}")
                
            elif self.series_2600:
                # 2600 series uses different syntax
                self.smu.write(f"smua.source.limiti = {compliance_current}")
                if current_range != "AUTO":
                    self.smu.write(f"smua.measure.rangei = {current_range}")
                else:
                    self.smu.write("smua.measure.autorangei = smua.AUTORANGE_ON")
            else:
                # Generic SCPI fallback
                self.smu.write(f":SOUR:VOLT:ILIM {compliance_current}")
                if current_range != "AUTO":
                    self.smu.write(f":SENS:CURR:RANG {current_range}")
                    self.smu.write(":SENS:CURR:RANG:AUTO OFF")
                else:
                    self.smu.write(":SENS:CURR:RANG:AUTO ON")
            
            # 5. Set measurement function to current
            self.smu.write(":SENS:FUNC 'CURR'")
            
            # 6. Log the settings for verification
            self.logger.info(f"Set compliance current: {compliance_current} A, range: {current_range}")
            self.status_var.set(f"Compliance: {compliance_current} A, Range: {current_range}")
            
        except Exception as e:
            self.logger.error(f"Error setting compliance/range: {e}")
            raise Exception(f"Failed to set current compliance and range: {e}")
    
    def _set_wire_mode(self, mode):
        """Set 2-wire or 4-wire measurement mode"""
        try:
            if mode == "4-Wire" and self.series_2400:
                self.smu.write(":SENS:REM ON")
            else:
                if self.series_2400:
                    self.smu.write(":SENS:REM OFF")
        except Exception as e:
            self.logger.warning(f"Could not set wire mode to {mode}: {e}")
    
    def start_iv_sweep(self):
        """Start I-V characterization sweep"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to an instrument first")
            return
        
        try:
            # Get parameters
            source_type = self.iv_source_type.get()
            start_val = float(self.iv_start.get())
            stop_val = float(self.iv_stop.get())
            points = int(self.iv_points.get())
            compliance = float(self.iv_compliance.get())
            current_range = self.iv_current_range.get()
            delay = float(self.iv_delay.get())
            
            # Validate parameters
            if points <= 0:
                raise ValueError("Points must be greater than 0")
            if compliance <= 0:
                raise ValueError("Compliance must be greater than 0")
            if delay < 0:
                raise ValueError("Delay must be non-negative")
            
            # Start measurement in separate thread
            self.measurement_running = True
            self.iv_start_btn.config(state=tk.DISABLED)
            self.iv_stop_btn.config(state=tk.NORMAL)
            self.progress_var.set(0)
            
            thread = threading.Thread(target=self._perform_iv_sweep,
                                    args=(source_type, start_val, stop_val, points, compliance, current_range, delay))
            thread.daemon = True
            thread.start()
            
        except ValueError as e:
            messagebox.showerror("Parameter Error", f"Invalid parameter: {str(e)}")
        except Exception as e:
            self.logger.error(f"IV sweep start error: {e}")
            messagebox.showerror("Error", f"Error starting I-V sweep: {str(e)}")
    
    def _perform_iv_sweep(self, source_type, start_val, stop_val, points, compliance, current_range, delay):
        """Perform the actual I-V sweep measurement"""
        try:
            # Configure SMU with proper current range and compliance
            if source_type == "Voltage":
                self._set_current_compliance_and_range(compliance, current_range)
            else:
                self.smu.write(":SOUR:FUNC CURR")
                self.smu.write(f":SOUR:CURR:VLIM {compliance}")
                self.smu.write(":SENS:FUNC 'VOLT'")
            
            self.smu.write(":OUTP ON")
            time.sleep(0.1)
            
            # Generate sweep points
            sweep_values = np.linspace(start_val, stop_val, points)
            self.data_points.clear()
            
            for i, value in enumerate(sweep_values):
                if not self.measurement_running:
                    break
                
                # Set source value
                if source_type == "Voltage":
                    self.smu.write(f":SOUR:VOLT:LEV {value}")
                else:
                    self.smu.write(f":SOUR:CURR:LEV {value}")
                
                time.sleep(delay)
                
                # Read measurement
                reading = self.smu.query(":READ?")
                voltage, current = self._safe_parse_reading(reading)
                
                if source_type == "Voltage":
                    measured_value = current
                    resistance = abs(voltage / current) if abs(current) > 1e-12 else float('inf')
                else:
                    measured_value = voltage
                    resistance = abs(voltage / current) if abs(current) > 1e-12 else float('inf')
                
                # Store data point
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                self.data_points.append({
                    'timestamp': timestamp,
                    'voltage': voltage,
                    'current': current,
                    'resistance': resistance,
                    'cycle': 1,
                    'state': 'Sweep',
                    'extra': f"Point {i+1}"
                })
                
                # Update GUI
                progress = (i + 1) / points * 100
                self.root.after(0, self._update_progress, progress)
                self.root.after(0, self._update_data_table, timestamp, voltage, current, resistance, 1, 'Sweep', f"Point {i+1}")
                self.root.after(0, self.status_var.set, f"I-V Sweep: Point {i+1}/{points} - Current: {current:.3e} A")
                
        except Exception as e:
            self.logger.error(f"IV sweep error: {e}")
            self.root.after(0, messagebox.showerror, "Measurement Error", f"Error during I-V sweep: {str(e)}")
        finally:
            try:
                self.smu.write(":OUTP OFF")
            except Exception:
                pass
            self.root.after(0, self._sweep_completed)
    
    def apply_dc_bias(self):
        """Apply DC bias"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to an instrument first")
            return
        
        try:
            source_type = self.dc_source_type.get()
            value = float(self.dc_value.get())
            compliance = float(self.dc_compliance.get())
            current_range = self.dc_current_range.get()
            
            # Configure SMU
            if source_type == "Voltage":
                self._set_current_compliance_and_range(compliance, current_range)
                self.smu.write(f":SOUR:VOLT:LEV {value}")
            else:
                self.smu.write(":SOUR:FUNC CURR")
                self.smu.write(f":SOUR:CURR:LEV {value}")
                self.smu.write(f":SOUR:CURR:VLIM {compliance}")
            
            self.smu.write(":OUTP ON")
            self.status_var.set(f"Applied {source_type} bias: {value}, Compliance: {compliance} A")
            self.dc_output_btn.config(text="Output Off")
            
        except Exception as e:
            self.logger.error(f"DC bias error: {e}")
            messagebox.showerror("Error", f"Error applying bias: {str(e)}")
    
    def toggle_output(self):
        """Toggle SMU output on/off"""
        if not self.connected:
            return
        
        try:
            if self.dc_output_btn.cget('text') == "Output Off":
                self.smu.write(":OUTP OFF")
                self.dc_output_btn.config(text="Output On")
                self.status_var.set("Output turned off")
            else:
                self.smu.write(":OUTP ON")
                self.dc_output_btn.config(text="Output Off")
                self.status_var.set("Output turned on")
                
        except Exception as e:
            self.logger.error(f"Output toggle error: {e}")
            messagebox.showerror("Error", f"Error toggling output: {str(e)}")
    
    def measure_resistance(self):
        """Measure resistance"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to an instrument first")
            return
        
        try:
            wire_mode = self.res_wire_mode.get()
            test_current = float(self.res_current.get())
            
            # Set wire mode
            self._set_wire_mode(wire_mode)
            
            # Configure for resistance measurement
            self.smu.write(":SOUR:FUNC CURR")
            self.smu.write(f":SOUR:CURR:LEV {test_current}")
            self.smu.write(":SENS:FUNC 'VOLT'")
            self.smu.write(":OUTP ON")
            
            time.sleep(0.1)
            
            # Read voltage
            reading = self.smu.query(":READ?")
            voltage, current_read = self._safe_parse_reading(reading)
            
            # Calculate resistance
            resistance = voltage / test_current if test_current != 0 else float('inf')
            
            self.smu.write(":OUTP OFF")
            
            # Display result
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self._update_data_table(timestamp, test_current, current_read, resistance, 1, f"R-{wire_mode}", "Resistance")
            
            messagebox.showinfo("Resistance Measurement",
                              f"Resistance: {resistance:.6f} Ω\nTest Current: {test_current} A\n"
                              f"Measured Voltage: {voltage:.6f} V\nMode: {wire_mode}")
                              
        except Exception as e:
            self.logger.error(f"Resistance measurement error: {e}")
            messagebox.showerror("Error", f"Error measuring resistance: {str(e)}")
        finally:
            try:
                self.smu.write(":OUTP OFF")
            except Exception:
                pass
    
    def start_iv_loop(self):
        """Start IV loop testing for memristors"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to an instrument first")
            return
        
        try:
            # Get parameters
            vpos = float(self.loop_vpos.get())
            vneg = float(self.loop_vneg.get())
            points = int(self.loop_points.get())
            compliance = float(self.loop_compliance.get())
            current_range = self.loop_current_range.get()
            delay = float(self.loop_delay.get())
            cycles = int(self.loop_cycles.get())
            
            # Validate parameters
            if points <= 0:
                raise ValueError("Points must be greater than 0")
            if compliance <= 0:
                raise ValueError("Compliance must be greater than 0")
            if delay < 0:
                raise ValueError("Delay must be non-negative")
            if cycles <= 0:
                raise ValueError("Number of cycles must be greater than 0")
            
            # Start measurement
            self.measurement_running = True
            self.loop_start_btn.config(state=tk.DISABLED)
            self.loop_stop_btn.config(state=tk.NORMAL)
            self.progress_var.set(0)
            
            thread = threading.Thread(target=self._perform_iv_loop,
                                    args=(vpos, vneg, points, compliance, current_range, delay, cycles))
            thread.daemon = True
            thread.start()
            
        except ValueError as e:
            messagebox.showerror("Parameter Error", f"Invalid parameter: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Error starting IV loop test: {str(e)}")
    
    def _perform_iv_loop(self, vpos, vneg, points, compliance, current_range, delay, cycles):
        """Perform IV loop testing"""
        try:
            # Configure SMU with proper current settings
            self._set_current_compliance_and_range(compliance, current_range)
            self.smu.write(":OUTP ON")
            time.sleep(0.1)
            
            self.data_points.clear()
            total_points = cycles * points * 4
            point_count = 0
            
            for cycle in range(cycles):
                if not self.measurement_running:
                    break
                
                # Triangular sweep segments
                segments = [
                    np.linspace(0, vpos, points),      # 0 to positive
                    np.linspace(vpos, vneg, points),   # positive to negative
                    np.linspace(vneg, 0, points),      # negative to 0
                    np.array([0])                      # ensure we end at 0
                ]
                
                segment_names = ["0→+V", "+V→-V", "-V→0", "End"]
                
                for seg_idx, segment in enumerate(segments):
                    for i, voltage in enumerate(segment):
                        if not self.measurement_running:
                            break
                        
                        self.smu.write(f":SOUR:VOLT:LEV {voltage}")
                        time.sleep(delay)
                        
                        reading = self.smu.query(":READ?")
                        v_read, current = self._safe_parse_reading(reading)
                        resistance = abs(v_read / current) if abs(current) > 1e-12 else float('inf')
                        
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        self.data_points.append({
                            'timestamp': timestamp,
                            'voltage': voltage,
                            'current': current,
                            'resistance': resistance,
                            'cycle': cycle + 1,
                            'state': segment_names[seg_idx],
                            'extra': f"Loop{cycle+1}-{segment_names[seg_idx]}"
                        })
                        
                        point_count += 1
                        progress = point_count / total_points * 100
                        self.root.after(0, self._update_progress, progress)
                        self.root.after(0, self._update_data_table, timestamp, voltage, current, resistance, 
                                      cycle + 1, segment_names[seg_idx], f"Loop{cycle+1}")
                        self.root.after(0, self.status_var.set, 
                                      f"IV Loop: Cycle {cycle+1}/{cycles}, {segment_names[seg_idx]} - I: {current:.3e} A")
                        
        except Exception as e:
            self.root.after(0, messagebox.showerror, "Measurement Error", f"Error during IV loop test: {str(e)}")
        finally:
            try:
                self.smu.write(":SOUR:VOLT:LEV 0")
                self.smu.write(":OUTP OFF")
            except Exception:
                pass
            self.root.after(0, self._sweep_completed)
    
    def start_retention_test(self):
        """Start retention testing for memristors"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to an instrument first")
            return
        
        try:
            # Get parameters
            vset = float(self.ret_vset.get())
            vreset = float(self.ret_vreset.get())
            vread = float(self.ret_vread.get())
            compliance = float(self.ret_compliance.get())
            duration = float(self.ret_duration.get())
            interval = float(self.ret_interval.get())
            
            # Validate parameters
            if compliance <= 0:
                raise ValueError("Compliance must be greater than 0")
            if duration <= 0:
                raise ValueError("Duration must be greater than 0")
            if interval <= 0:
                raise ValueError("Interval must be greater than 0")
            
            # Start measurement
            self.measurement_running = True
            self.ret_start_btn.config(state=tk.DISABLED)
            self.ret_stop_btn.config(state=tk.NORMAL)
            self.progress_var.set(0)
            
            thread = threading.Thread(target=self._perform_retention_test,
                                    args=(vset, vreset, vread, compliance, duration, interval))
            thread.daemon = True
            thread.start()
            
        except ValueError as e:
            messagebox.showerror("Parameter Error", f"Invalid parameter: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Error starting retention test: {str(e)}")
    
    def _perform_retention_test(self, vset, vreset, vread, compliance, duration, interval):
        """Perform retention testing"""
        try:
            # Configure SMU
            self._set_current_compliance_and_range(compliance, "AUTO")
            self.smu.write(":OUTP ON")
            time.sleep(0.1)
            
            self.data_points.clear()
            half_duration = duration / 2
            
            # SET retention test (first half)
            self.root.after(0, self.status_var.set, "Programming SET state...")
            self.smu.write(f":SOUR:VOLT:LEV {vset}")
            time.sleep(0.1)
            
            start_time = time.time()
            read_count = 0
            max_reads_set = int(half_duration / interval)
            
            while self.measurement_running and (time.time() - start_time) < half_duration:
                self.smu.write(f":SOUR:VOLT:LEV {vread}")
                time.sleep(0.01)
                reading = self.smu.query(":READ?")
                v_read_val, current = self._safe_parse_reading(reading)
                resistance = abs(v_read_val / current) if abs(current) > 1e-12 else float('inf')
                
                elapsed = time.time() - start_time
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                self.data_points.append({
                    'timestamp': timestamp,
                    'voltage': vread,
                    'current': current,
                    'resistance': resistance,
                    'cycle': 1,
                    'state': 'SET_retention',
                    'extra': f"SET@{elapsed:.1f}s"
                })
                
                read_count += 1
                progress = (read_count / max_reads_set) * 50
                self.root.after(0, self._update_progress, progress)
                self.root.after(0, self._update_data_table, timestamp, vread, current, resistance, 1, 'SET_retention', f"SET@{elapsed:.1f}s")
                self.root.after(0, self.status_var.set, f"SET Retention: {elapsed:.1f}s / {half_duration:.1f}s - R: {resistance:.2e} Ω")
                
                time.sleep(interval)
            
            if not self.measurement_running:
                return
            
            # RESET retention test (second half)
            self.root.after(0, self.status_var.set, "Programming RESET state...")
            self.smu.write(f":SOUR:VOLT:LEV {vreset}")
            time.sleep(0.1)
            
            start_time = time.time()
            read_count = 0
            max_reads_reset = int(half_duration / interval)
            
            while self.measurement_running and (time.time() - start_time) < half_duration:
                self.smu.write(f":SOUR:VOLT:LEV {vread}")
                time.sleep(0.01)
                reading = self.smu.query(":READ?")
                v_read_val, current = self._safe_parse_reading(reading)
                resistance = abs(v_read_val / current) if abs(current) > 1e-12 else float('inf')
                
                elapsed = time.time() - start_time
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                self.data_points.append({
                    'timestamp': timestamp,
                    'voltage': vread,
                    'current': current,
                    'resistance': resistance,
                    'cycle': 2,
                    'state': 'RESET_retention',
                    'extra': f"RESET@{elapsed:.1f}s"
                })
                
                read_count += 1
                progress = 50 + (read_count / max_reads_reset) * 50
                self.root.after(0, self._update_progress, progress)
                self.root.after(0, self._update_data_table, timestamp, vread, current, resistance, 2, 'RESET_retention', f"RESET@{elapsed:.1f}s")
                self.root.after(0, self.status_var.set, f"RESET Retention: {elapsed:.1f}s / {half_duration:.1f}s - R: {resistance:.2e} Ω")
                
                time.sleep(interval)
                
        except Exception as e:
            self.root.after(0, messagebox.showerror, "Measurement Error", f"Error during retention test: {str(e)}")
        finally:
            try:
                self.smu.write(":SOUR:VOLT:LEV 0")
                self.smu.write(":OUTP OFF")
            except Exception:
                pass
            self.root.after(0, self._sweep_completed)
    
    def start_endurance_test(self):
        """Start endurance testing for memristors"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to an instrument first")
            return
        
        try:
            # Get parameters with validation
            try:
                vset = float(self.end_vset.get())
                vreset = float(self.end_vreset.get())
                vread = float(self.end_vread.get())
                compliance = float(self.end_compliance.get())
                cycles = int(self.end_cycles.get())
                pulse_width = float(self.end_pulse_width.get())
            except ValueError as e:
                raise ValueError(f"Invalid numeric value: {e}")
            
            # Validate parameters
            if compliance <= 0:
                raise ValueError("Compliance current must be greater than 0")
            if cycles <= 0:
                raise ValueError("Number of cycles must be greater than 0")
            if pulse_width <= 0:
                raise ValueError("Pulse width must be greater than 0")
            if abs(vset) > 20 or abs(vreset) > 20:
                raise ValueError("Voltages should be reasonable (< 20V)")
            if cycles > 100000:
                raise ValueError("Too many cycles - limit to 100,000 for safety")
            
            # Start measurement
            self.measurement_running = True
            self.end_start_btn.config(state=tk.DISABLED)
            self.end_stop_btn.config(state=tk.NORMAL)
            self.progress_var.set(0)
            
            thread = threading.Thread(target=self._perform_endurance_test,
                                    args=(vset, vreset, vread, compliance, cycles, pulse_width))
            thread.daemon = True
            thread.start()
            
        except ValueError as e:
            messagebox.showerror("Parameter Error", f"Parameter validation failed: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Error starting endurance test: {str(e)}")
    
    def _perform_endurance_test(self, vset, vreset, vread, compliance, cycles, pulse_width):
        """Perform endurance testing"""
        try:
            # Configure SMU
            self._set_current_compliance_and_range(compliance, "AUTO")
            self.smu.write(":OUTP ON")
            time.sleep(0.1)
            
            self.data_points.clear()
            
            for cycle in range(cycles):
                if not self.measurement_running:
                    break
                
                # SET operation
                self.smu.write(f":SOUR:VOLT:LEV {vset}")
                time.sleep(pulse_width)
                
                # Read SET state
                self.smu.write(f":SOUR:VOLT:LEV {vread}")
                time.sleep(0.01)
                reading = self.smu.query(":READ?")
                v_read_val, current = self._safe_parse_reading(reading)
                r_set = abs(v_read_val / current) if abs(current) > 1e-12 else float('inf')
                
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                self.data_points.append({
                    'timestamp': timestamp,
                    'voltage': vset,
                    'current': current,
                    'resistance': r_set,
                    'cycle': cycle + 1,
                    'state': 'SET',
                    'extra': f"SET_Cycle{cycle+1}"
                })
                
                # RESET operation
                self.smu.write(f":SOUR:VOLT:LEV {vreset}")
                time.sleep(pulse_width)
                
                # Read RESET state
                self.smu.write(f":SOUR:VOLT:LEV {vread}")
                time.sleep(0.01)
                reading = self.smu.query(":READ?")
                v_read_val, current = self._safe_parse_reading(reading)
                r_reset = abs(v_read_val / current) if abs(current) > 1e-12 else float('inf')
                
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                self.data_points.append({
                    'timestamp': timestamp,
                    'voltage': vreset,
                    'current': current,
                    'resistance': r_reset,
                    'cycle': cycle + 1,
                    'state': 'RESET',
                    'extra': f"RESET_Cycle{cycle+1}"
                })
                
                # Update GUI
                progress = (cycle + 1) / cycles * 100
                self.root.after(0, self._update_progress, progress)
                self.root.after(0, self._update_data_table, timestamp, vset, current, r_set, cycle + 1, 'SET', f"SET_C{cycle+1}")
                self.root.after(0, self._update_data_table, timestamp, vreset, current, r_reset, cycle + 1, 'RESET', f"RESET_C{cycle+1}")
                self.root.after(0, self.status_var.set, f"Endurance: Cycle {cycle+1}/{cycles} - SET: {r_set:.2e}Ω, RESET: {r_reset:.2e}Ω")
                
                time.sleep(0.001)
                
        except Exception as e:
            self.root.after(0, messagebox.showerror, "Measurement Error", f"Error during endurance test: {str(e)}")
        finally:
            try:
                self.smu.write(":SOUR:VOLT:LEV 0")
                self.smu.write(":OUTP OFF")
            except Exception:
                pass
            self.root.after(0, self._sweep_completed)
    
    def stop_measurement(self):
        """Stop ongoing measurement"""
        try:
            self.measurement_running = False
            self.status_var.set("Stopping measurement...")
            self.root.after(100, self._finalize_stop)
        except Exception as e:
            self.logger.error(f"Error stopping measurement: {e}")
    
    def _finalize_stop(self):
        """Finalize the stop process"""
        try:
            if self.smu:
                self.smu.write(":OUTP OFF")
            
            # Re-enable all start buttons
            self.iv_start_btn.config(state=tk.NORMAL)
            self.loop_start_btn.config(state=tk.NORMAL)
            self.ret_start_btn.config(state=tk.NORMAL)
            self.end_start_btn.config(state=tk.NORMAL)
            
            # Disable all stop buttons
            self.iv_stop_btn.config(state=tk.DISABLED)
            self.loop_stop_btn.config(state=tk.DISABLED)
            self.ret_stop_btn.config(state=tk.DISABLED)
            self.end_stop_btn.config(state=tk.DISABLED)
            
            self.status_var.set("Measurement stopped by user")
        except Exception as e:
            self.logger.error(f"Error finalizing stop: {e}")
    
    def _update_progress(self, value):
        """Update progress bar"""
        self.progress_var.set(value)
    
    def _update_data_table(self, timestamp, voltage, current, resistance, cycle, state, extra_info):
        """Update the data table with new measurement"""
        self.data_tree.insert('', 'end', values=(
            timestamp, 
            f"{voltage:.6f}", 
            f"{current:.6e}", 
            f"{resistance:.6e}",
            cycle,
            state,
            extra_info
        ))
        children = self.data_tree.get_children()
        if children:
            self.data_tree.see(children[-1])
    
    def _sweep_completed(self):
        """Called when sweep is completed"""
        self.measurement_running = False
        
        # Re-enable all start buttons
        self.iv_start_btn.config(state=tk.NORMAL)
        try:
            self.loop_start_btn.config(state=tk.NORMAL)
            self.ret_start_btn.config(state=tk.NORMAL)
            self.end_start_btn.config(state=tk.NORMAL)
        except:
            pass
        
        # Disable all stop buttons
        self.iv_stop_btn.config(state=tk.DISABLED)
        try:
            self.loop_stop_btn.config(state=tk.DISABLED)
            self.ret_stop_btn.config(state=tk.DISABLED)
            self.end_stop_btn.config(state=tk.DISABLED)
        except:
            pass
        
        self.progress_var.set(100)
        self.status_var.set("Measurement completed")
    
    def export_csv(self):
        """Export data to CSV file"""
        if not self.data_points:
            messagebox.showwarning("No Data", "No data to export")
            return
        
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Save measurement data"
            )
            
            if filename:
                with open(filename, 'w', newline='',encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Write header with metadata
                    writer.writerow(['# Keithley SMU Measurement Data'])
                    writer.writerow(['# Timestamp:', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                    writer.writerow(['# Instrument:', self.model if self.model else "Unknown"])
                    writer.writerow(['# Total Points:', len(self.data_points)])
                    writer.writerow([])
                    
                    # Write data header
                    writer.writerow(['Timestamp', 'Voltage_V', 'Current_A', 'Resistance_Ohm', 'Cycle', 'State', 'Extra_Info'])
                    
                    # Write data
                    for point in self.data_points:
                        if isinstance(point, dict):
                            writer.writerow([
                                point['timestamp'],
                                point['voltage'],
                                point['current'],
                                point['resistance'],
                                point['cycle'],
                                point['state'],
                                point['extra']
                            ])
                        else:
                            # Legacy format support
                            writer.writerow(point)
                
                messagebox.showinfo("Export Complete", f"Data exported to {filename}")
                self.logger.info(f"Data exported to {filename}")
                
        except Exception as e:
            self.logger.error(f"Export error: {e}")
            messagebox.showerror("Export Error", f"Error exporting data: {str(e)}")
    
    def plot_external(self):
        """Create external plot using matplotlib"""
        if not self.data_points:
            messagebox.showwarning("No Data", "No data to plot")
            return
        
        try:
            import matplotlib.pyplot as plt
            
            # Convert data format if needed
            if isinstance(self.data_points[0], dict):
                voltages = [point['voltage'] for point in self.data_points]
                currents = [point['current'] for point in self.data_points]
                cycles = [point['cycle'] for point in self.data_points]
                states = [point['state'] for point in self.data_points]
            else:
                # Legacy format
                voltages = [point[1] for point in self.data_points]
                currents = [point[2] for point in self.data_points]
                cycles = [1] * len(voltages)
                states = ['Unknown'] * len(voltages)
            
            # Create comprehensive plots
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))
            fig.suptitle('Keithley SMU Measurement Results')
            
            # I-V plot
            axes[0,0].plot(voltages, currents, 'b.-', linewidth=1, markersize=2)
            axes[0,0].set_xlabel('Voltage (V)')
            axes[0,0].set_ylabel('Current (A)')
            axes[0,0].set_title('I-V Characteristic')
            axes[0,0].grid(True, alpha=0.3)
            
            # Current vs measurement point
            axes[0,1].semilogy(range(len(currents)), np.abs(currents), 'r.-', linewidth=1, markersize=2)
            axes[0,1].set_xlabel('Measurement Point')
            axes[0,1].set_ylabel('|Current| (A)')
            axes[0,1].set_title('Current vs Measurement Point')
            axes[0,1].grid(True, alpha=0.3)
            
            # Resistance calculation and plot
            resistances = [abs(v/c) if abs(c) > 1e-15 else 1e12 for v, c in zip(voltages, currents)]
            resistances = [min(r, 1e12) for r in resistances]  # Cap at 1 TΩ
            
            axes[1,0].semilogy(range(len(resistances)), resistances, 'g.-', linewidth=1, markersize=2)
            axes[1,0].set_xlabel('Measurement Point')
            axes[1,0].set_ylabel('Resistance (Ω)')
            axes[1,0].set_title('Resistance vs Measurement Point')
            axes[1,0].grid(True, alpha=0.3)
            
            # Cycle information if available
            if len(set(cycles)) > 1:
                axes[1,1].plot(cycles, resistances, 'k.-', linewidth=1, markersize=2)
                axes[1,1].set_xlabel('Cycle Number')
                axes[1,1].set_ylabel('Resistance (Ω)')
                axes[1,1].set_title('Resistance vs Cycle')
                axes[1,1].set_yscale('log')
            else:
                axes[1,1].text(0.5, 0.5, 'Single cycle data\nSee other plots', 
                             ha='center', va='center', transform=axes[1,1].transAxes)
                axes[1,1].set_title('Cycle Analysis')
            axes[1,1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.show()
            
        except ImportError:
            messagebox.showinfo("Matplotlib Not Available",
                              "Matplotlib is not installed.\n\n" +
                              "To enable plotting:\n" +
                              "pip install matplotlib\n\n" +
                              "Data has been saved and can be analyzed with external tools.")
        except Exception as e:
            self.logger.error(f"Plotting error: {e}")
            messagebox.showerror("Plot Error", f"Error creating plot: {str(e)}")
    
    def clear_data(self):
        """Clear all measurement data"""
        self.data_points.clear()
        for item in self.data_tree.get_children():
            self.data_tree.delete(item)
        self.progress_var.set(0)
        self.status_var.set("Data cleared")

def main():
    """Main function to run the application"""
    root = tk.Tk()
    app = KeithleySMUController(root)
    
    # Handle window closing gracefully
    def on_closing():
        try:
            app.measurement_running = False
            time.sleep(0.1)
            if app.connected:
                app.disconnect_instrument()
        except Exception as e:
            print(f"Error during shutdown: {e}")
        finally:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()