
module nios_accelerometer (
	accelerometer_spi_external_interface_I2C_SDAT,
	accelerometer_spi_external_interface_I2C_SCLK,
	accelerometer_spi_external_interface_G_SENSOR_CS_N,
	accelerometer_spi_external_interface_G_SENSOR_INT,
	clk_clk,
	led_external_connection_export,
	reset_reset_n,
	switch_external_connection_export,
	hex2_external_connection_export,
	hex1_external_connection_export,
	button_external_connection_export);	

	inout		accelerometer_spi_external_interface_I2C_SDAT;
	output		accelerometer_spi_external_interface_I2C_SCLK;
	output		accelerometer_spi_external_interface_G_SENSOR_CS_N;
	input		accelerometer_spi_external_interface_G_SENSOR_INT;
	input		clk_clk;
	output	[9:0]	led_external_connection_export;
	input		reset_reset_n;
	input	[9:0]	switch_external_connection_export;
	output	[6:0]	hex2_external_connection_export;
	output	[6:0]	hex1_external_connection_export;
	input	[3:0]	button_external_connection_export;
endmodule
