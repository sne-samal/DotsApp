#include "system.h"
#include <stdio.h>
#include "altera_up_avalon_accelerometer_spi.h"
#include "altera_avalon_timer_regs.h"
#include "altera_avalon_timer.h"
#include "altera_avalon_pio_regs.h"
#include "sys/alt_irq.h"
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "altera_avalon_jtag_uart.h"


#define OFFSET -32
#define PWM_PERIOD 16
#define FILTER_TAPS 5
#define ITERATIONS 5000
#define CHARLIM 256    // Maximum character length of what the user places in memory.  Increase to allow longer sequences
#define QUITLETTER '~' // Letter to kill all processing

altera_avalon_jtag_uart_state uart_state;


alt_8 pwm = 0;
alt_u8 led;
int level;

int num_samples;

int jtag_flag = 0;

void led_write(alt_u8 led_pattern);
int filter_accel_int (int accel_reading);
void convert_read(alt_32 acc_read, int * level, alt_u8 * led);
void sys_timer_isr();
void timer_init(void * isr);
void filter_sample();
void no_filter_sample();

alt_32 x_read_filtered;


void print_text(char *text, const int length)
{
    char *printMsg;
    asprintf(&printMsg, "<--> Detected %d characters: %s <--> \n %c", length, text, 0x4); // Print out the strings
    printf("Reading: %d", 1);
    alt_putstr(printMsg);
    free(printMsg);
    memset(text, 0, 2 * CHARLIM); // Empty the text buffer for next input
}

void print_result(int reading)
{
	char *value;
	asprintf(&value, "%d \n %c", reading, 0x4);
	alt_putstr(value);
	free(value);
}

char generate_text(char curr, int *length, char *text, int *running)
{
    if (curr == '\n')
        return curr; // If the line is empty, return nothing.
    int idx = 0;     // Keep track of how many characters have been sent down for later printing
    char newCurr = curr;

    while (newCurr != EOF && newCurr != '\n')
    { // Keep reading characters until we get to the end of the line
        if (newCurr == QUITLETTER)
        {
            *running = 0;
        }                        // If quitting letter is encountered, setting running to 0

//        else if (newCurr == 'F')
//        {
//        	printf("Entering filtering mode \n");
//        	filter_sample();
//        }
//        else if (newCurr == 'N')
//        {
//        	printf("Entering non filtering mode \n");
//        	no_filter_sample();
//        }

        text[idx] = newCurr;     // Add the next letter to the text buffer
        idx++;                   // Keep track of the number of characters read
        newCurr = alt_getchar(); // Get the next character
    }
    *length = idx;

    return newCurr;
}

void clear_input_buffer() {
    int c;
    while ((c = alt_getchar()) != '\n' && c != EOF) { }
}

void read_chars()
{
    char text[2 * CHARLIM]; // The buffer for the printing text
    char prevLetter = '!';
    int length = 0;
    int running = 1;


    while (running)
    {                                                                    // Keep running until QUITLETTER is encountered
        prevLetter = alt_getchar();                                      // Extract the first character (and create a hold until one arrives)
        prevLetter = generate_text(prevLetter, &length, text, &running); // Process input text
        num_samples = atoi(text);
        int i = 0;
        printf("#####\n");
        while(i < num_samples)
        {
        	filter_sample();
        	//print_text(text, length);
        	i++;
        }
        printf("#####\n");
        print_text(text, length);                                        // Print input text
    }

    // return 0;

}

void led_write(alt_u8 led_pattern) {
    IOWR(LED_BASE, 0, led_pattern);
}

int filter_accel_int (int accel_reading) {
	alt_32 filter_coeffs[FILTER_TAPS] = {
	    2, 2, 2, 2, 2
	};

	static alt_32 past_readings[FILTER_TAPS] = {0};
    alt_32 filtered_value = 0;

    for (int i = FILTER_TAPS - 1; i > 0; i--) {
        // Shift past readings to the right, making room for the new reading
        past_readings[i] = past_readings[i-1];
    }

    past_readings[0] = accel_reading;

    for (int i = 0; i < FILTER_TAPS; i++) {
    	filtered_value += past_readings[i] * filter_coeffs[i];
    }
    // printf("Value: %d\n", filtered_value/10);
    return filtered_value/10;

}

void convert_read(alt_32 acc_read, int * level, alt_u8 * led) {
    acc_read += OFFSET;
    alt_u8 val = (acc_read >> 6) & 0x07;
    * led = (8 >> val) | (8 << (8 - val));
    * level = (acc_read >> 1) & 0x1f;
}

void sys_timer_isr() {
    IOWR_ALTERA_AVALON_TIMER_STATUS(TIMER_BASE, 0);

    if (pwm < abs(level)) {

        if (level < 0) {
            led_write(led << 1);
        } else {
            led_write(led >> 1);
        }

    } else {
        led_write(led);
    }

    if (pwm > PWM_PERIOD) {
        pwm = 0;
    } else {
        pwm++;
    }

}

void timer_init(void * isr) {

    IOWR_ALTERA_AVALON_TIMER_CONTROL(TIMER_BASE, 0x0003);
    IOWR_ALTERA_AVALON_TIMER_STATUS(TIMER_BASE, 0);
    IOWR_ALTERA_AVALON_TIMER_PERIODL(TIMER_BASE, 0x0900);
    IOWR_ALTERA_AVALON_TIMER_PERIODH(TIMER_BASE, 0x0000);
    alt_irq_register(TIMER_IRQ, 0, isr);
    IOWR_ALTERA_AVALON_TIMER_CONTROL(TIMER_BASE, 0x0007);

}

void filter_sample()
{
	alt_32 x_read;
	alt_up_accelerometer_spi_dev * acc_dev;
	acc_dev = alt_up_accelerometer_spi_open_dev("/dev/accelerometer_spi");


	//int i = 0;
	timer_init(sys_timer_isr);

//	while (i < ITERATIONS)
//	{
	alt_up_accelerometer_spi_read_x_axis(acc_dev, & x_read);
	x_read_filtered = (alt_32)filter_accel_int(x_read);
	int number_to_send = x_read_filtered;
	char buffer[20];
	convert_read(x_read_filtered, & level, & led);
    int bytes_written = altera_avalon_jtag_uart_write(&uart_state, buffer, strlen(buffer), 0);
	// print_result(x_read_filtered);
	//i++;
	//}
    if (bytes_written > 0) {
    	printf("%d\n", x_read_filtered);
    } else if (bytes_written == -EWOULDBLOCK) {
    	printf("Non-blocking mode: Write would block\n");
    } else {
    	printf("Error writing data\n");
    }

	return;
}

void no_filter_sample()
{
	alt_32 x_read;
	alt_up_accelerometer_spi_dev * acc_dev;
	acc_dev = alt_up_accelerometer_spi_open_dev("/dev/accelerometer_spi");


	int i = 0;
	timer_init(sys_timer_isr);

	while (i < ITERATIONS*100)
	{
		alt_up_accelerometer_spi_read_x_axis(acc_dev, & x_read);
		convert_read(x_read, & level, & led);
		i++;
	}

	return;
}



int main() {
	read_chars();
    clear_input_buffer();
    return 0;
}
