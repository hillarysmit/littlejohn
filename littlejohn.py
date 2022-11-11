#    Copyright (C) 2022 Tagliaferri Ilario
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


# ===== imports =====
import mysql.connector

from tabulate import tabulate

import os
from pathlib import Path
from pwd import getpwnam

import datetime

import smtplib
from email.message import EmailMessage

import subprocess
from multiprocessing import Pool

import tarfile

import json

import argparse

import warnings

import logging
# ===== Decoration  =====


# ===== class definition =====

class user:
    def __init__(self,name,conf_list,fs_list,db_host,db_user,db_password,out_folder):
        self.name = name
        self.uid = getpwnam(self.name)[2]
        self.conf_list = conf_list
        self.fs_list = fs_list
        self.db_host = db_host
        self.db_user = db_user
        self.db_password = db_password
        self.out_folder_usr = Path(os.path.join(os.path.abspath(out_folder),self.name))
        
        time = datetime.datetime.now()	
        self.time_fmt =  time.strftime("%Y_%m_%d_%H_%M_%S")

    # ---- miscellanea ----

    def __create_out_folder(self):
        """
        Creates a folder in the form of

        outfolder/username

        where outfolder is the path passed during class instantiation.

        Assign the permissions to the user itself: uid == gid got from self.uid
        """
        if not os.path.exists(self.out_folder_usr):
            self.out_folder_usr.mkdir(parents=True)

        self.__change_permission(self.out_folder_usr,0o700)

        return(True)

    def __change_permission(self,path,permissions):
        """ 
        Assign the path to the user itself: uid == gid got from self.uid
        
        path: a path (pathlib object)

        permissions: permissions in octal notation: 664 is 0o664
        
        """
        # TODO: check if number is octal

        if os.path.exists(path):
            os.chown(path,self.uid,self.uid)
            os.chmod(path,permissions)

    def complete_report(self):
        """
        Creates both the file list per user and the small report 
        using robinhood tools such as rbh-report
        """
        
        self.recoursive_user_filelist()
        self.recoursive_report()
    
        return(None)

    # ---- file list ----

    def create_user_filelist(self,conf_file):
        """

        Creates a list of files relative to a user in a filesystem in csv format
        Relies on running externally rbh-report

        """
        try: 
            self.__create_out_folder()
        except:
            logging.error("Output folder {} could not be created".format(
                self.out_folder_usr))
            sys.exit()

        # create output_file
        out_csv_path = Path(
            os.path.join(self.out_folder_usr,"{}_{}_{}_filelist.csv".format(
                self.name,
                conf_file,
                self.time_fmt)
            )
        )

	# create the list rapresentative of the commandline (rbh-report):
        command_list = ["rbh-report",
            "-f",
            conf_file,
            "--dump-user",
            self.name,
            "-c"]

        out_file = open(out_csv_path,"w")
      
        try:
            subprocess.run(command_list, stdout=out_file, stderr=subprocess.STDOUT)
        except:
            logging.error("Could not produce file list for {} ({})".format(
                self.name,
                conf_file))
            sys.exit()

        out_file.close()

        out_file_tar = "{}.tar.gz".format(out_csv_path)

        try:
            tar = tarfile.open(out_file_tar,"w:gz")
            tar.add(out_csv_path)
            tar.close()        
            os.remove(out_csv_path)
            self.__change_permission(out_file_tar,0o500)
        except:
            logging.error("Could not compress file list for {} ({})".format(
                self.name,
                conf_file))

            sys.exit()

        return(out_file)

    def recoursive_user_filelist(self):
        """

        Given multiple filesystems, for each one of them create a list of files
        belonging to the user defined during class instantiation.
        Works multiprocessing

        """
        for fs in self.fs_list:
            self.create_user_filelist(fs)

        return(None)

    # ---- report creation ---- 

    def fs_file_classes(self,fs):
        """

        Given a user and a filesystem, interrogates the db created by robinhood
        and produces a report 

        """
        # connecto to db
        fs_db = mysql.connector.connect(
            host = self.db_host,
            user = self.db_user,
            password = self.db_password,
            database = fs
        )

        cursor = fs_db.cursor()
        cursor.execute("""
            SELECT fileclass, COUNT(*), sum(size) 
            FROM ENTRIES 
            WHERE uid = "{}" 
            GROUP BY fileclass""".format(self.name))

        file_user = cursor.fetchall()
        
        output_table = [["file type","file count","space used"]]

        for element in file_user:
            filetype = element[0].decode("UTF-8")
            file_count = element[1]
            file_size = int(element[2])
            output_table.append([filetype, file_count, file_size])
	
        return(output_table)

    def recoursive_report(self):
        """

        Given a list of filesystems whose name are consistent to the ones 
        explored by robinhood, create a report for each filesystem for
        a certain user. The report will be a txt file in the current
	directory (for now at least).

        """

        try:
            self.__create_out_folder()
        except:
            logging.error("Output folder {} could not be created".format(
                self.out_folder_usr))
            sys.exit()
	
	# create a file to write the result to
        out_file_path = Path(
            os.path.join(self.out_folder_usr,"{}_{}.report".format(self.name,self.time_fmt)
            )
        )

        out_file = open(out_file_path,"w")
        out_file.write("=={}===\n".format(datetime.datetime.now()))

        for element in self.fs_list:
            if element:
                try:
                    fs_file_list = self.fs_file_classes(element)
                    out_file.write("Report of user {} on {} filesystem:\n".format(self.name,element))
                    out_file.write(tabulate(fs_file_list,headers="firstrow"))
                    out_file.write("\n\n")
                except:
                    loggin.warning(
                            "Report of user {} for fs {} could not be created".format(
                            self.name,
                            element
                            ))
                    continue

        out_file.close()
 
        self.__change_permission(out_file_path,0o400)

        return(out_file_path)

    # ---- report post processing related methods ----
    def send_email_report(self):
        """

        Sends an email with the content of the report produced by recoursive
        report

        """
        out_file = self.recoursive_report()

        # send email. From: https://docs.python.org/3/library/email.examples.html
        with open(out_file) as fp:
            msg = EmailMessage()
            msg.set_content(fp.read())
            
        msg["Subject"] = "Robinhood report for user {}".format(self.name)
        msg["From"] = "robinhood@robinhood"

        # get email via getpwnam

        email = getpwnam(self.name)[4]
        msg["To"] = email
        
        try:
            s = smtplib.SMTP('localhost')
            s.send_message(msg)
            s.quit()
        except:
            logging.warning("No email was sent to {}".format(email))
        
        return(None)
 
# ==== function definition ====

# ---- db operations ----
def get_users(db_host,db_user,db_password,fs):
    """
    Given a robinhood database containing all the user, extracts all the users
    once and creates a list of users
    """
 
    # connecto to db
    fs_db = mysql.connector.connect(
        host = db_host,
        user = db_user,
        password = db_password,
        database = fs
    )

    cursor = fs_db.cursor()
    cursor.execute("SELECT DISTINCT uid FROM ACCT_STAT")
    user_encoded = cursor.fetchall()
   
    user_list = []

    for user in user_encoded:
        user_list.append(user[0].decode("UTF-8"))

    return(user_list)
    
# ---- parse json info ----

def parse_init_file(init_file):
    """
    Given an init json file with the following structure:
    
    {
        "connf_list": ["fs_1","fs_2"],
        "db_host": "host",
        "db_user": "db_user",
        "db_pwd": "db_password"
    }

    retunrs a dictionary with the elements reported in the init file. This
    dictionary will be used later on to run report_creation_wrapper_multiprocess
    """

    init_file = Path(os.path.abspath(init_file))
    with open (init_file,"r") as cred:
        credential_dict = json.load(cred)

    return(credential_dict)

def get_db_from_conf(conf_file):
    """
    Given a robinhood configuration file, obtains the database name
    relative to the filesystem of interest
    """
    conf_file = Path(conf_file)

    # if the path is not absolute, search for the file in the default
    # robinhood folder: /etc/robinhood.d

    if not conf_file.is_absolute() and not conf_file.is_file():
        robinhood_dir = Path("/etc/robinhood.d")
        conf_file = Path(os.path.join(robinhood_dir,conf_file.name))
    
    if not conf_file.exists():
        logging.warning("{} does not exists".format(conf_file))
        return(None)

    try:
        conf_content = open(conf_file,"r")
        conf_content = conf_content.readlines()
        for element in conf_content:
            if "db = " in element:
                db = element.split("=")[1].strip().strip(";")
        return(db)
    except:
        logging.warning("The robinhood configuration file {} is malformed and will be ignored".format(conf_file.absolute())) 
        return(None)

# ---- report generation wrappers ----

def user_instantiatior(*argument_list):
    """
    Instantiate an element of class user and runs the "complete_report"
    method.

    The argument must be a list of arguments required to the instantiation of
    the class itself.
    """
    logging.info("{}: Checking data for user {}".format(datetime.datetime.now(),argument_list[0]))
    try:
        user_inst=user(*argument_list)
    except:
        logging.warning("The user {} was not found on the system - Please verify".format(argument_list[0])) 
        return(None) 

    user_inst.complete_report()
    return(None) 

def report_creation_wrapper_multiprocess(conf_list,
        fs_list,
        db_host,
        db_user,
        db_password,
        out_folder,
        processes = 1):
    """
    Given informations to access a robinhood database, a list of the filesystems
    as reported in robinhood and the number of processes to be used proceed as
    follows:

    - gets a list of all the user on the filesystem

    - instantiate the class user for each user

    - produce the report with the method recoursive_report of the class user

    All is wrapped in a Pool object from the library multiprocessing to allow
    faster executeon. Default number of processes = 1

    """

    user_list=get_users(db_host,
        db_user,
        db_password,
        fs_list[0])

    # remove integers

    user_list = [user for user in user_list if not user.isdigit()]
    iterable_arguments = []
    for user in user_list:
        iterable_arguments.append([user,
            conf_list,
            fs_list,
            db_host,
            db_user,
            db_password,
            out_folder])

    with Pool(processes) as p:
        p.starmap(user_instantiatior,iterable_arguments)

def run_report_generator(init_file,out_folder,processes = 1):
    """
    Given an init file with the following structure:

    {
        "conf_list": ["fs_1","fs_2"],
        "db_host": "host",
        "db_user": "db_user",
        "db_pwd": "db_password"
    }

    a output folder (string) and the number of processes to be used (int, def =1)

    Creates the list of file and a report for each user

    """

    options_dict = parse_init_file(init_file)

    out_folder = Path(os.path.abspath(out_folder))

    db_list = [ get_db_from_conf(conf_file) for 
            conf_file in 
            options_dict["conf_list"] ]

    options_dict["db_list"] = db_list
 
    report_creation_wrapper_multiprocess(
        options_dict["conf_list"],
        options_dict["db_list"],
        options_dict["db_host"],
        options_dict["db_user"],
        options_dict["db_pwd"],
        out_folder,
        processes
    )

    return(None)

#---- Logging ----
def create_logging(log_file):
    """
    Create an appropriate log file in self.log_folder.
    If self.log_folder does not exists it will be created
    else it will be left untouched.
    Argument 1: the path of the file to be written
    """
    log_file = Path(log_file)
    logging.basicConfig(filename=log_file.as_posix(),
            format='%(asctime)s %(levelname)s:%(message)s',level=logging.INFO)

    return (None)

#---- Main ----
def main():
    parser = argparse.ArgumentParser(description='''
        Creates Report for space occupation using robinhood https://github.com/cea-hpc/robinhood
        ''')

    wrapper_name="""\
  _     _  _    _    _          _       _           __      __                                
 | |   (_)| |_ | |_ | | ___  _ | | ___ | |_   _ _   \ \    / /_ _  __ _  _ __  _ __  ___  _ _ 
 | |__ | ||  _||  _|| |/ -_)| || |/ _ \| ' \ | ' \   \ \/\/ /| '_|/ _` || '_ \| '_ \/ -_)| '_|
 |____||_| \__| \__||_|\___| \__/ \___/|_||_||_||_|   \_/\_/ |_|  \__,_|| .__/| .__/\___||_|  
                                                                        |_|   |_|             
    """

    print(wrapper_name)
    print("\nA convencience wrapper to run robinhood policy engine (https://github.com/cea-hpc/robinhood)\n")

    parser.add_argument('-i','--init_file', type = str, required = True,
                    help='A json file containing all the necessary infos')

    parser.add_argument('-o','--out_folder', type = str, required = True,

                    help='A folder that will contain the reports and file list')

    parser.add_argument('-p','--processes', type = int, required = True,   
                    help='A json file containing all the necessary infos')

    parser.add_argument('-l','--log_file', type = str, required = True,   
                    help='A file where the activities will be logged')

    args = parser.parse_args()
    
    create_logging(args.log_file)
    run_report_generator(args.init_file,args.out_folder,args.processes)

if __name__ == "__main__":
    main()
