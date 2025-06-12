import asyncio
import asyncssh
import pandas as pd


async def sftp_transfer(conn, local_file, remote_file, direction='upload'):
    def progress_callback(srcpath, dstpath, bytes_copied, total_bytes):
        if total_bytes > 0:
            percent = (bytes_copied * 100) // total_bytes
            print(f"Progress: {percent}% ({bytes_copied}/{total_bytes} bytes)")

    async with conn.start_sftp_client() as sftp:
        if direction == 'upload':
            await sftp.put(local_file, remote_file, progress_handler=progress_callback)
        else:
            await sftp.get(remote_file, local_file, progress_handler=progress_callback)


def pandas_to_device_list(df, host_column='host'):
    """Convert pandas DataFrame to device list for AsyncSSH"""
    devices = []
    for _, row in df.iterrows():
        host = row[host_column]
        variables = row.drop(host_column).to_dict()
        devices.append({
            'host': host,
            'variables': variables
        })
    return devices


def trim(dataset):
    trim = lambda x: x.strip() if type(x) is str else x
    return dataset.map(trim)


async def run_commands_with_variables(device_info, commands, username, password,
                                      firmware_path=None, program_path=None):
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

            # File transfers (if paths provided)
            transfer_tasks = []
            if firmware_path:
                transfer_tasks.append(
                    sftp_transfer(conn=conn, local_file=firmware_path,
                                  remote_file='./firmware', direction='upload')
                )
            if program_path:
                transfer_tasks.append(
                    sftp_transfer(conn=conn, local_file=program_path,
                                  remote_file='./program03', direction='upload')
                )

            if transfer_tasks:
                await asyncio.gather(*transfer_tasks)

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


# Your standalone script functionality
async def run_batch_from_file(csv_file, firmware_path, program_path,
                              commands, username, password, host_column='IP Address'):
    """Standalone function to run your original script logic"""
    df = pd.read_csv(csv_file)
    df = trim(df)
    df.columns = df.columns.str.strip()
    devices = pandas_to_device_list(df, host_column=host_column)

    tasks = [
        run_commands_with_variables(device, commands, username, password,
                                    firmware_path, program_path)
        for device in devices
    ]

    results = await asyncio.gather(*tasks)
    return results


# Keep your original main function for standalone use
async def main():
    # Your original logic here...
    pass


if __name__ == "__main__":
    asyncio.run(main())