import asyncio
import asyncssh
import time
import pandas as pd
import sys

from sftptransfer import sftp_transfer

##pandas config
pd.options.display.width= None
pd.options.display.max_columns= None
pd.set_option('display.max_rows', 3000)
pd.set_option('display.max_columns', 3000)


MyDevice = []
file_path = None
firmware_path = None
program_path = None
# file_path = ('devices.txt')

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
            print('transfering files')

            transfer_task = asyncio.create_task(
            sftp_transfer(conn=conn, local_file=firmware_path, remote_file='./firmware', direction='upload')
            )
            transfer_task2 = asyncio.create_task(
                sftp_transfer(conn=conn, local_file=program_path, remote_file='./program03', direction='upload')
            )
            try:
                # await transfer_task
                await asyncio.gather(transfer_task, transfer_task2)
                print(f'{host} - Transfers completed successfully!')
            except Exception as e:
                print(f'{host} - Transfer failed: {e}')
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


async def async_oob_init(host, new_username, new_password, timeout=30):
    """
    Async Out-of-Box initialization for Crestron devices.
    Connects with default credentials and sets up new admin account.

    Args:
        host: IP address of the device
        new_username: Username for the new admin account
        new_password: Password for the new admin account
        timeout: Maximum time to wait for prompts (default 30 seconds)

    Returns:
        dict with 'host', 'success', and 'message' keys
    """
    def_username = 'crestron'
    def_password = ''

    try:
        async with asyncssh.connect(
            host,
            username=def_username,
            password=def_password,
            known_hosts=None
        ) as conn:
            # Open interactive session with PTY
            async with conn.create_process(
                term_type='xterm',
                term_size=(80, 24)
            ) as process:

                buffer = ''
                start_time = asyncio.get_event_loop().time()

                # State machine for prompts
                state = 'waiting_username'

                while (asyncio.get_event_loop().time() - start_time) < timeout:
                    try:
                        # Read with short timeout to allow checking for prompts
                        data = await asyncio.wait_for(
                            process.stdout.read(4096),
                            timeout=1.0
                        )
                        if data:
                            buffer += data
                            print(data, end='', flush=True)

                            # Check for success message
                            if 'successfully created' in buffer.lower():
                                return {
                                    'host': host,
                                    'success': True,
                                    'message': 'Administrator account created successfully'
                                }

                            # State machine to handle prompts in order
                            if state == 'waiting_username' and 'Username:' in buffer:
                                await asyncio.sleep(0.5)
                                process.stdin.write(f'{new_username}\n')
                                state = 'waiting_password'
                                buffer = ''

                            elif state == 'waiting_password' and 'Password:' in buffer:
                                await asyncio.sleep(0.5)
                                process.stdin.write(f'{new_password}\n')
                                state = 'waiting_verify'
                                buffer = ''

                            elif state == 'waiting_verify' and ('Verify' in buffer or 'Password:' in buffer):
                                await asyncio.sleep(0.5)
                                process.stdin.write(f'{new_password}\n')
                                state = 'waiting_success'
                                buffer = ''

                    except asyncio.TimeoutError:
                        # No data available, continue waiting
                        continue

                return {
                    'host': host,
                    'success': False,
                    'message': f'Timeout waiting for device prompts (state: {state})'
                }

    except Exception as e:
        return {
            'host': host,
            'success': False,
            'message': f'Connection failed: {str(e)}'
        }


async def run_oob_init_batch(devices, new_username, new_password, max_concurrent=5):
    """
    Run OOB initialization on multiple devices concurrently.

    Args:
        devices: List of device dicts with 'host' key
        new_username: Username for new admin accounts
        new_password: Password for new admin accounts
        max_concurrent: Maximum concurrent connections

    Returns:
        List of result dicts
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def init_with_semaphore(device):
        async with semaphore:
            host = device['host'] if isinstance(device, dict) else device
            return await async_oob_init(host, new_username, new_password)

    tasks = [init_with_semaphore(device) for device in devices]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results


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
        'ipa 0 {NewIP Address}',
        'ipm 0 ',
        'dhcp',


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
                print(f"\n{result['host']} - {cmd['stdout']}", flush=True)
                if not cmd['success']:
                    print(f"  Failed: {cmd['command']}")
        else:
            print(f"{result['host']} - Connection failed: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())