import paramiko
import multiprocessing
from multiprocessing import Pool

class Device:
    def __init__(self,
                 hostname, ip_address, newip_address, model,
                 mac_address):  # firmware,tsid,serialnumber,crestron_dev_id,comment
        self.def_username = str('crestron')
        self.def_password = str('')
        self.username = str('admin')
        self.password = str('Crestr0n')
        self.model = str(model)
        self.hostname = str(hostname)
        self.ip_address = str(ip_address)
        self.new_ip_address = str(newip_address)
        self.new_subnet = str('255.255.0.0')
        self.new_router = str('172.22.0.1')
        self.dhcp_status = str('off')
        self.mac_address = str(mac_address)
        self.tn = None
        self.ssh = None
        self.channel = None
        self.session = None
        self.pty = None

    def connect(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.hostname, username=self.username, password=self.password)
        print(f"Connected to {self.hostname}")

    def execute_command(self, command):
        if self.ssh:
            stdin, stdout, stderr = self.ssh.exec_command(f'{command}\n')
            output = stdout.read().decode('utf-8')
            return output
        else:
            return "Not connected"

    def close(self):
        if self.ssh:
            self.ssh.close()
            print(f"Connection to {self.hostname} closed")

    def get_version(self):
        self.connect()
        self.execute_command("version")

def handle_device(device_info):
    try:
        device = Device(device_info['hostname'], device_info['username'], device_info['password'])
        device.connect()
        output = device.execute_command('echo "Hello from {}!"'.format(device.hostname))
        print(f"Output from {device.hostname}: {output}")
        device.close()
    except Exception as e:
        print(f"An error occurred with {device_info['hostname']}: {e}")

# List of device details
device_info_list = [
    {'hostname': 'host1', 'username': 'user1', 'password': 'password1'},
    {'hostname': 'host2', 'username': 'user2', 'password': 'password2'},
    # Add more devices as needed
]

# Limit concurrent processes to 10
max_concurrent_connections = 10

if __name__ == "__main__":
    # Using Pool to limit concurrent connections
    with Pool(processes=max_concurrent_connections) as pool:
        pool.map(handle_device, device_info_list)