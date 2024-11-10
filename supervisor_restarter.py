import subprocess
import time


def stop_all_supervisors():
    try:
        result = subprocess.run(['supervisorctl', 'stop', 'all'],
                                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(result.stdout.decode())
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e.stderr.decode()}")


def start_supervisor_process(process_name):
    try:
        result = subprocess.run(['supervisorctl', 'start', process_name],
                                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(result.stdout.decode())
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e.stderr.decode()}")


def kill_process_on_port(port):
    try:
        lsof_command = subprocess.run(
            ['lsof', '-ti', f':{port}'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pids = lsof_command.stdout.decode().strip().split()
        if pids:
            kill_command = subprocess.run(['xargs', 'kill', '-9'], input='\n'.join(
                pids).encode(), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(kill_command.stdout.decode())
        else:
            print(f"No process found running on port {port}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e.stderr.decode()}")


def tail_log_file(log_type='out'):
    log_file = f'/var/log/mark.{log_type}.log'
    try:
        result = subprocess.run(['tail', '-f', log_file, '--lines=100'],
                                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(result.stdout.decode())
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e.stderr.decode()}")


if __name__ == "__main__":
    stop_all_supervisors()
    kill_process_on_port('8080')
    start_supervisor_process("mark")
    time.sleep(5)
    start_supervisor_process("markb")
    tail_log_file()
