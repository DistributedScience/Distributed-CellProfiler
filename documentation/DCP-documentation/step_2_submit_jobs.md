# Step 2: Submit Jobs

## Overview

Distributed-CellProfiler works by breaking your analysis into a series of smaller jobs based on the metadata and groupings you've specified in your pipeline.
The choice of how to group your images is largely dependent on the details of your experiment.
For example, pipelines to create [illumination correction functions](http://onlinelibrary.wiley.com/doi/10.1111/jmi.12178/full) are usually run on a per-plate basis, while pipelines with a large number of memory intensive measurement steps such as [CellPainting](http://www.nature.com/nprot/journal/v11/n9/full/nprot.2016.105.html) are grouped based on plate, well, and site so that each node only analyzes one site at a time.  

Once you've decided on a grouping, you're ready to start configuring your job file.
Once your job file is configured, simply use `python run.py submitJob files/{YourJobFile}.json` to send all the jobs to the SQS queue [specified in your config file](step_1_configuration.md).

***

**Distributed-CellProfiler only works for pipelines with extracted metadata and specified groupings and which use the LoadData OR on h5 containers created by the CreateBatchFiles module**, though we hope to add support for file-lists in the future.
See [this page](https://github.com/CellProfiler/CellProfiler/wiki/Adapting-CellProfiler-to-a-LIMS-environment) for more information about running CellProfiler headless with file-lists versus LoadData CSVs.  

**The grouping specified in your pipeline MUST match what you specify here in order to successfully run jobs.**

Due to CellProfiler's image-loading mechanisms, experiments with >10,000 image sites can begin to suffer from decreased performance.
Breaking such experiments down into a number of smaller CSVs may increase your processing throughput.  
If using LoadData, make sure your "Base image location" is set to "None".

***

## Configuring your job file

* **pipeline:** The path to your pipeline file.
* **data_file:** The path to your CSV.  
At a minimum, this CSV should contain PathName_{NameOfChannel} and FileName_{NameOfChannel} columns for each of your channels, as well as Metadata_{PieceOfMetadata} for each kind of metadata being used to group your image sets.  
You can create this CSV yourself via your favorite scripting language or by using the Images, Metadata, and NamesAndTypes modules in CellProfiler to generate image sets then using the Export->Image Set Listing command.  
Some users have reported issues with using relative paths in the PathName columns; using absolute paths beginning with `/home/ubuntu/bucket/{relativepath}` may increase your odds of success.
* **input:** The path to your default input directory.
This is not necessary for every pipeline but can be helpful when non-image files are needed in the pipeline (such as a text file containing quality control rules for the FlagImage module).
DO NOT set this to a large directory, or CellProfiler will try to scan the entire thing before running your pipeline.
* **output:** The top output directory you'd like your files placed in.
* **output_structure:** By default, Distributed-CellProfiler will put your output in subfolders created by hyphenating all your Metadata entries (see below) in order (e.g. if the individual group being processed was `{"Metadata": "Metadata_Plate=Plate1,Metadata_Well=A01"}`, the output would be placed in `output_top_directory/Plate1-A01`.)
If you'd like a different folder structure, you may designate one here (e.g. if you set `"output_structure": "Metadata_Plate/Metadata_Well"` then the previous example would output to `output_top_directory/Plate1/A01`.
This setting is optional.
Job files that don't include it will use the default structure.
* **groups:** The list of all the groups of images you'd like to process.
For large numbers of groups, it may be helpful to create this list separately as a .txt file you can then append into the job's JSON file.
You may create this yourself in your favorite scripting language.
Alternatively, you can use the following additional tools to help you create and format this list:
    * `batches.sh` allows you to provide a list of all the individual metadata components (plates, columns, rows, etc).
    It then uses [GNU parallel](https://www.gnu.org/software/parallel/parallel_tutorial.html) to create a formatted text file with all the possible combinations of the components you provided.
    This approach is best when you have a large number of groups and the group structure is uniform.

      Example: for a 96-well plate experiment where one there are 3 plates and the experiment is grouped by Plate and Well, `batches.sh` would read:
        `parallel echo '{\"Metadata\": \"Metadata_Plate={1},Metadata_Well={2}{3}\"},' ::: Plate1 Plate2 Plate3 ::: A B C D E F G H ::: 01 02 03 04 05 06 07 08 09 10 11 12 | sort > batches.txt`      
    * You may also use the list of groupings created by calling `cellprofiler --print-groups` from the command line (see [here](https://github.com/CellProfiler/CellProfiler/wiki/Adapting-CellProfiler-to-a-LIMS-environment#cmd) and [here](https://github.com/CellProfiler/Distributed-CellProfiler/issues/52) for more information).  
    Note that for job files that specify groupings in this way, the `output_structure` variable is NOT optional - it must be specified or an error will be returned.

## Alternate job submission: run_batch_general.py

We also support an alternate second path besides `submitJobs` to create the list of jobs - the `run_batch_general.py` file.
This file essentially serves as a "shortcut" to run many common types of stereotyped experiments we run in our lab.
Essentially, if your data follows a regular structure (such as N rows, N columns, N grouping, a particular structure for output, etc.), you may find it useful to take and modify this file for your own usage.  
We recommend new users use the `submitJobs` pathway, as it will help users understand the kinds of information Distributed-CellProfiler needs in order to run properly, but once they are comfortable with it they may find `run_batch_general.py` helps them create jobs faster in the future.
