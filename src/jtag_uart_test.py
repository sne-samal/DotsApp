import time
import intel_jtag_uart

try:
    ju = intel_jtag_uart.intel_jtag_uart()

except Exception as e:
    print(e)
    sys.exit(0)

ju.write(b'testing 123')
time.sleep(1)
print("read: ", ju.read())
