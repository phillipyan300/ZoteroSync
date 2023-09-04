import requests
import json
import os
import hashlib

class UploadZoteroAPI:

    def __init__(self, userID: str, apiKey: str, directoryPath: str, filename: str, collection: str):
        self.userID = userID
        self.apiKey = apiKey
        self.directoryPath = directoryPath
        self.filename = filename
        self.collection = collection
        self.fullDirectoryPath = os.path.join(os.getcwd(), directoryPath)

        with open("PDFDictionary.json", "r") as file:
            self.PDFDictionary = json.load(file)

    def uploadHelper(self):
        #If the file already exists on Zotero
        if self.getPDFKey() == "0":
            print("Uploading a new attachment")
            self.isNew = True
        else:
            print("Updating an existing attachment")
            self.isNew = False
        self.upload()

    def upload(self) -> bool:
        #Getting the collection Key
        collectionKey = self.getCollectionKey()

        #Step 0: If it is simply updating a new file, delete the old file
        if not self.isNew:
            oldPdfKey = self.getPDFKey()
            attachmentMetadata = self.getAPIrequest(f"https://api.zotero.org/users/{self.userID}/items/{oldPdfKey}").json()
            oldVersion = attachmentMetadata["data"]["version"]
            headers = {
                "Zotero-API-Version": "3",
                "Zotero-API-Key": self.apiKey,
                "If-Unmodified-Since-Version": str(oldVersion)
            }
            response = requests.delete(f"https://api.zotero.org/users/{self.userID}/items/{oldPdfKey}", headers=headers)
            if response.status_code == 204:
                pass
                #print("Old file successfully deleted!")
            else:
                print("Error:", response.text)

        # Step 1: Obtain the Template and edit it
        response = self.getAPIrequest("https://api.zotero.org/items/new?itemType=attachment&linkMode=imported_file")
        structure = response.json()
        structure["title"] = self.filename
        structure["filename"] = self.filename
        structure["contentType"] = "application/pdf"
        structure["collections"].append(collectionKey)

        # Step 2: Sending the filled out template
        headers = {
            'Content-Type': 'application/json',
            "Zotero-API-Version": "3",
            "Zotero-API-Key": self.apiKey,
        }
        response = requests.post(f"https://api.zotero.org/users/{self.userID}/items", json=[structure], headers=headers)
        jsonToGetKey = response.json()
        itemKey = jsonToGetKey['successful']['0']['key']
        itemUrl = f"https://api.zotero.org/users/{self.userID}/items/{itemKey}/file/view"
        itemName = self.filename


        # Step 3: Upload confirmation and get md5, mtime, and filesize
        mtime = os.path.getmtime(f"{self.directoryPath}{self.filename}") * 1000  # Convert to milliseconds
        md5Hash = hashlib.md5()
        with open(f"{self.directoryPath}{self.filename}", "rb") as file:
            for byte_block in iter(lambda: file.read(4096), b""):
                md5Hash.update(byte_block)
        md5 = md5Hash.hexdigest()
        filesize = os.path.getsize(f"{self.directoryPath}{self.filename}")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Zotero-API-Version": "3",
            "Zotero-API-Key": self.apiKey,
            "If-None-Match": "*"
        }
        data = {
            "md5": md5,
            "filename": self.filename,
            "filesize": filesize,
            "mtime": mtime
        }
        response = requests.post(f"https://api.zotero.org/users/{self.userID}/items/{itemKey}/file", data=data, headers=headers)

        #If there's no change to the file, we can exit the program
        if response.text == "{\"exists\":1}":
            print("The file already exists in Zotero as its current version. No changes are necessary")
            return True

        # Step 4: Uploading the file
        headers = {
            "Content-Type": response.json()['contentType'],  # API response from step 3 needs to not say exists or this will break
            "Zotero-API-Version": "3",
            "Zotero-API-Key": self.apiKey
        }
        # Concatenate prefix, file content, and suffix
        with open(f"{self.directoryPath}{self.filename}", "rb") as file:
            fileContent = file.read()
        # Convert prefix and suffix to bytes
        prefixBytes = response.json()['prefix'].encode('utf-8')
        suffixBytes = response.json()['suffix'].encode('utf-8')
        # Now concatenate
        payload = prefixBytes + fileContent + suffixBytes
        # Upload the file
        uploadResponse = requests.post(response.json()['url'], data=payload, headers=headers)


        #Step 5: If the upload is successful, register the upload
        if uploadResponse.status_code == 201:
            print("File successfully uploaded")

            registerHeaders = {
                # Because the content to be sent is not application/json, you use data, the generic way to send post data
                "Content-Type": "application/x-www-form-urlencoded",
                "If-None-Match": "*",
                "Zotero-API-Version": "3",
                "Zotero-API-Key": self.apiKey
            }

            registerData = {
                "upload": response.json()['uploadKey']
            }

            registerResponse = requests.post(
                f"https://api.zotero.org/users/{self.userID}/items/{itemKey}/file",
                data=registerData, headers=registerHeaders)
            if registerResponse.status_code == 204:
                print("Upload successfully registered")
            else:
                print("Error registering upload:", registerResponse.text)
        else:
            print("Error uploading file:", uploadResponse.text)

        #Step 6: Upload the PDF dictionary with the new file. In the case that you are editing an existing file, this should overwrite the old url and key
        self.addToDictionary(itemKey, itemName, itemUrl)



    def addToDictionary(self, itemKey: str, itemName: str, itemUrl: str) -> None:
        #If it already exists, we have to delete the element and add a new one
        keyToDelete = ""
        for key, value in self.PDFDictionary.items():
            if value["pdf_name"] == itemName:
                key_to_delete = key
        if keyToDelete:
            del self.PDFDictionary[keyToDelete]
        self.PDFDictionary[itemKey] = {"pdf_name": itemName, "pdf_url": itemUrl}
        #Overwrite the previous document
        with open("PDFDictionary.json", "w") as file:
            json.dump(self.PDFDictionary, file)
        print("Successfully updated local PDFDictionary log of new attachments")

    def getCollectionKey(self) -> str:
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

    def getPDFKey(self) -> str:
        headers = {
            "Zotero-API-Version": "3",
            "Zotero-API-Key": self.apiKey
        }
        # Get all collections and search for the one that I need
        response = requests.get(f"https://api.zotero.org/users/{self.userID}/items", headers=headers)

        if response.status_code == 200:
            items = response.json()

            # Search for the collection with the given name
            for item in items:
                if item["data"]["itemType"] == "attachment" and item["data"]["filename"] == self.filename:
                    return item["data"]["key"]

            # If no file with the given name is found.
            return "0"

        else:
            print("Error retrieving items:", response.text)
            exit()



    def getAPIrequest(self, link: str) -> requests.models.Response:
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

if __name__ == "__main__":
    #Keeping the trailing slash int he directory address
    zotero = UploadZoteroAPI(userID="", apiKey="",
                             directoryPath="", filename="",
                             collection="")
    zotero.uploadHelper()



