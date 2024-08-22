import json
import boto3
import string
import posixpath


class JobQueue:

    def __init__(self, name=None):
        self.sqs = boto3.resource("sqs")
        self.queue = self.sqs.get_queue_by_name(QueueName=name + "Queue")
        self.inProcess = -1
        self.pending = -1

    def scheduleBatch(self, data):
        msg = json.dumps(data)
        response = self.queue.send_message(MessageBody=msg)
        print("Batch sent. Message ID:", response.get("MessageId"))


# project specific stuff
identifier = ""  # (e.g. cpg0000-jump-pilot)
source = ""  # (e.g. source_4, broad)
batch = ""  # (e.g. 2020_11_04_CPJUMP1)
rows = list(string.ascii_uppercase)[0:16]
columns = range(1, 25)
sites = range(1, 10)
well_digit_pad = True  # Set True to A01 well format name, set False to A1
platelist = []
zprojpipename = "Zproj.cppipe"
illumpipename = "illum.cppipe"
qcpipename = "qc.cppipe"
assaydevpipename = "assaydev.cppipe"
analysispipename = "analysis.cppipe"

# not project specific, unless you deviate from the structure
# Formatted to match data organization in the Cell Painting Gallery
pipelinepath = posixpath.join(identifier, source, "workspace", "pipelines", batch)
zprojoutpath = posixpath.join(identifier, source, "images", batch, "images_projected")
zprojoutputstructure = "Metadata_Plate"
illumoutpath = posixpath.join(identifier, source, "images", batch, "illum")
QCoutpath = posixpath.join(identifier, source, "workspace", "qc", batch, "results")
assaydevoutpath = posixpath.join(identifier, source, "workspace", "assaydev", batch)
analysisoutpath = posixpath.join(identifier, source, "workspace", "analysis", batch)
inputpath = posixpath.join(identifier, source, "workspace", "qc", batch, "rules")
datafilepath = posixpath.join(identifier, source, "workspace", "load_data_csv", batch)
analysisoutputstructure = (
    "Metadata_Plate/analysis/Metadata_Plate-Metadata_Well-Metadata_Site"
)
csvname = "load_data.csv"
csv_with_illumname = "load_data_with_illum.csv"
csv_unprojected_name = "load_data_unprojected.csv"

# well formatting
if well_digit_pad:
    well_format = "02d"
else:
    well_format = "01d"


def MakeZprojJobs():
    zprojqueue = JobQueue(f"{identifier}_Zproj")
    for plate in platelist:
        for eachrow in rows:
            for eachcol in columns:
                for eachsite in sites:
                    templateMessage_zproj = {
                        "Metadata": f"Metadata_Plate={plate},Metadata_Well={eachrow}{eachcol:{well_format}},Metadata_Site={str(eachsite)}",
                        "pipeline": posixpath.join(pipelinepath, zprojpipename),
                        "output": zprojoutpath,
                        "output_structure": zprojoutputstructure,
                        "input": inputpath,
                        "data_file": posixpath.join(
                            datafilepath, plate, csv_unprojected_name
                        ),
                    }
                    zprojqueue.scheduleBatch(templateMessage_zproj)
    print("Z projection job submitted. Check your queue")


def MakeIllumJobs():
    illumqueue = JobQueue(f"{identifier}_Illum")
    for plate in platelist:
        templateMessage_illum = {
            "Metadata": f"Metadata_Plate={plate}",
            "pipeline": posixpath.join(pipelinepath, illumpipename),
            "output": illumoutpath,
            "input": inputpath,
            "data_file": posixpath.join(datafilepath, plate, csvname),
        }

        illumqueue.scheduleBatch(templateMessage_illum)

    print("Illum job submitted. Check your queue")


def MakeQCJobs():
    qcqueue = JobQueue(f"{identifier}_QC")
    for plate in platelist:
        for eachrow in rows:
            for eachcol in columns:
                templateMessage_qc = {
                    "Metadata": f"Metadata_Plate={plate},Metadata_Well={eachrow}{eachcol:{well_format}}",
                    "pipeline": posixpath.join(pipelinepath, qcpipename),
                    "output": QCoutpath,
                    "input": inputpath,
                    "data_file": posixpath.join(datafilepath, plate, csvname),
                }
                qcqueue.scheduleBatch(templateMessage_qc)

    print("QC job submitted. Check your queue")


def MakeQCJobs_persite():
    qcqueue = JobQueue(f"{identifier}_QC")
    for plate in platelist:
        for eachrow in rows:
            for eachcol in columns:
                for eachsite in sites:
                    templateMessage_qc = {
                        "Metadata": f"Metadata_Plate={plate},Metadata_Well={eachrow}{eachcol:{well_format}},Metadata_Site={str(eachsite)}",
                        "pipeline": posixpath.join(pipelinepath, qcpipename),
                        "output": QCoutpath,
                        "input": inputpath,
                        "data_file": posixpath.join(datafilepath, plate, csvname),
                    }

                    qcqueue.scheduleBatch(templateMessage_qc)

    print("QC job submitted. Check your queue")


def MakeAssayDevJobs():
    assaydevqueue = JobQueue(f"{identifier}_AssayDev")
    for plate in platelist:
        for eachrow in rows:
            for eachcol in columns:
                templateMessage_ad = {
                    "Metadata": f"Metadata_Plate={plate},Metadata_Well={eachrow}{eachcol:{well_format}}",
                    "pipeline": posixpath.join(pipelinepath, assaydevpipename),
                    "output": assaydevoutpath,
                    "input": inputpath,
                    "data_file": posixpath.join(
                        datafilepath, plate, csv_with_illumname
                    ),
                }
                assaydevqueue.scheduleBatch(templateMessage_ad)

    print("AssayDev job submitted. Check your queue")


def MakeAnalysisJobs():
    analysisqueue = JobQueue(f"{identifier}_Analysis")
    for plate in platelist:
        for eachrow in rows:
            for eachcol in columns:
                for eachsite in sites:
                    templateMessage_analysis = {
                        "Metadata": f"Metadata_Plate={plate},Metadata_Well={eachrow}{eachcol:{well_format}},Metadata_Site={str(eachsite)}",
                        "pipeline": posixpath.join(pipelinepath, analysispipename),
                        "output": analysisoutpath,
                        "output_structure": analysisoutputstructure,
                        "input": inputpath,
                        "data_file": posixpath.join(
                            datafilepath, plate, csv_with_illumname
                        ),
                    }

                    analysisqueue.scheduleBatch(templateMessage_analysis)

    print("Analysis job submitted. Check your queue")


# MakeZprojJobs()
# MakeIllumJobs()
# MakeQCJobs()
# MakeQCJobs_persite()
# MakeAssayDevJobs()
# MakeAnalysisJobs()
