# Your actual integration would look like this:
async def process_device(self, device_info, commands, username, password, ...):
    hostname = device_info['host']

    try:
        # Use your actual async function directly!
        result = await run_commands_with_variables(device_info, commands, username, password)

        # File transfers (your actual sftp_transfer function)
        if firmware_config.get('enabled'):
            await sftp_transfer(conn=conn,
                                local_file=firmware_config['local_file'],
                                remote_file=firmware_config['remote_path'],
                                direction='upload')

        if program_config.get('enabled'):
            await sftp_transfer(conn=conn,
                                local_file=program_config['local_file'],
                                remote_file=program_config['remote_path'],
                                direction='upload')

        self.signals.device_completed.emit(hostname, True)
        return result

    except Exception as e:
        self.signals.device_completed.emit(hostname, False)
        return {'host': hostname, 'error': str(e), 'success': False}


    ##