#!/bin/bash
# Runs hyc2proj on all files of archv type
# - to be run from data

# In .bash_profile:
# 1. add MSCPROGS/bin to $PATH variable
#    (may need to compile MSCPROGS with "make" & "make install"
# 2. add this directory to $PATH variable
# 3. set environment variable $GIT_REPOS to the directory containing
#     this repository ("SWARP-routines")

# Info for hyc2proj
# - copied from MSCPROGS/Input & edited
h2p_in="$GIT_REPOS/SWARP-routines/netcdf_production/Input"

pwd=`pwd`
mkdir -p tmp
cd tmp

# Info for hyc2proj
ln -s $h2p_in/proj.in .
ln -s $h2p_in/extract.archv_wav .
ln -s $h2p_in/depthlevels.in .

# Info about grid from topo dir
tp4_input=/work/shared/nersc/msc/ModelInput/TOPAZ4/TP4a0.12/topo
ln -s $tp4_input/grid.info .
ln -s $tp4_input/regional.grid.a .
ln -s $tp4_input/regional.grid.b .
ln -s $tp4_input/regional.depth.a .
ln -s $tp4_input/regional.depth.b .

odir=../archv_netcdf
mkdir -p $odir
for f in $pwd/TP4archv_wav*.a
do
   len=${#pwd}
   g=${f:$((len+1))}
   len=${#g}
   base=${g:0:$((len-2))}
   ln -s $f $pwd/$base.b .

   echo "********************************************************"
   echo "Running hyc2proj on $g..."
   echo "********************************************************"
   echo " "

   hyc2proj $g
   mv *.nc $odir
done

echo "Netcdf files in $odir:"
ls -lh $odir

cd $pwd
rm -r tmp