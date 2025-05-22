`default_nettype none

module spi_peripheral (
    input  wire       clk,      // clock
    input  wire       rst_n,     // reset_n - low to reset
    input  wire       SCLK,     // SPI clock
    input  wire       COPI,     // SPI controller out, peripheral in
    input  wire       nCS,      // SPI chip select
    output  wire [7:0] en_reg_out_7_0,
    output  wire [7:0] en_reg_out_15_8,
    output  wire [7:0] en_reg_pwm_7_0,
    output  wire [7:0] en_reg_pwm_15_8,
    output  wire [7:0] pwm_duty_cycle,
);

    // Max register address in hex
    localparam max_addr = 4;

    // Register AddressSCLK_buff
    localparam en_out_7_0_addr = 8'h00;
    localparam en_out_15_8_addr = 8'h01; 
    localparam en_pwm_7_0_addr = 8'h02;
    localparam en_pwm_15_8_addr = 8'h03;
    localparam pwm_duty_cycle_addr = 8'h04; 

    // Registers
    reg [7:0] en_reg_out_7_0;
    reg [7:0] en_reg_out_15_8;
    reg [7:0] en_reg_pwm_7_0;
    reg [7:0] en_reg_pwm_15_8;
    reg [7:0] pwm_duty_cycle;

    assign en_reg_out_7_0 = en_reg_out_7_0;
    assign en_reg_out_15_8 = en_reg_out_15_8;
    assign en_reg_pwm_7_0 = en_reg_pwm_7_0;
    assign en_reg_pwm_15_8 = en_reg_pwm_15_8;
    assign pwm_duty_cycle = pwm_duty_cycle;

    // Flip Flop Buffer.
    reg [2:0] SCLK_buff;
    reg [1:0] nCS_buff;
    reg [1:0] COPI_buff;

    reg [15:0] input_reg; // 1b r/W, 7b address, 8b data
    reg [4:0] clock_counter;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin // Reset registers

            //Reset buffers
            SCLK_buff <= 3'b0;
            nCS_buff <= 2'b0;
            COPI_buff <= 2'b0;
            
            // Reset registers
            en_reg_out_7_0 <= 8'b0;
            en_reg_out_15_8 <= 8'b0;
            en_reg_pwm_7_0 <= 8'b0;
            en_reg_pwm_15_8 <= 8'b0;
            pwm_duty_cycle <= 8'b0;

            input_reg <= 16'b0;
            clock_counter <= 5'b0;

        end else begin
            SCLK_buff <= {SCLK_buff[1:0], SCLK};
            nCS_buff <= {nCS_buff[0], nCS};
            COPI_buff <= {COPI_buff[0], COPI};
            
            if (nCS[1] == 1'b0) begin  // Chip select is active, read data
                if (SCLK_buff[1] == 1'b0 && SCLK_buff[2] == 1'b1) begin // Rising edge of SCLK
                    input_reg <= {input_reg[14:0], COPI_buff[1]}; // Shift in the data
                    clock_counter <= clock_counter + 1; // Increment the clock counter
                end
            end else begin 

                if (clock_counter == 5'd16) begin // 16 bits received
                    switch (input_reg[14:8]) begin
                        en_out_7_0_addr: en_reg_out_7_0 <= input_reg[7:0]; // Write to en_reg_out_7_0
                        en_out_15_8_addr: en_reg_out_15_8 <= input_reg[7:0]; // Write to en_reg_out_15_8
                        en_pwm_7_0_addr: en_reg_pwm_7_0 <= input_reg[7:0]; // Write to en_reg_pwm_7_0
                        en_pwm_15_8_addr: en_reg_pwm_15_8 <= input_reg[7:0]; // Write to en_reg_pwm_15_8
                        pwm_duty_cycle_addr: pwm_duty_cycle <= input_reg[7:0]; // Write to pwm_duty_cycle
                        default: ; // Do nothing for invalid addresses
                end
                input_reg <= 16'b0; // Clear the input register
                clock_counter <= 5'b0; // Reset the clock counter
            end
        end
    end



endmodule
