''' A script to create a list of all the metadata combinations present in a given CSV
This is designed to be called from the command line with 
$ python ManualMetadata.py pathtocsv/csvfile.csv "['Metadata_Metadata1','Metadata_Metadata2']" 
'''
from __future__ import print_function

import pandas as pd
import sys
import ast

csv=sys.argv[1]
metadatalist=ast.literal_eval(sys.argv[2])

def manualmetadata():
    incsv=pd.read_csv(csv)
    manmet=open(csv[:-4]+'batch.txt','w')
    print(incsv.shape)
    done=[]
    for i in range(incsv.shape[0]):
            metadatatext='{"Metadata": "'
            for j in metadatalist:
                metadatatext+=j+'='+str(incsv[j][i])+','
            metadatatext=metadatatext[:-1]+'"}, \n'
            if metadatatext not in done:
                manmet.write(metadatatext)
                done.append(metadatatext)
    manmet.close()
    print(str(len(done)), 'batches found')
manualmetadata()
