from download import DownloadZoteroAPI, SingleDownloadZoteroAPI
from upload import MultipleUploadZoteroAPI

#Allows for the download of the entire library or a single file. Optional filenames for a list of files to fetch
def download(userID: str, apiKey: str, directoryName: str, singleFetch: bool, filenames=None):
    #Download specified files
    if singleFetch:
        for filename in filenames:
            singleDownloader = SingleDownloadZoteroAPI(userID = userID, apiKey = apiKey, directoryName = directoryName, filename=filename)
            singleDownloader.download()
    #Download all files
    else:
        downloader = DownloadZoteroAPI(userID = userID, apiKey = apiKey, directoryName = directoryName)
        downloader.download()

# Upload
def onSourceChanged(userID: str, apiKey: str, fileSource: list, filenames: list, collection: list, APIversion: str):
    zotero = MultipleUploadZoteroAPI(userID=userID, apiKey=apiKey,directoryPaths=fileSource, filenames=filenames,collections=collection, APIversion=APIversion)
    zotero.upload_all()


