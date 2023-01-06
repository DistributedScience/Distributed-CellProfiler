# AWS Hygiene Scripts

See also (AUSPICES)[https://github.com/broadinstitute/AuSPICES] for setting up various hygiene scripts to automatically run in your AWS account.

## Clean out old alarms

Python:

```python
import boto3
import time
filterstring = 'MyProjectName'
client = boto3.client('cloudwatch')
alarms = client.describe_alarms(AlarmTypes=['MetricAlarm'],StateValue='INSUFFICIENT_DATA')
while True:
  for eachalarm in alarms['MetricAlarms']:
    if eachalarm['StateValue'] == 'INSUFFICIENT_DATA':
      if filterstring in eachalarm['AlarmName']:
        client.delete_alarms(AlarmNames = [eachalarm['AlarmName']])
        time.sleep(1) #avoid throttling
  token = alarms['NextToken']
  print(token)
  alarms = client.describe_alarms(AlarmTypes=['MetricAlarm'],StateValue='INSUFFICIENT_DATA',NextToken=token)
```

# Clean out old log groups
Bash:

```sh
aws logs describe-log-groups| in2csv -f json --key logGroups > logs.csv
```

R:

(requires `dplyr` and `readr`)

```r
library(dplyr)
library(readr)
read_csv(
  "logs.csv",
  col_types = cols_only(
    storedBytes = col_integer(),
    creationTime = col_double(),
    logGroupName = col_character()
  )
) %>%
  mutate(creationTime =
           as.POSIXct(creationTime / 1000,
                      origin = "1970-01-01")) %>%
  filter(storedBytes == 0) %>%
  select(logGroupName) %>%
  write_tsv("logs_clear.txt", col_names = F)
```

Bash:

```sh
parallel aws logs delete-log-group --log-group-name {1} :::: logs_clear.txt
```
