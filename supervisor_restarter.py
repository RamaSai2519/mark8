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


if __name__ == "__main__":
    stop_all_supervisors()
    start_supervisor_process("mark")
    time.sleep(5)
    start_supervisor_process("markb")
