# eg call
# python ice_edge_OSISAF_1obs.py --date=20160821 --outdir=/work/timill/RealTime_Models/validation//TP4a0.12/ice_only/20160821/OSISAF --FC_rootdir=/work/timill/RealTime_Models/results//TP4a0.12/ice_only
import os,sys,matplotlib
matplotlib.use('Agg')

# SR = os.getenv('SWARP_ROUTINES')
# if SR+'/py_funs' not in sys.path:
#    sys.path.append(SR+'/py_funs')

import mod_reading   as mr
import MIZchar       as mc
from getopt import getopt

import datetime as DTM

# =======================================================================
# command line inputs
cdate    = None
outdir   = None
FCdir    = None
opts,args   = getopt(sys.argv[1:],"",["date=","outdir=","FC_rootdir="])
for opt,arg in opts:
   if opt=='--date':
      cdate = arg
   if opt=='--outdir':
      outdir   = arg
   if opt=='--FC_rootdir':
      FCdir = arg

# errors
if cdate is None:
   raise ValueError("specify date of OSISAF observation with --date=...")
if outdir is None:
   raise ValueError("specify output location with --outdir=...")
if cdate is None:
   raise ValueError("specify location of forecast results with --FC_rootdir=...")
# =======================================================================

fmt   = "%Y%m%d"
dto   = DTM.datetime.strptime(cdate+"12",fmt+"%H")

print('\nObservation date')
print(dto)
print('\n')

FCdays   = 6 # length of -ice-only FC's
for ndays in range(FCdays):
   # 0,...,5 (days which have daily average files)
   fcdate   = dto-DTM.timedelta(ndays+.5)
   fcdir    = FCdir+'/'+fcdate.strftime(fmt)+'/bin'
   # print(fcdate)
   # print(fcdir)

   hi = mr.file_list(fcdir,'DAILY','.a')
   # for i,DT in enumerate(hi.datetimes):
   #    print(i)
   #    print(DT)

   # find index corresponding to observation date
   dto2,idx = hi.nearestDate(dto)
   # print(dto2)
   # print(ndays,idx)

   # call the AOD routine
   odir  = outdir+'/FC'+str(ndays)+'days'
   hi.areas_of_disagreement(time_index=idx,\
      obs_type='OSISAF',obs_path=None,obs_option='multi',\
      vertices=None,regions=None,\
      do_sort=False,EastOnly=False,\
      forecast_day=ndays,\
      plotting=1,outdir=odir)