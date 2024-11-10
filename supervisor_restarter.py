import subprocess
import time


def run_subprocess(command):
    try:
        result = subprocess.run(command, check=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(result.stdout.decode())
    except subprocess.CalledProcessError as e:
        print(f"CalledProcessError occurred: {e.stderr.decode()}")


def stop_all_supervisors():
    run_subprocess(['supervisorctl', 'stop', 'all'])


def start_supervisor_process(process_name):
    run_subprocess(['supervisorctl', 'start', process_name])


def kill_process_on_port(port):
    try:
        lsof_command = subprocess.run(
            ['lsof', '-ti', f':{port}'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pids = lsof_command.stdout.decode().strip().split()
        if pids:
            run_subprocess(['xargs', 'kill', '-9'],
                           input='\n'.join(pids).encode())
        else:
            print(f"No process found running on port {port}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e.stderr.decode()}")


if __name__ == "__main__":
    stop_all_supervisors()
    # kill_process_on_port('8080')
    start_supervisor_process("mark")
    time.sleep(5)
    start_supervisor_process("markb")
