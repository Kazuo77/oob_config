Version 3 should look into net miko and concurrent.futures

I think programming logic in to try a prompt a few times before abandoning it.  is that possible10:05 PMAbsolutely, straightforward retry logic with a max attempt ceiling:
pythonimport time
from netmiko import ConnectHandler

def get_prompt(conn, max_attempts=3, delay=1.0):
    for attempt in range(max_attempts):
        conn.write_channel("\n")
        time.sleep(delay)
        output = conn.read_channel()
        
        if "#" in output or ">" in output:
            return True
            
        print(f"No prompt on attempt {attempt + 1}/{max_attempts}, retrying...")
    
    return False  # Exhausted all attempts

def configure_device(device):
    try:
        conn = ConnectHandler(**device)
        
        if not get_prompt(conn):
            conn.disconnect()
            return {"host": device["host"], "status": "failed", "error": "Could not get prompt after max attempts"}
        
        conn.clear_buffer()
        output = conn.send_command("ver", expect_string="#")
        conn.disconnect()
        return {"host": device["host"], "status": "success", "output": output}
        
    except Exception as e:
        return {"host": device["host"], "status": "failed", "error": str(e)}
A few things worth considering on top of this:
Exponential backoff — rather than a fixed delay between attempts, increasing it each retry gives slower devices more time to settle:
pythondelay = 1.0
for attempt in range(max_attempts):
    conn.write_channel("\n")
    time.sleep(delay)
    delay *= 2  # 1s, 2s, 4s
Logging failures — when you're running concurrent connections across multiple devices, you'll want a record of which ones failed rather than just a print statement:
pythonimport logging
logging.basicConfig(filename="deployment.log", level=logging.INFO)
logging.warning(f"{device['host']} failed to respond after {max_attempts} attempts")
Distinguishing timeout from rejection — wrapping the ConnectHandler itself in a try/except that catches NetmikoTimeoutException separately from a prompt failure lets you treat unreachable devices differently from devices that connected but didn't respond:
pythonfrom netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

try:
    conn = ConnectHandler(**device)
except NetmikoTimeoutException:
    return {"host": device["host"], "status": "unreachable"}
except NetmikoAuthenticationException:
    return {"host": device["host"], "status": "auth_failed"}
