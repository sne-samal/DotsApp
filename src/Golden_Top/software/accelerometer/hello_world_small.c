#include "system.h"
#include "alt_types.h"
#include "sys/times.h"
#include "altera_up_avalon_accelerometer_spi.h"
#include "altera_avalon_timer_regs.h"
#include "altera_avalon_timer.h"
#include "altera_avalon_pio_regs.h"
#include "sys/alt_irq.h"
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>

#define OFFSET -32
#define PWM_PERIOD 16
#define WINDOW_SIZE 5
#define FILTER_TAPS 49


// [0.0046    0.0074   -0.0024   -0.0071    0.0033]: filter coefficients.
// integer filter coefficient: [46, 74, -24, -71, 33], multiplied by 10000

alt_8 pwm = 0;
alt_u8 led;
int level;

float buffer[] = {0, 0, 0, 0, 0};
int buffer_q[] = {0, 0, 0, 0, 0};
int coefficients[] = {46, 74, -24, -71, 33};

void led_write(alt_u8 led_pattern) {
    IOWR(LED_BASE, 0, led_pattern);
}

int moving_average_quantized(alt_32 newValue) {
  static int window[WINDOW_SIZE];
  static int index = 0;

  // Add new value to window
  window[index] = newValue;

  // Increment index
  index++;
  if(index >= WINDOW_SIZE) {
    index = 0;
  }

  // Calculate average
  int sum = 0;
  for(int i=0; i<WINDOW_SIZE; i++) {
    sum += window[i];
  }

  return sum / WINDOW_SIZE;
}


float moving_average(alt_32 newValue)
{
	// each coefficient is 2
	// start by  shifting each item in the buffer to the right
	for (int i = 0; i < 4; i++)
	{
		buffer[i+1] = buffer[i];
	}
	// insert to the start, 0.2*newValue
	buffer[0] = 0.2*newValue;
	// calculate sum
	float average = 0;
	for(int i = 0; i < 5; i++)
	{
		average += buffer[i];
	}
	// return average
	return average;
}

int moving_average_q(alt_32 newValue)
{
	// each coefficient is 2
	// start by  shifting each item in the buffer to the right
	for (int i = 0; i < 4; i++)
	{
		buffer_q[i+1] = buffer_q[i];
	}
	// insert to the start, 0.2*newValue
	buffer_q[0] = 2*newValue;
	// calculate sum
	float average = 0;
	for(int i = 0; i < 5; i++)
	{
		average += buffer_q[i];
	}
	// return average
	return average/10;
}


int filter_accel_int (int accel_reading) {
	alt_32 filter_coeffs[FILTER_TAPS] = {
	    46, 74, -24, -71, 33, 1, -94, 40,
	    44, -133, 30, 114, -179, -11, 223, -225,
	    -109, 396, -263, -338, 752, -289, -1204, 2879,
	    6369, 2879, -1204, -289, 752, -338, -263, 396,
	    -109, -225, 223, -11, -179, 114, 30, -133,
	    44, 40, -94, 1, 33, -71, -24, 74,
	    46
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


    return filtered_value/10000;
}


float filter_accel_float (int accel_reading) {
	alt_32 filter_coeffs[FILTER_TAPS] = {
	    0.0046, 0.0074, -0.0024, -0.0071, 0.0033, 0.0001, -0.0094, 0.0040,
		0.0044, -0.0133, 0.0030, 0.0114, -0.0179, -0.0011, 0.0223, -0.0225,
	    -0.0109, 0.0396, -0.0263, -0.0338, 0.0752, -0.0289, -0.1204, 0.2879,
	    0.6369, 0.2879, -0.1204, -0.0289, 0.0752, -0.0338, -0.0263, 0.0396,
	    -0.0109, -0.0225, 0.0223, -0.0011, -0.0179, 0.0114, 0.0030, -0.0133,
	    0.0044, 0.0040, -0.0094, 0.0001, 0.0033, -0.0071, -0.0024, 0.0074,
	    0.0046
	};

	static alt_32 past_readings[FILTER_TAPS] = {0};
    float filtered_value = 0;

    for (int i = FILTER_TAPS - 1; i > 0; i--) {
        // Shift past readings to the right, making room for the new reading
        past_readings[i] = past_readings[i-1];
    }

    past_readings[0] = accel_reading;

    for (int i = 0; i < FILTER_TAPS; i++) {
    	filtered_value += past_readings[i] * filter_coeffs[i];
    	// alt_printf("Calculating...");
    }


    return filtered_value;
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


int main() {



    alt_32 x_read;
    alt_up_accelerometer_spi_dev * acc_dev;
    acc_dev = alt_up_accelerometer_spi_open_dev("/dev/accelerometer_spi");

    alt_32 x_read_filtered;

    if (acc_dev == NULL) { // if return 1, check if the spi ip name is "accelerometer_spi"
        return 1;
    }

    clock_t exec_t1, exec_t2;
    alt_printf("Timer Started");
    struct tms timer;
    int iterations = 1000;

    exec_t1 = times(NULL); // get system time before starting the process
    int i = 0;
    timer_init(sys_timer_isr);
    while (i < iterations) {

        alt_up_accelerometer_spi_read_x_axis(acc_dev, & x_read);

        x_read_filtered = (alt_32)filter_accel_int(x_read);

        // x_read_filtered = (alt_32)filter_accel_float(x_read);
        convert_read(x_read_filtered, & level, & led);
        printf("filtered value: %d\n", (int)x_read_filtered);
        alt_printf("level %x\n", level);

        i++;

    }

    exec_t2 = times(NULL); // get system time after finishing the process
    long time_1 = exec_t1;
    long time_2 = exec_t2;
    printf("%ld\n", time_1);
    printf("%ld\n", time_2);
    //printf(" proc time= %ju ticks\n", (uintmax_t)(exec_t2-exec_t1));

    return 0;
}
