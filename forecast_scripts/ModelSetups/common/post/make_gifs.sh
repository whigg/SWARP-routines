#!/bin/bash
# This script will collect and archive the results of the local TP4 model

# ===================================================================================
source $SWARP_ROUTINES/source_files/hex_vars.src
THIS_SRC=`readlink -f $1`
source $THIS_SRC
# ===================================================================================


# =============================================================================
# EMAIL ADDRESS
email=$(cat $FCemail)
# =============================================================================

if [ $# -ne 2 ]
then
   echo "Usage: make_gifs.sh [source file] [date]"
   echo "-date in yyyymmdd format"
   exit
else
   cdate=$2
fi

ncfil=$THISFC2/$cdate/final_output/${FC_OUTPUT}_start${cdate}T000000Z.nc
figdir=$THISFC2/$cdate/figures
mkdir -p $figdir

pdir=$figdir/pngs # directory with pngs
mkdir -p $pdir
gdir=$figdir/gifs # directory to save gifs to
mkdir -p $gdir

post=$FCcommon/post
$python $post/make_pngs.py --ncfile=$ncfil --outdir=$pdir --FCtype=$FCtype

cd $pdir
for vdir in *
do
   cd $vdir
   $convert -delay 15 -loop 0 *.png $vdir.gif
   mv $vdir.gif $gdir
   cd ..
done