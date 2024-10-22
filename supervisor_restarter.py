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


if __name__ == "__main__":
    stop_all_supervisors()
    start_supervisor_process("mark")
    time.sleep(5)
    start_supervisor_process("markb")
