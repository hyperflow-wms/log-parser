# HyperFlow log parser 
 
## How to run parser?
 
You can use optional run parameters:
- -s - to specify logs source directory (by default `logs-hf` is set)
- -d - to specify logs destination directory (by default `./` is set)
- -f - to specify `file-sizes.log` file directory (by default `logs-hf` is set)

e.g.
`python3 parser.py -s logs-hf -d parsed-logs -f logs-hf`

# Files structure

Logs are written to directory with name pattern `<dest_dir>/<workflow_name>__<workflow_size>__<version>__<date_time>`, where:
 * `dest_dir` - destination directory from run parameters,
 * `workflow_name` - extracted from `file-sizes.log` file, `undefined` if `name` key does not exist,
 * `workflow_size` - extracted from `file-sizes.log` file, number of processes if `size` key does not exist,
 * `version` - extracted from `file-sizes.log` file, `1.0.0` if `version` key does not exist,
 * `date_time`- timestamp in `%Y-%m-%d-%H-%M-%S` format
 
 eg. `montage__0.25__1.0.0__2020-04-20-12-01-24`,
 
 Parser generates following files in [JSON lines](http://jsonlines.org/) format:
 * `job_descriptions.jsonl`
 * `sys_info.jsonl`
 * `metrics.jsonl`

# Parsed data structure

Identifiers:
* `hyperflowId` - eg. _HbD2SFH5_
* `workflowId` - eg. _HbD2SFH5-16_
* `jobId` - eg. _HbD2SFH5-16-44_


## Job descriptions
```json
{
   "workflowName":"montage",
   "size":"0.25",
   "version":"1.0.0",
   "hyperflowId":"6ZYgjDbbG",
   "jobId":"6ZYgjDbbG-1-29",
   "executable":"mBgModel",
   "args":[
      "-i",
      "100000",
      "pimages_20180402_165339_22325.tbl",
      "fits.tbl",
      "corrections.tbl"
   ],
   "inputs":[
      {
         "name":"fits.tbl",
         "size":3745
      },
      {
         "name":"pimages_20180402_165339_22325.tbl",
         "size":1936
      }
   ],
   "outputs":[
      {
         "name":"corrections.tbl",
         "size":573
      }
   ],
   "name":"mBgModel",
   "command":"mBgModel -i 100000 pimages_20180402_165339_22325.tbl fits.tbl corrections.tbl",
   "execTimeMs":1030
}
```

## System info
```json
{
   "cpu":{
      "manufacturer":"Intel®",
      "brand":"Xeon®",
      "vendor":"",
      "family":"",
      "model":"",
      "stepping":"",
      "revision":"",
      "voltage":"",
      "speed":"2.00",
      "speedmin":"",
      "speedmax":"",
      "governor":"",
      "cores":2,
      "physicalCores":2,
      "processors":1,
      "socket":"",
      "cache":{
         "l1d":"",
         "l1i":"",
         "l2":"",
         "l3":""
      }
   },
   "mem":{
      "total":2095239168,
      "free":130646016,
      "used":1964593152,
      "active":849100800,
      "available":1246138368,
      "buffers":105852928,
      "cached":1078996992,
      "slab":149585920,
      "buffcache":1334435840,
      "swaptotal":0,
      "swapused":0,
      "swapfree":0
   },
   "jobId":"6ZYgjDbbG-1-29"
}
```

## Metrics

Two types of metrics (values for key `parameter`):
* events - `event`
* measurements - `cpu`, `memory`, `ctime`, `io`, `network` 

### Events
Possible values for events:
* `handlerStart`
* `jobStart`
* `jobEnd`
* `handlerEnd`

```json
{
   "time":"2020-03-30T17:22:45.160",
   "workflowId":"6ZYgjDbbG-1",
   "jobId":"6ZYgjDbbG-1-1",
   "name":"mProjectPP",
   "parameter":"event",
   "value":"jobStart"
}
```

### Measurements

**cpu**
```json
{
   "time":"2020-03-30T17:23:31.083",
   "pid":"8",
   "workflowId":"6ZYgjDbbG-1",
   "jobId":"6ZYgjDbbG-1-29",
   "name":"mBgModel",
   "parameter":"cpu",
   "value":0
}
```

**memory**
```json
{
   ...,
   "parameter":"memory",
   "value":11304960
}
```

**ctime**
```json
{
   ...,
   "parameter":"ctime",
   "value":30
}
```

**io**
```json
{
   ...,
   "parameter":"io",
   "value":{
      "read":1225,
      "write":1,
      "readSyscalls":5,
      "writeSyscalls":1,
      "readReal":0,
      "writeReal":0,
      "writeCancelled":0
   }
}
```

**network**
```json
{
   ...,
   "parameter":"network",
   "value":{
      "name":"eth0",
      "rxBytes":5777,
      "rxPackets":15,
      "rxErrors":0,
      "rxDrop":0,
      "rxFifo":0,
      "rxFrame":0,
      "rxCompressed":0,
      "rxMulticast":0,
      "txBytes":1336,
      "txPackets":15,
      "txErrors":0,
      "txDrop":0,
      "txFifo":0,
      "txColls":0,
      "txCarrier":0,
      "txCompressed":0
   }
}
```
