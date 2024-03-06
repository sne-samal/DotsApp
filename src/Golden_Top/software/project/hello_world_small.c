#include "system.h"
#include "altera_up_avalon_accelerometer_spi.h"
#include "altera_avalon_timer_regs.h"
#include "altera_avalon_timer.h"
#include "altera_avalon_pio_regs.h"
#include "sys/alt_irq.h"
#include <stdlib.h>
#include <sys/alt_stdio.h>
#include <stdio.h>
#include <unistd.h>

#define OFFSET -32
#define PWM_PERIOD 16
#define delay 45000

#define send_english_lth 		0xffffff30	// right tilt - ub 0xffffffc0
#define space_english_lth		0xffffff10	// forward tilt 0xffffffc0
#define morse_backspace_lth		0x28		// left tilt - added buffer lb - 0x38
#define letter_backspace_lth	0x70		// backward tilt - added buffer 0x80

#define send_english_hth 		0xffffffc0	// right tilt - ub 0xffffffc0
#define morse_backspace_hth		0xe0		// left tilt - added buffer lb - 0x38
#define letter_backspace_hth	0xe0		// backward tilt - added buffer 0x80
#define space_english_hth		0xffffffc0	// forward tilt 0xffffffc0

/*
 * S = Send/ confirm english letter - morse that has been sent is converted to english
 * B = Backspace morse
 * L = English Letter Backspace
 * E = English Letter Space - space between english words
 */

alt_8 pwm = 0;
alt_u8 led;
int level;

void led_write(alt_u8 led_pattern) {
    IOWR(LED_BASE, 0, led_pattern);
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

void print_flags(int S, int M, int L, int E)
{
	printf("S: %i\t", S);
	printf("B: %i\t", M);
	printf("L: %i\t", L);
	printf("E: %i\n", E);
}

int main() {

    alt_32 x_read;
    alt_32 y_read;
	int switch_datain;

	int room_switch_datain;
    alt_up_accelerometer_spi_dev * acc_dev;
    acc_dev = alt_up_accelerometer_spi_open_dev("/dev/accelerometer_spi");
    if (acc_dev == NULL) { // if return 1, check if the spi ip name is "accelerometer_spi"
        return 1;
    }

    timer_init(sys_timer_isr);
    int setFlag = 0;
    int S = 0;
    int M = 0;
    int L = 0;
    int E = 0;
    int count = 0;
    int justSetFlag = 1;

    int roomNumber = IORD_ALTERA_AVALON_PIO_DATA(SWITCH_BASE); // TODO: change this to check first.
    roomNumber &= (0b1000000000);

    int send_switch_intial = IORD_ALTERA_AVALON_PIO_DATA(SWITCH_BASE);
    send_switch_intial &= (0b1000000000);

    while (1) {
    	switch_datain = ~IORD_ALTERA_AVALON_PIO_DATA(BUTTON_BASE);

    	// get data from switches
    	room_switch_datain = IORD_ALTERA_AVALON_PIO_DATA(SWITCH_BASE);
    	// only accept data from last 2 switches
    	room_switch_datain &= (0b0000000011);


    	int send_switch_datain_new = IORD_ALTERA_AVALON_PIO_DATA(SWITCH_BASE);
    	send_switch_datain_new  &= (0b1000000000);

    	if(send_switch_datain_new != send_switch_intial)
    	{
    		printf("Send\n");
    		send_switch_intial = send_switch_datain_new;
    	}


    	// update room number
    	int newRoomNumber = room_switch_datain;
    	if (newRoomNumber != roomNumber)
    	{
    		roomNumber = newRoomNumber;
    		printf("New room number: %i\n", roomNumber);
    	}

		switch_datain &= (0b0000000011);
		if (switch_datain==1)
		{
			alt_putstr("Dot\n");
			// sending
		}
		else if (switch_datain==2)
		{
			alt_putstr("Dash\n");
			// sending
		}
		usleep(delay);
        alt_up_accelerometer_spi_read_x_axis(acc_dev, & x_read);
        alt_up_accelerometer_spi_read_y_axis(acc_dev, & y_read);
        if (!justSetFlag)
        {
        	if ((x_read > send_english_lth) && (x_read < send_english_hth))
        	{
        		// valid send (S)
        		S = 1;
        		setFlag = 1;
        		justSetFlag = 1;
        		// send data to jtag uart
        		print_flags(S, M, L, E);
        		// send flag data
        		alt_u32 val = 0x92;
        		IOWR_ALTERA_AVALON_PIO_DATA(0x00021060 ,val); //TODO: Fix this

        	}
        	else if ((x_read > morse_backspace_lth) && (x_read < morse_backspace_hth))
        	{
        		// valid morse backspace (M)
        		M = 1;
        		setFlag = 1;
        		justSetFlag = 1;
        		print_flags(S, M, L, E); // sending data
        		alt_u32 val = 0x00;
        		IOWR_ALTERA_AVALON_PIO_DATA(0x00021060 ,val); // printing "B"

        	}
        	else if ((y_read > letter_backspace_lth) && (y_read < letter_backspace_hth))
        	{
        		// valid letter backspace (L)
        		L = 1;
        		setFlag = 1;
        		justSetFlag = 1;
        		print_flags(S, M, L, E); // sending data
        		alt_u32 val = 0b1000111;
        		IOWR_ALTERA_AVALON_PIO_DATA(0x00021060 ,val);

        	}
        	else if ((y_read > space_english_lth) && (y_read < space_english_hth))
        	{
        		// valid english space (E)
        		E = 1;
        		setFlag = 1;
        		justSetFlag = 1;
        		print_flags(S, M, L, E); // sending data
        		alt_u32 val = 0x86;
        		IOWR_ALTERA_AVALON_PIO_DATA(0x00021060 ,val);
        	}
        }

        if (justSetFlag)
        {
        	count ++;
        	if (count == 3)
        	{
        		S = 0;
        		M = 0;
        		L = 0;
        		E = 0;
        		justSetFlag = 0;
        		count = 0;
        		IOWR_ALTERA_AVALON_PIO_DATA(0x00021060 ,0b11111111);

        	}
        }

        usleep(delay);
        setFlag = 0;
        S = 0;
        M = 0;
        L = 0;
        E = 0;


    }

    return 0;
}
