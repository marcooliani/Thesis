
# 1. Overview
- Docker project to build the PLCs
- Matlab-Simulink script of the physics
- Modbus connection script (To connect PLC1 and PLC2 over modbus)
- Simulink connection script (To connect the simulated sensors in Matlab-Simulink to the Docker containers of the PLCs)


# 2. Build
Edit the `interface.cfg` file accordingly. The ports of the containers must be inputted.
Build the simulink connection script, to interface the OpenPLC Simulink driver and the Simulink model using UDP Send and Receive blocks

To compile:  
`g++ simlink.cpp -o simlink -pthread`

## Matlab Simulink
![Model](/TestBED/simulink/Images/SimulinkSimplifiedModel.png "Simulink Simplified Model")
|:--:|
| <b>Simulink Model of a Simplified filtration unit</b>|

The model above is controlling a SWAT system composed of two tanks (Tank1 left, Tank2 right) with a level sensor on each tank and a pump on Tank1.
![Sensor1](/TestBED/simulink/Images/Sensor1OUT.png "Sensor1")
|:--:|
| <b>Level sensor on Tank1</b>|


![Sensor2](/TestBED/simulink/Images/Sensor2OUT.png "Sensor2")
|:--:|
| <b>Level sensor on Tank2</b>|


![Actuators](/TestBED/simulink/Images/ActuatorsInputs.png "Actuators")
|:--:|
| <b>Pump on Tank1</b>|


- Open the file `simulink/Model/SimplifedModel.slx` in Matlab Simulink, that contains the aforementioned SWAT system
- Open the file `simulink/Model/init.m`, that contains the variables that define the water flow, the diameter of the pipes, etc...

![Init](/TestBED/simulink/Images/Init.png "Init")
|:--:|
| <b>Init script</b>|

## Docker
cd into the folders /PLC1 and /PLC2 and build the docker image, using the command docker build. Remember to open ports: `502(Modbus), 6670(Simulink Connection), 6671(Simulink Connection) and 8080(OpenPLC web interface)`

# 3. Run

- Start the docker containers of PLC1 and PLC2
- Run `init.m`
- Run `SimplifedModel.slx`


A monitor, like the one in the following picture should appear

![Monitor](/TestBED/simulink/Images/OutputMonitor.png "Monitor")
|:--:|
| <b>Monitor</b>|


- Run the compiled file from `simulink/Link/simlink_modbus.cpp`

- Run the script `simulink/Link/connectPLC.py`

- DONE, the Simplified SCADA system should be up and running. 

All the scripts contained in `/PLC-RE` will now work on your computer

## I have some questions!

I am reachable via e-mail: *marco.lucchese* at *univr* dot *it*.
