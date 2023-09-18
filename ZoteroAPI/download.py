import requests
import json
import os
import subprocess



#Initial download. Downloads all of the files of the server
class DownloadZoteroAPI:
    def __init__(self, userID: str, apiKey: str, directoryName: str):
        self.userID = userID
        self.apiKey = apiKey
        self.directoryName = directoryName
        self.fullDirectoryPath = os.path.join(os.getcwd(), directoryName)
        self.PDFDictionary = {}




    def makeFolder(self):
        if not os.path.exists(self.fullDirectoryPath):
            os.mkdir(self.directoryName)

    # Multiple API calls needed because limit on number of files per API call
    def extract(self):
        start = 0
        itemsLeft = True
        while itemsLeft:
            itemsLeft = self._getPDFS(start)
            start += 25

        # Annotations
        start = 0
        itemsLeft = True
        while itemsLeft:
            itemsLeft = self._getAnnotations(start)
            start += 25

    def _getPDFS(self, start: int) -> bool:
        response = self._getAPIrequest(f"https://api.zotero.org/users/{self.userID}/items?limit=25&start={start}")

        items = response.json()

        # Commented code below lists all json data extracted from all the items of the library
        # print(json.dumps(items, indent=4))
        # If there are no more items, return false.
        if not len(items):
            return False

        # Each item is an item in Zotero represented as a dictionary. Beware of duplicates, a single file will have both a journal article (containing metadata) and a pdf
        for item in items:
            # Attachments
            if item["data"]["itemType"] == "attachment":
                pdfName = item["data"]["title"]
                print(f"Exporting PDF: {pdfName}")
                pdfKey = item["data"]["key"]
                pdfUrl = f"https://api.zotero.org/users/{self.userID}/items/{item['data']['key']}/file/view"
                # Get the PDF and store it in the drive
                response = self._getAPIrequest(pdfUrl)
                file_path = os.path.join(self.fullDirectoryPath, pdfName)
                with open(file_path, "wb") as f:
                    f.write(response.content)

                # Add to the dictionary of pdfs
                self.PDFDictionary[pdfKey] = {"pdf_name": pdfName, "pdf_url": pdfUrl}
        return True

    # Helper Method for extract
    def _getAnnotations(self, start: int) -> bool:
        response = self._getAPIrequest(f"https://api.zotero.org/users/{self.userID}/items?limit=25&start={start}")

        items = response.json()
        if not len(items):
            return False

        for item in items:
            # Annotations
            if item["data"]["itemType"] == "annotation":
                annotationTitle = item["key"]
                print(f"Exporting annotation: {annotationTitle}")
                annotationUrl = item["links"]["self"]["href"]
                annotationParentKey = item["data"]["parentItem"]

                # Get Annotation and store in local repo
                response = self._getAPIrequest(annotationUrl)
                filePath = os.path.join(self.fullDirectoryPath, annotationTitle)
                with open(filePath, "wb") as f:
                    f.write(response.content)
                # Add to dictionary
                self.PDFDictionary[annotationParentKey]["annotation_url"] = annotationUrl
                print(item)


    # Generic API get function, with generic error checking
    def _getAPIrequest(self, link: str) -> requests.models.Response:
        headers = {
            "Zotero-API-Version": "3",
            "Zotero-API-Key": self.apiKey,

        }
        try:
            response = requests.get(link, headers=headers)
            if response.status_code == 200:
                return response
            else:
                print(f"API call failed. Status code: {response.status_code}. ")
                exit()
        except Exception as e:
            print(f"API request error: {e}")

    def openPDF(self) -> bool:
        print(f"\nYour Zotero library has the following files: ")
        counter = 0
        for key, value in self.PDFDictionary.items():
            counter += 1
            print(f"{counter}. {value['pdf_name']}")
            # Assign an ordering to the Dictionary
            self.PDFDictionary[key]["Order"] = counter

        fileno = int(input("Enter -1 to quit. Choose a file to open by its number: (i.e. 1)  ")) - 1

        if fileno == -2:
            return True
        elif fileno >= len(self.PDFDictionary) or fileno < 0:
            print("Not a valid number!")
            return False
        else:
            for key, value in self.PDFDictionary.items():
                if value["Order"] == (fileno + 1):
                    subprocess.run(["open", f"{self.directoryName}/{self.PDFDictionary[key]['pdf_name']}"])
            return False

    def savePDFLibraryDict(self):
        with open("../PDFDictionary.json", "w") as file:
            json.dump(self.PDFDictionary, file)

    def download(self):
        self.makeFolder()
        self.extract()
        self.savePDFLibraryDict()
        doneViewing = False
        while not doneViewing:
            doneViewing = self.openPDF()

    #Data persistence for uploads

    def clearPDFLibraryDict(self):
        with open("../PDFDictionary.json", "w") as file:
            pass

#Single download class. For use when there are incremental updates to the Zotero repository and you don't want to download the whole repository
#Main concern is that the only way you can search for new files on Zotero is by pdfname, as you won't know the itemkey/pdfkey.
class SingleDownloadZoteroAPI:
    #TODO  check for duplicates; give priority to the most recent zotero
    def __init__(self, userID: str, apiKey: str, directoryName: str, filename: str):
        self.userID = userID
        self.apiKey = apiKey
        self.directoryName = directoryName
        self.fullDirectoryPath = os.path.join(os.getcwd(), directoryName)
        self.fileName = filename
        self.PDFDictionary = {}

    def _extract(self) -> bool:
        start = 0
        itemsLeft = "0"
        while itemsLeft == "0":
            itemsLeft = self._getPDFS(start)
            start += 25

        if itemsLeft == "itemNotFound":
            return False
        else:
            pdfKey = itemsLeft

        start = 0
        itemsLeft = True
        while itemsLeft:
            itemsLeft = self._getAnnotations(start, pdfKey)
            start += 25
        return True

    #Returns the key of the item if found, "0" if not found in the 25 files, and  "itemNotFound" if it has searched all files and not found it
    def _getPDFS(self, start: int) -> str:
        response = self._getAPIrequest(f"https://api.zotero.org/users/{self.userID}/items?limit=25&start={start}")

        items = response.json()

        # If there are no more items, return false.
        if not len(items):
            return "itemNotFound"

        # Each item is an item in Zotero represented as a dictionary. Beware of duplicates, a single file will have both a journal article (containing metadata, a sort of wrapper) and a pdf
        for item in items:
            # Attachments
            if item["data"]["itemType"] == "attachment":
                pdfName = item["data"]["title"]
                if pdfName == self.fileName:
                    pdfKey = item["data"]["key"]
                    pdfUrl = f"https://api.zotero.org/users/{self.userID}/items/{item['data']['key']}/file/view"
                    self.PDFDictionary[pdfKey] = {"pdf_name": pdfName, "pdf_url": pdfUrl}
                    print(f"Exporting PDF: {pdfName}")

                    # Get the PDF and store it in the local folder
                    response = self._getAPIrequest(pdfUrl)
                    filePath = os.path.join(self.fullDirectoryPath, pdfName)
                    with open(filePath, "wb") as f:
                        f.write(response.content)
                    self.PDFDictionary[pdfKey] = {"pdf_name": pdfName, "pdf_url": pdfUrl}
                    return pdfKey
        return "0"

    #This gets any annotations related to the pdf in question.
    def _getAnnotations(self, start: int, pdfKey: str) -> bool:
        response = self._getAPIrequest(f"https://api.zotero.org/users/{self.userID}/items?limit=25&start={start}")

        items = response.json()
        if not len(items):
            return False

        for item in items:
            # Annotations
            if item["data"]["itemType"] == "annotation":
                annotationParentKey = item["data"]["parentItem"]
                if annotationParentKey == pdfKey:
                    annotationTitle = item["key"]
                    annotationUrl = item["links"]["self"]["href"]
                    print(f"Exporting annotation: {annotationTitle}")

                    # Get Annotation and store in local repo
                    response = self._getAPIrequest(annotationUrl)
                    filePath = os.path.join(self.fullDirectoryPath, annotationTitle)
                    with open(filePath, "wb") as f:
                        f.write(response.content)

                    self.PDFDictionary[annotationParentKey]["annotation_url"] = annotationUrl
                    #Although the annotation is found, this should stop the loop in extract to save runtime
                    return False
        return True


    def _getAPIrequest(self, link: str) -> requests.models.Response:
        headers = {
            "Zotero-API-Version": "3",
            "Zotero-API-Key": self.apiKey,

        }
        try:
            response = requests.get(link, headers=headers)
            if response.status_code == 200:
                return response
            else:
                print(f"API call failed. Status code: {response.status_code}. ")
                exit()
        except Exception as e:
            print(f"API request error: {e}")

    #Appending rather than writing.
    def _savePDFLibraryDict(self):
        with open("../PDFDictionary.json", "a") as file:
            pass
    def download(self):
        if not self._extract():
            print("Item not Found!")
            exit()
        self._savePDFLibraryDict()
if __name__ == "__main__":
    #This is for downloading the entire repository
    zotero1 = DownloadZoteroAPI(userID = "", apiKey = "", directoryName = "")
    zotero1.download()

    #This is for a single item download
    zotero2 = SingleDownloadZoteroAPI(userID="", apiKey="", directoryName="", filename="")
    zotero2.download()






