##########################################
# Arduino Load Sensor Serial Monitor v.4 #
# Author: Ryan Cummings                  #
# Time-stamp: <2019-09-25 14:20:22 kubo> #
##########################################

#************************************************
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton, QAction, QLineEdit, QMessageBox, QMenu, QVBoxLayout, QSizePolicy, QFileDialog, QRadioButton, QVBoxLayout, QGroupBox, QHBoxLayout, QLabel, QProgressBar, QCheckBox
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import pyqtSlot, QObject, pyqtSignal
from PyQt5.QtCore import Qt #for alignment
#************************************************
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
#************************************************
import sys
from os.path import expanduser
import glob
import serial #from the PySerial library (pip install pyserial)
import csv
import time
import random
#************************************************
import numpy as np
from statistics import mean, stdev
from scipy.signal import find_peaks
#************************************************

# Initialize variables
baudrate = 9600

class Window(QMainWindow):
    def __init__(self):
        super(Window, self).__init__() # Returns parent object: qmainwindow
        self.running = False # Initialize flag for active data collection
        self.setup_main_window()
        self.set_window_layout()
        self.set_menubar()
        self.setup_plot()

    # Basic Views
    def setup_main_window(self):
        self.centralwidget = QWidget()
        self.setCentralWidget(self.centralwidget)
        self.setWindowTitle("Suture Data Collection Tool")

    def set_window_layout(self):
        #Initialize main vertical layout with a horizontal sublayout
        self.mainVertLayout = QVBoxLayout(self.centralwidget)
        self.horizontalLayout = QHBoxLayout()
        self.mainVertLayout.addLayout(self.horizontalLayout)
        
        #Set up left and right groupboxes
        self.leftGroupBox = QGroupBox("Input Settings")
        self.horizontalLayout.addWidget(self.leftGroupBox)

        self.rightGroupBox = QGroupBox("Output")
        self.horizontalLayout.addWidget(self.rightGroupBox)

        # Add vertical layouts to groupboxes)
        self.left_vertical_layout = QVBoxLayout()
        self.right_vertical_layout = QVBoxLayout()
        self.leftGroupBox.setLayout(self.left_vertical_layout)
        self.rightGroupBox.setLayout(self.right_vertical_layout)

        # Serial port automatic listing
        ## Identify serial ports for enumeration
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')
        available_ports = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                available_ports.append(port)
            except (OSError, serial.SerialException):
                pass
        if len(available_ports) == 0:
            available_ports.append("No device connected")
        ## Create radio buttons in an option box for available ports
        self.radio_buttons = [QRadioButton(o) for o in available_ports]
        self.option_box = QGroupBox('Choose a serial device')
        radio_layout = QVBoxLayout()
        for i, button in enumerate(self.radio_buttons):
            radio_layout.addWidget(button)
            if i == 0:
                button.setChecked(True)
        self.option_box.setLayout(radio_layout)
        self.left_vertical_layout.addWidget(self.option_box)

        # Set up output settings box
        self.output_box = QGroupBox('Configure output settings')
        self.output_layout = QVBoxLayout()
        self.output_button = QPushButton("Select Output Folder")
        self.output_button.clicked.connect(self.open_folder)
        self.output_layout.addWidget(self.output_button)

        self.output_folder_textbox = QLineEdit(self)
        self.output_layout.addWidget(self.output_folder_textbox)
        self.output_folder_textbox.setText(expanduser("~"))

        self.output_box.setLayout(self.output_layout)
        self.left_vertical_layout.addWidget(self.output_box)

        # Set up file name box
        self.name_box = QGroupBox('Enter a name for output file')
        self.name_layout = QHBoxLayout()
        self.name_textbox = QLineEdit(self)
        self.name_layout.addWidget(self.name_textbox)
        self.name_textbox.setText("Example")
        self.name_textbox_label = QLabel()
        self.name_textbox_label.setText(".csv")
        self.name_layout.addWidget(self.name_textbox_label)
        self.name_box.setLayout(self.name_layout)
        self.left_vertical_layout.addWidget(self.name_box)

        # Set up misc settings box
        self.settings_box = QGroupBox('Miscellaneous Settings')
        self.settings_layout = QVBoxLayout()

        self.serial_waste_layout = QHBoxLayout()
        self.serial_waste_label = QLabel("While stabilizing, waste [n] serial values:")
        self.serial_waste_textbox = QLineEdit(self)
        self.serial_waste_textbox.setText("50")
        self.serial_waste_layout.addWidget(self.serial_waste_label)
        self.serial_waste_layout.addWidget(self.serial_waste_textbox)
        
        self.plot_length_layout = QHBoxLayout()
        self.plot_length_label = QLabel("How many values to plot (low = fast):")
        self.plot_length_textbox = QLineEdit(self)
        self.plot_length_textbox.setText("40")
        self.plot_length_layout.addWidget(self.plot_length_label)
        self.plot_length_layout.addWidget(self.plot_length_textbox)
        
        self.plot_steps_layout = QHBoxLayout()
        self.plot_steps_label = QLabel("Plot every [n] new values (high=fast):")
        self.plot_steps_textbox = QLineEdit(self)
        self.plot_steps_textbox.setText("1")
        self.plot_steps_layout.addWidget(self.plot_steps_label)
        self.plot_steps_layout.addWidget(self.plot_steps_textbox)
        
        self.invert_checkbox = QCheckBox("Invert values")

        self.peak_int_layout = QHBoxLayout()
        self.peak_int_label = QLabel("Peak search interval:")
        self.peak_int_text = QLineEdit(self)
        self.peak_int_text.setText("10")
        self.peak_int_layout.addWidget(self.peak_int_label)
        self.peak_int_layout.addWidget(self.peak_int_text)
        
        self.settings_layout.addLayout(self.serial_waste_layout)
        self.settings_layout.addLayout(self.plot_length_layout)
        self.settings_layout.addLayout(self.plot_steps_layout)
        self.settings_layout.addWidget(self.invert_checkbox)
        self.settings_layout.addLayout(self.peak_int_layout)

        self.settings_box.setLayout(self.settings_layout)
        self.left_vertical_layout.addWidget(self.settings_box)


        #         invert = 1 # Change to -1 if values are inverted on the plot
        # local_peak_interval = 10 # The software will keep the highest local peak over this many values and filter out the rest
        # serial_delay_waste = 50
        # plot_steps = 1
        # plot_max_length = 40


        # Add some filler space
        self.left_vertical_layout.addStretch()
        
        # Set up stop and go buttons
        self.go_stop_layout = QHBoxLayout()
        self.go_btn = QPushButton("Go")
        self.go_btn.clicked.connect(self.run_trial)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_trial)
        self.go_btn.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Expanding)
        self.stop_btn.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Expanding)
        self.go_stop_layout.addWidget(self.go_btn, 2)
        self.go_stop_layout.addWidget(self.stop_btn, 2)
        self.left_vertical_layout.addLayout(self.go_stop_layout)

        # Progress Bar
        self.progress = QProgressBar(self)
        self.progress.setValue(0)
        self.left_vertical_layout.addWidget(self.progress)
        
        # Add some helpful text about serial delay
        self.go_stop_label = QLabel()
        self.go_stop_label.setText("Note: Program will wait for serial to stabilize before beginning to record data. Start suturing when progress bar is finished and plotter begins to plot new values.")
        self.go_stop_label.setWordWrap(True)
        self.left_vertical_layout.addWidget(self.go_stop_label)

        # Set up analysis button
        self.analyze_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("Analyze captured data file")
        self.analyze_btn.clicked.connect(self.analyze_data)
        self.analyze_btn.setEnabled(False)
        self.analyze_layout.addWidget(self.analyze_btn)
        
        # Set up save and discard buttons
        self.discard_btn = QPushButton("Discard")
        self.discard_btn.clicked.connect(self.discard_file)
        self.analyze_layout.addWidget(self.discard_btn)
        self.right_vertical_layout.addLayout(self.analyze_layout)
                
    def set_menubar(self):
        # Main Menu Setup
        extractAction = QAction("&Quit", self)
        extractAction.setShortcut("Ctrl+Q")
        extractAction.triggered.connect(self.close_application)

        ## Launch Menu
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu('&File')
        fileMenu.addAction(extractAction)

    def setup_plot(self):
        self.fig = Figure(figsize=(5, 3), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding,
                                  QSizePolicy.Expanding)
        self.right_vertical_layout.addWidget(self.canvas)

    # Functions
    def get_filename(self):
        # Returns the filename based on gui text box inputs
        filename = self.name_textbox.text() + '.csv'
        base_dir = self.output_folder_textbox.text()
        return os.path.join(base_dir, filename)
        
    def plot(self, x, y):
        # Plots x and y for live plots
        filename = self.get_filename()
        try:
            self.ax.remove()
        except:
            pass
        self.ax = self.canvas.figure.add_subplot(111)
        self.ax.plot(x, y, 'r-')
        self.ax.set_title(f'{filename}')
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Force')
        
        self.canvas.draw()
    
    def open_folder(self):
        # Dialog to select an output directory
        file = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        self.output_folder_textbox.setText(file)

    def close_application(self):
        sys.exit()

    def run_trial(self):
        if self.running:
            return

        invert = 1
        if self.invert_checkbox.isChecked():
            invert = -1

        serial_delay_waste = int(self.serial_waste_textbox.text())
        plot_max_length = int(self.plot_length_textbox.text())
        plot_steps = int(self.plot_steps_textbox.text())
        
        self.clear_plot()
        self.canvas.draw()
        self.ax = self.canvas.figure.add_subplot(111)
        self.running = True
        filename = self.get_filename()
        for button in self.radio_buttons:
            if button.isChecked():
                portname = button.text()
        self.x = []
        self.y = []

        try:
            os.remove(filename)
        except:
            pass

        startTime = time.time()
        elapsedTime = 0

        try:
            with serial.Serial(portname,baudrate) as s:
                s.flushInput()
                s.flushOutput()
                i = 0
                while self.running:
                    i += 1
                    if i <= serial_delay_waste:
                        value = s.readline()
                        self.progress.setValue(i / serial_delay_waste * 100)
                        QApplication.processEvents()
                    else:
                        if i == serial_delay_waste + 1:
                            startTime = time.time()
                        value = s.readline() # read line (single value) from the serial port
                        rightnow = time.time()
                        elapsedTime = rightnow - startTime
                        try:
                            value = float(value) * invert
                        except:
                            value = 0.0
                        self.x.append(elapsedTime)
                        self.y.append(value)
                        QApplication.processEvents()
                        if i % plot_steps == 0:
                            if i > serial_delay_waste + plot_max_length:
                                self.plot(self.x[-plot_max_length:], self.y[-plot_max_length:])
                            else:
                                self.plot(self.x, self.y)
        except:
            print(arg)
            sys.exit()
                
    def stop_trial(self):
        if self.running == False:
            return
        filename = self.get_filename()
        with open(filename, 'w') as csvfile:
            writer = csv.writer(csvfile,
                                delimiter=',',
                                quotechar='|',
                                quoting=csv.QUOTE_MINIMAL,
                                lineterminator = '\n')

        
            for x, y in zip(self.x, self.y):
                writer.writerow((str(x), str(y)))

        if os.path.exists(filename):
            self.analyze_btn.setEnabled(True)
            self.discard_btn.setEnabled(True)
        self.progress.setValue(0)
        self.running = False

    def discard_file(self):
        if self.running == True:
            return
        filename = self.get_filename()
        try:
            os.remove(filename)
            remove_msg = QMessageBox.about(self, "Filename Deletion", f"{filename} was deleted")
        except:
            remove_msg = QMessageBox.about(self, "Filename Deletion", "Nothing to discard. Try another run.")
        try:
            summary_name = filename[:-4] + '_summarystats.csv'
            os.remove(summary_name)
        except:
            pass
        
        self.analyze_btn.setEnabled(False)
        self.discard_btn.setEnabled(False)
        self.clear_plot()
        self.canvas.draw()

    def clear_plot(self):
        try:
            self.ax.remove()
        except:
            pass
        
    def analyze_data(self):
        local_peak_interval = int(self.peak_int_text.text())
        filename = self.get_filename()
        if not os.path.exists(filename):
            msg = QMessageBox.about(self, "Nothing to analyze", "There is no file to analyze. Try another run.")
            self.analyze_btn.setEnabled(False)
            return

        x = []
        y = []
        stats = {}

        with open(filename, 'r') as csvFile:
            reader = csv.reader(csvFile)
            for row in reader:
                x.append(float(row[0]))
                y.append(float(row[1]))

        name = filename[:-4]
        stats['Max force'] = max(y)
        stats['Min force'] = min(y)
        stats['Avg force'] = mean(y)
        stats['Std Dev force'] = stdev(y)
        
        peak_index, _ = find_peaks(y, distance=local_peak_interval, height=1)
        peaks_x = []
        peaks_y = []
        if len(peak_index) == 0:
            msg = QMessageBox("No peaks found; aborting...")
            return
        
        for peak in peak_index:
            peaks_x.append(x[peak])
            peaks_y.append(y[peak])

        stats['Avg peak force'] = mean(peaks_y)

        with open(f'{name}_summarystats.csv', 'w') as csvfile:
            writer = csv.writer(csvfile, delimiter=',',
                                quotechar='|', quoting=csv.QUOTE_MINIMAL, lineterminator = '\n')
            writer.writerow(f"Summary Stats for {name}")
            for key in stats:
                print(f"{key}: {stats[key]}")
                writer.writerow((key, stats[key]))
            writer.writerow("Peak Values")
            writer.writerow(("Time", "Force"))
            for i in range(len(peaks_x)):
                writer.writerow((f"{peaks_x[i]}", f"{peaks_y[i]}"))
        self.clear_plot()
        self.ax = self.canvas.figure.add_subplot(111)
        self.ax.plot(x, y)
        self.ax.plot(peaks_x, peaks_y, "x")
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Force')
        self.ax.set_title(f'{filename}')
        self.canvas.draw()

def run():
    app = QApplication(sys.argv)
    GUI = Window()
    GUI.show()
    sys.exit(app.exec_())


run()
