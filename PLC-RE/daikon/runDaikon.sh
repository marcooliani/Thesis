#!/bin/bash

#Adjust Daikon directory
#export DAIKONDIR=/absolute_path_to_daikon/daikon-5.8.10; source $DAIKONDIR/scripts/daikon.bashrc
cd Daikon_Invariants/
#perl $DAIKONDIR/scripts/convertcsv.pl PLC_Dataset.csv
perl $DAIKONDIR/scripts/convertcsv.pl PLC_SWaT_Dataset.csv
#java -cp $DAIKONDIR/daikon.jar daikon.Daikon --nohierarchy PLC_Dataset.decls PLC_Dataset.dtrace > daikon_results.txt
java -cp $DAIKONDIR/daikon.jar daikon.Daikon --nohierarchy PLC_SWaT_Dataset.decls PLC_SWaT_Dataset.dtrace > daikon_results.txt
echo "Invariants generated successfully :"
value=`cat daikon_results.txt`  
echo "$value" 
echo "*************************************************************"
echo "Insert variable name to display related invariants : "
read var
grep -n $var daikon_results.txt
echo "*************************************************************"
echo "Conditional invariants : "
#java -cp $DAIKONDIR/daikon.jar daikon.Daikon --nohierarchy PLC_Dataset.decls PLC_Dataset.dtrace Inv_conditions.spinfo > daikon_results_cond.txt
java -cp $DAIKONDIR/daikon.jar daikon.Daikon --nohierarchy PLC_SWaT_Dataset.decls PLC_SWaT_Dataset.dtrace Inv_conditions.spinfo > daikon_results_cond.txt

