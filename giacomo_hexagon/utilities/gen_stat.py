############################################################################
# Calling in all the needed packages
from netCDF4 import Dataset
import sys,os
import time
import datetime
import glob
import numpy as np
import subprocess
import shutil
import matplotlib
#NOTE to be used only on servers (i.e. Hexagon)
#matplotlib.use('Agg')
import matplotlib.lines as mlines
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.font_manager import FontProperties
from matplotlib import rc
from matplotlib import pyplot as plt 
from mpl_toolkits.basemap import Basemap, cm
from mpl_toolkits.axes_grid1.inset_locator import zoomed_inset_axes, mark_inset
from skimage import measure as msr
from skimage import morphology as morph
from scipy.interpolate import griddata as grd
from operator import itemgetter as itg

sys.path.append('../../py_funs')
import mod_reading as Mrdg
import Laplace_eqn_solution_2tw as Leqs
############################################################################

############################################################################
# Muting error coming from invalid values of binary_mod and binary_diff
np.seterr(invalid='ignore')
############################################################################

############################################################################
# Functions and classes
############################################################################
def binary_mod(data1,thresh1):
    odata = np.copy(data2)
    odata[odata<thresh1] = 0
    odata[odata>=thresh1] = 1 
    thenans = np.isnan(odata)
    odata[thenans] = 0
    return(odata)
############################################################################
def open_close(self):
    kernel = np.ones((3,3),np.uint8)
    DN_op = np.copy(DN)
    DN_cl = np.copy(DN)
    DN_op = cv2.morphologyEx(DN_op,cv2.MORPH_OPEN,kernel)
    DN_cl = cv2.morphologyEx(DN_cl,cv2.MORPH_CLOSE,kernel)
    return(DN_op,DN_cl)
############################################################################
# read in and prepare every file for polygon detection
class reader:
    def __init__(self,name,dadate,basemap):
        self.year = dadate[:4]
        self.month = dadate[4:6]
        self.day = dadate[6:8]
        gigio = datetime.datetime(int(float(self.year)),int(float(self.month)),int(float(self.day)),0,0)
        gigio = gigio.strftime('%j')
        gigio = int(float(gigio))
        self.julian = gigio - 1
        self.filname = name+'_'+dadate
        if name == 'Osisaf':
            self.lonO,self.latO,self.X,self.Y,self.Z = self._read_osi_(dadate,basemap) 
            return
        elif name == 'Model':
            self.lonM,self.latM,self.X,self.Y,self.ZC,self.ZD = self._read_mdl_(dadate,basemap)
            return
        elif name == 'Aari':
            self.ad = self._read_aari_(dadate,basemap)
    
    def _read_osi_(self,dadate,basemap):
        day = self.day
        month = self.month
        year = self.year
        # Read in OSI_SAF file
        #outdir = '/work/shared/nersc/msc/OSI-SAF/'+str(year)+'_nh_polstere/'
        outdir = './tmp/OSI'
        ncfil = outdir+'/ice_conc_nh_polstere-100_multi_'+dadate+'1200.nc'
        clon = 'lon'
        clat = 'lat'
        cconc = 'ice_conc'
        lonO = Mrdg.nc_get_var(ncfil,clon) # lon[:,:] is a numpy array
        latO = Mrdg.nc_get_var(ncfil,clat) # lat[:,:] is a numpy array
        conc = Mrdg.nc_get_var(ncfil,cconc,time_index=0)
        xc = Mrdg.nc_get_var(ncfil,'xc')
        yc = Mrdg.nc_get_var(ncfil,'yc')
        X2,Y2 = basemap(lonO[:,:],latO[:,:],inverse=False)
        XO = np.copy(X2)
        YO = np.copy(Y2)
        Z2 = conc[:,:].data
        mask2 = conc[:,:].mask
        Z2[mask2] = np.NaN
        ZO = Z2/100
        return(lonO,latO,XO,YO,ZO) 
   
    def _read_mdl_(self,dadate,basemap):
    
        #TODO
        # work on the binary reader, for now *.nc will be used 
    
        # NetCDF reader 
        day = self.day
        month = self.month
        year = self.year
        # Read TP4arch_wav
        #outdir = '/work/timill/RealTime_Models/results/TP4a0.12/wavesice/work/'+dadate+'/netcdf/'
        outdir = './tmp/MDL'
        ncfil = outdir+'/TP4archv_wav_start'+str(dadate)+'_000000Z_dump'+str(dadate)+'_120000Z.nc'
        slon = 'longitude'
        slat = 'latitude'
        sconc = 'fice'
        sdmax = 'dmax'
        lonM = Mrdg.nc_get_var(ncfil,slon) # lon[:,:] is a numpy array
        latM = Mrdg.nc_get_var(ncfil,slat) # lat[:,:] is a numpy array
        conc = Mrdg.nc_get_var(ncfil,sconc,time_index=0)
        dmax = Mrdg.nc_get_var(ncfil,sdmax,time_index=0)
        X,Y = basemap(lonM[:,:],latM[:,:],inverse=False)
        ZD = dmax[:,:].data
        mask = dmax[:,:].mask
        ZD[mask] = np.NaN
        ZC = conc[:,:].data
        mask = conc[:,:].mask
        ZC[mask] = np.NaN
        
        return(lonM,latM,X,Y,ZC,ZD)

############################################################################
# This class will find SDA polygons (single dataset analysis).
# NOTE output is a polygon between chosen thresholds (CLOSED & MAPPED)
class SDA_poly:
    def __init__(self,X1,Y1,Z1):
        ZM = Z1
        if len(ZM[ZM>1]) > 0:
            # NOTE Here FSD threshold is inserted
            self.DN,self.B1,self.B2,oDN,uDN = self.binary_diff(ZM,.01,299.99)
        else:
            # NOTE Here IC threshold is inserted
            self.DN,self.B1,self.B2,oDN,uDN = self.binary_diff(ZM,.15,.8)
        self.over,self.under = self.poly_maker(self.DN)
        self.DN = self.mapper(self.DN,ZM)
        return
    
    def binary_diff(self,data1,thresh1,thresh2):
        # binary difference method
        def closing(DN):
            # NOTE apply closing to avoid small polynias and clean up a little
            kernel = np.ones((3,3),np.uint8)
            DN_cl = morph.closing(DN,kernel)
            return(DN_cl)
        
        ndata1 = np.copy(data1)
        ndata2 = np.copy(data1)
#        ndata1[ndata1<thresh1] = 0
#        ndata2[ndata2<thresh2] = 0
#        ndata1[ndata1>=thresh1] = 1
#        ndata2[ndata2>=thresh2] = 1
        ndata1[ndata1>=thresh1] = 1
        ndata1[ndata1<thresh1] = 2
        ndata2[ndata2<thresh2] = 0
        ndata2[ndata2>=thresh2] = 3
        ddata = ndata2 - ndata1
        thenans = np.isnan(ddata)
        ddata[thenans] = 0
        over_data = np.copy(ddata)
        under_data = np.copy(ddata)
        over_data[over_data==-1] = 0
        under_data[under_data==1] = 0
        under_data = abs(under_data)
        o_data = closing(over_data)
        u_data = closing(under_data)
        o_data[u_data==1] = -1
        ddata = np.copy(o_data)
        return(ddata,ndata1,ndata2,o_data,u_data)
    
    def poly_maker(self,ddata):
        # finding contours from the difference data map
        over = msr.find_contours(ddata,.5)
        over = sorted(over, key=len)
        over = over[::-1]
        under = msr.find_contours(ddata,-.5)
        under = sorted(under, key=len)
        under = under[::-1]
        return(over,under)
    
    def mapper(self,DIFF,BIN):
        # getting back the terrain lost during binary_mod (for contour finding reasons)
        DN = DIFF
        ZO = BIN
        thenan = np.isnan(ZO)
        DN[thenan] = None
        return(DN)

############################################################################
# This class will find AOD polygons for 2 sets with different grid.
# NOTE the basemap used in the reprojector is thought for OSISAF database but 
# may fit any stereographical map, the reprojection should be fine as well.
class AOD_poly:
    def __init__(self,X1,Y1,Z1,X2,Y2,Z2):
        ZM = self._reprojector_(X1,Y1,Z1,X2,Y2,Z2)
        ZO = Z2
        # NOTE THRESHOLD FOR ICE EDGE VALIDATION
        self.DN,self.B1,self.B2,oDN,uDN = self.binary_diff(ZM,ZO,.15)
        self.over,self.under = self.poly_maker(self.DN)
        self.DN = self.mapper(self.DN,ZM,ZO)
        return
    
    def _reprojector_(self,X1,Y1,Z1,X2,Y2,Z2):
        # TODO this has to be good even for Jiping's files

        # low quality map
        self.lqm = Basemap(width=7600000,height=11200000,resolution='l',rsphere=(6378273,6356889.44891),\
            projection='stere',lat_ts=70,lat_0=90,lon_0=-45)
        # better quality map
        self.hqm = Basemap(width=7600000,height=11200000,resolution='i',rsphere=(6378273,6356889.44891),\
            projection='stere',lat_ts=70,lat_0=90,lon_0=-45)
        
        # getting ready for reprojection
        X3 = X1.reshape(X1.size)
        Y3 = Y1.reshape(Y1.size)
        Z3 = Z1.reshape(Z1.size)
        C = [X3,Y3]
        C = np.array(C)
        C = C.T
        
        # Interpolation can be done with other methods ('nearest','linear','cubic'<--doesn't work for our data)
        ZN = grd(C,Z3,(X2,Y2),method='nearest')
        
        return(ZN)
    
    def binary_diff(self,data1,data2,thresh):
        # NOTE data1 is MODEL, data2 is OSISAF
        # This gives the difference as:
        # -1 = OSI PRES, MDL MISS -> UNDERESTIMATION
        #  0 = OSI PRES, MDL PRES -> HIT
        # +1 = OSI MISS, MDL PRES -> OVERESTIMATION
        def closing(DN):
            # apply closing to avoid small polynias and clean up a little
            kernel = np.ones((3,3),np.uint8)
            DN_cl = morph.closing(DN,kernel)
            return(DN_cl)
        
        # NOTE outputs are difference, overpredictions and underpredictions (CLOSED & MAPPED)
        
        # generating the binary file, get the difference, divide into overprediction and
        # underprediction, apply the closing on both and finally re-map the land
        ndata1 = np.copy(data1)
        ndata2 = np.copy(data2)
#        ndata1[ndata1<thresh] = 0
#        ndata2[ndata2<thresh] = 0
#        ndata1[ndata1>=thresh] = 1  
#        ndata2[ndata2>=thresh] = 1  
        ndata1[ndata1>=thresh] = 1
        ndata1[ndata1<thresh] = 2
        ndata2[ndata2<thresh] = 0
        ndata2[ndata2>=thresh] = 3
        ddata = ndata2 - ndata1
        thenans = np.isnan(ddata)
        ddata[thenans] = 0
        over_data = np.copy(ddata)
        under_data = np.copy(ddata)
        over_data[over_data==-1] = 0
        under_data[under_data==1] = 0
        under_data = abs(under_data)
        o_data = closing(over_data)
        u_data = closing(under_data)
        o_data[u_data==1] = -1
        ddata = np.copy(o_data)
        return(ddata,ndata1,ndata2,o_data,u_data)
    
    def poly_maker(self,ddata):
        # finding contours from the difference data map
        over = msr.find_contours(ddata,.5)
        over = sorted(over, key=len)
        over = over[::-1]
        under = msr.find_contours(ddata,-.5)
        under = sorted(under, key=len)
        under = under[::-1]
        return(over,under)
    
    def mapper(self,DIFF,INS,OUT):
        # getting back the terrain lost during binary_mod (for contour finding reasons)
        DN = DIFF
        ZO = OUT
        ZI = INS
        thenan = np.isnan(ZO)
        thenan2 = np.isnan(ZI)
        DN[thenan] = None
        DN[thenan2] = None
        return(DN)

############################################################################
class daily_stat:
# Get's regional and whole arctic  daily stats (Underestimation, Overestimation, Bias, Perimeters)
    
    def __init__(self,X,Y,DN,ZM,ZO):
        X = self.X
        Y = self.Y
        DN = self.DN
        ZM = self.ZM
        ZO = self.ZO
        return

    def gen_region_stats(self,X,Y,DN,ZM,ZO):
        DN = self.DN
        lon,lat = basemap(X[:,:],Y[:,:],inverse=True)

        # Regional Lists
        bar_lst = []
        gre_lst = []
        lab_lst = []
        ncb_lst = []
        les_lst = []

        # Going through every point to assess status and location
        for i in range(len(DN[:,0])):
            for j in range(len(DN[0,:]):
                ptlon = lon[i,j]

        # defining the region
        if ptlon < 100 and ptlon > 340:
            region = 'Barents_Kara_sea'
            if DN[i,j] == 2:
                bar_lst.append([1,0,0,0,0]
            elif DN[i,j] == 1:
                bar_lst.append([0,1,0,0,0]
            elif DN[i,j] == -1:
                bar_lst.append([0,0,1,0,0]
            elif DN[i,j] == -2:
                bar_lst.append([0,0,0,1,0]
            elif DN[i,j] == 0:
                bar_lst.append([0,0,0,0,1]
        elif ptlon < 340 and ptlon > 315:
            region = 'Greenland_sea'
            if DN[i,j] == 2:
                gre_lst.append([1,0,0,0,0]
            elif DN[i,j] == 1:
                gre_lst.append([0,1,0,0,0]
            elif DN[i,j] == -1:
                gre_lst.append([0,0,1,0,0]
            elif DN[i,j] == -2:
                gre_lst.append([0,0,0,1,0]
            elif DN[i,j] == 0:
                gre_lst.append([0,0,0,0,1]
        elif ptlon < 315 and ptlon > 290:
            region = 'Labrador_sea'
            if DN[i,j] == 2:
                lab_lst.append([1,0,0,0,0]
            elif DN[i,j] == 1:
                lab_lst.append([0,1,0,0,0]
            elif DN[i,j] == -1:
                lab_lst.append([0,0,1,0,0]
            elif DN[i,j] == -2:
                lab_lst.append([0,0,0,1,0]
            elif DN[i,j] == 0:
                lab_lst.append([0,0,0,0,1]
        elif ptlon < 290 and ptlon > 190:
            region = 'North_Canada_Beaufort_sea'
            if DN[i,j] == 2:
                ncb_lst.append([1,0,0,0,0]
            elif DN[i,j] == 1:
                ncb_lst.append([0,1,0,0,0]
            elif DN[i,j] == -1:
                ncb_lst.append([0,0,1,0,0]
            elif DN[i,j] == -2:
                ncb_lst.append([0,0,0,1,0]
            elif DN[i,j] == 0:
                ncb_lst.append([0,0,0,0,1]
        elif ptlon < 190 and ptlon > 100:
            region = 'Laptev_East_Siberian_sea'
             if DN[i,j] == 2:
                les_lst.append([1,0,0,0,0]
            elif DN[i,j] == 1:
                les_lst.append([0,1,0,0,0]
            elif DN[i,j] == -1:
                les_lst.append([0,0,1,0,0]
            elif DN[i,j] == -2:
                les_lst.append([0,0,0,1,0]
            elif DN[i,j] == 0:
                les_lst.append([0,0,0,0,1]       
        
        return(bar_lst,gre_lst,lab_lst,ncb_lst,les_lst)

############################################################################
class reg_stats:
    def _init_(self,bar,gre,lab,les,ncb,typo):
        bar = self.bar
        gre = self.gre
        lab = self.lab
        les = self.les
        ncb = self.ncb
        typo = self.typo
        bar_plot = self._plotter_(bar,'Barents_Kara',typo)
        gre_plot = self._plotter_(gre,'Greenland',typo)
        lab_plot = self._plotter_(lab,'Labrador',typo)
        les_plot = self._plotter_(les,'Laptev_EastSea',typo)
        ncb_plot = self._plotter_(ncb,'NorthCanada_Beaufort',typo)
    
    def _plotter_(self,data,name,typo):
        m_width = data[:,0]
        area = data[:,1]
        perim = data[:,2]
        dadate = data[:,3]
        x = [date2num(dadate) for (m_width,area,perim,dadate) in data]
        f, axarr = plt.subplots(3, sharex=True)
        axarr[0].plot(x,m_width,'r-o')
        axarr[0].set_title('Mean Width')
        axarr[1].plot(x,area,'r-o')
        axarr[1].set_title('Area')
        axarr[2].plot(x,perim,'r-o')
        axarr[2].set_title('Perim')
        fig.savefig(str(typo)+str(dadate[0])+'_'+str(dadate[-1])+'_'+str(name)+'.png')
        plt.close(fig) 
        return
###########################################################################
class poly_stat:
    # gets single contour and sorts it
    def __init__(self,cont,poly_status,OUT,INS,DIFF,X,Y,number,typo,basemap=None,PLOT=None,STCH=None):
        # class definition
        if len(cont) > 200:
            self.polygon_class = 'H'
        elif len(cont) > 100 and len(cont) <= 200:
            self.polygon_class = 'B'
        elif len(cont) > 30 and len(cont) <= 100:
            self.polygon_class = 'M'
        elif len(cont) <= 30:
            self.polygon_class = 'S'
        self.polygon_status = poly_status
        self.typo = typo
        self.number = number
        self.ij_list = cont
        self.ij2xy(cont,X,Y)
        self.difference = DIFF
        self.split_cont(OUT,INS,poly_status)
        self.lon_lat(basemap)
        self.dist_edges()
        self.area_perimeter()
        self.laplacian_solution()
        if STCH:
            self.stat_chart(save=True)
        if PLOT:
            self.poly_contour_plot()
        if self.region == 'Barents_Kara_sea':
            bar_poly_stat.append([str(self.name), str(self.polygon_status), str(self.polygon_class), \
            str(self.centroid_longitude), str(self.centroid_latitude), str(self.L_width), \
            str(self.E_width), str(self.L_area), str(self.E_area), \
            str(self.L_perim), str(self.E_perim), str(dadate)])
        elif self.region == 'Greenland_sea':
            gre_poly_stat.append([str(self.name), str(self.polygon_status), str(self.polygon_class), \
            str(self.centroid_longitude),str(self.centroid_latitude), str(self.L_width), \
            str(self.E_width), str(self.L_area), str(self.E_area), \
            str(self.L_perim), str(self.E_perim), str(dadate)])
        elif self.region == 'Labrador_sea':
            lab_poly_stat.append([str(self.name), str(self.polygon_status), str(self.polygon_class), \
            str(self.centroid_longitude),str(self.centroid_latitude), str(self.L_width), \
            str(self.E_width), str(self.L_area), str(self.E_area), \
            str(self.L_perim), str(self.E_perim), str(dadate)])
        elif self.region == 'Laptev_East_Siberian_sea':
            les_poly_stat.append([str(self.name), str(self.polygon_status), str(self.polygon_class), \
            str(self.centroid_longitude),str(self.centroid_latitude), str(self.L_width), \
            str(self.E_width), str(self.L_area), str(self.E_area), \
            str(self.L_perim), str(self.E_perim), str(dadate)])
        elif self.region == 'North_Canada_Beaufort_sea':
            ncb_poly_stat.append([str(self.name), str(self.polygon_status), str(self.polygon_class), \
            str(self.centroid_longitude),str(self.centroid_latitude), str(self.L_width), \
            str(self.E_width), str(self.L_area), str(self.E_area), \
            str(self.L_perim), str(self.E_perim), str(dadate)])
    
    def ij2xy(self,cont,X,Y):
        # changes indexes to x and y (NOTE i and j are inverted -> i = [:,1], j = [:,0])
        x = []
        y = []
        xvec = range(len(cont[:,0]))
        for n,en in enumerate(xvec):
            en = X[cont[n,0]][cont[n,1]]
            x.append(en)
        yvec = range(len(cont[:,1]))
        for n,en in enumerate(yvec):
            en = Y[cont[n,0]][cont[n,1]]
            y.append(en)
        xy_list = zip(x,y)
        xy_list = np.array(xy_list)
        self.xy_list = xy_list
        return
    
    def split_cont(self,OUT,INS,polygon_status):
        # this function find the different contours
        # NOTE if a point has non integer i coordinate is going to be a vertical edge,
        # if has non integer j coordinate is going to be a horizontal edge hence the use
        # of different arounds depending on the indexes of the point
        # NOTE if the polygon is an OVERESTIMATION the contour finding is inverted
        vs = self.ij_list # list of (i,j) pixel indices
        in_cont = []
        out_cont = []
        unk_cont = []
        func_vals= []
        func_mod = 0 # value of func_vals at model ice edge
        func_osi = 1 # value of func_vals at OSISAF ice edge
        func_unk = 2 # value of func_vals at other parts of contour
        
        if polygon_status == 0:
            for n,el in enumerate(vs):
                #getting all the neighbours
                around2 = ((el[0]+.5,el[1]),(el[0]-.5,el[1])) # vertical boundaries - OK!
                around1 = ((el[0],el[1]+.5),(el[0],el[1]-.5)) # horizontal boundaries
                check_cont = 0
                if el[0]/int(el[0]) == 1:
                    for h,v in around1:
                        if OUT[h][v] == INS[h][v] == 1:
                            in_cont.append(el)
                            func_val=func_mod
                            check_cont = 1
                        elif OUT[h][v] == INS[h][v] == 0:
                            out_cont.append(el)
                            func_val=func_osi
                            check_cont = 1
                    if check_cont == 0:
                        unk_cont.append(el)
                        func_val=func_unk
                    func_vals.append(func_val)
                else:
                    for h,v in around2:
                        if OUT[h][v] == INS[h][v] == 1:
                            in_cont.append(el)
                            func_val=func_mod
                            check_cont = 1
                        elif OUT[h][v] == INS[h][v] == 0:
                            out_cont.append(el)
                            func_val=func_osi
                            check_cont = 1
                    if check_cont == 0:
                        unk_cont.append(el)
                        func_val=func_unk
                    func_vals.append(func_val)
        else:
            for n,el in enumerate(vs):
                #getting all the neighbours
                around2 = ((el[0]+.5,el[1]),(el[0]-.5,el[1])) # vertical boundaries - OK!
                around1 = ((el[0],el[1]+.5),(el[0],el[1]-.5)) # horizontal boundaries
                check_cont = 0
                if el[0]/int(el[0]) == 1:
                    for h,v in around1:
                        if OUT[h][v] == INS[h][v] == 0:
                            in_cont.append(el)
                            func_val=func_mod
                            check_cont = 1
                        elif OUT[h][v] == INS[h][v] == 1:
                            out_cont.append(el)
                            func_val=func_osi
                            check_cont = 1
                    if check_cont == 0:
                        unk_cont.append(el)
                        func_val=func_unk
                    func_vals.append(func_val)
                else:
                    for h,v in around2:
                        if OUT[h][v] == INS[h][v] == 0:
                            in_cont.append(el)
                            func_val=func_mod
                            check_cont = 1
                        elif OUT[h][v] == INS[h][v] == 1:
                            out_cont.append(el)
                            func_val=func_osi
                            check_cont = 1
                    if check_cont == 0:
                        unk_cont.append(el)
                        func_val=func_unk
                    func_vals.append(func_val)
        
        in_cont = np.array(in_cont)
        out_cont = np.array(out_cont)
        unk_cont = np.array(unk_cont)
        func_vals = np.array(func_vals)
        self.in_ice_edge = in_cont
        self.out_ice_edge = out_cont
        self.unknown_edge = unk_cont
        self.f_vals = func_vals
        return
    
    def lon_lat(self,basemap):
        xy_list = self.xy_list
        
        # Centroid - Location in lon/lat of the centroid of the polygon
        DX = 0
        DY = 0
        B = 0
        for n in range(len(xy_list)-1):
            DX += ((xy_list[n][0]+xy_list[n+1][0])*\
                  ((xy_list[n][0]*xy_list[n+1][1])-(xy_list[n+1][0]*xy_list[n][1])))  
            DY += ((xy_list[n][1]+xy_list[n+1][1])*\
                  ((xy_list[n][0]*xy_list[n+1][1])-(xy_list[n+1][0]*xy_list[n][1])))  
            B += ((xy_list[n][0]*xy_list[n+1][1])-(xy_list[n+1][0]*xy_list[n][1]))
        A = (0.5)*B 
        CX = (1/float(6*A))*DX
        CY = (1/float(6*A))*DY
        centroid = [CX,CY]
        self.centroid = centroid
        self.centroid_longitude,self.centroid_latitude = basemap(CX,CY,inverse=True)
        self.lon_list,self.lat_list=basemap(xy_list[:,0],xy_list[:,1],inverse=True)
        
        # defining the region
        centroid_longitude = self.centroid_longitude
        centroid_latitude = self.centroid_latitude
        bblone,bblate,bblonw,bblatw = baffin_bay()
        if centroid_longitude < 90 and centroid_longitude > 8:
            self.region = 'Barents_Kara_sea'
        elif centroid_longitude < 8 and centroid_longitude > -44:
            self.region = 'Greenland_sea'
        elif centroid_longitude < -44 and centroid_longitude > -90:
            n = 0
            N = len(bblatw[:-1])
            if centroid_latitude <= bblatw[-1] and centroid_longitude >= bblonw[-1]:
                self.region = 'Labrador_sea'
            else:
                while n < N:
                    if centroid_latitude >= bblatw[n+1] and centroid_latitude <= bblatw[n]:
                        if centroid_longitude >= bblonw[n]: 
                            self.region = 'Labrador_sea'
                            break
                    n += 1
                else:
                    self.region = 'North_Canada_Beaufort_sea'
        elif centroid_longitude < 180 and centroid_longitude > 90:
            self.region = 'Laptev_East_Siberian_sea'
        else:
            self.region = 'North_Canada_Beaufort_sea'
        
        # Calculating lon/lat for model,osisaf,unknown contours and distances
        inside_contour = self.in_ice_edge
        outside_contour = self.out_ice_edge
        unknown_contour = self.unknown_edge
        if len(inside_contour) != 0:
            self.inside_contour_lon,self.inside_contour_lat = basemap(inside_contour[:,0],inside_contour[:,1],inverse=True)
        if len(outside_contour) != 0:
            self.outside_contour_lon,self.outside_contour_lat = basemap(outside_contour[:,0],outside_contour[:,1],inverse=True)
        if len(unknown_contour) != 0:
            self.unknown_contour_lon,self.unknown_contour_lat = basemap(unknown_contour[:,0],unknown_contour[:,1],inverse=True)
        return

    def laplacian_solution(self):
        lon = self.lon_list
        lat = self.lat_list
        xy = self.xy_list
        fval = self.f_vals
        region = self.region
        typo = self.typo
        daname = 'Polygon_'+str(self.number)
        f_out = './outputs/'+str(typo)+'/'+str(dadate)
        basemap = hqm
        results = Leqs.get_MIZ_widths(lon,lat,fval,name=daname,region=region,fig_outdir=f_out,basemap=basemap,xy_coords2=xy)
        self.AI = results[0]
        self.fun_sol = results[1]
        self.stream = results[2]
        self.L_width = results[3]
        self.L_area = results[4]
        self.L_perim = results[5]
        if results[3] != results[3]:
            in2out = self.widths_in2out
            out2in = self.widths_out2in
            if in2out.tolist() != [0,0,0,0,0] and out2in.tolist() != [0,0,0,0,0]: 
                self.med_width = self.E_width
                print 'M.WIDTH(E) : ',self.med_width
            else:
                self.med_width = 10
                print 'M.WIDTH(MIN) : ',self.med_width
        else:
            self.med_width = self.L_width
            print 'M.WIDTH(L) : ',self.med_width
        if results[4] < 100:
            print ''
            print 'CHECK OUT THE DIFFERENCES'
            print 'AREAS(L.,E.,DIF.): ',self.L_area,self.E_area,abs(self.L_area - self.E_area)
            print 'PERIM.(L.,E.,DIF.): ',self.L_perim,self.E_perim,abs(self.L_perim - self.E_perim)
        else:
            print 'AREA: ',self.L_area
            print 'PERIM.: ',self.L_perim
        return
    
    def poly_contour_plot(self):
        inside_contour = self.in_ice_edge
        outside_contour	= self.out_ice_edge
        unknown_contour = self.unknown_edge
        if len(inside_contour) != 0:
            plt.plot(inside_contour[:,1],inside_contour[:,0],'ro',markersize=5)
        if len(outside_contour) != 0:
            plt.plot(outside_contour[:,1],outside_contour[:,0],'yo',markersize=5)
        if len(unknown_contour) != 0:
            plt.plot(unknown_contour[:,1],unknown_contour[:,0],'go',markersize=5)
        if dist_in2out != [0,0,0,0,0]:
            for n,en in enumerate(dist_in2out):
                plt.plot([en[2],en[4]],[en[1],en[3]],color='black',alpha=0.1)
        if dist_out2in != [0,0,0,0,0]:
            for n,en in enumerate(dist_out2in):
                plt.plot([en[2],en[4]],[en[1],en[3]],color='magenta',alpha=0.1)
        return
    
    def area_perimeter(self):
        # Calculating the area of irregular polygon (from perimeter)
        vs = self.ij_list
        a = 0
        x0,y0 = vs[0]
        for [x1,y1] in vs[1:]:
            dx = x1-x0
            dy = y1-y0
            a += 0.5*(y0*dx - x0*dy)
            x0 = x1 
            y0 = y1 
        self.E_area = abs(a*100)
        # Calculating perimeter in xy coordinates (unit = 10km)
        perim = 0
        for n in range(len(vs)-1):
            perim += np.sqrt(pow(vs[n+1][0]-vs[n][0],2)+pow(vs[n+1][1]-vs[n][1],2))
        self.E_perim = abs(perim*10)
        return
    
    def dist_edges(self):
        # Calculating the min distance from a model point to any osisaf point
        # and vice-versa (osisaf to model)
        # same script applied for the Model2Model(in&out) products - see legends
        inside_contour = self.in_ice_edge
        outside_contour = self.out_ice_edge
        unknown_contour = self.unknown_edge
        tcont = self.ij_list
        UKW = 'Unknown contours < 20%'
        DMW = 'Contour difference < 40%'
        width_in2out = []
        width_out2in = []
        if len(inside_contour) == 0 or len(outside_contour) == 0:
            width_in2out = [0,0,0,0,0]
            width_out2in = [0,0,0,0,0]
            self.E_width = 0
        else:
            unk = 100*(len(unknown_contour)/float(len(tcont)))
            dmo = 100*(abs(len(inside_contour)-len(outside_contour))/float(len(tcont)))
            if unk >= 20:
                UKW = 'WARNING - unknown contours > 20%'
            if dmo >= 40:
                DMW = 'WARNING - contours difference > 40%'
            for n,en in enumerate(inside_contour):
                dist_pt = []
                for m,em in enumerate(outside_contour):
                    dist1	= np.sqrt(pow(en[0]-em[0],2)+pow(en[1]-em[1],2))
                    dist_pt.append([dist1,en[0],en[1],em[0],em[1]])
                idx,value = min(enumerate(dist_pt),key=itg(1))
                width_in2out.append(value)
            for n,en in enumerate(outside_contour):
                dist_pt = []
                for m,em in enumerate(inside_contour):
                    dist1	= np.sqrt(pow(en[0]-em[0],2)+pow(en[1]-em[1],2))
                    dist_pt.append([dist1,en[0],en[1],em[0],em[1]])
                idx,value = min(enumerate(dist_pt),key=itg(1))
                width_out2in.append(value)
            gigio = np.array(width_in2out)
            topo = np.array(width_out2in)
            in2out_m = np.mean(gigio[:,0])
            out2in_m = np.mean(topo[:,0])
            self.E_width = (in2out_m+out2in_m)/float(2)
        self.widths_in2out = np.array(width_in2out)
        self.widths_out2in = np.array(width_out2in)
        self.UKW = UKW
        self.DMW = DMW
        return
    
    
    def stat_chart(self,save=False):
        # The Statistical Chart is an output that tries to compress as many informations
        # as possible in a single figure.
        # The figure is:
        # 1) Top left arctic map with studied polygon highlighted
        # 2) Top right a close up of the polygon with contours and min. distances
        # 3) Bottom left a recap of statistics about the polygon (only Euclidean and min dist for now)
        # 4) Bottom right is a legend for the small image
        
        nmbr = self.number
        pname = 'Polygon_'+str(nmbr)
        self.name = pname
        typo = self.typo
        pclass = self.polygon_class
        if self.polygon_status == 0:
            pstat = 'Overestimation'
        else:
            pstat = 'Underestimation'
        region = self.region
        print ''
        print 'Statistic Chart for ',pname
        print ''
        print 'Class and Region ',pclass,region
        print ''
        print 'Status ',pstat
        print ''
        DN = self.difference
        DMW = self.DMW
        UKW = self.UKW
        ij = self.ij_list
        inside_contour = self.in_ice_edge
        outside_contour = self.out_ice_edge
        unknown_contour = self.unknown_edge
        dist_in2out = self.widths_in2out
        dist_out2in = self.widths_out2in
        clon = '%1.2f' %self.centroid_longitude
        clat = '%1.2f' %self.centroid_latitude
        clonlat = '{0}/{1}'.format(clon,clat)
        L_area = self.L_area
        E_area = self.E_area
        area = '%1.4e %1.4e' %(L_area,E_area) 
        L_perim = self.L_perim
        E_perim = self.E_perim
        perim = '%1.4e %1.4e' %(L_perim,E_perim)
        if dist_in2out.tolist() != [0,0,0,0,0]:
            # changing units from decakilometer to kilometer
            dist_in = np.median(dist_in2out[:,0])*10
            dist_in = '%1.2f' %dist_in
        else:
            dist_in = 'NaN'
        if dist_out2in.tolist() != [0,0,0,0,0]:
            # changing units from decakilometer to kilometer
            dist_out = np.median(dist_out2in[:,0])*10
            dist_out = '%1.2f' %dist_out
        else:
            dist_out = 'NaN'
        pstat = self.polygon_status
        
        # Setting up the plot (2x2) and subplots
        fig = plt.figure(figsize=(15,10))
        gs = gridspec.GridSpec(2,2,width_ratios=[2,1],height_ratios=[4,2])
        plt.suptitle(pname+', class '+pclass+', '+region,fontsize=18)
        main = plt.subplot(gs[0,0])
        polyf = plt.subplot(gs[0,1])
        tab = plt.subplot(gs[1,0])
        leg = plt.subplot(gs[1,1])
        tab.set_xticks([])
        leg.set_xticks([])
        tab.set_yticks([])
        leg.set_yticks([])
        tab.set_frame_on(False)
        leg.set_frame_on(False)
        
        # Main image on the top left
        main.imshow(DN,interpolation='nearest',cmap='winter')
        x1,x2,y1,y2 = np.min(ij[:,1])-10,np.max(ij[:,1])+10,np.min(ij[:,0])-10,np.max(ij[:,0])+10
        main.axvspan(x1,x2,ymin=1-((y1-320)/float(len(DN)-320)),\
            ymax=1-((y2-320)/float(len(DN)-320)),color='red',alpha=0.3)
        main.axis([0,760,0,800])
        
        # Polygon image on the top right
        polyf.imshow(DN,interpolation='nearest',cmap='winter')
        polyf.axis([x1,x2,y2,y1])
        if len(inside_contour) != 0:
            polyf.plot(inside_contour[:,1],inside_contour[:,0],'ro',markersize=4)
        if len(outside_contour) != 0:
            polyf.plot(outside_contour[:,1],outside_contour[:,0],'yo',markersize=4)
        if len(unknown_contour) != 0:
            polyf.plot(unknown_contour[:,1],unknown_contour[:,0],'go',markersize=4)
        if dist_in2out.tolist() != [0,0,0,0,0]:
            for n,en in enumerate(dist_in2out):
                polyf.plot([en[2],en[4]],[en[1],en[3]],color='black',alpha=0.1)
        if dist_out2in.tolist() != [0,0,0,0,0]:
            for n,en in enumerate(dist_out2in):
                polyf.plot([en[2],en[4]],[en[1],en[3]],color='magenta',alpha=0.1)
        
        if typo == 'DFP':
            # Legend on the bottom right
            mc = mlines.Line2D([],[],color='red',marker='o')
            oc = mlines.Line2D([],[],color='yellow',marker='o')
            uc = mlines.Line2D([],[],color='green',marker='o')
            md = mlines.Line2D([],[],color='grey')
            od = mlines.Line2D([],[],color='magenta')
            leg.legend([mc,oc,uc,md,od],(\
               'Open Water Cont.','Ice Pack Cont.','Unknown Cont.','Dist. Water to Pack', \
               'Dist. Pack to Water'),loc='center')
                       
            # Statistics text on the bottom left
            txt = '1) Center Lon/Lat = '+str(clonlat)+' degrees\n'+ \
                  '2) Area = '+str(area)+' km^2\n'+ \
                  '3) Perimeter = '+str(perim)+' km\n'+ \
                  '4) Mean W-P Width = '+str(dist_in)+' km\n'+ \
                  '5) Mean P-W Width = '+str(dist_out)+' km\n'+ \
                  '6) '+str(DMW)+'\n'+ \
                  '7) '+str(UKW)
            tab.text(.2,.2,txt,fontsize=15,bbox=dict(boxstyle='round',facecolor='white',alpha=1))
            if save:
                valid_class = './outputs/'+str(typo)+'/'+str(dadate)
                if not os.path.exists(valid_class):
                    os.mkdir(valid_class)
                if not os.path.exists(valid_class+'/'+region):
                    os.mkdir(valid_class+'/'+region)
                fig.savefig(valid_class+'/'+region+'/'+pclass+'_'+pname+'.png',bbox_inches='tight')
                plt.close()
            else:
                plt.show(False)
            print 'Statistic chart done for '+str(pname)
        elif typo == 'ICP':
            # Legend on the bottom right
            mc = mlines.Line2D([],[],color='red',marker='o')
            oc = mlines.Line2D([],[],color='yellow',marker='o')
            uc = mlines.Line2D([],[],color='green',marker='o')
            md = mlines.Line2D([],[],color='grey')
            od = mlines.Line2D([],[],color='magenta')
            leg.legend([mc,oc,uc,md,od],(\
                  '15 % Cont.','80 % Cont.','Unknown Cont.','Dist. 15 to 80', \
                  'Dist. 80 to 15'),loc='center')
                       
            # Statistics text on the bottom left
            txt = '1) Center Lon/Lat = '+str(clonlat)+' degrees\n'+ \
                  '2) Area = '+str(area)+' km^2\n'+ \
                  '3) Perimeter = '+str(perim)+' km\n'+ \
                  '4) Mean 15-80 Width = '+str(dist_in)+' km\n'+ \
                  '5) Mean 80-15 Width = '+str(dist_out)+' km\n'+ \
                  '6) '+str(DMW)+'\n'+ \
                  '7) '+str(UKW)
            tab.text(.2,.2,txt,fontsize=15,bbox=dict(boxstyle='round',facecolor='white',alpha=1))
            if save:
                valid_class = './outputs/'+str(typo)+'/'+str(dadate)
                if not os.path.exists(valid_class):
                    os.mkdir(valid_class)
                if not os.path.exists(valid_class+'/'+region):
                    os.mkdir(valid_class+'/'+region)
                fig.savefig(valid_class+'/'+region+'/'+pclass+'_'+pname+'.png',bbox_inches='tight')
                plt.close()
            else:
                plt.show(False)
            print 'Statistic chart done for '+str(pname)
        else:
            # Legend on the bottom right
            mc = mlines.Line2D([],[],color='red',marker='o')
            oc = mlines.Line2D([],[],color='yellow',marker='o')
            uc = mlines.Line2D([],[],color='green',marker='o')
            md = mlines.Line2D([],[],color='grey')
            od = mlines.Line2D([],[],color='magenta')
            pos_p = mpatches.Patch(color='lightgreen')
            neg_p = mpatches.Patch(color='royalblue')
            leg.legend([mc,oc,uc,md,od,pos_p,neg_p],(\
                  'Model Cont.','Observation Cont.','Unknown Cont.','Dist. Mdl to Osi', \
                  'Dist. Osi to Mdl','Model Underestimate','Model Overestimate'),loc='center')
                     
            # Statistics text on the bottom left
            txt = '1) Center Lon/Lat = '+str(clonlat)+' degrees\n'+ \
                  '2) Area = '+str(area)+' km^2\n'+ \
                  '3) Perimeter = '+str(perim)+' km\n'+ \
                  '4) Mean M-O Width = '+str(dist_in)+' km\n'+ \
                  '5) Mean O-M Width = '+str(dist_out)+' km\n'+ \
                  '6) Status = '+str(pstat)+'\n'+ \
                  '7) '+str(DMW)+'\n'+ \
                  '8) '+str(UKW)
            tab.text(.2,.2,txt,fontsize=15,bbox=dict(boxstyle='round',facecolor='white',alpha=1))
            if save:
                outdir = './outputs/'+str(typo)
                if not os.path.exists(outdir):
                    os.mkdir(outdir)
                valid_class = outdir+'/'+dadate
                if not os.path.exists(valid_class):
                    os.mkdir(valid_class)
                if not os.path.exists(valid_class+'/'+region):
                    os.mkdir(valid_class+'/'+region)
                fig.savefig(valid_class+'/'+region+'/'+pclass+'_'+pname+'.png',bbox_inches='tight')
                plt.close()
            else:
                plt.show(False)
            print 'Statistic chart done for '+str(pname)
        return


###########################################################################
# Beginning of the script
###########################################################################

###########################################################################
# Defining the basemap
# low quality map
lqm = Basemap(width=7600000,height=11200000,resolution='l',rsphere=(6378273,6356889.44891),\
        projection='stere',lat_ts=70,lat_0=90,lon_0=-45)
# better quality map
hqm = Basemap(width=7600000,height=11200000,resolution='i',rsphere=(6378273,6356889.44891),\
        projection='stere',lat_ts=70,lat_0=90,lon_0=-45)
###########################################################################

mission = sys.argv[1]

# AOD RUN
if mission == 'AOD':
    time0 = time.time()
    dadate = sys.argv[2] 
    osisaf = reader('Osisaf',dadate,hqm)
    model = reader('Model',dadate,hqm)
    lonO,latO,XO,YO,ZO = osisaf.lonO,osisaf.latO,osisaf.X,osisaf.Y,osisaf.Z
    lonM,latM,XM,YM,ZM = model.lonM,model.latM,model.X,model.Y,model.ZC
    AOD = AOD_poly(XM,YM,ZM,XO,YO,ZO)
    over,under,DN,BM,BO = AOD.over,AOD.under,AOD.DN,AOD.B1,AOD.B2

    # Regional statistics
    bar_stat = []
    gre_stat = []
    lab_stat = []
    les_stat = []
    ncb_stat = []


#    
#    bar_poly_stat = []
#    gre_poly_stat = []
#    lab_poly_stat = []
#    les_poly_stat = []
#    ncb_poly_stat = []
#    
#    poly_list=[]
#    for n,el in enumerate(over):
#        # classification of positive polygons
#        aod=poly_stat(el,'1',BO,BM,DN,XO,YO,n,'AOD',basemap=hqm,PLOT=None,STCH=True)
#        poly_list.append(aod)
#    try:
#        n
#    except NameError:
#        n = -1 
#    for n2,el in enumerate(under):
#        # classification of negative (n+1 for good enumeration)
#        n += 1 
#        aod=poly_stat(el,'0',BO,BM,DN,XO,YO,n,'AOD',basemap=hqm,PLOT=None,STCH=True)
#        poly_list.append(aod)
#    
#    outdir = './outputs/AOD/'+str(dadate)
#    if not os.path.exists(outdir):
#        os.mkdir(outdir)
#    
#    reg_repo = outdir+'/Barents_Kara_sea'
#    if not os.path.exists(reg_repo):
#        os.mkdir(reg_repo)
#    
#    f = open('./outputs/AOD/'+str(dadate)+'/Barents_Kara_sea/analysis.txt', 'w')
#    f.write('\n'.join(map(lambda x: str(x), bar_poly_stat)))
#    f.close()
#    
#    reg_repo = outdir+'/Greenland_sea'
#    if not os.path.exists(reg_repo):
#        os.mkdir(reg_repo)
#    
#    f = open('./outputs/AOD/'+str(dadate)+'/Greenland_sea/analysis.txt', 'w')
#    f.write('\n'.join(map(lambda x: str(x), gre_poly_stat)))
#    f.close()
#    
#    reg_repo = outdir+'/Labrador_sea'
#    if not os.path.exists(reg_repo):
#        os.mkdir(reg_repo)
#    
#    f = open('./outputs/AOD/'+str(dadate)+'/Labrador_sea/analysis.txt', 'w')
#    f.write('\n'.join(map(lambda x: str(x), lab_poly_stat)))
#    f.close()
#    
#    reg_repo = outdir+'/Laptev_East_Siberian_sea'
#    if not os.path.exists(reg_repo):
#        os.mkdir(reg_repo)
#    
#    f = open('./outputs/AOD/'+str(dadate)+'/Laptev_East_Siberian_sea/analysis.txt', 'w')
#    f.write('\n'.join(map(lambda x: str(x), les_poly_stat)))
#    f.close()
#    
#    reg_repo = outdir+'/North_Canada_Beaufort_sea'
#    if not os.path.exists(reg_repo):
#        os.mkdir(reg_repo)
#    
#    f = open('./outputs/AOD/'+str(dadate)+'/North_Canada_Beaufort_sea/analysis.txt', 'w')
#    f.write('\n'.join(map(lambda x: str(x), ncb_poly_stat)))
#    f.close()
#    
    elapsedtime = time.time() - time0
    print str(dadate)+' done in ',elapsedtime
