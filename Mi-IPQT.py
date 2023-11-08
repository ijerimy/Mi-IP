import sys
import subprocess
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QAction, QMenu, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QFormLayout, QHBoxLayout, QStyle, QComboBox, QMessageBox, QCheckBox
from PyQt5.QtCore import Qt
import os

class NetworkAdapterManager(QMainWindow):
    def __init__(self, network_adapters):
        super().__init__()

        if not network_adapters:
            self.show_message("Error", "No network adapters found. Make sure you have at least one network adapter connected.")
            sys.exit(1)

        self.network_adapters = network_adapters
        self.current_profile = None

        self.init_ui()

    def init_ui(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        self.tray_icon.setToolTip('Network Adapter Manager')

        self.create_context_menu()

        self.tray_icon.show()

    def create_context_menu(self):
        menu = QMenu()
        open_manager_action = QAction("Open Manager", self)
        open_manager_action.triggered.connect(self.open_manager)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close_app)

        menu.addAction(open_manager_action)
        menu.addSeparator()
        menu.addAction(exit_action)

        self.tray_icon.setContextMenu(menu)

    def open_manager(self):
        self.adapter_settings_dialog = AdapterSettingsDialog(self.network_adapters, self.current_profile)
        self.adapter_settings_dialog.show()

    def close_app(self):
        self.tray_icon.hide()
        sys.exit()

    def show_message(self, title, message):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec_()

class AdapterSettingsDialog(QWidget):
    def __init__(self, network_adapters, current_profile):
        super().__init__()

        self.network_adapters = network_adapters
        self.current_profile = current_profile
        self.adapter_name = None

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Network Adapter Manager")
        self.setGeometry(100, 100, 400, 350)

        layout = QVBoxLayout()

        label = QLabel("Select a network adapter:", self)
        self.adapter_combo = QComboBox(self)
        for adapter in self.network_adapters:
            self.adapter_combo.addItem(adapter['Name'])

        profile_label = QLabel("Select Profile:", self)
        self.profile_combo = QComboBox(self)
        self.load_profiles()
        self.profile_combo.currentIndexChanged.connect(self.select_profile)

        save_profile_checkbox = QCheckBox("Save Profile", self)
        save_profile_checkbox.stateChanged.connect(self.toggle_profile_saving)

        apply_button = QPushButton("Apply Configuration", self)
        apply_button.clicked.connect(self.apply_configuration)

        layout.addWidget(label)
        layout.addWidget(self.adapter_combo)
        layout.addWidget(profile_label)
        layout.addWidget(self.profile_combo)
        layout.addWidget(save_profile_checkbox)
        layout.addSpacing(10)  # Add some spacing between the dropdowns and IP info

        label = QLabel("IPv4 Configuration (Leave fields empty for DHCP):", self)
        self.ip_input = QLineEdit(self)
        self.subnet_input = QLineEdit(self)
        self.gateway_input = QLineEdit(self)
        revert_button = QPushButton("Revert to DHCP", self)
        revert_button.clicked.connect(self.revert_to_dhcp)

        form_layout = QFormLayout()
        form_layout.addRow("IP Address:", self.ip_input)
        form_layout.addRow("Subnet Mask:", self.subnet_input)
        form_layout.addRow("Default Gateway:", self.gateway_input)

        layout.addWidget(label)
        layout.addLayout(form_layout)
        layout.addSpacing(10)

        # DNS Settings Section
        dns_label = QLabel("DNS Configuration:", self)
        self.dns_mode_combo = QComboBox(self)
        self.dns_mode_combo.addItem("Manually Enter DNS")
        self.dns_mode_combo.addItem("Select DNS Provider")
        self.dns_mode_combo.currentIndexChanged.connect(self.toggle_dns_mode)

        self.dns_manual_input = QLineEdit(self)
        self.dns_manual_input.setPlaceholderText("Enter DNS Address")
        self.dns_provider_combo = QComboBox(self)
        self.dns_provider_combo.addItems(["Google DNS (8.8.8.8, 8.8.4.4)", "OpenDNS (208.67.222.222, 208.67.220.220)", "Cloudflare DNS (1.1.1.1, 1.0.0.1)"])

        layout.addWidget(dns_label)
        layout.addWidget(self.dns_mode_combo)
        layout.addWidget(self.dns_manual_input)
        layout.addWidget(self.dns_provider_combo)

        button_layout = QHBoxLayout()
        button_layout.addWidget(apply_button)
        button_layout.addWidget(revert_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def toggle_dns_mode(self, index):
        manual_mode = index == 0
        self.dns_manual_input.setEnabled(manual_mode)
        self.dns_provider_combo.setEnabled(not manual_mode)

    def toggle_profile_saving(self, state):
        if state == Qt.Checked:
            self.save_profile()
        else:
            self.remove_saved_profile()

    def select_profile(self, index):
        if index >= 0:
            selected_profile = self.profile_combo.itemText(index)
            self.load_profile(selected_profile)

    def save_profile(self):
        profile_name = self.ip_input.text()  # Use IP address as profile name
        profile_data = {
            'IP': self.ip_input.text(),
            'Subnet': self.subnet_input.text(),
            'Gateway': self.gateway_input.text(),
            'DNSManual': self.dns_manual_input.text(),
            'DNSProvider': self.dns_provider_combo.currentText()
        }

        profile_dir = os.path.expanduser("~/.network_adapter_manager_profiles")
        if not os.path.exists(profile_dir):
            os.makedirs(profile_dir)

        profile_file = os.path.join(profile_dir, f"{profile_name}.json")
        with open(profile_file, 'w') as f:
            json.dump(profile_data, f)

        self.load_profiles()
        self.profile_combo.setCurrentText(profile_name)

    def remove_saved_profile(self):
        if self.current_profile:
            profile_file = os.path.join(os.path.expanduser("~/.network_adapter_manager_profiles"), f"{self.current_profile}.json")
            if os.path.exists(profile_file):
                os.remove(profile_file)
            self.load_profiles()

    def load_profiles(self):
        profile_dir = os.path.expanduser("~/.network_adapter_manager_profiles")
        if not os.path.exists(profile_dir):
            return

        profiles = [f.replace('.json', '') for f in os.listdir(profile_dir) if f.endswith('.json')]
        self.profile_combo.clear()
        self.profile_combo.addItems(profiles)

    def load_profile(self, profile_name):
        profile_file = os.path.join(os.path.expanduser("~/.network_adapter_manager_profiles"), f"{profile_name}.json")
        if os.path.exists(profile_file):
            with open(profile_file, 'r') as f:
                profile_data = json.load(f)
                self.ip_input.setText(profile_data.get('IP', ''))
                self.subnet_input.setText(profile_data.get('Subnet', ''))
                self.gateway_input.setText(profile_data.get('Gateway', ''))
                dns_manual = profile_data.get('DNSManual', '')
                self.dns_manual_input.setText(dns_manual)
                dns_provider = profile_data.get('DNSProvider', 'Manually Enter DNS')
                dns_provider_index = self.dns_provider_combo.findText(dns_provider)
                if dns_provider_index >= 0:
                    self.dns_provider_combo.setCurrentIndex(dns_provider_index)
                self.toggle_dns_mode(0)  # Manually Enter DNS mode
                self.current_profile = profile_name

    def apply_configuration(self):
        static_ip = self.ip_input.text()
        subnet = self.subnet_input.text()
        gateway = self.gateway_input.text()
        dns_manual = self.dns_manual_input.text()
        dns_provider = self.dns_provider_combo.currentText()

        selected_index = self.adapter_combo.currentIndex()
        if selected_index < 0:
            self.show_message("Error", "Please select a network adapter.")
            return

        selected_adapter = self.network_adapters[selected_index]
        adapter_name = selected_adapter['Name']

        # Input validation
        if not self.validate_input(static_ip, subnet, gateway, dns_manual, dns_provider):
            return

        if not static_ip and not gateway and not subnet:
            subprocess.run(["netsh", "interface", "ipv4", "set", "address", f"name={adapter_name}", "source=dhcp"])
        else:
            commands = ["netsh", "interface", "ipv4", "set", "address", f"name={adapter_name}"]
            if static_ip:
                commands.extend([f"source=static", f"addr={static_ip}", f"mask={subnet}", f"gateway={gateway}"])
            subprocess.run(commands)

        if dns_provider and dns_provider != "Manually Enter DNS":
            if dns_provider == "Google DNS (8.8.8.8, 8.8.4.4)":
                dns_servers = "8.8.8.8,8.8.4.4"
            elif dns_provider == "OpenDNS (208.67.222.222, 208.67.220.220)":
                dns_servers = "208.67.222.222,208.67.220.220"
            elif dns_provider == "Cloudflare DNS (1.1.1.1, 1.0.0.1)":
                dns_servers = "1.1.1.1,1.0.0.1"
            else:
                dns_servers = ""

            if dns_provider != "Choose DNS Provider":
                # Use PowerShell to set DNS servers
                powershell_command = f"Set-DnsClientServerAddress -InterfaceAlias '{adapter_name}' -ServerAddresses {dns_servers}"
                subprocess.run(["powershell.exe", "-Command", powershell_command])
            else:
                # Clear manual DNS and reset to DHCP
                powershell_command = f"Set-DnsClientServerAddress -InterfaceAlias '{adapter_name}' -ResetServerAddresses"
                self.dns_manual_input.clear()  # Clear the manual DNS input field
                subprocess.run(["powershell.exe", "-Command", powershell_command])
        elif dns_manual:
            # Use PowerShell to set DNS server manually
            powershell_command = f"Set-DnsClientServerAddress -InterfaceAlias '{adapter_name}' -ServerAddresses {dns_manual}"
            subprocess.run(["powershell.exe", "-Command", powershell_command])
        else:
            # Use PowerShell to reset DNS to DHCP
            powershell_command = f"Set-DnsClientServerAddress -InterfaceAlias '{adapter_name}' -ResetServerAddresses"
            subprocess.run(["powershell.exe", "-Command", powershell_command])

        self.show_message("Success", "Configuration applied successfully.")


    def revert_to_dhcp(self):
        selected_index = self.adapter_combo.currentIndex()
        if selected_index < 0:
            self.show_message("Error", "Please select a network adapter.")
            return

        selected_adapter = self.network_adapters[selected_index]
        adapter_name = selected_adapter['Name']

        subprocess.run(["netsh", "interface", "ipv4", "set", "address", f"name={adapter_name}", "dhcp"])
        subprocess.run(["netsh", "interface", "ipv4", "set", "dnsservers", f"name={adapter_name}", "source=dhcp"])
        self.ip_input.clear()
        self.subnet_input.clear()
        self.gateway_input.clear()
        self.dns_manual_input.clear()
        self.dns_provider_combo.setCurrentIndex(0)
        self.toggle_dns_mode(0)  # Manually Enter DNS mode
        self.show_message("Success", "Configuration reverted to DHCP.")

    def validate_input(self, static_ip, subnet, gateway, dns_manual, dns_provider):
        # Implement input validation rules as needed
        if static_ip:
            # Example: IPv4 address validation
            import socket
            try:
                socket.inet_pton(socket.AF_INET, static_ip)
            except socket.error:
                self.show_message("Invalid Input", "Invalid IP address format.")
                return False

        if dns_provider and dns_provider != "Manually Enter DNS":
            if dns_provider not in ["Google DNS (8.8.8.8, 8.8.4.4)", "OpenDNS (208.67.222.222, 208.67.220.220)", "Cloudflare DNS (1.1.1.1, 1.0.0.1)"]:
                self.show_message("Invalid Input", "Invalid DNS provider selection.")
                return False

        return True

    def show_message(self, title, message):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec_()

def list_network_adapters():
    raw_result = subprocess.run(
        ["powershell.exe", "-Command", "ConvertTo-Json -InputObject (Get-NetAdapter | Select-Object -Property Name,InterfaceDescription,ifIndex)"],
        capture_output=True,
        text=True
    )
    network_adapters = json.loads(raw_result.stdout)
    return network_adapters

if __name__ == '__main__':
    app = QApplication(sys.argv)
    network_adapters = list_network_adapters()
    network_manager = NetworkAdapterManager(network_adapters)
    sys.exit(app.exec_())
