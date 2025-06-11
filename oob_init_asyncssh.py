import asyncio
import asyncssh
import time
import pandas as pd
import sys
from tkinter import filedialog

##pandas config
pd.options.display.width= None
pd.options.display.max_columns= None
pd.set_option('display.max_rows', 3000)
pd.set_option('display.max_columns', 3000)


MyDevice = []
# file_path = filedialog.askopenfilename()
file_path = ('devices.txt')

def pandas_to_device_list(df, host_column='host'):
    """Convert pandas DataFrame to device list for AsyncSSH"""
    devices = []

    for _, row in df.iterrows():
        # Extract host
        host = row[host_column]

        # All other columns become variables
        variables = row.drop(host_column).to_dict()

        devices.append({
            'host': host,
            'variables': variables
        })

    return devices


async def run_commands_with_variables(device_info, commands, username, password):
    def auto_add_policy(host, addr, port, key):
        return True

    host = device_info['host']
    variables = device_info.get('variables', {})

    try:
        async with asyncssh.connect(
                host,
                username=username,
                password=password,
                known_hosts=None
        ) as conn:
            results = []

            for command_template in commands:
                # Format command with device-specific variables
                command = command_template.format(**variables)

                result = await asyncio.wait_for(
                    conn.run(command, check=False),
                    timeout=5.0
                )
                results.append({
                    'command': command,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'success': result.exit_status == 0
                })

            return {
                'host': host,
                'results': results,
                'success': True
            }

    except Exception as e:
        return {
            'host': host,
            'error': str(e),
            'success': False
        }
def trim(dataset):
    trim = lambda x: x.strip() if type(x) is str else x
    return dataset.map(trim)


async def main():
    # Load your CSV with pandas
    df = pd.read_csv('devices.txt')

    # device_fields = ['Hostname', 'IP Address', 'NewIP Address', 'Model Name', 'Firmware', 'TSID', 'MAC Address',
    #                  'SerialNumber', 'Crestron Dev ID', 'Comment','IPID','ControllerIP']
    # df = trim(pd.read_csv(file_path, skip_blank_lines=True))
    # df.columns = df.columns.str.strip()  # Clear whitespace on data in columns
    # device_df = df[device_fields]
    #
    # # Convert to device list

    df = trim(df)  # Clean whitespace
    df.columns = df.columns.str.strip()  # Clean column headers
    devices = pandas_to_device_list(df, host_column='IP Address')  # or whatever your host column is named

    # Your command templates
    command_templates = [
        'version',
    ]
    # for device in devices:
    #     print(device['host'])
    #     print(device['variables']['NewIP Address'])


    # Run commands on all devices concurrently
    tasks = [
        run_commands_with_variables(device, command_templates, 'admin', 'Anuvision123!')
        for device in devices
    ]
    print('before await')
    results = await asyncio.gather(*tasks)
    print('after await')
    # Process results
    for result in results:
        if result['success']:
            print(f"\n{result['host']} - Success!")
            for cmd in result['results']:
                print(f"\n{result['host']} - {cmd['stdout']}")
                if not cmd['success']:
                    print(f"  Failed: {cmd['command']}")
        else:
            print(f"{result['host']} - Connection failed: {result['error']}")


asyncio.run(main())