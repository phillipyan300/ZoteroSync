from typing import Optional
import requests
import json
import os
import hashlib




#This class is for multiple Zotero Uploads. Note that the length of the directoryPaths list, filename, and collections have to be the same
class MultipleUploadZoteroAPI:

    def __init__(self, userID: str, apiKey: str, directoryPaths: list, filenames: list, collections: list, APIversion: str):
        self.userID = userID
        self.apiKey = apiKey
        self.directoryPaths = directoryPaths
        self.filenames = filenames
        self.collections = collections
        self.APIversion = APIversion

    def upload_all(self):
        for directoryPath, filename, collection in zip(self.directoryPaths, self.filenames, self.collections):
            singleUploader = self.SingleUploadZoteroAPI(self.userID, self.apiKey, directoryPath, filename, collection, self.APIversion)
            singleUploader.upload()


    # This class is for a SINGLE zotero upload

    class SingleUploadZoteroAPI:

        def __init__(self, userID: str, apiKey: str, directoryPath: str, filename: str, collection: str, APIversion: str):
            self.userID = userID
            self.apiKey = apiKey
            self.directoryPath = directoryPath
            self.filename = filename
            self.collection = collection
            self.fullDirectoryPath = os.path.join(os.getcwd(), directoryPath)
            self.headers =  {
                "Zotero-API-Version": APIversion,
                "Zotero-API-Key": self.apiKey
            }
            self.collectionKey = self._getCollectionKey()

            with open("../PDFDictionary.json", "r") as file:
                self.PDFDictionary = json.load(file)

        def upload(self) -> bool:

            #If the file already exists on Zotero
            if self._getPDFKey() == None:
                print("Uploading a new attachment")
                if self._uploadNewItem():
                    return True
                else:
                    return False
            else:
                print("Updating an existing attachment")
                if self._updateItem():
                    return True
                else:
                    return False



        def _deleteOldFile(self) -> bool:
            oldPdfKey = self._getPDFKey()
            attachmentMetadata = self._getAPIrequest(f"https://api.zotero.org/users/{self.userID}/items/{oldPdfKey}").json()
            oldVersion = attachmentMetadata["data"]["version"]
            uniqueHeaders = self.headers
            uniqueHeaders["If-Unmodified-Since-Version"] = str(oldVersion)
            response = requests.delete(f"https://api.zotero.org/users/{self.userID}/items/{oldPdfKey}", headers=uniqueHeaders)
            if response.status_code == 204:
                return True
            else:
                 return False

        def _fillOutTemplate(self):
            # Step 1: Obtain the Template and edit it
            response = self._getAPIrequest("https://api.zotero.org/items/new?itemType=attachment&linkMode=imported_file")
            structure = response.json()
            structure["title"] = self.filename
            structure["filename"] = self.filename
            structure["contentType"] = "application/pdf"
            structure["collections"].append(self.collectionKey)
            return structure

        def _sendTemplate(self, structure) -> str:
            uniqueHeaders = self.headers
            uniqueHeaders["Content-Type"] = "application/json"
            response = requests.post(f"https://api.zotero.org/users/{self.userID}/items", json=[structure], headers=uniqueHeaders)
            #This occurs if you try to upload the same file while (I am assuming) the previous one is supposedly processing. This error occurs if you run the program on the same file in quick succession
            if response.status_code == 412:
                print("Previous request still processing. Please wait and rerun the program")
                exit()
            jsonToGetKey = response.json()
            itemKey = jsonToGetKey['successful']['0']['key']
            itemUrl = f"https://api.zotero.org/users/{self.userID}/items/{itemKey}/file/view"
            itemName = self.filename

            # Step 6: Upload the PDF dictionary with the new file. In the case that you are editing an existing file, this should overwrite the old url and key
            self._addToDictionary(itemKey, itemName, itemUrl)
            return itemKey

        def _uploadCheck(self, itemKey: str):
            lastChangeMilliseconds = os.path.getmtime(f"{self.directoryPath}{self.filename}") * 1000  # Convert to milliseconds
            md5Hash = hashlib.md5()
            with open(f"{self.directoryPath}{self.filename}", "rb") as file:
                for byte_block in iter(lambda: file.read(4096), b""):
                    md5Hash.update(byte_block)
            md5 = md5Hash.hexdigest()
            filesize = os.path.getsize(f"{self.directoryPath}{self.filename}")
            uniqueHeaders = self.headers
            uniqueHeaders["If-None-Match"] = "*"
            uniqueHeaders["Content-Type"] = "application/x-www-form-urlencoded"
            data = {
                "md5": md5,
                "filename": self.filename,
                "filesize": filesize,
                "mtime": lastChangeMilliseconds
            }
            response = requests.post(f"https://api.zotero.org/users/{self.userID}/items/{itemKey}/file", data=data,
                                     headers=uniqueHeaders)

            # If there's no change to the file, we can exit the program
            response_json = response.json()
            if ("exists" in response_json) and (response_json["exists"] == 1):
                print("The file already exists in Zotero as its current version. No changes are necessary")
                return False
            return response_json


        def _fileUpload(self, response, itemKey: str) -> bool:
            uniqueHeaders = self.headers
            uniqueHeaders["Content-Type"] = str(response['contentType'])
            # Concatenate prefix, file content, and suffix to build a multipart request
            # Prefix includes headers, suffix tell the server that it is the end file

            #If this code is unclear, Zotero offers an alternative: "Add params=1 to the upload authorization request above
            # to retrieve the individual parameters in a params array, which will replace contentType, prefix, and suffix"

            with open(f"{self.directoryPath}{self.filename}", "rb") as file:
                fileContent = file.read()
            # Convert prefix and suffix to bytes
            prefixBytes = response['prefix'].encode('utf-8')
            suffixBytes = response['suffix'].encode('utf-8')
            # Now concatenate
            payload = prefixBytes + fileContent + suffixBytes
            # Upload the file
            uploadResponse = requests.post(response['url'], data=payload, headers=uniqueHeaders)

            # Step 5: If the upload is successful, register the upload
            if uploadResponse.status_code == 201:
                print("File successfully uploaded")
                uniqueHeaders = self.headers
                uniqueHeaders["Content-Type"] = "application/x-www-form-urlencoded"
                uniqueHeaders["If-None-Match"] = "*"
                registerData = {"upload": response['uploadKey']}
                registerResponse = requests.post( f"https://api.zotero.org/users/{self.userID}/items/{itemKey}/file", data=registerData, headers=uniqueHeaders)

                #According to the docs, for this step in the upload, the server should only respond with either 204 (success) or 412 (failure), but just in case I included  200
                if registerResponse.status_code == 204 or registerResponse.status_code == 200:
                    print("Upload successfully registered")
                    return True
                else:
                    print("Error registering upload:", registerResponse.text)
                    return False
            else:
                print("Error uploading file:", uploadResponse.text)
                return False

        #False returns means there is an error
        def _updateItem(self) -> bool:
            #Deleting the original item
            self._deleteOldFile()
            structure = self._fillOutTemplate()
            key = self._sendTemplate(structure)
            postInformation = self._uploadCheck(key)
            if postInformation == False:
                return False
            self._fileUpload(postInformation, key)

        def _uploadNewItem(self) -> bool:
            structure = self._fillOutTemplate()
            key = self._sendTemplate(structure)
            if not self._uploadCheck(key):
                return False
            postInformation = self._uploadCheck(key)
            if postInformation == False:
                return False
            self._fileUpload(postInformation, key)

        def _addToDictionary(self, itemKey: str, itemName: str, itemUrl: str) -> None:
            #If it already exists, we have to delete the element and add a new one
            keyToDelete = None
            for key, value in self.PDFDictionary.items():
                if value["pdf_name"] == itemName:
                    keyToDelete = key
            if keyToDelete:
                del self.PDFDictionary[keyToDelete]
            self.PDFDictionary[itemKey] = {"pdf_name": itemName, "pdf_url": itemUrl}
            #Overwrite the previous document
            with open("../PDFDictionary.json", "w") as file:
                json.dump(self.PDFDictionary, file)
            print("Successfully updated local PDFDictionary log of new attachments")

        def _getCollectionKey(self) -> str:
            headers = {
                "Zotero-API-Version": "3",
                "Zotero-API-Key" : self.apiKey
            }
            #Get all collections and search for the one that I need
            response = requests.get(f"https://api.zotero.org/users/{self.userID}/collections", headers = headers)

            if response.status_code == 200:
                collections = response.json()

                # Search for the collection with the given name
                for collection in collections:
                    if collection["data"]["name"] == self.collection:
                        return collection["data"]["key"]

                # If no collection with the given name is found
                print(f"No collection named '{self.collection}' found.")
                exit()

            else:
                print("Error retrieving collections:", response.text)
                exit()

        def _getPDFKey(self) -> Optional[str]:

             # Search for the attachment that I need from Zotero's repository
            MAX_ITERATIONS = 100  # Example maximum number of iterations to prevent infinite loops
            start = 0
            iterations = 0
            while True:
                response = self._getAPIrequest(f"https://api.zotero.org/users/{self.userID}/items?limit=25&start={start}")
                if response.status_code // 100 != 2:  # Check for non-successful status codes
                    print("Error retrieving items:", response.text)
                    raise Exception("API Error")
                items = response.json()

                if not items:  # If no more items are found, exit the loop
                    break

                for item in items:
                    if item["data"]["itemType"] == "attachment" and item["data"]["filename"] == self.filename:
                        return item["data"]["key"]

                start += 25
                iterations += 1

                if iterations >= MAX_ITERATIONS:  # Prevent potential infinite loop
                    print("Maximum number of iterations reached")
                    break
            # If no file with the given name is found.
            return None

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
                    #Did not percolate up, but I think that in debugging it should be obvious given the print statement
                    print(f"API call failed. Status code: {response.status_code}. ")
                    exit()
            except Exception as e:
                print(f"API request error: {e}")

if __name__ == "__main__":
    #Keeping the trailing slash int he directory address
    zotero = MultipleUploadZoteroAPI(userID="", apiKey="", directoryPaths=[""], filenames=[""], collections=[""], APIversion="")
    zotero.upload_all()




