import subprocess
import sys
import os
import matplotlib.pyplot as plt
import multiprocessing
from matplotlib.animation import FuncAnimation
import numpy as np
import csv


NIOS_CMD_SHELL_BAT = "C:/intelFPGA_lite/18.1/nios2eds/Nios II Command Shell.bat"


x_values = []
y_values = []
fieldnames = ["sample", "value"]

sample_number = 0


def send_on_jtag():
    # Check if at least one character is being sent down

    global sample_number

    # Create a subprocess which will run the nios2-terminal
    process = subprocess.Popen(
        NIOS_CMD_SHELL_BAT,
        bufsize=0,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        universal_newlines=True,  # Decode stdout as text
    )

    # Send command to subprocess
    process.stdin.write(f"nios2-terminal.exe --cable 2\n")
    #print("Command sent\n")
    process.stdin.flush()  # Flush the input buffer

    printing = False  # Flag to indicate when to start printing lines
    # Read stdout line by line until the subprocess completes or specific output is detected
    while True:

        
        line = process.stdout.readline()
        if not line:  # End of file reached
            break

        if "nios2-terminal: (Use the IDE stop button or Ctrl-C to terminate)" in line:  # Check if the line contains "#####"
            if printing:  # Toggle printing flag
                printing = False
            else:
                printing = True
            continue

        if printing:  # Print lines only if printing flag is True
            print(line.strip())
        if "nios2-terminal: exiting due to ^D on remote" in line:
            return # need to return hear, or else heavy buffering will occur

    # Wait for the subprocess to finish and get the return code
    return_code = process.wait()
    return return_code


def perform_computation():

    while True:
        # try:
        #     num_samples = int(input("Please enter the number of samples: "))
        #     if num_samples <= 0:
        #         print("Number of samples must be a positive integer.")
        #     else:
        send_on_jtag()
        #         res = send_on_jtag(str(num_samples))
##                print(y_values)
##                print(x_values)

    return


def main():
    # with open('data.csv', 'w') as file:
    #     csv_writer = csv.DictWriter(file, fieldnames=fieldnames)
    #     csv_writer.writeheader()
        
    perform_computation()


if __name__ == "__main__":
    main()
        


