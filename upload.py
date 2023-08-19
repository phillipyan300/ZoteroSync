import requests
import json
import os
import subprocess
import hashlib


#Uploading one file at a time

#FIlename vs title?


#changing the name of a file doesn't change its md5 hash (which is what Zotero uses to identify it.)
#Make it so that when I upload, I also update the PDFDIctionary with the file just uploaded.
class uploadZoteroAPI:

    def __init__(self, userID: str, api_key: str, directory_address: str, file_name: str):
        self.userID = userID
        self.api_key = api_key
        self.directory_address = directory_address
        self.filename = file_name
        self.full_directory_path = os.path.join(os.getcwd(), directory_address)

        with open("PDFDictionary.json", "r") as file:
            self.PDFDictionary = json.load(file)

    def upload(self):
        #First check if the file exists; if so, then update the file rather than uploading a completely new one
        pdf_key = None
        for key, value in self.PDFDictionary.items():
            if value["pdf_name"] == self.filename:
                pdf_key = key
        if pdf_key:
            print("uploading Existing")
            self.uploadExisting(pdf_key, self.filename)
        else:
            print("uploading New")
            self.uploadNew(self.filename)

    def uploadNew(self, filename: str):
        # Step 1: Obtain the Template and edit it
        response = self.getAPIrequest("https://api.zotero.org/items/new?itemType=attachment&linkMode=imported_file")
        structure = response.json()
        structure["title"] = filename
        structure["filename"] = filename
        structure["contentType"] = "application/pdf"

        # Step 2: Obtaining an itemkey
        headers = {
            'Content-Type': 'application/json',
            "Zotero-API-Version": "3",
            "Zotero-API-Key": self.api_key,
        }
        response = requests.post(f"https://api.zotero.org/users/{self.userID}/items", json=[structure], headers=headers)
        print("\n\nthe skelenton from step 2: "+ json.dumps(response.json(), indent=4) + "\n\n")
        jsonToGetKey = response.json()

        # Step 3: Upload confirmation and get md5, mtime, and filesize

        mtime = os.path.getmtime(f"{self.directory_address}{self.filename}") * 1000  # Convert to milliseconds
        md5_hash = hashlib.md5()
        with open(f"{self.directory_address}{self.filename}", "rb") as file:
            for byte_block in iter(lambda: file.read(4096), b""):
                md5_hash.update(byte_block)
        md5 = md5_hash.hexdigest()

        filesize = os.path.getsize(f"{self.directory_address}{self.filename}")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Zotero-API-Version": "3",
            "Zotero-API-Key": self.api_key,
            "If-None-Match": "*"
        }

        data = {
            "md5": md5,
            "filename": self.filename,
            "filesize": filesize,
            "mtime": mtime
        }

        #basically telling them what the key will be
        response = requests.post(f"https://api.zotero.org/users/{self.userID}/items/{jsonToGetKey['successful']['0']['key']}/file", data=data, headers=headers)

        print(response)
        print(json.dumps(response.json(), indent=4))

        print("step three done")  # The step to confirm upload ability


        # Step 4: Uploading the file
        headers = {
            "Content-Type": response.json()['contentType'],  # API response from step 3 needs to not say exists or this will break
            "Zotero-API-Version": "3",
            "Zotero-API-Key": self.api_key
        }

        # Concatenate prefix, file content, and suffix
        with open(f"{self.directory_address}{jsonToGetKey['successful']['0']['data']['title']}", "rb") as file:
            file_content = file.read()

        # Convert prefix and suffix to bytes
        prefix_bytes = response.json()['prefix'].encode('utf-8')
        suffix_bytes = response.json()['suffix'].encode('utf-8')

        # Now concatenate
        payload = prefix_bytes + file_content + suffix_bytes

        # Upload the file
        upload_response = requests.post(response.json()['url'], data=payload, headers=headers)


        #Step 5: If the upload is successful, register the upload
        if upload_response.status_code == 201:
            print("File successfully uploaded")

            register_headers = {
                # Because the content to be sent is not application/json, you use data, the generic way to send post data
                "Content-Type": "application/x-www-form-urlencoded",
                "If-None-Match": "*",
                "Zotero-API-Version": "3",
                "Zotero-API-Key": self.api_key
            }

            register_data = {
                "upload": response.json()['uploadKey']
            }

            register_response = requests.post(
                f"https://api.zotero.org/users/{self.userID}/items/{jsonToGetKey['successful']['0']['key']}/file",
                data=register_data, headers=register_headers)
            if register_response.status_code == 204:
                print("Upload successfully registered")
            else:
                print("Error registering upload:", register_response.text)
        else:
            print("Error uploading file:", upload_response.text)

    def uploadExisting(self, pdf_key: str, filename: str):
        pass

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

if __name__ == "__main__":
    #Keeping the trailing slash int he directory address
    zotero = uploadZoteroAPI(userID = "", api_key = "", directory_address = "", file_name = "")
    zotero.upload()



