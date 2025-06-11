import asyncssh
import asyncio

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


# Usage from another file:
async def main():
    async with asyncssh.connect('hostname', username='user') as conn:
        await sftp_transfer(conn, 'local.txt', 'remote.txt', 'upload')