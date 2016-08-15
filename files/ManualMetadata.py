# -*- coding: utf-8 -*-
"""
Created on Mon Aug 15 12:27:08 2016

@author: bcimini
"""
import pandas as pd

def manualmetadata():
    incsv=pd.read_csv(r'C:\Example\Example.csv')
    manmet=open(r'C:\Example\ExampleMetadata.txt','w')
    print incsv.shape
    for i in range(incsv.shape[0]):
        manmet.write('{"Metadata": "Metadata_Plate='+str(incsv.Metadata_Plate[i])+',Metadata_Well='+str(incsv.Metadata_Well[i])+',Metadata_Site='+str(incsv.Metadata_Site[i])+'"},\n')
    manmet.close()
manualmetadata()