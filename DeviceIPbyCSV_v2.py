import paramiko
import time
import pandas as pd
import tkinter as tk
from tkinter import filedialog
from pprint import pprint as pprint

import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


pd.options.display.width= None
pd.options.display.max_columns= None
pd.set_option('display.max_rows', 3000)
pd.set_option('display.max_columns', 3000)

#create a list to hold threads
threads = []
MyDevice = []



class Device(object):
    def __init__(self,
                 hostname,ip_address,newip_address,model,mac_address):#firmware,tsid,serialnumber,crestron_dev_id,comment
        self.def_username = str('crestron')
        self.username = str('admin')
        self.def_password = str('')
        self.password = str('Anuvision123!')
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



    def ssh_connect(self):
        try:
            print("connecting to device")
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(self.ip_address, 22,
                             self.username, self.password)
            self.session = self.ssh.get_transport().open_session()
            #-- adding session lines
            self.ssh.load_system_host_keys()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            #self.pty = self.session.get
            #-----finished session lines
            self.channel = self.ssh.invoke_shell()
            time.sleep(5)
            #-----Session Recieve---------
            if self.session.recv_ready():
                output = self.session.recv(65535).decode('utf-8')

                print(output)
            #------Session end recieve

            ##------------------Added for Initialization feedback------------
            # self.ssh.exec_command('')
        except Exception as e:
            print(f'Connection failed: {e}')



    def ssession_send(self,cmd):
        self.session.send(f'{cmd}\n')
        time.sleep(.3)
        if self.session.recv_ready():
            response = self.session.recv(16384).decode('utf-8')
            print(response)



#-------------------------------Out of Box Initialize------------------------------------------------------
    #-----------------------------------------------------------------------------------------------

    def crestron_oob_init(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        try:
            print("connecting to device")
            self.ssh.connect(self.ip_address, 22, self.def_username, self.def_password)
            self.session = self.ssh.get_transport().open_session()
            self.session.get_pty()
            self.session.invoke_shell()

            start = time.time()
            while time.time() - start < 6:
                if self.session.recv_ready():
                    response = self.session.recv(16384).decode('utf-8')
                    self.session.send('\n')

                    sys.stdout.write(response)
                    sys.stdout.flush()
                    #print(response)
                    pass_find = response.find('Please create a new password:')
                    oob_find = response.find('Please create a local administrator account')
                    newAccountUser_find = response.find('Username:')
                    newAccountPass_find =  response.find('Password:')
                    newAccountSuccess = response.find('An administrator account was successfully created.')

                    if pass_find != -1:
                        self.ssession_send(self.password)
                        time.sleep(.5)
                        self.ssession_send(self.password)
                    if oob_find != -1:
                        self.ssession_send(self.username)
                        time.sleep(.5)
                        self.ssession_send(self.password)
                        time.sleep(.5)
                        self.ssession_send(self.password)

        finally:
            self.session.close()
            print('')


    def crestron_ip_config(self):
        try:
            self.ssh_connect()
            time.sleep(.5)

    #   Set Network Config Fields
    #        pprint(self.ssh_cmd(f'ipa 0 {self.new_ip_address}'))
    #        pprint(self.ssh_cmd(f'ipm 0 {self.new_subnet}'))
    #        pprint(self.ssh_cmd(f'defr 0 {self.new_router}'))
    #        pprint(self.ssh_cmd(f'dhcp 0 {self.dhcp_status}'))
            pprint(self.ssh_cmd(f'hostname {self.hostname}'))

            time.sleep(3)

            pprint(self.ssh_cmd(f'reboot'))
            self.ssh_cmd('bye')

        ## Exception handling
        except Exception as e:
           print(e)

    #    # # Explicitly close SSH session
        finally:
            self.ssh_close()
            print()


#--------------------------------Combine functions for threading. -- ADD AND REMOVE CONFIG FUNCTIONS HERE


    def crestron_device_config(self):
        self.crestron_oob_init()
        ##time.sleep(2)
        # self.crestron_ip_config()

#--------------------------------SSH_Cmd----------------------------------------
    def ssh_cmd(self, cmd):
        response = None
        #self.channel.send('\n')
        self.channel.send(f'{cmd}\n')
#-----------------------Channel Reply---------------------------------

    #    while not self.channel.recv_ready():
    #        time.sleep(.25)

    #    out = self.channel.recv(9999).decode('utf-8')
    #    response = out.split('\n')

    #    while response[0] == '' or response[0] == '\r':
    #        del response[0]
    #    del response[0]

#        del response[-1]
#        while response[-1] == '' or response[-1] == '\r':
#            del response[-1]

#-------------------Paramiko response---------------------------------------------

        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        response = stdout.read().decode('utf-8')

#---------------------Parsing---------------------------------------------------------

    #    response = stdout.readlines()
        #print(response)

        while response[0] == '\r\n':
           del response[0]

    #    response = response.strip("\r\n").splitlines()
    #    response = [line.replace('\r\n', '').strip() for line in response]
    #   print('while')

        if response:
            return response
        else:
            return 'Error, no response'
    #
    def ssh_close(self):
        if self.ssh:
            self.session.close()
            self.ssh.close()
            #del self.session
            #del self.channel
            #del self.ssh

        print(f"Disconnected from {self.hostname}")

    def test(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        try:
            print("connecting to device")
            self.ssh.connect(self.ip_address, 22, self.username, self.password)
            self.session = self.ssh.get_transport().open_session()
            self.session.get_pty()
            self.session.invoke_shell()

            start = time.time()
            while time.time() - start < 6:
                if self.session.recv_ready():
                    response = self.session.recv(16384).decode('utf-8')

                    sys.stdout.write(response)
                    sys.stdout.flush()

                    self.session.send('version' + '\n')

        finally:
            self.session.close()
            print('')


#------------------Clear SSH on list?-------------------------------------------------------


#---------------------pandas-------------------------

file_path = filedialog.askopenfilename()

#file_path = ('crestron_test.csv')


# -------- Strip spaces out of CSV files Pandas -----------####################



def trim(dataset):
    trim = lambda x: x.strip() if type(x) is str else x
    return dataset.applymap(trim)


device_fields = ['Hostname','IP Address','NewIP Address','Model Name','Firmware','TSID','MAC Address','SerialNumber','Crestron Dev ID','Comment']
df = trim(pd.read_csv(file_path, skip_blank_lines=True))
df.columns = df.columns.str.strip()         #Clear whitespace on data in columns
device_df = df[device_fields]


#--------------------------------------Instantiate Device----------------------------------------

for device in device_df.index:
    devices = Device(device_df.at[device,'Hostname'], device_df.at[device,'IP Address'],
                            device_df.at[device,'NewIP Address'], device_df.at[device,'Model Name'],
                            device_df.at[device,'MAC Address'])

    MyDevice.append(devices) #append objects to list


    #----------------------------------------------
    #-------------Uncomment to run without threadding, make sure to comment out threadding section

    # Combines both initial config and IP config
    # # Sets static Ip from device summary List. - need to add NewIP Address column after export from toolbox. 'Hostname','IP Address','NewIP Address','Model Name','Firmware','TSID','MAC Address','SerialNumber','Crestron Dev ID','Comment'
    devices.crestron_device_config()