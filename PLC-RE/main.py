import pandas as pd #json 
import os
from datetime import datetime # Per il timestamp dei file JSON (per uso futuro)
import time #needed for sleep and to capture data for set amount of time
import ray # Execute in parallel -> ray.get([plc1.remote(), plc2.remote()])
import json 
from collections import defaultdict
import modbus_tk
import modbus_tk.defines as cst
from modbus_tk import modbus_tcp, hooks
import logging
import itertools
from time import sleep
import sys

#logger
logger = modbus_tk.utils.create_logger("console", level=logging.DEBUG)

logging.basicConfig(filename="plcHistoryTOOL",
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.DEBUG)

#parallel distributed execution 
ray.init()



def connect_to_slave(ip,port):
    """Connect to the slave

    Args:
        ip (string): ip of the modbus slave
        port (int): port of the modbus slave
    """
    # Connect to the slave
    ip=str(ip)
    port=int(port)
    master = modbus_tcp.TcpMaster(host=ip,port=port)
    master.set_timeout(5.0)
    logger.info("Connected to ip=%s:%s",ip,port)
    return(master)

##Functions to read data from the PLCs
def read_c(master):
    """read coils, coils are addressed as follows: [0-xxx].[0-7]

    Args:
        master (object): to send the read command to the right plc
    """
    registers= {}
    values=master.execute(1, cst.READ_COILS, 0, 90)  
    count=0
    for c in range(0,11):
        for a in range(0,8):
            registers['%QX' + str(c) + '.' + str(a)] = str(values[count])
            count+=1
            
    return(registers)
    
def read_ir(master):
    """read input registers, ir are addressed as follows: [0-xxx]

    Args:
        master (object): to send the read command to the right plc
    """
    registers= {}
    values=master.execute(1, cst.READ_INPUT_REGISTERS, 0, 11)
    c=0
    for i in values:
        registers['%IW' + str(c)] = str(i)
        c+=1    
    return(registers)

def read_di(master):
    """read discrete input, di are addressed as follows: [0-xxx].[0-7]

    Args:
        master (object): to send the read command to the right plc
    """
    registers= {}
    values=master.execute(1, cst.READ_DISCRETE_INPUTS, 0, 90)
    count=0
    for c in range(0,11):
        for a in range(0,8):
            registers['%IX' + str(c) + '.' + str(a)] = str(values[count])
            count+=1
    return(registers)
    
def read_mr(master):
    """read memory registers, mr are addressed as follows: [0-xxx] and are holding registers starting from the address 1024

    Args:
        master (object): to send the read command to the right plc
    """
    registers= {}
    values=master.execute(1, cst.READ_HOLDING_REGISTERS, 1024, 11)
    c=0
    for i in values:
        registers['%MW' + str(c)] = str(i)
        c+=1    
    return(registers)
    
def read_hr(master):
    """read holding registers, hr are addressed as follows: [0-xxx]

    Args:
        master (object): to send the read command to the right plc
    """
    registers= {}
    values=master.execute(1, cst.READ_HOLDING_REGISTERS, 0, 11)
    c=0
    for i in values:
        registers['%QW' + str(c)] = str(i)
        c+=1    
    return(registers)
    
@ray.remote
def read_registers(name,ip,port,master):
    name=str(name)
    ip=str(ip)
    port=str(port)
    single_plc_registers = defaultdict(dict)
    
    single_plc_registers[ip]['DiscreteInputRegisters'] = read_di(master)
    single_plc_registers[ip]['InputRegisters'] = read_ir(master)
    single_plc_registers[ip]['HoldingOutputRegisters'] = read_hr(master)
    single_plc_registers[ip]['MemoryRegisters'] = read_mr(master)
    single_plc_registers[ip]['Coils'] = read_c(master)
    
    ora=datetime.now(tz=None)

    with open(f'historian/plc{name}-{ip}-{port}@{ora}.json', 'w') as sp:
        sp.write(json.dumps(single_plc_registers, indent=4))

#function that asks the user to input the ip and port of the PLCs and outputs a list of tuples
def ask_plc():
    plc_list=[]
    while True:
        ip=input("Insert the ip of the PLC (or press enter to exit): ")
        if ip=="":
            break
        port=input("Insert the port of the PLC: ")
        name=str(input("Insert the number of the PLC: "))
        plc_list.append((name,ip,port))
    return(plc_list)

#function that gets a list of tuples and connects the PLCs and return a list of objects with the connection
def connect_plc(plc_list):
    plc_connection=[]
    for plc in plc_list:
        plc_connection.append(connect_to_slave(plc[1],plc[2]))
    return(plc_connection)

#function that triggers the read of the registers and saves the data in a json file
def read_and_save(plc_list,plc_connection):
    t_end = time.time() + int(sys.argv[1])
    
    while time.time() < t_end:
        for plc,connection in zip(plc_list,plc_connection):
            read_registers(plc[0],plc[1],plc[2],connection)
            sleep(float(sys.argv[2]))

def main(): 
    plc_list=ask_plc()
    plc_connection=connect_plc(plc_list)
    read_and_save(plc_list,plc_connection)

if __name__ == '__main__':
    main()
