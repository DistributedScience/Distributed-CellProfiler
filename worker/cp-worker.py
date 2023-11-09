import boto3
import json
import logging
import os
import subprocess
import time
import watchtower

#################################
# CONSTANT PATHS IN THE CONTAINER
#################################

DATA_ROOT = '/home/ubuntu/bucket'
LOCAL_OUTPUT = '/home/ubuntu/local_output'
PLUGIN_DIR = '/home/ubuntu/CellProfiler-plugins'
QUEUE_URL = os.environ['SQS_QUEUE_URL']
AWS_BUCKET = os.environ['AWS_BUCKET']
if 'SOURCE_BUCKET' not in os.environ:
    SOURCE_BUCKET = os.environ['AWS_BUCKET']
else:
    SOURCE_BUCKET = os.environ['SOURCE_BUCKET']
if 'DESTINATION_BUCKET' not in os.environ:
    DESTINATION_BUCKET = os.environ['AWS_BUCKET']
else:
    DESTINATION_BUCKET = os.environ['DESTINATION_BUCKET']
if 'UPLOAD_FLAGS' in os.environ:
    UPLOAD_FLAGS = os.environ['UPLOAD_FLAGS']
else:
    UPLOAD_FLAGS = False
LOG_GROUP_NAME= os.environ['LOG_GROUP_NAME']
CHECK_IF_DONE_BOOL= os.environ['CHECK_IF_DONE_BOOL']
EXPECTED_NUMBER_FILES= os.environ['EXPECTED_NUMBER_FILES']
if 'MIN_FILE_SIZE_BYTES' not in os.environ:
    MIN_FILE_SIZE_BYTES = 1
else:
    MIN_FILE_SIZE_BYTES = int(os.environ['MIN_FILE_SIZE_BYTES'])
if 'USE_PLUGINS' not in os.environ:
    USE_PLUGINS = 'False'
else:
    USE_PLUGINS = os.environ['USE_PLUGINS']
if 'NECESSARY_STRING' not in os.environ:
    NECESSARY_STRING = ''
else:
    NECESSARY_STRING = os.environ['NECESSARY_STRING']
if 'DOWNLOAD_FILES' not in os.environ:
    DOWNLOAD_FILES = 'False'
else:
    DOWNLOAD_FILES = os.environ['DOWNLOAD_FILES']

localIn = '/home/ubuntu/local_input'


#################################
# CLASS TO HANDLE THE SQS QUEUE
#################################

class JobQueue():

    def __init__(self, queueURL):
        self.client = boto3.client('sqs')
        self.queueURL = queueURL

    def readMessage(self):
        response = self.client.receive_message(QueueUrl=self.queueURL, WaitTimeSeconds=20)
        if 'Messages' in response.keys():
            data = json.loads(response['Messages'][0]['Body'])
            handle = response['Messages'][0]['ReceiptHandle']
            return data, handle
        else:
            return None, None

    def deleteMessage(self, handle):
        self.client.delete_message(QueueUrl=self.queueURL, ReceiptHandle=handle)
        return

    def returnMessage(self, handle):
        self.client.change_message_visibility(QueueUrl=self.queueURL, ReceiptHandle=handle, VisibilityTimeout=60)
        return

#################################
# AUXILIARY FUNCTIONS
#################################


def monitorAndLog(process,logger):
    while True:
        output= process.stdout.readline().decode()
        if output== '' and process.poll() is not None:
            break
        if output:
            print(output.strip())
            logger.info(output)

def printandlog(text,logger):
    print(text)
    logger.info(text)

#################################
# RUN CELLPROFILER PROCESS
#################################

def runCellProfiler(message):
    #List the directories in the bucket- this prevents a strange s3fs error
    rootlist=os.listdir(DATA_ROOT)
    for eachSubDir in rootlist:
        subDirName=os.path.join(DATA_ROOT,eachSubDir)
        if os.path.isdir(subDirName):
            trashvar=os.system(f'ls {subDirName}')

    # Configure the logs
    logger = logging.getLogger(__name__)

    # Prepare paths and parameters
    if type(message['Metadata'])==dict: #support for cellprofiler --print-groups output
        if  message['output_structure']=='':
            watchtowerlogger=watchtower.CloudWatchLogHandler(log_group=LOG_GROUP_NAME, stream_name=str(message['Metadata'].values()),create_log_group=False)
            logger.addHandler(watchtowerlogger)
            printandlog('You must specify an output structure when passing Metadata as dictionaries',logger)
            logger.removeHandler(watchtowerlogger)
            return 'INPUT_PROBLEM'
        else:
            metadataID = message['output_structure']
            metadataForCall = ''
            for eachMetadata in message['Metadata'].keys():
                if eachMetadata not in metadataID:
                    watchtowerlogger=watchtower.CloudWatchLogHandler(log_group=LOG_GROUP_NAME, stream_name=str(message['Metadata'].values()),create_log_group=False)
                    logger.addHandler(watchtowerlogger)
                    printandlog('Your specified output structure does not match the Metadata passed. If your CellProfiler-pipeline-grouping is different than your output-file-location-grouping (typically because you are using the output_structure job parameter), then this is expected and NOT an error. Cloudwatch logs will be stored under the output-file-location-grouping, rather than the CellProfiler-pipeline-grouping.',logger)
                    logger.removeHandler(watchtowerlogger)
                else:
                    metadataID = str.replace(metadataID,eachMetadata,message['Metadata'][eachMetadata])
                    metadataForCall+=f"{eachMetadata}={message['Metadata'][eachMetadata]},"
            message['Metadata']=metadataForCall[:-1]
    elif 'output_structure' in message.keys():
        if message['output_structure']!='': #support for explicit output structuring
            watchtowerlogger=watchtower.CloudWatchLogHandler(log_group=LOG_GROUP_NAME, stream_name=message['Metadata'],create_log_group=False)
            logger.addHandler(watchtowerlogger)
            metadataID = message['output_structure']
            for eachMetadata in message['Metadata'].split(','):
                if eachMetadata.split('=')[0] not in metadataID:
                    printandlog('Your specified output structure does not match the Metadata passed. If your CellProfiler-pipeline-grouping is different than your output-file-location-grouping (typically because you are using the output_structure job parameter), then this is expected and NOT an error. Cloudwatch logs will be stored under the output-file-location-grouping, rather than the CellProfiler-pipeline-grouping.',logger)
                else:
                    metadataID = str.replace(metadataID,eachMetadata.split('=')[0],eachMetadata.split('=')[1])
            printandlog(f'metadataID={metadataID}', logger)
            logger.removeHandler(watchtowerlogger)
        else: #backwards compatability with 1.0.0 and/or no desire to structure output
            metadataID = '-'.join([x.split('=')[1] for x in message['Metadata'].split(',')]) # Strip equal signs from the metadata
    else: #backwards compatability with 1.0.0 and/or no desire to structure output
        metadataID = '-'.join([x.split('=')[1] for x in message['Metadata'].split(',')]) # Strip equal signs from the metadata

    localOut = f'{LOCAL_OUTPUT}/{metadataID}'
    remoteOut= os.path.join(message['output'],metadataID)

    # Start loggging now that we have a job we care about
    watchtowerlogger=watchtower.CloudWatchLogHandler(log_group=LOG_GROUP_NAME, stream_name=metadataID,create_log_group=False)
    logger.addHandler(watchtowerlogger)

    # See if this is a message you've already handled, if you've so chosen
    if CHECK_IF_DONE_BOOL.upper() == 'TRUE':
        try:
            s3client=boto3.client('s3')
            bucketlist=s3client.list_objects(Bucket=DESTINATION_BUCKET,Prefix=f'{remoteOut}/')
            objectsizelist=[k['Size'] for k in bucketlist['Contents']]
            objectsizelist = [i for i in objectsizelist if i >= MIN_FILE_SIZE_BYTES]
            if NECESSARY_STRING != '':
                objectsizelist = [i for i in objectsizelist if NECESSARY_STRING in i]
            if len(objectsizelist)>=int(EXPECTED_NUMBER_FILES):
                printandlog('File not run due to > expected number of files',logger)
                logger.removeHandler(watchtowerlogger)
                return 'SUCCESS'
        except KeyError: #Returned if that folder does not exist
            pass	

    downloaded_files = []

    # Optional - download all files, bypass S3 mounting
    if DOWNLOAD_FILES.lower() == 'true':
        # Download load data file and image files
        data_file_path = os.path.join(localIn,message['data_file'])
        printandlog(f"Downloading {message['data_file']} from {SOURCE_BUCKET}", logger)
        csv_insubfolders = message['data_file'].split('/')
        subfolders = '/'.join((csv_insubfolders)[:-1])
        if not os.path.exists(os.path.join(localIn,subfolders)):
            os.makedirs(os.path.join(localIn,subfolders), exist_ok=True)
        s3 = boto3.resource('s3')
        s3.meta.client.download_file(SOURCE_BUCKET, message['data_file'], data_file_path)
        if message['data_file'][-4:]=='.csv':
            printandlog('Figuring which files to download', logger)
            import pandas
            csv_in = pandas.read_csv(data_file_path)
            csv_in=csv_in.astype('str')
            #Figure out what metadata fields we need in this experiment, as a dict
            if type(message['Metadata'])==dict:
                filter_dict = message['Metadata']
            else:
                filter_dict = {}
                for eachMetadata in message['Metadata'].split(','):
                    filterkey, filterval = eachMetadata.split('=')
                    filter_dict[filterkey] = filterval
            #Filter our CSV to just the rows CellProfiler will process, so that we can download only what we need
            for eachfilter in filter_dict.keys():
                csv_in = csv_in[csv_in[eachfilter] == filter_dict[eachfilter]]
            if len(csv_in) <= 1:
                printandlog('WARNING: All rows filtered out of csv before download. Check your Metadata.',logger)
                logger.removeHandler(watchtowerlogger)
                import shutil
                shutil.rmtree(localOut, ignore_errors=True)
                return 'INPUT_PROBLEM'
            #Figure out the actual file names and get them
            channel_list = [x.split('FileName_')[1] for x in csv_in.columns if 'FileName' in x]
            printandlog(f'Downloading files for channels {channel_list}', logger)
            for channel in channel_list:
                for field in range(csv_in.shape[0]):
                    full_old_file_name = os.path.join(list(csv_in[f'PathName_{channel}'])[field],list(csv_in[f'FileName_{channel}'])[field])
                    prefix_on_bucket = full_old_file_name.split(DATA_ROOT)[1][1:]
                    new_file_name = os.path.join(localIn,prefix_on_bucket)
                    if not os.path.exists(os.path.split(new_file_name)[0]):
                        os.makedirs(os.path.split(new_file_name)[0])
                        printandlog(f'Made directory {os.path.split(new_file_name)[0]}',logger)
                    if not os.path.exists(new_file_name):
                        s3.meta.client.download_file(SOURCE_BUCKET,prefix_on_bucket,new_file_name)
                        downloaded_files.append(new_file_name)
            printandlog(f'Downloaded {str(len(downloaded_files))} files',logger)
            import random
            newtag = False
            while newtag == False:
                tag = str(random.randint(100000,999999)) #keep files from overwriting one another
                local_data_file_path = os.path.join(localIn,tag,os.path.split(data_file_path)[1])
                if not os.path.exists(local_data_file_path):
                    if not os.path.exists(os.path.split(local_data_file_path)[0]):
                        os.makedirs(os.path.split(local_data_file_path)[0])
                    csv_in = pandas.read_csv(data_file_path)
                    csv_in.replace(DATA_ROOT,localIn,regex=True, inplace=True)
                    csv_in.to_csv(local_data_file_path,index=False)
                    print('Wrote updated CSV')
                    newtag = True
                else:
                    newtag = False
            data_file_path = local_data_file_path
        elif message['data_file'][-4:]=='.txt':
            printandlog('Downloading files', logger)
            with open(data_file_path, 'r') as f:
                for file_path in f:
                    prefix_on_bucket = file_path.split(DATA_ROOT)[1][1:]
                    new_file_name = os.path.join(localIn,prefix_on_bucket)
                    if not os.path.exists(os.path.split(new_file_name)[0]):
                        os.makedirs(os.path.split(new_file_name)[0])
                        printandlog(f'made directory {os.path.split(new_file_name)[0]}',logger)
                    if not os.path.exists(new_file_name):
                        s3.meta.client.download_file(SOURCE_BUCKET,prefix_on_bucket,new_file_name)
                        downloaded_files.append(new_file_name)
            printandlog(f'Downloaded {str(len(downloaded_files))} files',logger)
        else:
            printandlog("Couldn't parse data file for file download. Not supported input of .csv or .txt",logger)
        # Download pipeline and update pipeilne path in message
        printandlog(f"Downloading {message['pipeline']} from {SOURCE_BUCKET}", logger)
        pipepath = os.path.join(localIn, message['pipeline'].split('/')[-1])
        s3.meta.client.download_file(SOURCE_BUCKET, message['pipeline'], pipepath)
    else:
        data_file_path = os.path.join(DATA_ROOT,message['data_file'])
        pipepath = os.path.join(DATA_ROOT,message["pipeline"])

    # Build and run CellProfiler command
    cpDone = f'{localOut}/cp.is.done'
    if message['data_file'][-4:]=='.csv':
        cmd = f'cellprofiler -c -r -p {pipepath} -i {DATA_ROOT}/{message["input"]} -o {localOut} -d {cpDone} --data-file={data_file_path} -g {message["Metadata"]}'
    elif message['data_file'][-3:]=='.h5':
        cmd = f'cellprofiler -c -r -p {pipepath} -i {DATA_ROOT}/{message["input"]} -o {localOut} -d {cpDone} -g {message["Metadata"]}'
    elif message['data_file'][-4:]=='.txt':
        cmd = f'cellprofiler -c -r -p {pipepath} -i {DATA_ROOT}/{message["input"]} -o {localOut} -d {cpDone} --file-list={data_file_path} -g {message["Metadata"]}'
    else:
        printandlog("Didn't recognize input file",logger)
    if USE_PLUGINS.lower() == 'true':
        cmd += f' --plugins-directory={PLUGIN_DIR}'
    print(f'Running {cmd}')
    logger.info(cmd)

    subp = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    monitorAndLog(subp,logger)

    # Get the outputs and move them to S3
    if os.path.isfile(cpDone):
        time.sleep(30)
        if len(downloaded_files) > 0:
            for eachfile in downloaded_files:
                if os.path.exists(eachfile): #Shared files are possible, and might already be cleaned up
                    os.remove(eachfile)
        mvtries=0
        while mvtries <3:
            try:
                printandlog(f'Move attempt #{mvtries+1}',logger)
                cmd = f'aws s3 mv {localOut} s3://{DESTINATION_BUCKET}/{remoteOut} --recursive --exclude=cp.is.done'
                if UPLOAD_FLAGS:
                    cmd += f' {UPLOAD_FLAGS}'
                printandlog(f'Uploading with command {cmd}', logger)
                subp = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out,err = subp.communicate()
                out=out.decode()
                err=err.decode()
                printandlog(f'== OUT {out}', logger)
                if err == '':
                    break
                else:
                    printandlog(f'== ERR {err}',logger)
                    mvtries+=1
            except:
                printandlog('Move failed',logger)
                printandlog(f'== ERR {err}',logger)
                time.sleep(30)
                mvtries+=1
        if next(open(cpDone))=='Complete\n':
            if mvtries<3:
                printandlog('SUCCESS',logger)
                logger.removeHandler(watchtowerlogger)
                return 'SUCCESS'
            else:
                printandlog(f'OUTPUT PROBLEM. Giving up on {metadataID}',logger)
                logger.removeHandler(watchtowerlogger)
                return 'OUTPUT_PROBLEM'
        else:
            printandlog('CP PROBLEM: Done file reports failure',logger)
            logger.removeHandler(watchtowerlogger)
            return 'CP_PROBLEM'
    else:
        printandlog('CP PROBLEM: Done file does not exist.',logger)
        logger.removeHandler(watchtowerlogger)
        import shutil
        shutil.rmtree(localOut, ignore_errors=True)
        return 'CP_PROBLEM'


#################################
# MAIN WORKER LOOP
#################################

def main():
    queue = JobQueue(QUEUE_URL)
    # Main loop. Keep reading messages while they are available in SQS
    while True:
        msg, handle = queue.readMessage()
        if msg is not None:
            result = runCellProfiler(msg)
            if result == 'SUCCESS':
                print('Batch completed successfully.')
                queue.deleteMessage(handle)
            else:
                print('Returning message to the queue.')
                queue.returnMessage(handle)
        else:
            print('No messages in the queue')
            break

#################################
# MODULE ENTRY POINT
#################################

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print('Worker started')
    main()
    print('Worker finished')
