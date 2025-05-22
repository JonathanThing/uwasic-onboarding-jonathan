# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

# Returns the period between rising edges
async def measure_freq(dut, timeout_ms):

    start_measure_time = cocotb.utils.get_sim_time(units="ns")

    while True:
        await ClockCycles(dut.clk, 1)
        if (cocotb.utils.get_sim_time(units="ns") - start_measure_time) > timeout_ms * 1000000:
            return 0
        if dut.uo_out.value == 0:
            break
    while True:
        await ClockCycles(dut.clk, 1)
        if (cocotb.utils.get_sim_time(units="ns") - start_measure_time) > timeout_ms * 1000000:
            return 0
        if dut.uo_out.value != 0:
            break

    start_time = cocotb.utils.get_sim_time(units="ns")

    while True:
        await ClockCycles(dut.clk, 1)
        if (cocotb.utils.get_sim_time(units="ns") - start_measure_time) > timeout_ms * 1000000:
            return 0
        if dut.uo_out.value == 0:
            break
    while True:
        await ClockCycles(dut.clk, 1)
        if (cocotb.utils.get_sim_time(units="ns") - start_measure_time) > timeout_ms * 1000000:
            return 0
        if dut.uo_out.value != 0:
            break

    end_time = cocotb.utils.get_sim_time(units="ns")
    return end_time - start_time
        
@cocotb.test()
async def test_pwm_freq(dut):
    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Enable all outputs and PWM
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xFF) 
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xFF) 
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF) 
    ui_in_val = await send_spi_transaction(dut, 1, 0x03, 0xFF) 
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x80) # ~ 50% duty cycle 

    period = await measure_freq(dut, 3) # 3ms timeout
    if period == 0:
        assert False, "Timeout while measuring frequency"
    frequency = 1 / (period * 1e-9) # ns is 1e-9 seconds
    
    dut._log.info(f"Measured frequency: {frequency} Hz")

    expected_freq = 3000
    valid = ((frequency >= expected_freq * 0.99) and (frequency <= expected_freq * 1.01))

    assert valid, f"Frequency out of range: {frequency} Hz, expected around {expected_freq*0.99} to {expected_freq*1.01} Hz"
    dut._log.info("PWM Frequency test completed successfully")

# Returns the period between rising edges
async def measure_duty(dut, timeout_ms):

    period = await measure_freq(dut, timeout_ms)

    if (period == 0): # 0% or 100% duty cycle
        return 0 if dut.uo_out.value == 0 else 1

    while True:
        await ClockCycles(dut.clk, 1)
        if dut.uo_out.value == 0:
            break
    while True:
        await ClockCycles(dut.clk, 1)
        if dut.uo_out.value != 0:
            break

    start_time = cocotb.utils.get_sim_time(units="ns")

    while True:
        await ClockCycles(dut.clk, 1)
        if dut.uo_out.value == 0:
            break

    end_time = cocotb.utils.get_sim_time(units="ns")
    return (end_time - start_time) / period

@cocotb.test()
async def test_pwm_duty(dut):
    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Enable all outputs and PWM
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xFF) 
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xFF) 
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF) 
    ui_in_val = await send_spi_transaction(dut, 1, 0x03, 0xFF) 

    await test_duty(dut, 0)
    await test_duty(dut, 0.25)
    await test_duty(dut, 0.50)
    await test_duty(dut, 0.75)
    await test_duty(dut, 1)

    dut._log.info("PWM Duty Cycle test completed successfully")

async def test_duty(dut, duty):
    value = int(duty * 255)
    dut.log.info(f"Testing duty cycle: {value/255*100} %")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, value) # 100% duty cycle 
    duty = await measure_duty(dut, 2)
    dut._log.info(f"Measured duty: {duty*100} %")
    assert (duty >= value/255*0.99) and (duty <= value/255*1.01), f"Meaused duty: {duty*100}%, expected in range {value/255*0.99}% to {value/255*1.01}%"