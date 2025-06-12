import sys
import asyncio
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QPushButton, QTextEdit, QLineEdit, QLabel,
                             QFileDialog, QProgressBar, QTabWidget, QFormLayout,
                             QCheckBox, QSpinBox, QGroupBox, QSplitter
                             )
from PyQt5.QtCore import pyqtSignal, Qt, QObject
from PyQt5.QtGui import QFont, QTextCursor
import qasync
from sshoperations import run_commands_with_variables

def trim(dataset):
    return dataset.map(lambda x: x.strip() if isinstance(x, str) else x)

class SSHSignals(QObject):
    """Signals for async SSH operations"""
    progress_update = pyqtSignal(str)  # For progress messages
    device_completed = pyqtSignal(str, bool)  # hostname, success
    command_output = pyqtSignal(str, str, str)  # hostname, command, output
    finished_all = pyqtSignal()
    device_started = pyqtSignal(str)  # hostname


class SSHManagerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.devices = []
        self.current_task = None
        self.signals = SSHSignals()
        self.setup_ui()
        self.connect_signals()

    def connect_signals(self):
        """Connect async signals to UI updates"""
        self.signals.progress_update.connect(self.update_progress)
        self.signals.device_completed.connect(self.device_completed)
        self.signals.command_output.connect(self.command_output)
        self.signals.finished_all.connect(self.execution_finished)
        self.signals.device_started.connect(self.device_started)

    def setup_ui(self):
        self.setWindowTitle("SSH/SFTP Device Manager")
        self.setGeometry(100, 100, 1000, 700)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)

        # Create tab widget
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # Configuration Tab
        config_tab = self.create_config_tab()
        tab_widget.addTab(config_tab, "Configuration")

        # Execution Tab
        exec_tab = self.create_execution_tab()
        tab_widget.addTab(exec_tab, "Execution")

        # Results Tab
        results_tab = self.create_results_tab()
        tab_widget.addTab(results_tab, "Results")

    def create_config_tab(self):
        """Create the configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Device file selection
        file_group = QGroupBox("Device Configuration")
        file_layout = QFormLayout(file_group)

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select devices.txt or CSV file...")
        file_browse_btn = QPushButton("Browse")
        file_browse_btn.clicked.connect(self.browse_device_file)

        file_row = QHBoxLayout()
        file_row.addWidget(self.file_path_edit)
        file_row.addWidget(file_browse_btn)
        file_layout.addRow("Device File:", file_row)

        # Host column
        self.host_column_edit = QLineEdit("IP Address")
        file_layout.addRow("Host Column:", self.host_column_edit)

        layout.addWidget(file_group)

        # SSH Credentials
        cred_group = QGroupBox("SSH Credentials")
        cred_layout = QFormLayout(cred_group)

        self.username_edit = QLineEdit("admin")
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)

        cred_layout.addRow("Username:", self.username_edit)
        cred_layout.addRow("Password:", self.password_edit)

        layout.addWidget(cred_group)

        # Commands
        cmd_group = QGroupBox("Commands to Execute")
        cmd_layout = QVBoxLayout(cmd_group)

        self.commands_edit = QTextEdit()
        self.commands_edit.setPlaceholderText(
            "Enter commands, one per line:\nversion\necho {NewIP Address}\nshow ip interface brief")
        self.commands_edit.setMaximumHeight(150)
        cmd_layout.addWidget(self.commands_edit)

        layout.addWidget(cmd_group)

        # Transfer options
        transfer_group = QGroupBox("File Transfer Options")
        transfer_layout = QVBoxLayout(transfer_group)

        self.enable_transfer = QCheckBox("Enable file transfers")
        transfer_layout.addWidget(self.enable_transfer)

        # Firmware transfer section
        firmware_group = QGroupBox("Firmware Transfer")
        firmware_layout = QFormLayout(firmware_group)

        self.enable_firmware = QCheckBox("Transfer firmware")
        self.firmware_local_edit = QLineEdit("./firmware.bin")
        self.firmware_remote_edit = QLineEdit("./ftp/firmware/")

        firmware_browse_btn = QPushButton("Browse")
        firmware_browse_btn.clicked.connect(lambda: self.browse_file(self.firmware_local_edit))

        firmware_row = QHBoxLayout()
        firmware_row.addWidget(self.firmware_local_edit)
        firmware_row.addWidget(firmware_browse_btn)

        firmware_layout.addRow("", self.enable_firmware)
        firmware_layout.addRow("Local Firmware:", firmware_row)
        firmware_layout.addRow("Remote Path:", self.firmware_remote_edit)

        transfer_layout.addWidget(firmware_group)

        # Program transfer section
        program_group = QGroupBox("Program Transfer")
        program_layout = QFormLayout(program_group)

        self.enable_program = QCheckBox("Transfer program")
        self.program_local_edit = QLineEdit("./program.zip")
        self.program_remote_edit = QLineEdit("./nvram/")

        program_browse_btn = QPushButton("Browse")
        program_browse_btn.clicked.connect(lambda: self.browse_file(self.program_local_edit))

        program_row = QHBoxLayout()
        program_row.addWidget(self.program_local_edit)
        program_row.addWidget(program_browse_btn)

        program_layout.addRow("", self.enable_program)
        program_layout.addRow("Local Program:", program_row)
        program_layout.addRow("Remote Path:", self.program_remote_edit)

        transfer_layout.addWidget(program_group)

        layout.addWidget(transfer_group)

        # Concurrency
        perf_group = QGroupBox("Performance Settings")
        perf_layout = QFormLayout(perf_group)

        self.max_concurrent = QSpinBox()
        self.max_concurrent.setRange(1, 50)
        self.max_concurrent.setValue(5)

        perf_layout.addRow("Max Concurrent:", self.max_concurrent)

        layout.addWidget(perf_group)

        # Load devices button
        load_btn = QPushButton("Load Devices")
        print(f"Button type: {type(load_btn)}")
        print(f"Has clicked attribute: {hasattr(load_btn, 'clicked')}")
        print(f"Clicked type: {type(load_btn.clicked) if hasattr(load_btn, 'clicked') else 'No clicked'}")
        load_btn.clicked.connect(self.load_devices)
        layout.addWidget(load_btn)



        # Device count label
        self.device_count_label = QLabel("No devices loaded")
        layout.addWidget(self.device_count_label)

        layout.addStretch()
        return widget

    def create_execution_tab(self):
        """Create the execution tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Control buttons
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start Execution")
        self.start_btn.clicked.connect(self.start_execution)
        self.start_btn.setEnabled(False)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_execution)
        self.cancel_btn.setEnabled(False)

        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Status text
        self.status_label = QLabel("Ready to execute")
        layout.addWidget(self.status_label)

        # Real-time output
        output_group = QGroupBox("Real-time Output")
        output_layout = QVBoxLayout(output_group)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 9))
        output_layout.addWidget(self.output_text)

        layout.addWidget(output_group)

        return widget

    def create_results_tab(self):
        """Create the results tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Results summary
        summary_group = QGroupBox("Execution Summary")
        summary_layout = QFormLayout(summary_group)

        self.total_devices_label = QLabel("0")
        self.successful_label = QLabel("0")
        self.failed_label = QLabel("0")

        summary_layout.addRow("Total Devices:", self.total_devices_label)
        summary_layout.addRow("Successful:", self.successful_label)
        summary_layout.addRow("Failed:", self.failed_label)

        layout.addWidget(summary_group)

        # Detailed results
        results_group = QGroupBox("Detailed Results")
        results_layout = QVBoxLayout(results_group)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Consolas", 9))
        results_layout.addWidget(self.results_text)

        # Export button
        export_btn = QPushButton("Export Results")
        export_btn.clicked.connect(self.export_results)
        results_layout.addWidget(export_btn)

        layout.addWidget(results_group)

        return widget

    def browse_file(self, line_edit):
        """Open file dialog to select any file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select File", "", "All Files (*)"
        )
        if file_path:
            line_edit.setText(file_path)

    def browse_device_file(self):
        """Open file dialog to select device file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Device File", "",
            "Text Files (*.txt);;CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            self.file_path_edit.setText(file_path)

    def load_devices(self):
        """Load devices from the selected file"""
        print('load_device_function')
        file_path = self.file_path_edit.text()
        if not file_path:
            self.status_label.setText("Please select a device file first")
            return

        try:
            # Load the file
            print('loading file')
            # Fix: .endswith() takes a tuple for multiple extensions
            if file_path.endswith(('.csv', '.txt')):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_csv(file_path, delimiter='\t')  # Assume tab-delimited

            # Clean data - Fix: you're reading the file twice, only need once
            df = trim(df)  # Use the df you already loaded above
            df.columns = df.columns.str.strip()

            # Convert to device list
            print('working on host column')
            host_column = self.host_column_edit.text()
            if host_column not in df.columns:
                self.status_label.setText(f"Column '{host_column}' not found in file")
                return

            self.devices = []
            # Fix: syntax errors in the loop
            for _, row in df.iterrows():  # underscore, not asterisk
                host = row[host_column]  # underscore, not asterisk
                variables = row.drop(host_column).to_dict()
                self.devices.append({
                    'host': host,
                    'variables': variables
                })

            # Update UI
            count = len(self.devices)
            self.device_count_label.setText(f"Loaded {count} devices")
            self.total_devices_label.setText(str(count))
            self.start_btn.setEnabled(count > 0)
            self.status_label.setText(f"Successfully loaded {count} devices")

        except Exception as e:
            self.status_label.setText(f"Error loading file: {str(e)}")
            print(f"Error: {e}")  # This will help you see what went wrong

    @qasync.asyncSlot()
    async def start_execution(self):
        """Start the SSH execution process using pure asyncio"""
        if not self.devices:
            self.status_label.setText("No devices loaded")
            return

        # Get commands
        commands_text = self.commands_edit.toPlainText().strip()
        if not commands_text:
            self.status_label.setText("No commands specified")
            return

        commands = [cmd.strip() for cmd in commands_text.split('\n') if cmd.strip()]

        # Get credentials
        username = self.username_edit.text()
        password = self.password_edit.text()

        if not username or not password:
            self.status_label.setText("Please enter username and password")
            return

        # Setup UI for execution
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.output_text.clear()
        self.results_text.clear()
        self.progress_bar.setMaximum(len(self.devices))
        self.progress_bar.setValue(0)

        # Prepare transfer configurations
        firmware_config = {
            'enabled': self.enable_firmware.isChecked(),
            'local_file': self.firmware_local_edit.text(),
            'remote_path': self.firmware_remote_edit.text()
        }

        program_config = {
            'enabled': self.enable_program.isChecked(),
            'local_file': self.program_local_edit.text(),
            'remote_path': self.program_remote_edit.text()
        }

        # Start async execution
        self.current_task = asyncio.create_task(
            self.run_ssh_batch(self.devices, commands, username, password,
                               firmware_config, program_config)
        )

        self.status_label.setText("Execution started...")

    async def run_ssh_batch(self, devices, commands, username, password,
                            firmware_config, program_config):
        """Run SSH operations on all devices concurrently"""
        max_concurrent = self.max_concurrent.value()
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_single_device(device):
            async with semaphore:
                return await self.process_device(device, commands, username, password,
                                                 firmware_config, program_config)

        # Create tasks for all devices
        tasks = [process_single_device(device) for device in devices]

        # Run all devices concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process final results
        self.signals.finished_all.emit()
        return results

    async def process_device(self, device_info, commands, username, password,
                             firmware_config, program_config):
        """Process a single device - replace this with your actual SSH function"""
        hostname = device_info['host']
        variables = device_info.get('variables', {})

        try:
            self.signals.device_started.emit(hostname)
            self.signals.progress_update.emit(f"Connecting to {hostname}...")

            # This is where you'd call your actual function:
            result = await run_commands_with_variables(device_info, commands, username, password)

            # Simulate for now
            await asyncio.sleep(1)  # Simulate connection

            # Process each command template with variables
            for command_template in commands:
                # Format command with device-specific variables (same as your existing code)
                try:
                    formatted_command = command_template.format(**variables)
                except KeyError as e:
                    # Handle missing variables gracefully
                    formatted_command = command_template
                    self.signals.progress_update.emit(f"Warning: Variable {e} not found for {hostname}")

                self.signals.progress_update.emit(f"Running '{formatted_command}' on {hostname}")
                await asyncio.sleep(0.5)  # Simulate command execution

                # Simulate command output
                output = f"Simulated output from '{formatted_command}' on {hostname}"
                self.signals.command_output.emit(hostname, formatted_command, output)

            # Simulate file transfers
            if firmware_config.get('enabled'):
                self.signals.progress_update.emit(f"Transferring firmware to {hostname}...")
                await asyncio.sleep(2)  # Simulate transfer

            if program_config.get('enabled'):
                self.signals.progress_update.emit(f"Transferring program to {hostname}...")
                await asyncio.sleep(2)  # Simulate transfer

            self.signals.device_completed.emit(hostname, True)
            return {'host': hostname, 'success': True}

        except Exception as e:
            self.signals.device_completed.emit(hostname, False)
            self.signals.progress_update.emit(f"ERROR on {hostname}: {str(e)}")
            return {'host': hostname, 'success': False, 'error': str(e)}

    def cancel_execution(self):
        """Cancel the current execution"""
        if self.current_task:
            self.current_task.cancel()
            self.status_label.setText("Cancelling...")

    def device_started(self, hostname):
        """Handle device start"""
        self.output_text.append(f"[STARTED] {hostname}")
        self.output_text.moveCursor(QTextCursor.End)

    def update_progress(self, message):
        """Update progress display"""
        self.output_text.append(f"[INFO] {message}")
        self.output_text.moveCursor(QTextCursor.End)

    def device_completed(self, hostname, success):
        """Handle device completion"""
        current = self.progress_bar.value()
        self.progress_bar.setValue(current + 1)

        status = "SUCCESS" if success else "FAILED"
        self.output_text.append(f"[{status}] {hostname}")
        self.output_text.moveCursor(QTextCursor.End)

        # Update summary
        if success:
            current_success = int(self.successful_label.text())
            self.successful_label.setText(str(current_success + 1))
        else:
            current_failed = int(self.failed_label.text())
            self.failed_label.setText(str(current_failed + 1))

    def command_output(self, hostname, command, output):
        """Handle command output"""
        self.results_text.append(f"\n=== {hostname} - {command} ===")
        self.results_text.append(output)
        self.results_text.moveCursor(QTextCursor.End)

    def execution_finished(self):
        """Handle execution completion"""
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("Execution completed")
        self.output_text.append("[INFO] All devices processed")
        self.current_task = None

    def export_results(self):
        """Export results to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "ssh_results.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(self.results_text.toPlainText())
                self.status_label.setText(f"Results exported to {file_path}")
            except Exception as e:
                self.status_label.setText(f"Export failed: {str(e)}")


def main():
    app = QApplication(sys.argv)

    # Setup async event loop for PyQt
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = SSHManagerUI()
    window.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()