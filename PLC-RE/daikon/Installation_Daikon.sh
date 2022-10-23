# Documentation
NOTE: Daikon is supported on Unix-like environments, including Linux, Mac OS X, and Windows Subsystem for Linux (WSL). It is not supported on Windows or Cygwin!

## installation
https://plse.cs.washington.edu/daikon/download/doc/daikon.html#Installation

## install requirements on ubuntu
sudo apt-get install openjdk-8-jdk gcc ctags graphviz netpbm texlive texinfo

## cmds to add to .bashrc (or run individually)
export DAIKONDIR=path_to_daikon/daikon-5.8.0
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
source $DAIKONDIR/scripts/daikon.bashrc

## compile Daikon (takes a long time...)
make -C $DAIKONDIR rebuild-everything

# running daikon on CSV data
https://plse.cs.washington.edu/daikon/download/doc/daikon.html#convertcsv_002epl

## prereq1: install Text::CSV, a Perl package that convertcsv.pl uses
sudo apt-get install libtext-csv-perl

## prereq1-alt: https://metacpan.org/pod/Text::CSV
cpan App::cpanminus
cpanm Text::CSV

## prereq2: place checkargs.pm file from (https://github.com/plume-lib/html-tools) into an @INC location, usually: /daikon_path/daikon-5.8.0/scripts
perl $DAIKONDIR/scripts/convertcsv.pl example.csv 


# execution cmds 
## (if you're not in the directory of the target file, it doesn't work for some reason)
cd Documents/daikonparent/datasets
perl $DAIKONDIR/scripts/convertcsv.pl sample1.csv
java -cp $DAIKONDIR/daikon.jar daikon.Daikon --nohierarchy sample1.decls sample1.dtrace

#in order to add a condition you must create a splitter info file (.spinfo) to the java comand
java -cp $DAIKONDIR/daikon.jar daikon.Daikon --nohierarchy sample1.decls sample1.dtrace sample1.spinfo

# at this point, you will be able to see the invariants on your terminal
