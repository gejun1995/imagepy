# -*- coding: utf-8 -*-
"""
Created on Tue Dec 27 01:06:59 2016
@author: yxl
"""
from imagepy import IPy
import numpy as np
from imagepy.core.engine import Simple, Filter
from imagepy.core.manager import ImageManager
from scipy.ndimage import label, generate_binary_structure
from skimage.measure import regionprops
from imagepy.core.mark import GeometryMark
import pandas as pd

# center, area, l, extent, cov
class RegionCounter(Simple):
    title = 'Geometry Analysis'
    note = ['8-bit', '16-bit']
    para = {'con':'8-connect', 'center':True, 'area':True, 'l':True, 'extent':False, 'cov':False, 'slice':False,
            'ed':False, 'holes':False, 'ca':False, 'fa':False, 'solid':False}
    view = [(list, 'con', ['4-connect', '8-connect'], str, 'conection', 'pix'),
            (bool, 'slice', 'slice'),
            ('lab', None, '=========  indecate  ========='),
            (bool, 'center', 'center'),
            (bool, 'area', 'area'),
            (bool, 'l', 'perimeter'),
            (bool, 'extent', 'extent'),
            (bool, 'ed', 'equivalent diameter'),
            (bool, 'ca', 'convex area'),
            (bool, 'holes', 'holes'),
            (bool, 'fa', 'filled area'),
            (bool, 'solid', 'solidity'),
            (bool, 'cov', 'cov')]

    #process
    def run(self, ips, imgs, para = None):
        if not para['slice']:imgs = [ips.img]
        k = ips.unit[0]

        titles = ['Slice', 'ID'][0 if para['slice'] else 1:]
        if para['center']:titles.extend(['Center-X','Center-Y'])
        if para['area']:titles.append('Area')
        if para['l']:titles.append('Perimeter')
        if para['extent']:titles.extend(['Min-Y','Min-X','Max-Y','Max-X'])
        if para['ed']:titles.extend(['Diameter'])
        if para['ca']:titles.extend(['ConvexArea'])
        if para['holes']:titles.extend(['Holes'])
        if para['fa']:titles.extend(['FilledArea'])
        if para['solid']:titles.extend(['Solidity'])
        if para['cov']:titles.extend(['Major','Minor','Ori'])
        buf = imgs[0].astype(np.uint16)
        data, mark = [], {'type':'layers', 'body':{}}
        strc = generate_binary_structure(2, 1 if para['con']=='4-connect' else 2)
        for i in range(len(imgs)):
            label(imgs[i], strc, output=buf)
            ls = regionprops(buf)

            dt = [[i]*len(ls), list(range(len(ls)))]
            if not para['slice']:dt = dt[1:]

            layer = {'type':'layer', 'body':[]}
            texts = [(i.centroid[::-1])+('id=%d'%n,) for i,n in zip(ls,range(len(ls)))]
            layer['body'].append({'type':'texts', 'body':texts})
            if para['cov']:
                ellips = [i.centroid[::-1] + (i.major_axis_length/2,i.minor_axis_length/2,i.orientation) for i in ls]
                layer['body'].append({'type':'ellipses', 'body':ellips})
            mark['body'][i] = layer

            if para['center']:
                dt.append([round(i.centroid[1]*k,1) for i in ls])
                dt.append([round(i.centroid[0]*k,1) for i in ls])
            if para['area']:
                dt.append([i.area*k**2 for i in ls])
            if para['l']:
                dt.append([round(i.perimeter*k,1) for i in ls])
            if para['extent']:
                for j in (0,1,2,3):
                    dt.append([i.bbox[j]*k for i in ls])
            if para['ed']:
                dt.append([round(i.equivalent_diameter*k, 1) for i in ls])
            if para['ca']:
                dt.append([i.convex_area*k**2 for i in ls])
            if para['holes']:
                dt.append([1-i.euler_number for i in ls])
            if para['fa']:
                dt.append([i.filled_area*k**2 for i in ls])
            if para['solid']:
                dt.append([round(i.solidity, 2) for i in ls])
            if para['cov']:
                dt.append([round(i.major_axis_length*k, 1) for i in ls])
                dt.append([round(i.minor_axis_length*k, 1) for i in ls])
                dt.append([round(i.orientation*k, 1) for i in ls])

            data.extend(list(zip(*dt)))
        ips.mark = GeometryMark(mark)
        IPy.show_table(pd.DataFrame(data, columns=titles), ips.title+'-region')

# center, area, l, extent, cov
class RegionFilter(Filter):
    title = 'Geometry Filter'
    note = ['8-bit', '16-bit', 'auto_msk', 'auto_snap','preview']
    para = {'con':'4-connect', 'inv':False, 'area':0, 'l':0, 'holes':0, 'solid':0, 'e':0, 'front':255, 'back':100}
    view = [(list, 'con', ['4-connect', '8-connect'], str, 'conection', 'pix'),
            (bool, 'inv', 'invert'),
            ('lab', None, 'Filter: "+" means >=, "-" means <'),
            (int, 'front', (0, 255), 0, 'front color', ''),
            (int, 'back', (0, 255), 0, 'back color', ''),
            (float, 'area', (-1e6, 1e6), 1, 'area', 'unit^2'),
            (float, 'l', (-1e6, 1e6), 1, 'perimeter', 'unit'),
            (int, 'holes', (-10,10), 0, 'holes', 'num'),
            (float, 'solid', (-1, 1,), 1, 'solidity', 'ratio'),
            (float, 'e', (-100,100), 1, 'eccentricity', 'ratio')]

    #process
    def run(self, ips, snap, img, para = None):
        k, unit = ips.unit
        strc = generate_binary_structure(2, 1 if para['con']=='4-connect' else 2)

        lab, n = label(snap==0 if para['inv'] else snap, strc, output=np.uint16)
        idx = (np.ones(n+1)*(0 if para['inv'] else para['front'])).astype(np.uint8)
        ls = regionprops(lab)
        
        for i in ls:
            if para['area'] == 0: break
            if para['area']>0:
                if i.area*k**2 < para['area']: idx[i.label] = para['back']
            if para['area']<0:
                if i.area*k**2 >= -para['area']: idx[i.label] = para['back']

        for i in ls:
            if para['l'] == 0: break
            if para['l']>0:
                if i.perimeter*k < para['l']: idx[i.label] = para['back']
            if para['l']<0:
                if i.perimeter*k >= -para['l']: idx[i.label] = para['back']

        for i in ls:
            if para['holes'] == 0: break
            if para['holes']>0:
                if 1-i.euler_number < para['holes']: idx[i.label] = para['back']
            if para['holes']<0:
                if 1-i.euler_number >= -para['holes']: idx[i.label] = para['back']

        for i in ls:
            if para['solid'] == 0: break
            if para['solid']>0:
                if i.solidity < para['solid']: idx[i.label] = para['back']
            if para['solid']<0:
                if i.solidity >= -para['solid']: idx[i.label] = para['back']

        for i in ls:
            if para['e'] == 0: break
            if para['e']>0:
                if i.minor_axis_length>0 and i.major_axis_length/i.minor_axis_length < para['e']: 
                    idx[i.label] = para['back']
            if para['e']<0:
                if i.minor_axis_length>0 and i.major_axis_length/i.minor_axis_length >= -para['e']: 
                    idx[i.label] = para['back']

        idx[0] = para['front'] if para['inv'] else 0
        img[:] = idx[lab]
plgs = [RegionCounter, RegionFilter]