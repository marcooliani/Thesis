
# 1. Overview
- PLC registers reading
- Modbus message captures
- Data processing
- Interactive graphs and statistical analysis
- Invariant inference
- Business process mining

![RE drawio](https://user-images.githubusercontent.com/10734889/193014155-45176133-cd85-42b0-9b2f-6d456b74ba48.png)

# 2. Requirements

 - Operating system: Unix-like environments, including Linux, Mac OS X, and Windows Subsystem for Linux (WSL) 
 - Python 3.8 and PIP 3
 ```
sudo apt update
sudo apt upgrade
 sudo apt install python3.8
 sudo apt install python3-pip
 ```
 
 - Python3.8 libraries: pandas, matplotlib, numpy, ray, json, glob, modbus_tk, scipy
  ```
pip3 install -r requirements.txt
 ```

 
-  Java JDK version 8 or higher.
 
 ```
sudo apt-get install openjdk-8-jdk
 ```
- Gradle Build Tool : [installation](https://gradle.org/install/)

- perl 5
 
```
sudo apt install perl
```

- TShark - Wireshark 3.4.8
 
```
sudo apt install wireshark
```
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;To install from source
```
wget https://www.wireshark.org/download/src/wireshark-3.4.8.tar.xz -O /tmp/wireshark-3.0.0.tar.xz tar -xvf /tmp/wireshark-3.4.8.tar.xz cd /tmp/wireshark-3.0.0 sudo apt update && sudo apt dist-upgrade sudo apt install cmake libglib2.0-dev libgcrypt20-dev flex yacc bison byacc \ libpcap-dev qtbase5-dev libssh-dev libsystemd-dev qtmultimedia5-dev \ libqt5svg5-dev qttools5-dev cmake . make sudo make install
```

- Daikon 5.8.10 : [installation](daikon/Installation_Daikon.sh)
- Fluxicon Disco 3.2.4 : [installation](https://fluxicon.com/disco/)  
 Disco is not supported by Unix-like operating systems. The users can make use of [Wine](https://www.winehq.org/) or [Darling](https://www.darlinghq.org/) to install and run this software.

# 3. Information gathering

## 3.1 PLC registers reading
 
 Execute the script **_main.py_** to generate the data logs of the PLCs registers 
 ```
  python3 main.py simTime samplingTime
```

 - _simTime_ is the simulation time of the CPS model in seconds.  
   
 - _samplingTime_ is the sampling frequency in seconds.

Ray framework was used to get simultaneous data from the PLCs and  to seamlessly scale to a distributed attack architecture (eg. Botnet) if needed.
The output are JSON Files, with the following naming convention:
```
 {name_of_the_PLC}-{ip_of_the_PLC}-{port_of_the_PLC}@{timestamp}.json
```
These files are saved in the folder _historian/_ contained in the main directory.

## 3.2 Modbus message capture
In parallel with main.py, Tshark has to be started. 
To start capturing packets a capture interface has to be specified, Tshark will treat the first interface as the default interface and capture from it by default. In other words, `tshark` aliases to `tshark -i 1`
To list all the interfaces available to Tshark and select another one
```
tshark -D 
```
Run the capture
```
tshark  -i 1 -w modbusPackets.pcap-ng
```
While running, the total number of captured packets will appear on the console.
Tshark generates a pcap-ng files that contains all the information about the captured packets.
Once the pcap-ng file is created it can be translated int a CSV file by running
```
tshark -r modbusPackets.pcap-ng -T fields -E occurrence=f -e m -e t -e s -e d -e p -e L -e Cus:modbus.func_code:0:R -e Cus:modbus.bitval:0:R -e Cus:text:0:R -e Cus:modbus.regval_uint16:0:R -e Cus:mbtcp.trans_id:0:R -e i
```


# 4. Information processing

## 4.1 Data processing

The goal of the data processing is to convert the resulted files from the information gathering into datasets acceptable by invariant detection and business process mining tools.  

Executethe script 	**_convertoCSV.py_** by specifying an integer value of the variable _numberofPLCs_ that indicates the number of PLCs controlling the CPS model.   
Execute **_mergeDatasets.py_** to convert the JSON files to a CSV datasets. 
The column hold the values of the registers for each PLC  with the following naming convention ```{name_of_the_PLC}_{name_of_the_Register}```.  
The outputs are two CSV files saved in the directories _PLC_CSV_ and _process-mining/data_.  
 ```
  python3 convertoCSV.py numberofPLCs
  python3 mergeDatasets.py 
```   
The file saved in _process-mining/data_ is a timestamped dataset, it will be used for the business process mining.   
The file saved in _PLC_CSV_ is an enriched dataset with a partial bounded history of registers, and additional informations such as stable states, slope values of measurements and relative setpoints. This dataset will be used for the invariant detection.   


## 4.2 Interactive graphs and statistical analysis
  
Execute the script **_runChartPlots.py_** :    
```
  python3 runChartPlots.py var1 var2 .... varn
```
The outputs of this execution are run-sequence plots of the specified variables in function of the simulation time.  
  
Execute the script **_histPlots_Stats.py_** : 
```
  python3 histPlots_Stats.py var  
```
The outputs of this execution are a histogram and statistical informations of the variable _var_.  
These informations include :
- The mean, median, standard deviation, the maximum and minimum values.  
- Two tests are performed for the statistical distribution : Chi-squared test for uniformity and Shapiro-Wilk test for normality. 


## 4.3 Invariant inference
The invariant generation is done using the front-end tool of [Daikon](http://plse.cs.washington.edu/daikon/download/doc/daikon.html#convertcsv_002epl) for CSV dataset. To install Daikon follow the [guide](daikon/Installation_Daikon.sh).     
Execute the bash script **_runDaikon.sh_** to generate the invariants. 
```
  ./runDaikon.sh 
```
  
This script offers a query system to target specific invariants and to specify conditional invariants.  
The users have the possibility to insert a variable name in order to display the associated invariants.   
The users can customize the [splitter info file](https://plse.cs.washington.edu/daikon/download/doc/daikon/Enhancing-Daikon-output.html#Splitter-info-file-format) **_Daikon_Invariants/Inv_conditions.spinfo_** by specifying the conditions that Daikon should use to create conditional invariants.   
*Spinfo file example :*
```
PPT_NAME aprogram.point:::POINT
VAR1 > VAR2
VAR1 == VAR3 && VAR1 != VAR4
```

The results of the invariant analysis will be saved in the location **_Daikon_Invariants/daikon_results.txt_**.  
The conditional invariant will be saved in the location **_Daikon_Invariants/daikon_results_cond.txt_**.

## 4.4 Business process mining

This step relies on Disco to generate graphs representing the business process. 
Disco takes as input a CSV file containing the exchanged messages between the PLCs of the CPS model and the values of the PLCs registers.  
To create this CSV file we use a java program to convert the pcap files and the CSV dataset generated from the previous steps. 

The first step is to compile our java program. Within the directory **_process-mining_** run the command: 
```
./gradlew build
```
The second step is to convert the pcap file and the csv dataset into an admissible format by Disco: 
```
./gradlew runMessages
./gradlew runReadings
```
The final step is to combine the resulting files in a single one to generate the business process graphs: 
```
./gradlew Merge
```
The output files are saved in directory **_process-mining/data_**.  

To generate the business process graphs:    
_Launch Disco > Open File > Select the file **MergeEvents.csv** > Define each column role > Click Start Import_

## Experimental Data

* [PLC registers captures (JSON)](https://www.dropbox.com/s/c6rc16375o2wjxm/historian.zip?dl=0)  Extract the JSON files to the directory **_/historian_**. 
* [Timestamped Dataset register values (CSV)](https://www.dropbox.com/s/fd6y59272voydse/PLC_Dataset_TS.csv?dl=0)  Place the CSV file in the directory **_process-mining/data._**
* [Dataset register values (CSV)](https://www.dropbox.com/s/nsaerogqlxhpry2/PLC_Dataset.csv?dl=0)  Place the CSV file in the directory **_daikon/Daikon_Invariants._**
* [Network capture (CSV)](https://www.dropbox.com/s/76uxd4jq68iaud5/CleanCaptureWrite.csv?dl=0) Place the CSV file in the directory **_process-mining/data._**
* [Network capture (PCAPNG)](https://www.dropbox.com/s/89its5qf7zhqq31/NetworkTraffic.pcap?dl=0) Convert the pcap file to CSV by using the tshark commands.
