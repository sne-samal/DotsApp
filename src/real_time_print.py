import subprocess

NIOS_CMD_SHELL_BAT = "your_nios_cmd_shell_bat_command_here"

def send_on_jtag(cmd):
    # check if at least one character is being sent down
    assert (len(cmd) >= 1), "Please make the cmd a single character"
    
    # create a subprocess which will run the nios2-terminal
    process = subprocess.Popen(
        NIOS_CMD_SHELL_BAT,
        bufsize=0,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        universal_newlines=True,  # Decode stdout as text
    )

    # Send command to subprocess
    process.stdin.write(f"nios2-terminal <<< {cmd}\n")
    process.stdin.flush()  # Flush the input buffer
    
    # Read stdout line by line until the subprocess completes or specific output is detected
    while True:
        line = process.stdout.readline()
        if not line:  # End of file reached
            break
        print(line.strip())  # Print the line (remove trailing newline)
        if "nios2-terminal: exiting due to ^D on remote" in line:
            break

    # Wait for the subprocess to finish and get the return code
    return_code = process.wait()
    return return_code

# Example usage:

def perform_computation():

    while True:
        try:
            num_samples = int(input("Please enter the number of samples: "))
            if num_samples <= 0:
                print("Number of samples must be a positive integer.")
            else:
                res = send_on_jtag(str(num_samples))
                # print(res)
        except ValueError:
            print("Invalid input. Please enter a valid integer.")

    return

def main():
    perform_computation()


if __name__ == "__main__":
    main()
