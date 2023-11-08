import sys
import subprocess
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QAction, QMenu, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QFormLayout, QHBoxLayout, QStyle, QComboBox
from PyQt5.QtCore import Qt

class NetworkAdapterManager(QMainWindow):
    def __init__(self, network_adapters):
        super().__init__()

        self.network_adapters = network_adapters
        self.ip_profiles = {}

        self.init_ui()

    def init_ui(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        self.tray_icon.setToolTip('Network Adapter Manager')

        self.create_context_menu()

        self.tray_icon.show()

    def create_context_menu(self):
        menu = QMenu()
        select_adapter_menu = menu.addMenu("Select Adapter")
        for adapter in self.network_adapters:
            adapter_name = adapter['Name']
            adapter_action = QAction(adapter_name, self)
            adapter_action.triggered.connect(lambda checked, adapter=adapter: self.show_adapter_settings(adapter))
            select_adapter_menu.addAction(adapter_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close_app)
        menu.addSeparator()
        menu.addAction(exit_action)

        self.tray_icon.setContextMenu(menu)

    def show_adapter_settings(self, adapter):
        adapter_name = adapter['Name']
        self.adapter_window = AdapterSettingsWindow(adapter_name, self.ip_profiles.get(adapter_name, {}), self.ip_profiles)
        self.adapter_window.show()

    def close_app(self):
        self.tray_icon.hide()
        sys.exit()

class AdapterSettingsWindow(QWidget):
    def __init__(self, adapter_name, profile_data, all_profiles):
        super().__init__()

        self.adapter_name = adapter_name
        self.original_settings = None
        self.profile_data = profile_data
        self.all_profiles = all_profiles

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f'IPv4 Configuration - {self.adapter_name}')
        self.setGeometry(100, 100, 400, 250)

        layout = QVBoxLayout()

        label = QLabel(f'IPv4 Configuration for Adapter {self.adapter_name} (Leave fields empty for DHCP):', self)
        self.ip_input = QLineEdit(self)
        self.subnet_input = QLineEdit(self)
        self.gateway_input = QLineEdit(self)
        set_button = QPushButton("Save", self)
        set_button.clicked.connect(self.set_configuration)
        revert_button = QPushButton("Revert to DHCP", self)
        revert_button.clicked.connect(self.revert_to_dhcp)
        
        profile_label = QLabel("Select Profile:", self)
        self.profile_combo = QComboBox(self)
        self.profile_combo.addItem("Default") 

        for profile_name in self.all_profiles:
            self.profile_combo.addItem(profile_name)

        form_layout = QFormLayout()
        form_layout.addRow("IP Address:", self.ip_input)
        form_layout.addRow("Subnet Mask:", self.subnet_input)
        form_layout.addRow("Default Gateway:", self.gateway_input)

        layout.addWidget(label)
        layout.addLayout(form_layout)
        layout.addSpacing(10)
        layout.addWidget(profile_label)
        layout.addWidget(self.profile_combo)
        button_layout = QHBoxLayout()
        button_layout.addWidget(set_button)
        button_layout.addWidget(revert_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        
        self.set_profile_data(self.profile_data)

    def get_profile_data(self):
        return {
            'ip': self.ip_input.text(),
            'subnet': self.subnet_input.text(),
            'gateway': self.gateway_input.text()
        }

    def set_profile_data(self, profile_data):
        self.ip_input.setText(profile_data.get('ip', ''))
        self.subnet_input.setText(profile_data.get('subnet', ''))
        self.gateway_input.setText(profile_data.get('gateway', ''))

    def set_configuration(self):
        static_ip = self.ip_input.text()
        subnet = self.subnet_input.text()
        gateway = self.gateway_input.text()

        if not static_ip and not gateway and not subnet:
            subprocess.run(["netsh", "interface", "ipv4", "set", "address", f"name={self.adapter_name}", "source=dhcp"])
        else:
            commands = ["netsh", "interface", "ipv4", "set", "address", f"name={self.adapter_name}"]
            if static_ip:
                commands.extend([f"source=static", f"addr={static_ip}", f"mask={subnet}", f"gateway={gateway}"])
            subprocess.run(commands)

    def revert_to_dhcp(self):
        subprocess.run(["netsh", "interface", "ipv4", "set", "address", f"name={self.adapter_name}", "dhcp"])
        self.ip_input.clear()
        self.subnet_input.clear()
        self.gateway_input.clear()
        self.profile_combo.setCurrentIndex(0)

def list_network_adapters():
    raw_result = subprocess.run(
        ["powershell.exe", "-Command", "ConvertTo-Json -InputObject (Get-NetAdapter | Select-Object -Property Name,InterfaceDescription,ifIndex)"],
        capture_output=True,
        text=True
    )
    network_adapters = json.loads(raw_result.stdout)
    return network_adapters

def main():
    app = QApplication(sys.argv)
    network_adapters = list_network_adapters()
    network_manager = NetworkAdapterManager(network_adapters)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
