import numpy as np
from datetime import datetime,timedelta
from netCDF4 import Dataset as ncopen

##########################################################
class plot_object:

   def __init__(self,fig=None,ax=None,cbar=None,axpos=None):

      if fig is None:
         from matplotlib import pyplot as plt
         self.fig   = plt.figure()
      else:
         self.fig   = fig

      if ax is None:
         self.ax = self.fig.add_subplot(1,1,1)
      else:
         self.ax  = ax

      self.cbar   = cbar
      self.axpos  = axpos

      return

   def get(self):
      return self.fig,self.ax,self.cbar

   def renew(self,axpos=None):
      
      pobj  = plot_object(fig=self.fig,ax=self.ax,cbar=self.cbar,axpos=axpos)

      return pobj
##########################################################

##########################################################
class proj_obj:
   # projection info in this object
   def __init__(self,att_names,att_vals=None):

      # rest of attributes:
      if att_vals is not None:
         for n in range(len(att_names)):
            setattr(self,att_names[n],att_vals[n])
      else:
         for n in range(len(att_names)):
            setattr(self,att_names[n],0)
      return
##########################################################


###########################################################
class make_plot_options:

   def __init__(self,vname,vec_opt=0,conv_fac=1,\
      wave_mask=False,ice_mask=False,dir_from=True):

      self.name      = vname
      self.vec_opt   = vec_opt
      self.conv_fac  = conv_fac
      self.ice_mask  = ice_mask
      self.wave_mask = wave_mask
      self.dir_from  = dir_from

      return
###########################################################


###########################################################
def check_pair(var_opts1,var_opts2):
   # ====================================================================
   # check options
   if var_opts1.vec_opt in [2,3,5]:
      print('Variable : '+var_opts1.name)
      print('vec_opt  : '+var_opts1.vec_opt)
      raise ValueError('Invalid plot option for pcolor plot')

   if var_opts2.vec_opt in [0,1,4]:
      print('Variable : '+var_opts1.name)
      print('vec_opt  : '+var_opts1.vec_opt)
      raise ValueError('Invalid plot option for quiver plot')
   # ====================================================================
   return
###########################################################

##########################################################
def lonlat_names(ncfil):
   nc = ncopen(ncfil)
   for vbl in nc.variables:
      if 'lon' in vbl or 'Lon' in vbl:
         lon   = vbl
      if 'lat' in vbl or 'Lat' in vbl:
         lat   = vbl
   nc.close()
   return lon,lat
##########################################################

##########################################################
class nc_get_var:
   #get basic info from 2d variable

   #####################################################
   def __init__(self,ncfil,vblname,time_index=None):

      nc    = ncopen(ncfil)
      vbl0  = nc.variables[vblname]

      # get the netcdf attributes
      ncatts   = vbl0.ncattrs()
      for att in ncatts:
         attval   = getattr(vbl0,att)
         setattr(self,att,attval)

      dims  = vbl0.shape

      ##################################################
      # some attributes that depend on rank
      if vbl0.ndim==1:
         vals  = vbl0[:]
      elif vbl0.ndim==2:
         vals  = vbl0[:,:]
      elif vbl0.ndim==3:
         if time_index is None:
            vals  = vbl0[:,:,:]
         elif dims[0]==1:
            vals  = vbl0[0,:,:]
            dims  = dims[1:]# drop time dimension
         else:
            vals  = vbl0[time_index,:,:]
            dims  = dims[1:]# drop time dimension
      ##################################################

      nc.close()
      self.dimensions   = dims
      self.values       = vals
      self.shape        = vals.shape
      self.ndim         = vals.ndim
      self.__getitem__  = self.values.__getitem__
      return
   #####################################################

########################################################
class nc_getinfo:

   #####################################################
   def __init__(self,ncfil,time_index=None):

      ##################################################
      self.filename  = ncfil
      if ncfil[0]=='/':
         self.basedir   = '/'
      else:
         import os
         self.basedir   = os.getcwd()+'/'

      ss = ncfil.split('/')
      for i in range(len(ss)-1):
         self.basedir   = self.basedir+'/'

      self.basename  = ss[-1].strip('.nc')
      ##################################################

      # added here manually
      # - TODO could possibly be determined
      #   from netcdf metadata though
      # - could also be an input
      self.reftime_sig  = 'start of forecast'


      # open the file
      self.lonname,self.latname  = lonlat_names(ncfil)
      nc                         = ncopen(ncfil)
      self.dimensions            = nc.dimensions.keys()

      # get global netcdf attributes
      class ncatts:
         def __init__(self,nc):
            for att in nc.ncattrs():
               attval   = getattr(nc,att)
               setattr(self,att,attval)
            return
         def list(self):
            return vars(self).keys()

      self.ncattrs   = ncatts(nc)

      dkeys = nc.dimensions.keys()
      vkeys = nc.variables.keys()
      Nkeys = len(vkeys)

      ########################################################
      # time info:
      time        = nc.variables['time']
      Nt          = len(time[:])
      reftime_u   = time[0] # hours since refpoint
      time_info   = time.units.split()
      #
      time_info[0]   = time_info[0].strip('s') # 1st word gives units
      if time_info[0]=='econd':
         time_info[0]   = 'second'
      #
      tu    = time.units
      if ('T' in tu) and ('Z' in tu):
         # using the T...Z format for time
         # eg hyc2proj (this is the standard)
         split1   = tu.split('T')
         ctime    = split1[1].split('Z')[0]
         cdate    = split1[0].split()[2]
      else:
         # eg WAMNSEA product from met.no
         split1   = tu.split()
         cdate    = split1[2]
         ctime    = split1[3]

      if '-' in cdate:
         # remove '-'
         # - otherwise assume YYYYMMDD format
         split2   = cdate.split('-')
         for loop_i in range(1,3):
            if (split2[loop_i])==1:
               split2[loop_i] = '0'+split2[loop_i]
         cdate = split2[0]+split2[1]+split2[2] # should be YYYYMMDD now

      if ':' in ctime:
         # remove ':'
         # - otherwise assume HHMMSS format
         split2   = ctime.split(':')
         for loop_i in range(0,3):
            if (split2[loop_i])==1:
               split2[loop_i] = '0'+split2[loop_i]
         ctime = split2[0]+split2[1]+split2[2] # should be HHMMSS now

      time_fmt = '%Y%m%d %H%M%S' # eg 19500101 120000
      refpoint = datetime.strptime(cdate+' '+ctime,time_fmt)
      #
      if time_info[0]=='second':
         self.reftime = refpoint+timedelta(seconds=reftime_u)
      elif time_info[0]=='hour':
         self.reftime = refpoint+timedelta(hours=reftime_u)
      elif time_info[0]=='day':
         self.reftime = refpoint+timedelta(reftime_u) #NB works for fraction of days also

      if time_info[0]=='second':
         # convert time units to hours for readability of the messages:
         self.timeunits  = 'hour'
         self.timevalues = [int((time[i]-time[0])/3600.) for i in range(Nt)]
      else:
         self.timeunits  = time_info[0]
         self.timevalues = [time[i]-time[0] for i in range(Nt)]

      self.number_of_time_records = Nt
      self.datetimes              = []
      for tval in self.timevalues:
         self.datetimes.append(self.timeval_to_datetime(tval))


      ########################################################

      ########################################################
      # grid info:
      self.lon0    = nc.variables[self.lonname][0,0]
      self.lat0    = nc.variables[self.latname][0,0]
      #
      self.shape   = nc.variables[self.lonname][:,:].shape
      ny,nx        = self.shape
      self.Npts_x  = nx # No of points in x dirn
      self.Npts_y  = ny # No of points in y dirn
      self.Npts    = nx*ny # Total no of points

      self.shape   = nc.variables[self.lonname] [:,:].shape
      ########################################################

      ########################################################
      # projection info:
      proj_list   = ['stereographic','projection_3'] # could also have mercator or regular lon-lat
      HAVE_PROJ   = 0   # if 0 assume HYCOM native grid
      for proj_name in proj_list: 
         if proj_name in vkeys:
            proj     = nc.variables[proj_name]
            att_list = proj.ncattrs()
            HAVE_PROJ   = 1
            break

      if HAVE_PROJ:
         # object with the netcdf attributes of projection variable
         # + some extra proj-dependent info 
         att_list_full  = [att_list[i] for i in range(len(att_list))]
         att_vals_full  = []
         for att in att_list:
            att_val  = proj.getncattr(att)
            att_vals_full.append(att_val)

         # specific to stereographic
         if proj_name=='stereographic':
            # add x,y resolution to ncinfo.proj_info
            att_list_full.extend(['x_resolution','y_resolution'])

            xx = nc.variables['x'][0:2]
            yy = nc.variables['y'][0:2]
            dx = xx[1]-xx[0]
            dy = yy[1]-yy[0]

            #convert to m
            xunits   = nc.variables['x'].units.split()
            fac      = 1.
            if len(xunits)==2:
               fac   = float(xunits[0])
               xunits.remove(xunits[0])

            if xunits[0]=='km':
               fac   = fac*1.e3
            #
            att_vals_full.extend([dx*fac,dy*fac])

         self.proj_info = proj_obj(att_list_full,att_vals_full)
      else:
         self.proj_info = []
      ########################################################
      
      ########################################################
      # variable list
      vlist = []
      bkeys = [proj_name,self.lonname,self.latname,'model_depth']
      bkeys.extend(dkeys)
      for key in vkeys:
         if key not in bkeys:
            vlist.append(key)

      self.variable_list   = vlist
      ########################################################

      nc.close()
      return
   ###########################################################

   ###########################################################
   def timeval_to_datetime(self,timeval):
      if self.timeunits=='second':
         dt = self.reftime +timedelta(seconds=timeval)
      elif self.timeunits=='hour':
         dt = self.reftime +timedelta(hours=timeval)
      elif self.timeunits=='day':
         dt = self.reftime +timedelta(timeval) #NB works for fraction of days also
      return dt
   ###########################################################

   ###########################################################
   def get_lonlat(self):

      nc    = ncopen(self.filename)
      lon   = nc.variables[self.lonname][:,:]
      lat   = nc.variables[self.latname][:,:]
      nc.close()

      return lon,lat
   ###########################################################

   ###########################################################
   def get_var(self,vname,time_index=None):

      # conc can have multiple names
      vlist    = self.variable_list
      cnames   = ['fice','ficem','icec']
      if vname in cnames:
         for vi in cnames:
            if vi in vlist:
               vname = vi

      # thcikness can have multiple names
      hnames   = ['hice','hicem','icetk']
      if vname in hnames:
         for vi in hnames:
            if vi in vlist:
               vname = vi

      vbl   = nc_get_var(self.filename,vname,time_index=time_index)

      return vbl
   ###########################################################


   ###########################################################
   def plot_var(self,var_opts,time_index=0,\
         pobj=None,bmap=None,HYCOMreg='TP4',\
         clim=None,add_cbar=True,clabel=None,show=True,\
         test_lonlats=None):

      from mpl_toolkits.basemap import Basemap, cm
      import fns_plotting as Fplt

      vname       = var_opts.name
      vec_opt     = var_opts.vec_opt
      conv_fac    = var_opts.conv_fac
      ice_mask    = var_opts.ice_mask
      wave_mask   = var_opts.wave_mask
      dir_from    = var_opts.dir_from

      if pobj is None:
         from matplotlib import pyplot as plt
         pobj  = plot_object()

      fig,ax,cbar = pobj.get()

      if bmap is None:
         # make basemap
         bmap  = Fplt.start_HYCOM_map(HYCOMreg,cres='i')

      if clim is not None:
         vmin,vmax   = clim
      else:
         vmin  = None
         vmax  = None

      lon,lat  = self.get_lonlat()
      vbl      = self.get_var(vname,time_index=time_index)
      mask     = vbl.values.mask

      ################################################################## 
      # add ice or wave masks
      if ice_mask and wave_mask:
         fice  = self.get_var('fice',time_index=time_index)
         mask1 = 1-np.logical_and(1-mask,fice[:,:]>.01) #0 if finite,non-low conc
         #
         Hs    = self.get_var('swh',time_index=time_index)
         mask2 = 1-np.logical_and(1-mask,Hs[:,:]>.01) #0 if finite,non-low waves
         #
         mask  = np.logical_or(mask1,mask2)

      elif ice_mask:
         fice  = self.get_var('fice',time_index=time_index)
         mask  = 1-np.logical_and(1-mask,fice[:,:]>.01) #0 if finite,non-low conc

      elif wave_mask:
         Hs    = self.get_var('swh',time_index=time_index)
         mask  = 1-np.logical_and(1-mask,Hs[:,:]>.01) #0 if finite,non-low waves
      ################################################################## 


      ################################################################## 
      if vec_opt==0:

         # just plot scalar
         U     = None # no quiver plot
         Marr  = vbl.values.data
         Marr  = np.ma.array(conv_fac*Marr,mask=mask) #masked array


      elif vec_opt==1:

         # plot vector magnitude
         U  = None # no quiver plot
         if vname[0]=='u':
            vname2   = 'v'+vname[1:]
         elif vname[:4]=='taux':
            vname2   = 'tauy'+vname[4:]

         vbl2     = self.get_var(vname2,time_index=time_index)
         Marr  = np.sqrt(vbl.values.data*vbl.values.data\
                         +vbl2.values.data*vbl2.values.data)
         Marr  = np.ma.array(conv_fac*Marr,mask=mask) #masked array

      elif vec_opt==2:

         # plot vector magnitude + direction (unit vectors)
         if vname[0]=='u':
            vname2   = 'v'+vname[1:]
         elif vname[:4]=='taux':
            vname2   = 'tauy'+vname[4:]

         vbl2  = self.get_var(vname2,time_index=time_index)
         U     = vbl.values.data
         V     = vbl2.values.data

         # speed
         spd   = np.hypot(U,V)
         Marr  = np.ma.array(conv_fac*spd,mask=mask) #masked array

         # rotate vectors
         U,V   = bmap.rotate_vector(U,V,lon,lat)

         #unit vectors
         U     = np.ma.array(U/spd,mask=mask)
         V     = np.ma.array(V/spd,mask=mask)

      elif vec_opt==3:

         # plot vector direction only
         # (no pcolor, but vector length is proportional to magnitude)
         Marr  = None

         if vname[0]=='u':
            vname2   = 'v'+vname[1:]
         elif vname[:4]=='taux':
            vname2   = 'tauy'+vname[4:]

         vbl2  = self.get_var(vname2,time_index=time_index)
         U     = conv_fac*vbl.values.data
         V     = conv_fac*vbl2.values.data

         # speed
         spd   = np.hypot(U,V)
         avg   = np.mean(np.ma.array(spd,mask=mask))
         print('avg speed: '+str(avg))

         # rotate vectors
         U,V   = bmap.rotate_vector(U,V,lon,lat)

         # scale by the average speed
         # TODO: add key
         U  = np.ma.array(U/avg,mask=mask)
         V  = np.ma.array(V/avg,mask=mask)

      elif vec_opt==4:

         # plot direction as scalar
         U  = None

         if vname[0]=='u':
            vname2   = 'v'+vname[1:]
         elif vname[:4]=='taux':
            vname2   = 'tauy'+vname[4:]

         vbl2  = self.get_var(vname2,time_index=time_index)
         dir   = 180/np.pi*np.arctan2(vbl2.values.data,vbl.values.data)#dir-to in degrees (<180,>-180)
         dir   = 90-dir #north is 0,angle clockwise
         if dir_from:
            # direction-from
            dir[dir>0]  = dir[dir>0]-360
            Marr        = np.ma.array(dir+180,mask=np.logical_or(mask,1-np.isfinite(dir)))
         else:
            # direction-to
            dir[dir>180]   = dir[dir>180]-360
            Marr           = np.ma.array(dir,mask=np.logical_or(mask,1-np.isfinite(dir)))

      elif vec_opt==5:
         #vbl is a direction - convert to vector
         Marr  = None
         dir   = 90-vbl.values.data
         if dir_from:
            dir   = np.pi/180*(dir+180)
         else:
            dir   = np.pi/180*dir

         # rotate unit vectors
         U,V   = bmap.rotate_vector(np.cos(dir),np.sin(dir),lon,lat)
         U     = np.ma.array(U,mask=mask)
         V     = np.ma.array(V,mask=mask)
      ################################################################## 


      ################################################################## 
      # pcolor plot
      if Marr is not None:
         PC = bmap.pcolor(lon,lat,Marr,latlon=True,ax=ax,vmin=vmin,vmax=vmax)

         if add_cbar:

            if cbar is None:
               cbar  = fig.colorbar(PC)
            else:
               cbar  = fig.colorbar(PC,cax=cbar.ax)

            pobj  = plot_object(fig=fig,ax=ax,cbar=cbar,axpos=pobj.axpos)
            if clabel is not None:
               cbar.set_label(clabel,rotation=270,labelpad=20,fontsize=16)
      ################################################################## 


      ################################################################## 
      if pobj.axpos is not None:
         # try to make sure axes don't move round
         pobj.ax.set_position(pobj.axpos)
      ################################################################## 


      ################################################################## 
      # quiver plot
      if U is not None:
         dens  = 10   # density of arrows
         scale = 50
         QP    = bmap.quiver(lon[::dens,::dens],lat[::dens,::dens],\
                              U[::dens,::dens],V[::dens,::dens],\
                              latlon=True,scale=scale,ax=ax)

      if test_lonlats is not None:
         for lont,latt in test_lonlats:
            bmap.plot(lont,latt,'^m',markersize=5,latlon=True,ax=ax)

      Fplt.finish_map(bmap,ax=ax)
      if show:
         fig.show()

      return pobj,bmap
   ###########################################################

   ###########################################################
   def plot_var_pair(self,var_opts1,var_opts2,pobj=None,bmap=None,**kwargs):

      # ====================================================================
      # check options
      check_pair(var_opts1,var_opts2)
      # ====================================================================

      pobj,bmap   = self.plot_var(var_opts1,pobj=pobj,bmap=bmap,**kwargs)
      self.plot_var(var_opts2,pobj=pobj,bmap=bmap,**kwargs)

      return pobj,bmap
   ###########################################################

   ###########################################################
   def make_png(self,var_opts,pobj=None,bmap=None,figdir='.',time_index=0,date_label=True,**kwargs):

      from matplotlib import pyplot as plt

      new_fig  = (pobj is None)
      if new_fig:
         pobj  = plot_object()

      pobj,bmap   = self.plot_var(var_opts,pobj=pobj,bmap=bmap,time_index=time_index,**kwargs)

      dtmo     = self.datetimes[time_index]
      datestr  = dtmo.strftime('%Y%m%dT%H%M%SZ')

      if date_label:
         tlabel   = dtmo.strftime('%d %b %Y %H:%M')
         pobj.ax.annotate(tlabel,xy=(0.05,.925),xycoords='axes fraction',fontsize=18)

      if pobj.axpos is not None:
         # try to make sure axes don't move round
         pobj.ax.set_position(pobj.axpos)

      vname    = var_opts.name
      Fname    = vname
      vec_opt  = var_opts.vec_opt

      if vec_opt==1:
         #magnitude only
         if vname in ['u','usurf']:
            Fname = 'surf_speed'
         elif 'u' in vname:
            Fname = vname.strip('u')+'_speed'
         elif 'taux' in vname:
            Fname = vname.strip('taux')+'_stress_magnitude'

      elif vec_opt==2 or vec_opt==3:
         #quiver plots on top of magnitude or by itself
         if vname in ['u','usurf']:
            Fname = 'surf_vel'
         elif 'u' in vname:
            Fname = vname.strip('u')+'_vel'
         elif 'taux' in vname:
            Fname = vname.strip('taux')+'_stress'

      elif vec_opt==4:
         #direction as scalar
         if vname in ['u','usurf']:
            Fname = 'surf_current_dirn'
         elif 'u' in vname:
            Fname = vname.strip('u')+'_vel_dirn'
         elif 'taux' in vname:
            Fname = vname.strip('taux')+'_stress_dirn'

      elif vec_opt==5:
         #direction -> vector
         if vname in ['u','usurf']:
            Fname = 'surf_current_dirn'
         elif 'u' in vname:
            Fname = vname.strip('u')+'_vel_dirn'
         elif 'taux' in vname:
            Fname = vname.strip('taux')+'_stress_dirn'

      Fname    = Fname.strip('_')
      figname  = figdir+'/'+self.basename+'_'+Fname+datestr+'.png'

      print('Saving to '+figname) 
      pobj.fig.savefig(figname)

      if new_fig:
         pobj.ax.cla()
         pobj.fig.clear()
         plt.close(pobj.fig)

      return pobj,bmap
   ###########################################################


   ###########################################################
   def make_png_pair(self,var_opts1,var_opts2,time_index=0,\
         pobj=None,bmap=None,figdir='.',date_label=True,**kwargs):

      from matplotlib import pyplot as plt

      # ====================================================================
      # check options
      check_pair(var_opts1,var_opts2)
      # ====================================================================

      new_fig  = (pobj is None)
      if new_fig:
         pobj  = plot_object()

      pobj,bmap   = self.plot_var_pair(var_opts1,var_opts2,time_index=time_index,\
                     pobj=pobj,bmap=bmap,**kwargs)
      fig,ax,cbar = pobj.get()

      dtmo     = self.datetimes[time_index]
      datestr  = dtmo.strftime('%Y%m%dT%H%M%SZ')

      if date_label:
         tlabel   = dtmo.strftime('%d %b %Y %H:%M')
         ax.annotate(tlabel,xy=(0.05,.925),xycoords='axes fraction',fontsize=18)

      # set name with 1st variable only
      Fname    = var_opts1.name
      vec_opt  = var_opts1.vec_opt
      if vec_opt==1:
         #magnitude only
         if vname in ['u','usurf']:
            Fname = 'surf_speed'
         elif 'u' in vname:
            Fname = vname.strip('u')+'_speed'
         elif 'taux' in vname:
            Fname = vname.strip('taux')+'_stress_magnitude'

      elif vec_opt==4:
         #direction as scalar
         if vname in ['u','usurf']:
            Fname = 'surf_current_dirn'
         elif 'u' in vname:
            Fname = vname.strip('u')+'_vel_dirn'
         elif 'taux' in vname:
            Fname = vname.strip('taux')+'_stress_dirn'

      Fname    = Fname.strip('_')
      figname  = figdir+'/'+self.basename+'_'+Fname+datestr+'.png'

      print('Saving to '+figname) 
      fig.savefig(figname)

      if new_fig:
         ax.cla()
         fig.clear()
         plt.close(fig)

      return pobj,bmap
   ###########################################################


   ###########################################################
   def make_png_all(self,var_opts,HYCOMreg='TP4',figdir='.',**kwargs):

      from matplotlib import pyplot as plt
      import fns_plotting as Fplt

      pobj        = plot_object()
      fig,ax,cbar = pobj.get()

      bmap  = Fplt.start_HYCOM_map(HYCOMreg,cres='i')

      N  = len(self.timevalues)
      for i in range(N):

         print('\n'+str(i)+' records done out of '+str(N))

         pobj,bmap   = self.make_png(var_opts,\
                           bmap=bmap,time_index=i,\
                           figdir=figdir,show=False,**kwargs)

         ax.cla()
         if pobj.cbar is not None:
            pobj.cbar.ax.clear()   # cbar.ax.clear()

      plt.close(fig)
      return
   ###########################################################


   ###########################################################
   def make_png_pair_all(self,var_opts1,var_opts2,HYCOMreg='TP4',figdir='.',**kwargs):

      from matplotlib import pyplot as plt
      import fns_plotting as Fplt

      # ====================================================================
      # check options
      check_pair(var_opts1,var_opts2)
      # ====================================================================

      pobj        = plot_object()
      fig,ax,cbar = pobj.get()
      bmap        = Fplt.start_HYCOM_map(HYCOMreg,cres='i')

      N  = len(self.timevalues)
      for i in range(N):

         print('\n'+str(i)+' records done out of '+str(N))

         pobj,bmap   = self.make_png_pair(var_opts1,var_opts2,\
                        pobj=pobj,bmap=bmap,time_index=i,\
                        figdir=figdir,show=False,**kwargs)

         if i==0:
            # Fix axes position to stop it moving round
            pobj  = pobj.renew(axpos=pobj.ax.get_position())

         ax.cla()
         if pobj.cbar is not None:
            pobj.cbar.ax.clear()   # cbar.ax.clear()

      plt.close(fig)
      return
   ###########################################################

###########################################################

###########################################################
def print_grib_messages(grb2fil,N=None):

   import pygrib
   from ncepgrib2 import Grib2Encode as g2e
   from ncepgrib2 import Grib2Decode as g2d

   gr       = pygrib.open(grb2fil)

   if N is None:
      # print all messages:
      grbmsgs  = gr.read()
   else:
      # print 1st N messages:
      grbmsgs  = gr.read(N)

   for msg in grbmsgs:
      print(msg)
      print('\n')
      grb   = g2d(msg.tostring(),gribmsg=True)
      print(grb)
      print('\n')

   gr.close()
###########################################################

##############################################################
def get_array_from_binary(fid,nx,ny,fmt_size=4,order='fortran'):
   # routine to get the array from the .a (binary) file
   # * fmt_size = size in bytes of each entry)
   #   > default = 4 (real*4/single precision)

   import struct

   recs     = nx*ny
   rec_size = recs*fmt_size
   #
   data  = fid.read(rec_size)
   if fmt_size==4:
      fmt_py   = 'f' # python string for single
   else:
      fmt_py   = 'd' # python string for double

   fld   = struct.unpack(recs*fmt_py,data)
   fld   = np.array(fld)

   if order!='fortran':
      fld   = fld.reshape((nx,ny))  # array order follows python/c convention
                                    # (index increases across array)
   else:
      fld   = fld.reshape((ny,nx)).transpose()  # need to transpose because of differences between
                                                # python/c and fortran/matlab 

   return fld
##############################################################

##############################################################
def get_array_from_HYCOM_binary(afile,recno,dims=None,grid_dir='.'):
   # routine to get the array from the .a (binary) file
   # * recno=1 is 1st record 
   # * fmt_size = size in bytes of each entry)
   #   > default = 4 (real*4/single precision)

   import struct

   ######################################################################
   # get size of grid
   if dims is None:
      if 'regional.grid' in afile:
         # afile is a grid file
         # - check .b file for size of grid
         bfile = afile[:-2]+'.b'
      else:
         # check regional.grid.b file for size of grid
         bfile = grid_dir+'/regional.grid.b'
         if os.path.exists(bfile):
            sys.exit('Grid file not present: '+bfile)

      bid   = open(bfile,'r')
      nx    = int( bid.readline().split()[0] )
      ny    = int( bid.readline().split()[0] )
      bid.close()
   else:
      nx = dims[0]
      ny = dims[1]
   ######################################################################

   ######################################################################
   # set record size, skip to record number
   fmt_size = 4      # HYCOM files are single precision
   if fmt_size==4:
      fmt_py   = 'f' # python string for single
   else:
      fmt_py   = 'd' # python string for double

   n0       = 4096   # HYCOM stores records in multiples of 4096
   Nhyc     = (1+(nx*ny)/n0)*n0
   rec_size = Nhyc*fmt_size
   #
   aid   = open(afile,'rb')
   for n in range(1,recno):
      aid.seek(rec_size,1) # seek in bytes (1: reference is current position)
   ######################################################################

   # read data and close file
   data  = aid.read(rec_size)
   aid.close()

   # rearrange into correctly sized array
   fld   = struct.unpack('>'+Nhyc*fmt_py,data) # NB BIG-ENDIAN so need '>'
   fld   = np.array(fld[0:nx*ny]) # select the 1st nx,ny - rest of the Nhyc record is rubbish
   fld   = fld.reshape((ny,nx)).transpose()  # need to transpose because of differences between
                                             # python/c and fortran/matlab 

   land_thresh          = 1.e30# on land 1.2677e30 
   fld[fld>land_thresh] = np.nan

   return fld
##############################################################

##############################################################
def get_record_numbers_HYCOM(bfile):
   # routine to get the array from the .a (binary) file
   # * fmt_size = size in bytes of each entry)
   #   > default = 4 (real*4/single precision)


   bid   = open(bfile,'r')
   word  = bid.readline().split()[0] # 1st word in line 
   while word!='field':
      word  = bid.readline().split()[0] # 1st word in line 

   # have found table title
   n     = 0
   lut   = {}
   lin   = bid.readline()
   EOF   = (lin=='')
   while not EOF:
      n     = n+1
      word  = lin.split()[0] # 1st word in line 
      lut.update({word:n})
      #
      lin   = bid.readline()
      EOF   = (lin=='')

   bid.close()

   if 'ficem' in lut.keys():
      lut.update({'fice':lut['ficem']})

   if 'hicem' in lut.keys():
      lut.update({'hice':lut['hicem']})

   return lut
   ######################################################################

######################################################################
class HYCOM_binary_info:
   def __init__(self,fname,gridpath='.'):

      ss = fname.split('.')
      if ss[-1]=='a':
         self.afile = fname
         self.bfile = fname[:-1]+'b'
      elif ss[-1]=='b':
         self.bfile = fname
         self.afile = fname[:-1]+'a'
      else:
         raise ValueError('HYCOM binaries should have extensions .a or .b')

      self.record_numbers  = get_record_numbers_HYCOM(self.bfile)
      self.variables       = self.record_numbers.keys()

      #######################################################################
      # get grid size
      bid   = open(gridpath+'/regional.grid.b','r')
      line  = bid.readline()
      while 'idm' not in line:
         line  = bid.readline()
      nx    = int( line.split()[0] )

      line  = bid.readline()
      while 'jdm' not in line:
         line  = bid.readline()
      ny    = int( line.split()[0] )
      bid.close()

      self.dims   = [nx,ny]
      self.Nx     = nx
      self.Ny     = ny
      #######################################################################

      #path to regional.grid.[ab] files
      self.gridpath = gridpath

      return # __init__
   #######################################################################

   #######################################################################
   def get_grid(self):

      gfil  = self.gridpath+'/regional.grid.a'
      dfil  = self.gridpath+'/regional.depth.a'
      #
      plon  = get_array_from_HYCOM_binary(gfil,1,\
                     dims=self.dims,grid_dir=self.gridpath)
      #
      plat     = get_array_from_HYCOM_binary(gfil,2,\
                     dims=self.dims,grid_dir=self.gridpath)
      depths   = get_array_from_HYCOM_binary(dfil,1,\
                     dims=self.dims,grid_dir=self.gridpath)

      return plon,plat,depths
   #######################################################################

   #######################################################################
   def get_var(self,vname):

      if vname not in self.variables:
         raise ValueError('Variable '+vname+'not in '+afile)

      recno = self.record_numbers[vname]
      vbl   = get_array_from_HYCOM_binary(self.afile,recno,\
                  dims=self.dims)
      return vbl
   #######################################################################

   #######################################################################
   def plot_var(self,vname,pobj=None,bmap=None,HYCOMreg='TP4',\
         clim=None,show=True,vec_opt=0,conv_fac=1,ice_mask=False):

      from mpl_toolkits.basemap import Basemap
      from matplotlib import cm
      import fns_plotting as Fplt

      if vname not in self.variables:
         raise ValueError('Variable '+vname+'not in '+self.afile)

      if pobj is not None:
         fig,ax   = pobj
      else:
         from matplotlib import pyplot as plt
         fig   = plt.figure()
         ax    = fig.add_subplot(1,1,1)

      lon,lat  = self.get_grid()[:2]
      if bmap is None:
         # make basemap
         bmap  = Fplt.start_HYCOM_map(HYCOMreg,cres='i')
      else:
         lonc     = np.mean(lon)
         latc     = np.mean(lat)
         #
         latmin   = np.min(lat)
         latmax   = np.max(lat)
         width    = 1.2*111.e3*(latmax-latmin)
         height   = width

         bmap = Basemap(lon_0=lonc,lat_0=latc,lat_ts=latc,\
                        projection='stere',resolution='i',\
                        width=width,height=height)

      recno    = self.record_numbers[vname]
      vbl      = get_array_from_HYCOM_binary(self.afile,recno,\
                     dims=self.dims)

      if ice_mask:
         recno    = self.record_numbers['ficem']
         fice     = get_array_from_HYCOM_binary(self.afile,recno,\
                     dims=self.dims)
         mask     = 1-np.logical_and(np.isfinite(vbl),fice>.01)
      else:
         mask  = 1-np.isfinite(vbl)

      ###############################################################
      if vec_opt==1:
         # vector magnitude of vel or stress

         if vname[0]=='u':
            vname2   = 'v'+vname[1:]
            recno2   = self.record_numbers[vname]
         elif vname[:4]=='taux':
            vname2   = 'tauy'+vname[4:]
            recno2   = self.record_numbers[vname]

         vbl2  = get_array_from_HYCOM_binary(self.afile,recno2,\
                     dims=self.dims)
         Marr  = np.hypot(vbl,vbl2)
         Marr  = np.ma.array(conv_fac*Marr,mask=mask)
      else:
         Marr  = np.ma.array(conv_fac*vbl,mask=mask)

      ###############################################################

      vmin  = Marr.min()
      vmax  = Marr.max()

      print(' ')
      print('Plotting '+vname)
      print('Min: '+str(vmin))
      print('Max: '+str(vmax))

      if clim is not None:
         # manual value range
         Vmin,Vmax   = clim
         print(' ')
      else:
         Vmin  = None
         Vmax  = None
      #    # use histogram
      #    p0    = 10
      #    p1    = 90
      #    Vmin  = np.percentile(vfin,p0)
      #    Vmax  = np.percentile(vfin,p1)
      #    print(str(p0) +'-th percentile: '+str(Vmin))
      #    print(str(p1) +'-th percentile: '+str(Vmax))
      #    print(' ')
      cmap    = cm.jet
      # cmap.set_bad(color='w')

      PC = bmap.pcolor(lon,lat,Marr,latlon=True,ax=ax,vmin=Vmin,vmax=Vmax,cmap=cmap)
      fig.colorbar(PC)

      Fplt.finish_map(bmap)
      if show:
         fig.show()

      return fig,ax,bmap
   #######################################################################

#######################################################################

######################################################################