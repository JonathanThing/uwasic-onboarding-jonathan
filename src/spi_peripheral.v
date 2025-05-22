`default_nettype none

module spi_peripheral (
    input  wire       clk,      // clock
    input  wire       rst_n,     // reset_n - low to reset
    input  wire       SCLK,     // SPI clock
    input  wire       COPI,     // SPI controller out, peripheral in
    input  wire       nCS,      // SPI chip select
    output  reg [7:0] en_reg_out_7_0,
    output  reg [7:0] en_reg_out_15_8,
    output  reg [7:0] en_reg_pwm_7_0,
    output  reg [7:0] en_reg_pwm_15_8,
    output  reg [7:0] pwm_duty_cycle
);
    // Register AddressSCLK_buff
    localparam en_out_7_0_addr = 8'h00;
    localparam en_out_15_8_addr = 8'h01; 
    localparam en_pwm_7_0_addr = 8'h02;
    localparam en_pwm_15_8_addr = 8'h03;
    localparam pwm_duty_cycle_addr = 8'h04; 

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
            // Update async input buffer
            SCLK_buff <= {SCLK_buff[1:0], SCLK};
            nCS_buff <= {nCS_buff[0], nCS};
            COPI_buff <= {COPI_buff[0], COPI};
            
            if (nCS_buff[1] == 1'b0) begin  // Chip select is active, SPI transmission occuring
                if (SCLK_buff[2] == 1'b0 && SCLK_buff[1] == 1'b1) begin // Rising edge of SCLK
                    input_reg <= {input_reg[14:0], COPI_buff[1]};
                    clock_counter <= clock_counter + 1; 
                end
            end else begin // Chip select is inactive, SPI transmission is complete
                if (clock_counter == 5'd16 && input_reg[15] == 1'b1) begin // 16 clocks received and write is requested
                    case ({1'b0,input_reg[14:8]}) // Address bits
                        en_out_7_0_addr: en_reg_out_7_0 <= input_reg[7:0]; 
                        en_out_15_8_addr: en_reg_out_15_8 <= input_reg[7:0]; 
                        en_pwm_7_0_addr: en_reg_pwm_7_0 <= input_reg[7:0];
                        en_pwm_15_8_addr: en_reg_pwm_15_8 <= input_reg[7:0]; 
                        pwm_duty_cycle_addr: pwm_duty_cycle <= input_reg[7:0]; 
                        default: ; // Invalid adress
                    endcase
                end

                // Clear input register and clock counter
                input_reg <= 16'b0;
                clock_counter <= 5'b0;
          end
        end
    end
endmodule
