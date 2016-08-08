# Command to generate batches for a single plate.
# It generates 384*9 tasks, corresponding to 384 wells with 9 images each.
# An image is the unit of parallelization in this example.
#
# You need to install parallel to run this command.

parallel echo '{\"Metadata\": \"Metadata_Plate={1},Metadata_Well={2}{3},Metadata_Site={4}\"},' :::  Plate1 Plate2  ::: `echo {A..P}`  ::: `seq -w 24` ::: `seq -w 9` | sort > batches.txt
