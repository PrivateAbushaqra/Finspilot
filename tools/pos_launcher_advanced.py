"""
FinsPilot-ERP - Advanced Launcher GUI
========================================
شاشة تشغيل متقدمة مع إدارة كاملة للمستخدمين والجلسات

Features:
✅ Auto-detect network interfaces
✅ Active users management  
✅ Recent sessions with logout time
✅ Disconnect users
✅ Clear recent sessions
✅ Auto-restart server if crashed
✅ Copy content with CTRL+C
✅ Scrollable content
✅ Single instance (prevent multiple launches)
✅ System requirements checker with auto-install
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import subprocess
import sys
import os
import socket
import threading
import webbrowser
import shutil
from pathlib import Path
from datetime import datetime
import ctypes
import time
import queue
import re

# Single instance check using mutex
try:
    import win32event
    import win32api
    from winerror import ERROR_ALREADY_EXISTS
    WIN32_AVAILABLE = True
except ImportError:
    win32event = None
    win32api = None
    ERROR_ALREADY_EXISTS = None
    WIN32_AVAILABLE = False

# Check if running as admin
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# Singleton pattern for single instance
class SingleInstance:
    def __init__(self, app_name):
        self.app_name = app_name
        self.mutex = None
        self.already_running = False
        if WIN32_AVAILABLE:
            try:
                self.mutex = win32event.CreateMutex(None, False, f'Global\\{app_name}')
                self.already_running = win32api.GetLastError() == ERROR_ALREADY_EXISTS
            except Exception:
                self.mutex = None
                self.already_running = False
        
    def is_already_running(self):
        return self.already_running
        
    def bring_existing_to_front(self):
        """Bring existing window to front"""
        if not WIN32_AVAILABLE:
            return False
        try:
            import win32gui
            import win32con
            
            def callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if 'FinsPilot-ERP - Launcher' in title:
                        windows.append(hwnd)
                return True
                
            windows = []
            win32gui.EnumWindows(callback, windows)
            
            if windows:
                hwnd = windows[0]
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return True
        except:
            pass
        return False

# Setup Django environment
try:
    PROJECT_ROOT = Path(__file__).parent.parent.absolute()
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
    
    import django
    django.setup()
    
    from django.contrib.sessions.models import Session
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    
    try:
        from core.models import SessionActivity
        from core.ws_utils import force_disconnect_session
        SESSION_MANAGEMENT_AVAILABLE = True
    except Exception:
        SessionActivity = None
        def force_disconnect_session(session_key):
            return False
        SESSION_MANAGEMENT_AVAILABLE = False
    
    User = get_user_model()
    DJANGO_AVAILABLE = True
except Exception as e:
    print(f'Django not available: {e}')
    DJANGO_AVAILABLE = False
    SESSION_MANAGEMENT_AVAILABLE = False

class AdvancedLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("FinsPilot Launcher")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # Project root and environment
        self.project_dir = Path(__file__).parent.parent.absolute()
        
        # Colors - Modern Dark Theme
        self.colors = {
            'bg': '#1e1e1e',
            'bg_light': '#2d2d2d',
            'bg_lighter': '#3e3e3e',
            'accent': '#007acc',
            'accent_hover': '#1e88e5',
            'success': '#4caf50',
            'warning': '#ff9800',
            'error': '#f44336',
            'text': '#ffffff',
            'text_secondary': '#b0b0b0',
            'border': '#444444'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        # Variables
        self.server_process = None
        self.server_running = False
        self.server_crashed_count = 0
        self.auto_restart_enabled = tk.BooleanVar(value=True)
        self.project_dir = Path(__file__).parent.parent.absolute()
        self.venv_path = None
        self.network_interfaces = []
        self.selected_interface = tk.StringVar()
        self.queue = queue.Queue()
        self.db_ready = DJANGO_AVAILABLE
        
        # Initialize UI
        self.setup_styles()
        self.create_widgets()
        self.detect_environment()
        self.check_system_requirements()
        self.detect_networks()
        
        # Auto-refresh
        self.auto_refresh()
        self.monitor_server()
        self.update_users()
        
    def setup_styles(self):
        """Setup modern ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('.', 
                       background=self.colors['bg'],
                       foreground=self.colors['text'],
                       fieldbackground=self.colors['bg_light'],
                       bordercolor=self.colors['border'])
        
        # Frame styles
        style.configure('Card.TFrame', 
                       background=self.colors['bg_light'],
                       relief='flat')
        
        # Label styles
        style.configure('Title.TLabel',
                       background=self.colors['bg'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 24, 'bold'))
        
        style.configure('Subtitle.TLabel',
                       background=self.colors['bg_light'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 12, 'bold'))
        
        style.configure('Info.TLabel',
                       background=self.colors['bg_light'],
                       foreground=self.colors['text_secondary'],
                       font=('Segoe UI', 10))
        
        style.configure('Status.TLabel',
                       background=self.colors['bg_light'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 10))
        
        # Button styles
        style.configure('Accent.TButton',
                       background=self.colors['accent'],
                       foreground=self.colors['text'],
                       borderwidth=0,
                       font=('Segoe UI', 10, 'bold'),
                       padding=10)
        
        style.map('Accent.TButton',
                 background=[('active', self.colors['accent_hover'])],
                 foreground=[('active', self.colors['text'])])
        
        style.configure('Success.TButton',
                       background=self.colors['success'],
                       foreground=self.colors['text'],
                       borderwidth=0,
                       font=('Segoe UI', 10, 'bold'),
                       padding=10)
        
        style.configure('Warning.TButton',
                       background=self.colors['warning'],
                       foreground=self.colors['text'],
                       borderwidth=0,
                       font=('Segoe UI', 10),
                       padding=8)
        
        # Treeview style for user lists
        style.configure('Treeview',
                       background=self.colors['bg_lighter'],
                       foreground=self.colors['text'],
                       fieldbackground=self.colors['bg_lighter'],
                       borderwidth=0)
        style.map('Treeview', background=[('selected', self.colors['accent'])])
        
        # Combobox style
        style.configure('TCombobox',
                       fieldbackground=self.colors['bg_lighter'],
                       background=self.colors['bg_lighter'],
                       foreground=self.colors['text'],
                       arrowcolor=self.colors['text'],
                       borderwidth=1,
                       relief='solid')
        
    def create_widgets(self):
        """Create all UI widgets"""
        # Main container with padding
        main_container = tk.Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_frame = tk.Frame(main_container, bg=self.colors['bg'])
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(title_frame, 
                               text="🚀 FinsPilot-ERP",
                               style='Title.TLabel')
        title_label.pack(side=tk.LEFT)
        
        version_label = ttk.Label(title_frame,
                                 text="v3.0 Advanced",
                                 style='Info.TLabel')
        version_label.pack(side=tk.LEFT, padx=10, pady=8)
        
        # Create notebook (tabs)
        notebook = ttk.Notebook(main_container)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Server Control
        server_tab = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(server_tab, text='🖥️ Server Control')
        self.create_server_tab(server_tab)
        
        # Tab 2: Active Users
        users_tab = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(users_tab, text='👥 Active Users')
        self.create_users_tab(users_tab)
        
        # Tab 3: Recent Sessions
        sessions_tab = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(sessions_tab, text='📋 Recent Sessions')
        self.create_sessions_tab(sessions_tab)
        
        # Tab 4: Network Info
        network_tab = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(network_tab, text='🌐 Network')
        self.create_network_tab(network_tab)
        
        # Tab 5: System & Actions
        system_tab = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(system_tab, text='⚙️ System & Actions')
        self.create_system_tab(system_tab)
        
        # === BOTTOM STATUS BAR ===
        self.create_status_bar(main_container)
        
    def create_server_tab(self, parent):
        """Create server control tab"""
        # Server status card
        status_card = ttk.Frame(parent, style='Card.TFrame', padding=15)
        status_card.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(status_card, text="🖥️ Server Status", 
                 style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 10))
        
        # Status indicator
        status_frame = tk.Frame(status_card, bg=self.colors['bg_light'])
        status_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(status_frame, text="Status:", style='Info.TLabel').pack(side=tk.LEFT, padx=5)
        
        self.status_indicator = tk.Canvas(status_frame, width=20, height=20,
                                         bg=self.colors['bg_light'],
                                         highlightthickness=0)
        self.status_indicator.pack(side=tk.LEFT, padx=5)
        self.status_circle = self.status_indicator.create_oval(2, 2, 18, 18,
                                                              fill=self.colors['error'],
                                                              outline='')
        
        self.status_label = ttk.Label(status_frame, text="Server Stopped",
                                      style='Status.TLabel')
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Auto-restart checkbox
        auto_restart_cb = ttk.Checkbutton(status_frame, text="Auto-restart if crashed",
                                         variable=self.auto_restart_enabled)
        auto_restart_cb.pack(side=tk.RIGHT, padx=10)
        
        # Server URL
        url_frame = tk.Frame(status_card, bg=self.colors['bg_light'])
        url_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(url_frame, text="URL:", style='Info.TLabel').pack(side=tk.LEFT, padx=5)
        
        self.url_label = tk.Label(url_frame, text="http://localhost:8000",
                                 bg=self.colors['bg_light'],
                                 fg=self.colors['accent'],
                                 font=('Segoe UI', 10, 'underline'),
                                 cursor='hand2')
        self.url_label.pack(side=tk.LEFT, padx=5)
        self.url_label.bind('<Button-1>', self.open_browser)
        
        # Control buttons
        btn_frame = tk.Frame(status_card, bg=self.colors['bg_light'])
        btn_frame.pack(fill=tk.X, pady=15)
        
        self.start_btn = ttk.Button(btn_frame, text="▶️ Start Server",
                                    command=self.start_server,
                                    style='Success.TButton')
        self.start_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.stop_btn = ttk.Button(btn_frame, text="⏹️ Stop Server",
                                   command=self.stop_server,
                                   style='Warning.TButton',
                                   state='disabled')
        self.stop_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        open_btn = ttk.Button(btn_frame, text="🌐 Open Browser",
                             command=self.open_browser,
                             style='Accent.TButton')
        open_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Server log card
        log_card = ttk.Frame(parent, style='Card.TFrame', padding=15)
        log_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(log_card, text="📄 Server Log (CTRL+C to copy)", 
                 style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 10))
        
        # Log with scrollbar
        log_frame = tk.Frame(log_card, bg=self.colors['bg_light'])
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            bg=self.colors['bg_lighter'],
            fg=self.colors['text'],
            font=('Consolas', 9),
            relief='flat',
            padx=10,
            pady=10,
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Enable text selection and copy
        self.log_text.bind('<Control-c>', lambda e: self.copy_from_text(self.log_text))
        self.log_text.bind('<Control-a>', lambda e: self.select_all_text(self.log_text))
        
    def create_users_tab(self, parent):
        """Create active users tab"""
        users_card = ttk.Frame(parent, style='Card.TFrame', padding=15)
        users_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header
        header_frame = tk.Frame(users_card, bg=self.colors['bg_light'])
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="👥 Active Users",
                 style='Subtitle.TLabel').pack(side=tk.LEFT)
        
        refresh_btn = ttk.Button(header_frame, text="🔄 Refresh",
                                command=self.update_users,
                                style='Warning.TButton')
        refresh_btn.pack(side=tk.RIGHT, padx=5)
        
        # Treeview for active users
        tree_frame = tk.Frame(users_card, bg=self.colors['bg_light'])
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columns = ('username', 'session', 'role', 'login', 'duration', 'ip')
        self.active_tree = ttk.Treeview(tree_frame, columns=columns, 
                                       show='headings', selectmode='extended')
        
        self.active_tree.heading('username', text='Username')
        self.active_tree.heading('session', text='Session ID')
        self.active_tree.heading('role', text='Role')
        self.active_tree.heading('login', text='Login Time')
        self.active_tree.heading('duration', text='Duration')
        self.active_tree.heading('ip', text='IP Address')
        
        # Column widths
        self.active_tree.column('username', width=120)
        self.active_tree.column('session', width=100)
        self.active_tree.column('role', width=100)
        self.active_tree.column('login', width=150)
        self.active_tree.column('duration', width=100)
        self.active_tree.column('ip', width=120)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.active_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.active_tree.xview)
        self.active_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.active_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Enable copy
        self.active_tree.bind('<Control-c>', lambda e: self.copy_from_tree(self.active_tree))
        
        # Action buttons
        btn_frame = tk.Frame(users_card, bg=self.colors['bg_light'])
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="🔌 Disconnect Selected",
                  command=self.disconnect_selected,
                  style='Warning.TButton').pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="🔌 Disconnect All",
                  command=self.disconnect_all,
                  style='Warning.TButton').pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="📋 Copy Selected",
                  command=lambda: self.copy_from_tree(self.active_tree),
                  style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        
        # Role-based disconnect
        ttk.Label(btn_frame, text="Role:", style='Info.TLabel').pack(side=tk.LEFT, padx=(20, 5))
        
        self.role_combo = ttk.Combobox(btn_frame, state='readonly', width=15)
        self.role_combo['values'] = ['admin', 'manager', 'cashier', 'waiter', 'kitchen']
        self.role_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="🔌 Disconnect Role",
                  command=self.disconnect_by_role,
                  style='Warning.TButton').pack(side=tk.LEFT, padx=5)
        
    def create_sessions_tab(self, parent):
        """Create recent sessions tab"""
        sessions_card = ttk.Frame(parent, style='Card.TFrame', padding=15)
        sessions_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header
        header_frame = tk.Frame(sessions_card, bg=self.colors['bg_light'])
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="📋 Recent Sessions (Show Logout Time)",
                 style='Subtitle.TLabel').pack(side=tk.LEFT)
        
        refresh_btn = ttk.Button(header_frame, text="🔄 Refresh",
                                command=self.update_users,
                                style='Warning.TButton')
        refresh_btn.pack(side=tk.RIGHT, padx=5)
        
        # Treeview for recent sessions
        tree_frame = tk.Frame(sessions_card, bg=self.colors['bg_light'])
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columns = ('username', 'session', 'role', 'login', 'logout', 'duration', 'ip')
        self.recent_tree = ttk.Treeview(tree_frame, columns=columns,
                                       show='headings', selectmode='extended')
        
        self.recent_tree.heading('username', text='Username')
        self.recent_tree.heading('session', text='Session ID')
        self.recent_tree.heading('role', text='Role')
        self.recent_tree.heading('login', text='Login Time')
        self.recent_tree.heading('logout', text='Logout Time')
        self.recent_tree.heading('duration', text='Duration')
        self.recent_tree.heading('ip', text='IP Address')
        
        # Column widths
        self.recent_tree.column('username', width=120)
        self.recent_tree.column('session', width=100)
        self.recent_tree.column('role', width=100)
        self.recent_tree.column('login', width=150)
        self.recent_tree.column('logout', width=150)
        self.recent_tree.column('duration', width=100)
        self.recent_tree.column('ip', width=120)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.recent_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.recent_tree.xview)
        self.recent_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.recent_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Enable copy
        self.recent_tree.bind('<Control-c>', lambda e: self.copy_from_tree(self.recent_tree))
        
        # Action buttons
        btn_frame = tk.Frame(sessions_card, bg=self.colors['bg_light'])
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="📋 Copy Selected",
                  command=lambda: self.copy_from_tree(self.recent_tree),
                  style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="🗑️ Clear All Recent Sessions",
                  command=self.clear_recent_sessions,
                  style='Warning.TButton').pack(side=tk.LEFT, padx=5)
        
    def create_network_tab(self, parent):
        """Create network information tab"""
        network_card = ttk.Frame(parent, style='Card.TFrame', padding=15)
        network_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(network_card, text="🌐 Network Information", 
                 style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 10))
        
        # Network interface selector
        selector_frame = tk.Frame(network_card, bg=self.colors['bg_light'])
        selector_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(selector_frame, text="Network Interface:", 
                 style='Info.TLabel').pack(side=tk.LEFT, padx=5)
        
        self.interface_combo = ttk.Combobox(selector_frame, 
                                           textvariable=self.selected_interface,
                                           state='readonly',
                                           width=30)
        self.interface_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.interface_combo.bind('<<ComboboxSelected>>', self.on_interface_selected)
        
        refresh_btn = ttk.Button(selector_frame, text="🔄 Refresh",
                                command=self.detect_networks,
                                style='Warning.TButton',
                                width=10)
        refresh_btn.pack(side=tk.RIGHT, padx=5)
        
        # Network info display
        self.network_info_text = scrolledtext.ScrolledText(
            network_card,
            height=15,
            bg=self.colors['bg_lighter'],
            fg=self.colors['text'],
            font=('Consolas', 9),
            relief='flat',
            padx=10,
            pady=10
        )
        self.network_info_text.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Enable copy
        self.network_info_text.bind('<Control-c>', lambda e: self.copy_from_text(self.network_info_text))
        
    def create_system_tab(self, parent):
        """Create system info and actions tab"""
        # System info card
        system_card = ttk.Frame(parent, style='Card.TFrame', padding=15)
        system_card.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(system_card, text="⚙️ System Information",
                 style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 10))
        
        self.system_info_text = scrolledtext.ScrolledText(
            system_card,
            height=8,
            bg=self.colors['bg_lighter'],
            fg=self.colors['text'],
            font=('Consolas', 9),
            relief='flat',
            padx=10,
            pady=10
        )
        self.system_info_text.pack(fill=tk.BOTH, expand=True)
        
        # Actions card
        actions_card = ttk.Frame(parent, style='Card.TFrame', padding=15)
        actions_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(actions_card, text="🔧 Actions",
                 style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 10))
        
        # Action buttons grid
        btn_grid = tk.Frame(actions_card, bg=self.colors['bg_light'])
        btn_grid.pack(fill=tk.BOTH, expand=True)
        
        buttons = [
            ("📦 Check System Requirements", self.check_system_requirements),
            ("📥 Install Dependencies", self.install_dependencies),
            ("� Collect Static Files", self.collect_static),
            ("🔗 Create Desktop Shortcut", self.create_shortcut),
            ("📂 Install to Custom Location", self.install_to_location),
            ("🧹 Clear All Sessions", self.clear_all_sessions_on_demand),
        ]
        
        for i, (text, command) in enumerate(buttons):
            btn = ttk.Button(btn_grid, text=text, command=command, style='Accent.TButton')
            btn.grid(row=i//2, column=i%2, padx=5, pady=5, sticky='ew')
        
        btn_grid.grid_columnconfigure(0, weight=1)
        btn_grid.grid_columnconfigure(1, weight=1)
        
    def create_status_bar(self, parent):
        """Create bottom status bar"""
        status_bar = tk.Frame(parent, bg=self.colors['bg_lighter'], height=30)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        
        self.status_bar_label = tk.Label(status_bar,
                                         text="Ready",
                                         bg=self.colors['bg_lighter'],
                                         fg=self.colors['text_secondary'],
                                         font=('Segoe UI', 9),
                                         anchor=tk.W,
                                         padx=10)
        self.status_bar_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        time_label = tk.Label(status_bar,
                             text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                             bg=self.colors['bg_lighter'],
                             fg=self.colors['text_secondary'],
                             font=('Segoe UI', 9),
                             padx=10)
        time_label.pack(side=tk.RIGHT)
        
        # Update time every second
        def update_time():
            time_label.config(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            self.root.after(1000, update_time)
        update_time()
        
    def detect_environment(self):
        """Detect Python environment and project settings"""
        self.log_system("🔍 Detecting environment...")
        
        # Find virtual environment
        venv_dirs = ['.venv-1', '.venv', 'venv', 'venv_clean']
        for venv_dir in venv_dirs:
            venv_path = self.project_dir / venv_dir
            python_exe = venv_path / 'Scripts' / 'python.exe'
            if python_exe.exists():
                self.venv_path = venv_path
                self.log_system(f"✅ Found virtual environment: {venv_dir}")
                break
        
        if not self.venv_path:
            self.log_system("⚠️ Virtual environment not found!")
        
        # Update system info
        info = []
        info.append(f"📂 Project Directory:\n   {self.project_dir}\n\n")
        
        if self.venv_path:
            info.append(f"🐍 Python Environment:\n   {self.venv_path}\n")
            python_exe = self.venv_path / 'Scripts' / 'python.exe'
            try:
                # Hide console window
                startupinfo = None
                creationflags = 0
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    creationflags = subprocess.CREATE_NO_WINDOW
                
                result = subprocess.run([str(python_exe), '--version'],
                                      capture_output=True, text=True, timeout=5,
                                      startupinfo=startupinfo, creationflags=creationflags)
                info.append(f"   {result.stdout.strip()}\n\n")
            except:
                info.append("\n\n")
        else:
            info.append("🐍 Python Environment:\n   ❌ Not found\n\n")
        
        info.append(f"💻 OS: {os.name}\n")
        info.append(f"🖥️ Platform: {sys.platform}\n")
        info.append(f"👤 Admin: {'Yes ✅' if is_admin() else 'No ⚠️'}\n\n")
        
        # Check files
        manage_py = self.project_dir / 'manage.py'
        info.append(f"📄 manage.py: {'Found ✅' if manage_py.exists() else 'Not found ❌'}\n")
        
        requirements = self.project_dir / 'requirements.txt'
        info.append(f"📄 requirements.txt: {'Found ✅' if requirements.exists() else 'Not found ❌'}\n")
        
        self.system_info_text.delete('1.0', tk.END)
        self.system_info_text.insert('1.0', ''.join(info))
        
    def check_system_requirements(self):
        """Check system requirements and offer to install missing packages"""
        if not self.venv_path:
            return
        
        python_exe = self.venv_path / 'Scripts' / 'python.exe'
        
        # Map package names to their import names
        required_packages = {
            'psutil': 'psutil',
            'pywin32': 'win32api',  # pywin32 imports as win32api/win32com
            'django': 'django'
        }
        missing_packages = []
        
        # Hide console window on Windows
        startupinfo = None
        creationflags = 0
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW
        
        for package, import_name in required_packages.items():
            try:
                result = subprocess.run(
                    [str(python_exe), '-c', f'import {import_name}'],
                    capture_output=True,
                    timeout=5,
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )
                if result.returncode != 0:
                    missing_packages.append(package)
            except:
                missing_packages.append(package)
        
        if missing_packages:
            msg = f"Missing packages detected:\n\n" + "\n".join(f"• {pkg}" for pkg in missing_packages)
            msg += "\n\nWould you like to install them now?"
            
            if messagebox.askyesno("Missing Packages", msg):
                self.install_missing_packages(missing_packages)
        else:
            self.log_system("✅ All required packages are installed")
            messagebox.showinfo("System Check", 
                              "✅ All required packages are installed!\n\n"
                              "The system meets all requirements:\n"
                              "• psutil ✓\n"
                              "• pywin32 ✓\n"
                              "• django ✓")
            
    def install_missing_packages(self, packages):
        """Install missing packages"""
        if not self.venv_path:
            return
        
        python_exe = self.venv_path / 'Scripts' / 'python.exe'
        
        def install():
            # Hide console window on Windows
            startupinfo = None
            creationflags = 0
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creationflags = subprocess.CREATE_NO_WINDOW
            
            for package in packages:
                try:
                    self.log(f"📦 Installing {package}...")
                    self.update_status_bar(f"Installing {package}...")
                    
                    result = subprocess.run(
                        [str(python_exe), '-m', 'pip', 'install', package],
                        capture_output=True,
                        text=True,
                        timeout=120,
                        startupinfo=startupinfo,
                        creationflags=creationflags
                    )
                    
                    if result.returncode == 0:
                        self.log(f"✅ {package} installed successfully")
                    else:
                        self.log(f"❌ Failed to install {package}")
                except Exception as e:
                    self.log(f"❌ Error installing {package}: {e}")
            
            self.log("✅ Package installation completed")
            self.update_status_bar("Package installation completed")
            messagebox.showinfo("Success", "Package installation completed!")
        
        threading.Thread(target=install, daemon=True).start()
        
    def detect_networks(self):
        """Detect all network interfaces"""
        self.log_system("🔍 Detecting network interfaces...")
        
        self.network_interfaces = []
        
        try:
            import psutil
            
            interfaces = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            
            for interface_name, addresses in interfaces.items():
                if 'Loopback' in interface_name:
                    continue
                
                interface_info = {
                    'name': interface_name,
                    'addresses': [],
                    'is_up': stats.get(interface_name, None) and stats[interface_name].isup
                }
                
                for addr in addresses:
                    if addr.family == socket.AF_INET:
                        interface_info['addresses'].append({
                            'type': 'IPv4',
                            'address': addr.address,
                            'netmask': addr.netmask,
                            'broadcast': getattr(addr, 'broadcast', None)
                        })
                
                if interface_info['addresses']:
                    self.network_interfaces.append(interface_info)
            
            # Update combobox
            interface_names = [f"{iface['name']} {'(UP)' if iface['is_up'] else '(DOWN)'}" 
                             for iface in self.network_interfaces]
            self.interface_combo['values'] = interface_names
            
            if interface_names:
                for i, iface in enumerate(self.network_interfaces):
                    if iface['is_up']:
                        self.interface_combo.current(i)
                        break
                else:
                    self.interface_combo.current(0)
                
                self.display_network_info()
                self.log_system(f"✅ Found {len(interface_names)} network interface(s)")
        except ImportError:
            self.log_system("⚠️ psutil not installed. Installing...")
            self.install_missing_packages(['psutil'])
        except Exception as e:
            self.log_system(f"❌ Error detecting networks: {e}")
            
    def on_interface_selected(self, event):
        """Handle interface selection"""
        self.display_network_info()
        
    def display_network_info(self):
        """Display network information"""
        selected_index = self.interface_combo.current()
        if selected_index < 0 or selected_index >= len(self.network_interfaces):
            return
        
        interface = self.network_interfaces[selected_index]
        
        info = []
        info.append(f"Interface: {interface['name']}\n")
        info.append(f"Status: {'🟢 UP' if interface['is_up'] else '🔴 DOWN'}\n")
        info.append("=" * 50 + "\n\n")
        
        for addr in interface['addresses']:
            if addr['type'] == 'IPv4':
                info.append(f"IPv4 Address: {addr['address']}\n")
                info.append(f"Netmask: {addr['netmask']}\n")
                if addr.get('broadcast'):
                    info.append(f"Broadcast: {addr['broadcast']}\n")
                
                gateway = self.get_default_gateway()
                if gateway:
                    info.append(f"Gateway: {gateway}\n")
                
                info.append(f"\n🌐 Server URLs:\n")
                info.append(f"   Local:    http://127.0.0.1:8000\n")
                info.append(f"   Network:  http://{addr['address']}:8000\n")
                
                if gateway:
                    info.append(f"\n📡 Access from other devices:\n")
                    info.append(f"   http://{addr['address']}:8000\n")
        
        self.network_info_text.delete('1.0', tk.END)
        self.network_info_text.insert('1.0', ''.join(info))
        
    def get_default_gateway(self):
        """Get default gateway"""
        try:
            # Hide console window on Windows
            startupinfo = None
            creationflags = 0
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creationflags = subprocess.CREATE_NO_WINDOW
            
            result = subprocess.run(['route', 'print', '0.0.0.0'],
                                  capture_output=True, text=True, timeout=5,
                                  startupinfo=startupinfo, creationflags=creationflags)
            
            for line in result.stdout.split('\n'):
                if '0.0.0.0' in line and 'On-link' not in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        return parts[2]
        except:
            pass
        return None
        
    def start_server(self):
        """Start Django server"""
        if self.server_running:
            self.log("⚠️ Server is already running")
            return
        
        if not self.venv_path:
            messagebox.showerror("Error", "Virtual environment not found!")
            return
        
        python_exe = self.venv_path / 'Scripts' / 'python.exe'
        manage_py = self.project_dir / 'manage.py'
        
        if not manage_py.exists():
            messagebox.showerror("Error", "manage.py not found!")
            return
        
        def run_server():
            try:
                self.log("🚀 Starting Django server...")
                self.update_status("Starting...", self.colors['warning'])
                
                os.chdir(self.project_dir)
                
                # Hide console window on Windows
                startupinfo = None
                creationflags = 0
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    creationflags = subprocess.CREATE_NO_WINDOW
                
                self.server_process = subprocess.Popen(
                    [str(python_exe), str(manage_py), 'runserver', '0.0.0.0:8000'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )
                
                self.server_running = True
                self.server_crashed_count = 0
                self.start_btn.config(state='disabled')
                self.stop_btn.config(state='normal')
                self.update_status("Running", self.colors['success'])
                self.log("✅ Server started successfully")
                self.update_status_bar("Server is running on http://0.0.0.0:8000")
                
                # Read server output
                for line in iter(self.server_process.stdout.readline, ''):
                    if line:
                        self.queue.put(('stdout', line.strip()))
                    if self.server_process.poll() is not None:
                        break
                
                # Server stopped
                exit_code = self.server_process.returncode
                self.server_running = False
                
                if exit_code != 0 and self.auto_restart_enabled.get():
                    self.server_crashed_count += 1
                    self.log(f"⚠️ Server crashed with exit code {exit_code}")
                    self.log(f"🔄 Auto-restarting... (attempt {self.server_crashed_count})")
                    time.sleep(2)
                    self.start_server()
                else:
                    self.start_btn.config(state='normal')
                    self.stop_btn.config(state='disabled')
                    self.update_status("Stopped", self.colors['error'])
                    self.log("⏹️ Server stopped")
                    self.update_status_bar("Server stopped")
                
            except Exception as e:
                self.server_running = False
                self.start_btn.config(state='normal')
                self.stop_btn.config(state='disabled')
                self.update_status("Error", self.colors['error'])
                self.log(f"❌ Error starting server: {e}")
                self.update_status_bar(f"Error: {e}")
        
        threading.Thread(target=run_server, daemon=True).start()
        
    def stop_server(self):
        """Stop Django server"""
        if not self.server_running or not self.server_process:
            return
        
        try:
            self.log("⏹️ Stopping server...")
            self.auto_restart_enabled.set(False)  # Disable auto-restart
            self.server_process.terminate()
            self.server_process.wait(timeout=5)
            self.log("✅ Server stopped successfully")
        except:
            self.log("⚠️ Force killing server...")
            self.server_process.kill()
            self.log("✅ Server killed")
        
        self.server_running = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.update_status("Stopped", self.colors['error'])
        self.update_status_bar("Server stopped")
        
    def monitor_server(self):
        """Monitor server output"""
        try:
            while not self.queue.empty():
                kind, line = self.queue.get_nowait()
                self.log(line)
        except:
            pass
        
        self.root.after(100, self.monitor_server)
        
    def open_browser(self, event=None):
        """Open browser"""
        if self.network_interfaces:
            selected_index = self.interface_combo.current()
            if selected_index >= 0:
                interface = self.network_interfaces[selected_index]
                for addr in interface['addresses']:
                    if addr['type'] == 'IPv4':
                        url = f"http://{addr['address']}:8000"
                        webbrowser.open(url)
                        self.log(f"🌐 Opening browser: {url}")
                        return
        
        webbrowser.open('http://127.0.0.1:8000')
        self.log("🌐 Opening browser: http://127.0.0.1:8000")
        
    def update_users(self):
        """Update active users and recent sessions"""
        if not DJANGO_AVAILABLE or not self.db_ready or not SESSION_MANAGEMENT_AVAILABLE:
            return
        
        def update():
            try:
                # Clear trees
                for item in self.active_tree.get_children():
                    self.active_tree.delete(item)
                for item in self.recent_tree.get_children():
                    self.recent_tree.delete(item)
                
                now = timezone.now()
                
                # Active users
                active = SessionActivity.objects.filter(logout_time__isnull=True).select_related('user')
                for act in active:
                    if not Session.objects.filter(session_key=act.session_key).exists():
                        SessionActivity.objects.filter(session_key=act.session_key, 
                                                      logout_time__isnull=True).update(logout_time=now)
                        continue
                    
                    username = act.user.username if act.user else 'unknown'
                    role = act.user.role if act.user and hasattr(act.user, 'role') else '-'
                    login_time = act.login_time.strftime('%Y-%m-%d %H:%M:%S') if act.login_time else '-'
                    duration = self.format_duration((now - act.login_time).total_seconds()) if act.login_time else '-'
                    ip = act.ip_address or '-'
                    
                    self.active_tree.insert('', 'end', iid=act.session_key,
                                          values=(username, act.session_key[:8], role, login_time, duration, ip))
                
                # Recent sessions
                recent = SessionActivity.objects.filter(logout_time__isnull=False).order_by('-logout_time')[:200]
                for act in recent:
                    username = act.user.username if act.user else 'unknown'
                    role = act.user.role if act.user and hasattr(act.user, 'role') else '-'
                    login_time = act.login_time.strftime('%Y-%m-%d %H:%M:%S') if act.login_time else '-'
                    logout_time = act.logout_time.strftime('%Y-%m-%d %H:%M:%S') if act.logout_time else '-'
                    
                    if act.login_time and act.logout_time:
                        duration = self.format_duration((act.logout_time - act.login_time).total_seconds())
                    else:
                        duration = '-'
                    
                    ip = act.ip_address or '-'
                    
                    self.recent_tree.insert('', 'end', iid=f'recent-{act.id}',
                                          values=(username, act.session_key[:8], role, login_time, logout_time, duration, ip))
                
            except Exception as e:
                self.log(f"❌ Error updating users: {e}")
        
        threading.Thread(target=update, daemon=True).start()
        
    def format_duration(self, seconds):
        """Format duration"""
        seconds = int(seconds)
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f'{h:02d}:{m:02d}:{s:02d}'
        
    def disconnect_selected(self):
        """Disconnect selected users"""
        if not DJANGO_AVAILABLE or not SESSION_MANAGEMENT_AVAILABLE:
            messagebox.showwarning('Unavailable', 'Session management features are unavailable.')
            return
        
        sel = self.active_tree.selection()
        if not sel:
            messagebox.showinfo('Info', 'Please select one or more sessions to disconnect')
            return
        
        if not messagebox.askyesno('Confirm', f'Disconnect {len(sel)} session(s)?'):
            return
        
        def disconnect():
            try:
                for key in sel:
                    Session.objects.filter(session_key=key).delete()
                    SessionActivity.objects.filter(session_key=key, 
                                                  logout_time__isnull=True).update(logout_time=timezone.now())
                    try:
                        force_disconnect_session(key)
                    except:
                        pass
                    self.log(f"🔌 Disconnected session {key[:8]}")
                
                self.log(f"✅ Disconnected {len(sel)} session(s)")
                self.update_users()
            except Exception as e:
                self.log(f"❌ Error disconnecting: {e}")
        
        threading.Thread(target=disconnect, daemon=True).start()
        
    def disconnect_all(self):
        """Disconnect all users"""
        if not DJANGO_AVAILABLE or not SESSION_MANAGEMENT_AVAILABLE:
            messagebox.showwarning('Unavailable', 'Session management features are unavailable.')
            return
        
        if not messagebox.askyesno('Confirm', 'Disconnect ALL active sessions?'):
            return
        
        def disconnect():
            try:
                active = SessionActivity.objects.filter(logout_time__isnull=True)
                keys = [a.session_key for a in active]
                
                if keys:
                    Session.objects.filter(session_key__in=keys).delete()
                    active.update(logout_time=timezone.now())
                    
                    for k in keys:
                        try:
                            force_disconnect_session(k)
                        except:
                            pass
                
                self.log(f"✅ Disconnected {len(keys)} session(s)")
                self.update_users()
            except Exception as e:
                self.log(f"❌ Error disconnecting all: {e}")
        
        threading.Thread(target=disconnect, daemon=True).start()
        
    def disconnect_by_role(self):
        """Disconnect users by role"""
        if not DJANGO_AVAILABLE or not SESSION_MANAGEMENT_AVAILABLE:
            messagebox.showwarning('Unavailable', 'Session management features are unavailable.')
            return
        
        role = self.role_combo.get()
        if not role:
            messagebox.showinfo('Info', 'Please select a role')
            return
        
        if not messagebox.askyesno('Confirm', f'Disconnect all "{role}" users?'):
            return
        
        def disconnect():
            try:
                acts = SessionActivity.objects.filter(logout_time__isnull=True, user__role=role)
                keys = [a.session_key for a in acts]
                
                if keys:
                    Session.objects.filter(session_key__in=keys).delete()
                    acts.update(logout_time=timezone.now())
                    
                    for k in keys:
                        try:
                            force_disconnect_session(k)
                        except:
                            pass
                
                self.log(f"✅ Disconnected {len(keys)} {role} session(s)")
                self.update_users()
            except Exception as e:
                self.log(f"❌ Error disconnecting by role: {e}")
        
        threading.Thread(target=disconnect, daemon=True).start()
        
    def clear_recent_sessions(self):
        """Clear all recent sessions"""
        if not DJANGO_AVAILABLE or not SESSION_MANAGEMENT_AVAILABLE:
            messagebox.showwarning('Unavailable', 'Session management features are unavailable.')
            return
        
        if not messagebox.askyesno('Confirm', 'Permanently delete ALL recent session records?'):
            return
        
        def clear():
            try:
                count = SessionActivity.objects.filter(logout_time__isnull=False).delete()[0]
                self.log(f"✅ Deleted {count} recent session records")
                self.update_users()
            except Exception as e:
                self.log(f"❌ Error clearing sessions: {e}")
        
        threading.Thread(target=clear, daemon=True).start()
        
    def clear_all_sessions_on_demand(self):
        """Clear all sessions on demand"""
        if not DJANGO_AVAILABLE or not SESSION_MANAGEMENT_AVAILABLE:
            messagebox.showwarning('Unavailable', 'Session management features are unavailable.')
            return
        
        if not messagebox.askyesno('Confirm', 'Clear ALL sessions (active and recent)?'):
            return
        
        def clear():
            try:
                # Disconnect all active
                active = SessionActivity.objects.filter(logout_time__isnull=True)
                keys = [a.session_key for a in active]
                
                if keys:
                    Session.objects.filter(session_key__in=keys).delete()
                    active.update(logout_time=timezone.now())
                    
                    for k in keys:
                        try:
                            force_disconnect_session(k)
                        except:
                            pass
                
                # Clear all recent
                count = SessionActivity.objects.filter(logout_time__isnull=False).delete()[0]
                
                self.log(f"✅ Cleared {len(keys)} active and {count} recent sessions")
                self.update_users()
            except Exception as e:
                self.log(f"❌ Error clearing sessions: {e}")
        
        threading.Thread(target=clear, daemon=True).start()
        
    def install_dependencies(self):
        """Install dependencies"""
        if not self.venv_path:
            messagebox.showerror("Error", "Virtual environment not found!")
            return
        
        python_exe = self.venv_path / 'Scripts' / 'python.exe'
        requirements = self.project_dir / 'requirements.txt'
        
        if not requirements.exists():
            messagebox.showerror("Error", "requirements.txt not found!")
            return
        
        def install():
            try:
                self.log("📦 Installing dependencies...")
                self.update_status_bar("Installing dependencies...")
                
                # Hide console window
                startupinfo = None
                creationflags = 0
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    creationflags = subprocess.CREATE_NO_WINDOW
                
                result = subprocess.run(
                    [str(python_exe), '-m', 'pip', 'install', '-r', str(requirements)],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )
                
                if result.returncode == 0:
                    self.log("✅ Dependencies installed successfully")
                    self.update_status_bar("Dependencies installed")
                    messagebox.showinfo("Success", "Dependencies installed successfully!")
                else:
                    self.log(f"❌ Error: {result.stderr}")
                    messagebox.showerror("Error", f"Failed to install:\n{result.stderr[:500]}")
            except Exception as e:
                self.log(f"❌ Error: {e}")
                messagebox.showerror("Error", str(e))
        
        threading.Thread(target=install, daemon=True).start()
        
    def run_migrations(self):
        """Run migrations"""
        if not self.venv_path:
            messagebox.showerror("Error", "Virtual environment not found!")
            return
        
        python_exe = self.venv_path / 'Scripts' / 'python.exe'
        manage_py = self.project_dir / 'manage.py'
        
        def migrate():
            try:
                self.log("🗄️ Running migrations...")
                self.update_status_bar("Running migrations...")
                
                os.chdir(self.project_dir)
                
                # Hide console window
                startupinfo = None
                creationflags = 0
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    creationflags = subprocess.CREATE_NO_WINDOW
                
                result = subprocess.run(
                    [str(python_exe), str(manage_py), 'migrate'],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )
                
                if result.returncode == 0:
                    self.log("✅ Migrations completed")
                    self.log(result.stdout)
                    messagebox.showinfo("Success", "Migrations completed!")
                else:
                    self.log(f"❌ Error: {result.stderr}")
                    messagebox.showerror("Error", result.stderr[:500])
            except Exception as e:
                self.log(f"❌ Error: {e}")
                messagebox.showerror("Error", str(e))
        
        threading.Thread(target=migrate, daemon=True).start()
        
    def collect_static(self):
        """Collect static files"""
        if not self.venv_path:
            messagebox.showerror("Error", "Virtual environment not found!")
            return
        
        python_exe = self.venv_path / 'Scripts' / 'python.exe'
        manage_py = self.project_dir / 'manage.py'
        
        def collect():
            try:
                self.log("📁 Collecting static files...")
                os.chdir(self.project_dir)
                
                # Hide console window
                startupinfo = None
                creationflags = 0
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    creationflags = subprocess.CREATE_NO_WINDOW
                
                result = subprocess.run(
                    [str(python_exe), str(manage_py), 'collectstatic', '--noinput'],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )
                
                if result.returncode == 0:
                    self.log("✅ Static files collected")
                    messagebox.showinfo("Success", "Static files collected!")
                else:
                    self.log(f"❌ Error: {result.stderr}")
                    messagebox.showerror("Error", result.stderr[:500])
            except Exception as e:
                self.log(f"❌ Error: {e}")
                messagebox.showerror("Error", str(e))
        
        threading.Thread(target=collect, daemon=True).start()
        
    def create_superuser(self):
        """Create superuser"""
        if not self.venv_path:
            messagebox.showerror("Error", "Virtual environment not found!")
            return
        
        python_exe = self.venv_path / 'Scripts' / 'python.exe'
        manage_py = self.project_dir / 'manage.py'
        
        self.log("👤 Opening terminal for superuser creation...")
        os.chdir(self.project_dir)
        
        subprocess.Popen(
            ['start', 'cmd', '/k', str(python_exe), str(manage_py), 'createsuperuser'],
            shell=True
        )
        
    def create_shortcut(self):
        """Create desktop shortcut"""
        try:
            from win32com.client import Dispatch
            
            desktop = Path.home() / 'Desktop'
            shortcut_path = desktop / 'FinsPilot-ERP.lnk'
            
            target = self.project_dir / 'START_LAUNCHER.bat'
            if not target.exists():
                target = self.project_dir / 'FinsPilot-ERP.bat'
            
            # Ensure target exists
            if not target.exists():
                raise FileNotFoundError(f"Batch file not found: {target}")
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(str(shortcut_path))
            shortcut.Targetpath = str(target)
            shortcut.WorkingDirectory = str(self.project_dir)
            shortcut.Description = "FinsPilot-ERP Launcher"
            
            # Use Save (capital S) instead of save
            shortcut.Save()
            
            self.log(f"✅ Shortcut created: {shortcut_path}")
            messagebox.showinfo("Success", f"Shortcut created!\n{shortcut_path}")
        except Exception as e:
            self.log(f"❌ Error creating shortcut: {e}")
            messagebox.showerror("Error", f"Failed to create shortcut:\n{str(e)}")
            
    def install_to_location(self):
        """Install to custom location"""
        target_dir = filedialog.askdirectory(title="Select Installation Directory")
        
        if not target_dir:
            return
        
        target_path = Path(target_dir) / 'FinsPilot-ERP'
        
        if target_path.exists():
            if not messagebox.askyesno("Exists", f"{target_path} exists.\nOverwrite?"):
                return
        
        def install():
            try:
                self.log(f"📂 Installing to: {target_path}")
                self.update_status_bar(f"Installing...")
                
                if target_path.exists():
                    shutil.rmtree(target_path)
                
                shutil.copytree(self.project_dir, target_path, 
                              ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 
                                                          '.git', 'media', 'staticfiles'))
                
                self.log(f"✅ Installation completed: {target_path}")
                messagebox.showinfo("Success", f"Installed to:\n{target_path}")
            except Exception as e:
                self.log(f"❌ Error: {e}")
                messagebox.showerror("Error", str(e))
        
        threading.Thread(target=install, daemon=True).start()
        
    def copy_from_tree(self, tree):
        """Copy selected row from tree"""
        sel = tree.selection()
        if not sel:
            return
        
        items = []
        for item in sel:
            values = tree.item(item, 'values')
            items.append(' | '.join(str(v) for v in values))
        
        text = '\n'.join(items)
        
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.log(f"📋 Copied {len(items)} item(s)")
        except:
            pass
            
    def copy_from_text(self, text_widget):
        """Copy selected text"""
        try:
            selection = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selection)
            self.log("📋 Copied selection")
        except:
            pass
            
    def select_all_text(self, text_widget):
        """Select all text"""
        text_widget.tag_add(tk.SEL, "1.0", tk.END)
        text_widget.mark_set(tk.INSERT, "1.0")
        text_widget.see(tk.INSERT)
        return 'break'
        
    def update_status(self, text, color):
        """Update status indicator"""
        self.root.after(0, lambda: self.status_label.config(text=f"Server {text}"))
        self.root.after(0, lambda: self.status_indicator.itemconfig(
            self.status_circle, fill=color))
        
    def update_status_bar(self, text):
        """Update status bar"""
        self.root.after(0, lambda: self.status_bar_label.config(text=text))
        
    def log(self, message):
        """Log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.root.after(0, lambda: self._log(f"[{timestamp}] {message}\n"))
        
    def _log(self, message):
        """Internal log"""
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)
        
    def log_system(self, message):
        """Log system message"""
        print(message)
        self.update_status_bar(message)
        
    def auto_refresh(self):
        """Auto-refresh"""
        def refresh():
            if DJANGO_AVAILABLE:
                self.update_users()
            self.display_network_info()
            self.root.after(10000, refresh)
        
        self.root.after(10000, refresh)
        
    def on_closing(self):
        """Handle window closing"""
        if self.server_running:
            if messagebox.askyesno("Server Running", 
                                  "Stop server and exit?"):
                self.stop_server()
                self.root.after(1000, self.root.destroy)
        else:
            self.root.destroy()


def main():
    # Check single instance
    singleton = SingleInstance('FinsPilot-ERPLauncher')
    
    if singleton.is_already_running():
        if not singleton.bring_existing_to_front():
            messagebox.showwarning("Already Running",
                                  "FinsPilot-ERP Launcher is already running!")
        sys.exit(0)
    
    root = tk.Tk()
    
    try:
        root.iconbitmap(default='icon.ico')
    except:
        pass
    
    app = AdvancedLauncher(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()
