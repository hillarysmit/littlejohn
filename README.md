# Littlejohn Wrapper #

## What is it ##

This is a python wrapper to extract informations abount user occupations on
certain filesystems using [robinhood](https://github.com/cea-hpc/robinhood).

This software was developed in [San Raffaele Hospital](https://www.hsr.it/) - 
research department

## Dependencies:

- python 3.9 or superior

- tabulate module: [link](https://pypi.org/project/tabulate/)

## How to run:

1. Get all the necessary infos to run the script:

2. populate the template json with the required information

3. run the script as follows:

```bash
python3 create_report.py -i <json_path> -o <output_folder> -p <number of processes>
```

NOTE: All the arguments are required

## Argument description

```bash

usage: create_report.py [-h] -i INIT_FILE -o OUT_FOLDER -p PROCESSES

Creates Report for space occupation using robinhood https://github.com/cea-hpc/robinhood

optional arguments:
  -h, --help            show this help message and exit
  -i INIT_FILE, --init_file INIT_FILE
                        A json file containing all the necessary infos
  -o OUT_FOLDER, --out_folder OUT_FOLDER
                        A folder that will contain the reports and file list
  -p PROCESSES, --processes PROCESSES
                        Number of subproceeses to be spawned
                        
```

The json required must be in a form consistent with the template.json file
present in the repo

```json
{
    "conf_list": ["fs_1","fs_2"],
    "db_host": "host",
    "db_user": "db_user",
    "db_pwd": "db_password"
}
```

## Outputs ##
The produced output are the the following:

1. A report in the following form

```bash

===2022-11-17 20:03:34.639032===
Report of user user1 on filesystem_1 filesystem:
file type      file count     space used
-----------  ------------  -------------
++                 182413    28190232166
+fastqz+             1052  2079929525675

Report of user user_1 on filesystem_2 filesystem:
file type      file count    space used
-----------  ------------  ------------
++                  10064   89603570551
+bam+                 606  192381971436
+bed+                 224   17538521575
+fastq+                94   74941283740
+fastqz+              668  150399740025

```

The same report will be sent to each user by email

2. a cvs files containing a list of all the files belonging to each user


## Contacts ##

Ilario Tagliaferri: tagliaferri.ilario\@hsr.it
