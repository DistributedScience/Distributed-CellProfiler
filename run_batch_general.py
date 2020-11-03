import json
import boto3
import string
import os
import posixpath
class JobQueue():

    def __init__(self,name=None):
        self.sqs = boto3.resource('sqs')
        self.queue = self.sqs.get_queue_by_name(QueueName=name+'Queue')
        self.inProcess = -1
        self.pending = -1

    def scheduleBatch(self, data):
        msg = json.dumps(data)
        response = self.queue.send_message(MessageBody=msg)
        print 'Batch sent. Message ID:',response.get('MessageId')

#project specific stuff
topdirname='' #PROJECTNAME        
projectname='' #PROJECTNAME
batchsuffix='' #BATCHNAME
rows=list(string.ascii_uppercase)[0:8]
columns=range(1,13)
sites=range(1,18)
platelist=[] # PLATEFOLDERNAMES
illumpipename='illum.cppipe'
qcpipename='qc.cppipe'
analysispipename='analysis.cppipe'
batchpipenameillum='Batch_data_illum.h5'
batchpipename='Batch_data.h5'

#not project specific, unless you deviate from the structure
startpath=posixpath.join('projects',topdirname)
pipelinepath=posixpath.join(startpath,os.path.join('workspace/pipelines',batchsuffix))
illumoutpath=posixpath.join(startpath,os.path.join(batchsuffix,'illum'))
QCoutpath=posixpath.join(startpath,os.path.join('workspace/qc',os.path.join(batchsuffix,'results')))
analysisoutpath=posixpath.join(startpath,os.path.join('workspace/analysis',batchsuffix))
inputpath=posixpath.join(startpath,os.path.join('workspace/qc',os.path.join(batchsuffix,'rules')))
datafilepath=posixpath.join(startpath,os.path.join('workspace/load_data_csv',batchsuffix))
anlysisoutputstructure="Metadata_Plate/analysis/Metadata_Plate-Metadata_Well-Metadata_Site"
batchpath=posixpath.join(startpath,os.path.join('workspace/batchfiles',batchsuffix))
   
def MakeIllumJobs(mode='repurp'):    
    illumqueue = JobQueue(projectname+'_Illum')
    for toillum in platelist:
        if mode=='repurp':
            templateMessage_illum = {'Metadata': 'Metadata_Plate='+toillum,
                                     'pipeline': posixpath.join(pipelinepath,illumpipename),'output': illumoutpath,
                                     'input': inputpath, 'data_file':posixpath.join(datafilepath,toillum+'.csv')}
        elif mode=='batch':
            templateMessage_illum = {'Metadata': 'Metadata_Plate='+toillum,
                                        'pipeline': posixpath.join(batchpath,batchpipenameillum),
                                        'output': illumoutpath,
                                        'input':inputpath,
                                        'data_file': posixpath.join(batchpath,batchpipenameillum)
                                        }
        else:
            templateMessage_illum = {'Metadata': 'Metadata_Plate='+toillum,
                                     'pipeline': posixpath.join(pipelinepath,illumpipename),'output': illumoutpath,
                                     'input': inputpath, 'data_file':posixpath.join(datafilepath,untruncatedplatedict[toillum],'load_data.csv')}
            
        illumqueue.scheduleBatch(templateMessage_illum)

    print 'Illum job submitted. Check your queue'

def MakeQCJobs(repurp=False):
    qcqueue = JobQueue(projectname+'_QC')
    for toqc in platelist:
        for eachrow in rows:
            for eachcol in columns:
                if repurp==False:
                    templateMessage_qc = {'Metadata': 'Metadata_Plate='+toqc+',Metadata_Well='+eachrow+'%02d' %eachcol,
                                    'pipeline': posixpath.join(pipelinepath,qcpipename),
                                    'output': QCoutpath,
                                    'input': inputpath,
                                    'data_file': posixpath.join(datafilepath,toqc+'.csv')
                                }
                else:
                    templateMessage_qc = {'Metadata': 'Metadata_Plate='+toqc+',Metadata_Well='+eachrow+'%02d' %eachcol,
                                    'pipeline': posixpath.join(pipelinepath,qcpipename),
                                    'output': QCoutpath,
                                    'input': inputpath,
                                    'data_file': posixpath.join(datafilepath,untruncatedplatedict[toqc],'load_data.csv')
                                }
                qcqueue.scheduleBatch(templateMessage_qc)

    print 'QC job submitted. Check your queue'

def MakeQCJobs_persite(repurp=False):
    qcqueue = JobQueue(projectname+'_QC')
    for toqc in platelist:
        for eachrow in rows:
            for eachcol in columns:
                for eachsite in sites:
                    if repurp==False:
                        templateMessage_qc = {'Metadata': 'Metadata_Plate='+toqc+',Metadata_Well='+eachrow+'%02d' %eachcol+',Metadata_Site='+str(eachsite),
                                        'pipeline': posixpath.join(pipelinepath,qcpipename),
                                        'output': QCoutpath,
                                        'input': inputpath,
                                        'data_file': posixpath.join(datafilepath,toqc+'.csv')
                                        }
                    else:
                        templateMessage_qc = {'Metadata': 'Metadata_Plate='+toqc+',Metadata_Well='+eachrow+'%02d' %eachcol+',Metadata_Site='+str(eachsite),
                                        'pipeline': posixpath.join(pipelinepath,qcpipename),
                                        'output': QCoutpath,
                                        'input': inputpath,
                                        'data_file': posixpath.join(datafilepath,untruncatedplatedict[toqc],'load_data.csv')
                                        }

                    qcqueue.scheduleBatch(templateMessage_qc)

    print 'QC job submitted. Check your queue'


def MakeAnalysisJobs(mode='repurp'):
    analysisqueue = JobQueue(projectname+'_Analysis')
    for toanalyze in platelist:
        for eachrow in rows:
            for eachcol in columns:
                for eachsite in sites:
                    if mode=='repurp':
                        templateMessage_analysis = {'Metadata': 'Metadata_Plate='+toanalyze+',Metadata_Well='+eachrow+'%02d' %eachcol+',Metadata_Site='+str(eachsite),
                                        'pipeline': posixpath.join(pipelinepath,analysispipename),
                                        'output': analysisoutpath,
                                        'output_structure':anlysisoutputstructure,
                                        'input':inputpath,
                                        'data_file': posixpath.join(datafilepath,toanalyze+'_with_illum.csv')
                                        }
                    elif mode=='batch':
                        templateMessage_analysis = {'Metadata': 'Metadata_Plate='+toanalyze+',Metadata_Well='+eachrow+'%02d' %eachcol+',Metadata_Site='+str(eachsite),
                                        'pipeline': posixpath.join(batchpath,batchpipename),
                                        'output': analysisoutpath,
                                        'output_structure':anlysisoutputstructure,
                                        'input':inputpath,
                                        'data_file': posixpath.join(batchpath,batchpipename)
                                        }
                    else:
                        templateMessage_analysis = {'Metadata': 'Metadata_Plate='+toanalyze+',Metadata_Well='+eachrow+'%02d' %eachcol+',Metadata_Site='+str(eachsite),
                                        'pipeline': posixpath.join(pipelinepath,analysispipename),
                                        'output': analysisoutpath,
                                        'output_structure':anlysisoutputstructure,
                                        'input':inputpath,
                                        'data_file': posixpath.join(datafilepath,untruncatedplatedict[toanalyze],'load_data_with_illum.csv')
                                        }

                    analysisqueue.scheduleBatch(templateMessage_analysis)

    print 'Analysis job submitted. Check your queue'
    
#MakeIllumJobs(mode='batch')
#MakeQCJobs(repurp=True)
#MakeQCJobs_persite(repurp=True)
#MakeAnalysisJobs(mode='batch')

