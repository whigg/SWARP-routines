#!/bin/bash
# This script will collect and archive the results of the local TP4 model

echo "Collecting data produced in date `date +%d/%m/%Y`"

# defining all the dir that will be used
RTM=/work/timill/RealTime_Models
DFDIR=$RTM/TP4a0.12/expt_01.1
WKDIR=$RTM/results/TP4a0.12/ice_only/work
FCDIR=/home/nersc/timill/GITHUB-REPOSITORIES/SWARP-routines/forecast_scripts


tday=`date +%Y%m%d`
TDIR=$WKDIR/$tday
mkdir -p $WKDIR/$tday/bin
mkdir -p $WKDIR/$tday/netcdf
mkdir -p $WKDIR/$tday/final_output
mkdir -p $WKDIR/$tday/info

#moving TP4archv & TP4DAILY
echo "Moving the TP4archv*.[ab] and TP4DAILY*.[ab]"
mv $DFDIR/data/TP4archv* $TDIR/bin
mv $DFDIR/data/TP4DAILY* $TDIR/bin
echo ""

#moving the info files
echo "Moving the info files"
cp $DFDIR/log/mpijob.out $TDIR/info
cp $TP4_REALTIME/Build_V2.2.12_X01.1/flags $TDIR/info
mv $FCDIR/last_restart.txt $TDIR/info
echo "Transfer complete"
echo ""
echo "Producing the websitego file"
touch $RTM/results/TP4a0.12/ice_only/website/websitego
echo $tday > $RTM/results/TP4a0.12/ice_only/website/websitego