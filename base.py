import os,time,sys
import pandas as pd
from datetime import datetime
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive


class gdrive(object):

    def __init__(self):
        self.gauth = GoogleAuth()
        self.auth()
        self.drive = GoogleDrive(self.gauth)

    def auth(self):
        self.gauth.LoadCredentialsFile("creds.txt")
        if self.gauth.credentials is None:
            self.gauth.LocalWebserverAuth()
        elif self.gauth.access_token_expired:
            self.gauth.Refresh()
        else:
            self.gauth.Authorize()
        self.gauth.SaveCredentialsFile("creds.txt")

    def download(self, filename, folder="", rename=""):
        folderid = "" if folder else "root"
        if folder:
            rootfolder = self.drive.ListFile({'q': "'root' in parents"}).GetList()
            for file in rootfolder:
                if folder in file['title']:
                    folderid = file['id']
        fileid = ""
        targetfolder = self.drive.ListFile({'q': "'{0}' in parents".format(folderid)}).GetList()
        for file in targetfolder:
            if filename in file['title']:
                fileid = file['id']
        fileobj = self.drive.CreateFile({'id': fileid})
        newfilename = rename if rename else filename
        fileobj.GetContentFile(newfilename)
        return filename, fileid

    def upload(self, filename, folderid=""):
        fileobj = self.drive.CreateFile()
        if folderid:
            fileobj=self.drive.CreateFile({'parents': [{'id': folderid}]})
        fileobj.SetContentFile(filename)
        fileobj.Upload()
        return fileobj['title'], fileobj['id']


def cimblejar(filename):
    cimbdf = pd.read_csv(filename)
    cimbdf.set_index('Date/Time', inplace=True)
    for col in cimbdf.columns.tolist():
        cimbdf[col] = cimbdf[col].str.replace('MYR ', '')
        try:
            cimbdf[col] = cimbdf[col].astype('float64')
        except ValueError:
            cimbdf[col] = cimbdf[col].astype('str')
    return cimbdf


