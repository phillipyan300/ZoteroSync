import requests
import json
import os
import subprocess

#How to stop it from accessing trash
#TODO: When the user specifies a specific directory, wll need to change the os.path.join
#Maybe add some way to access webpage screenshots too, beyond just PDFs
#Permanent storage of PDF Dictionary? even after program has stopped running? maybe a text file?

class downloadZoteroAPI:
    def __init__(self, userID: str, api_key: str, directory_name: str):
        self.userID = userID
        self.api_key = api_key
        self.directory_name = directory_name
        self.full_directory_path = os.path.join(os.getcwd(), directory_name)
        self.PDFDictionary = {}

    def makeFolder(self):
        if not os.path.exists(self.full_directory_path):
            os.mkdir(self.directory_name)

    # Multiple API calls needed because limit on number of files per API call
    def extract(self):
        start = 0
        itemsLeft = True
        while itemsLeft:
            itemsLeft = self.getPDFS(start)
            start += 25

        # Annotations
        start = 0
        itemsLeft = True
        while itemsLeft:
            itemsLeft = self.getAnnotations(start)
            start += 25

    def getPDFS(self, start: int) -> bool:
        response = self.getAPIrequest(f"https://api.zotero.org/users/{self.userID}/items?limit=25&start={start}")

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
                pdf_name = item["data"]["title"]
                print(f"Exporting PDF: {pdf_name}")
                pdf_key = item["data"]["key"]
                pdf_url = f"https://api.zotero.org/users/{self.userID}/items/{item['data']['key']}/file/view"
                # Get the PDF and store it in the drive
                response = self.getAPIrequest(pdf_url)
                file_path = os.path.join(self.full_directory_path, pdf_name)
                with open(file_path, "wb") as f:
                    f.write(response.content)

                # Add to the dictionary of pdfs
                self.PDFDictionary[pdf_key] = {"pdf_name": pdf_name, "pdf_url": pdf_url}
        return True

    # Helper Method for extract
    def getAnnotations(self, start: int) -> bool:
        response = self.getAPIrequest(f"https://api.zotero.org/users/{self.userID}/items?limit=25&start={start}")

        items = response.json()
        if not len(items):
            return False

        for item in items:
            # Annotations
            if item["data"]["itemType"] == "annotation":
                annotation_title = item["key"]
                print(f"Exporting annotation: {annotation_title}")
                annotation_url = item["links"]["self"]["href"]
                annotation_parent_key = item["data"]["parentItem"]

                # Get Annotation and store in local repo
                response = self.getAPIrequest(annotation_url)
                file_path = os.path.join(self.full_directory_path, annotation_title)
                with open(file_path, "wb") as f:
                    f.write(response.content)
                # Add to dictionary
                self.PDFDictionary[annotation_parent_key]["annotation_url"] = annotation_url

                # TODO call another function to clip the annotation on to the parent function, pikepdf?

    # Generic API get function, with generic error checking
    def getAPIrequest(self, link: str) -> requests.models.Response:
        headers = {
            "Zotero-API-Version": "3",
            "Zotero-API-Key": self.api_key,

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
                    subprocess.run(["open", f"{self.directory_name}/{self.PDFDictionary[key]['pdf_name']}"])
            return False

    def savePDFLibraryDict(self):
        with open("PDFDictionary.json", "w") as file:
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
        with open("PDFDictionary.json", "w") as file:
            pass


if __name__ == "__main__":
    zotero = downloadZoteroAPI(userID = "", api_key = "", directory_name = "")
    zotero.download()






