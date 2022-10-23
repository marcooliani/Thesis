#This script simulates the communication between two PLCs
#The first PLC is the master and the second PLC is the slave
#The master PLC reads the coil of the master PLC and writes the value in the coil of the slave PLC
#The packets exchanged will be captured by wireshark 

import easymodbus.modbusClient
import time

#function that asks the user to input the ip and port of the plc
def ask_plc():
    plc_list=[]
    while True:
        ip=input("Insert the ip of the PLC (or press enter to exit): ")
        if ip=="":
            break
        port=input("Insert the port of the PLC: ")
        name=input("Insert the name of the PLC: ")
        plc_list.append((name,ip,port))
    return(plc_list)

#function that connects the plc and return a list of objects with the connection
def connect_plc(plc_list):
    plc_connection=[]
    for plc in plc_list:
        master = easymodbus.modbusClient.ModbusClient(plc[1], port=plc[2])
        master.connect()
        plc_connection.append(master)
    return(plc_connection)

#funtion that reads the coils of the plc and writes the value in the other plc coil
def read_and_write(plc_list,plc_connection):
    while True:
        try:
            coils=plc_list[0].read_coils(0,0)
        except:
            print("Error in reading coil")
        try:
            plc_list[1].write_single_coil(0,coils[0])
        except:
            print("Error in writing coil")
        time.sleep(1)

def main():
    plc_list=ask_plc()
    plc_connection=connect_plc(plc_list)
    read_and_write(plc_list,plc_connection)
    


if __name__ == "__main__":
    main()


    
