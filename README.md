# DotsApp
![dotsapp](https://github.com/sne-samal/Team-6/assets/66144849/819e08e1-b447-4d2f-90fe-5fc4c352fff2)

A FPGA and morse code chatting application.

### Usage - 1 FPGA to 1 Computer
- Clone this repo
- Blast `.sof` file via Quartus programmer
- Open nios II command shell as per lab 2 instructions
- `cd` to `'Team-6/src/Golden_Top/software/project'`
- run `nios2-download -g project.elf`
- make sure server is running
- run `python <path>/client.py`
- Start typing in Morse

### Usage - 2 FPGAs to 1 Computer
- Clone this repo
- Blast `.sof` file to both FPGAs
- Open 2 nios II command shells, one for each FPGA
- `cd` to `'Team-6/src/Golden_Top/software/project'`
- On the first terminal run: `nios2-download -g --cable 1 project.elf`
- On the second terminal run: `nios2-download -g --cable 2 project.elf`
- make sure server is running
- On the first terminal run `python <path>/client.py`
- On the second terminal run `python <path>/client_duplicate.py`
- Start typing in Morse from either FPGA

### Usage - Encrypted Chat
- Run secureserver.py instead of server.py
- Instead of running `python <path>/client.py`, run `python <path>/secureclient2.py`

### Video demonstration
https://youtu.be/0Z9BxCR3ug8
