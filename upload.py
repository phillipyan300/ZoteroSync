import requests
import json
import os
import subprocess
import hashlib

#Notes: This is uploading a new file, but I can theoretically update/edit and old file with the partial file upload
#Need to build the above functionality, two potential paths, depending on the user choiceg
userID = ""
api_key = ""

#Start by just pushing pdfs.
headers = {
        "Zotero-API-Version": "3",
        "Zotero-API-Key": api_key,

    }
response = requests.get(f"https://api.zotero.org/items/new?itemType=attachment&linkMode=imported_file", headers = headers)
print(json.dumps(response.json(), indent=4))
structure = response.json()
#Applying an arbitrary pdf
structure["title"] = "AApaper.pdf"
structure["filename"] = "AApaper.pdf"
structure["contentType"] = "application/pdf"
print(json.dumps(structure, indent=4))


#Now step 2, actually filling this out and obtaining a itemkey
headers = {
    'Content-Type': 'application/json',
    "Zotero-API-Version": "3",
    "Zotero-API-Key": api_key,
}
response = requests.post(f"https://api.zotero.org/users/{userID}/items", json=[structure], headers=headers)
print(response)
print("step two done")
print(json.dumps(response.json(), indent=4))
jsonToGetKey = response.json()


#Now step 3, confirming that I can upload
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Zotero-API-Version": "3",
    "Zotero-API-Key": api_key,
    "If-None-Match": "*"
}

#I don't think I need this? Mtime and md5? NOt sure,gonna keep it cuz chatGPT said so lol
mtime = os.path.getmtime(f"/Users/phillipyan/Downloads/{jsonToGetKey['successful']['0']['data']['title']}") * 1000  # Convert to milliseconds
filename = "AApaper.pdf"
md5_hash = hashlib.md5()
with open(f"/Users/phillipyan/Downloads/{jsonToGetKey['successful']['0']['data']['title']}", "rb") as file:
    for byte_block in iter(lambda: file.read(4096), b""):
        md5_hash.update(byte_block)
md5 = md5_hash.hexdigest()

data = {
    "md5": md5,  # The MD5 hash of the file
    "filename": jsonToGetKey['successful']['0']['data']['filename'],
    "filesize": 626851,  #Will need to find a way to get this number automatically
    "mtime": mtime  # The modification time in milliseconds
}

#This should get the key for the item
print(jsonToGetKey['successful']['0']['key'])
response = requests.post(f"https://api.zotero.org/users/{userID}/items/{jsonToGetKey['successful']['0']['key']}/file", data=data, headers=headers)

print(response)
print(response.text)
print(json.dumps(response.json(), indent=4))



print("step three done") #The step to confirm upload ability


#Last step: to actually upload the file:

# ... [Your code above]

# STEP 4: UPLOAD THE FILE
headers = {
    "Content-Type": response.json()['contentType'],  # this should be set based on the API response from Step 3
    "Zotero-API-Version": "3",
    "Zotero-API-Key": api_key
}

# Concatenate prefix, file content, and suffix
with open(f"/Users/phillipyan/Downloads/{jsonToGetKey['successful']['0']['data']['title']}", "rb") as file:
    file_content = file.read()

# Convert prefix and suffix to bytes
prefix_bytes = response.json()['prefix'].encode('utf-8')
suffix_bytes = response.json()['suffix'].encode('utf-8')

# Now concatenate
payload = prefix_bytes + file_content + suffix_bytes

# Upload the file

upload_response = requests.post(response.json()['url'], data=payload, headers=headers)

if upload_response.status_code == 201:
    print("File successfully uploaded")

    # STEP 5: REGISTER THE UPLOAD
    register_headers = {
        #Because the content to be sent is not application/json, you use data, the generic way to send post data
        "Content-Type": "application/x-www-form-urlencoded",
        #Figure out why I need this?
        "If-None-Match": "*",

        # I don't think I need the code below
        "Zotero-API-Version": "3",
        "Zotero-API-Key": api_key
    }
    register_data = {
        "upload": response.json()['uploadKey']
    }
    register_response = requests.post(f"https://api.zotero.org/users/{userID}/items/{jsonToGetKey['successful']['0']['key']}/file", data=register_data, headers=register_headers)
    if register_response.status_code == 204:
        print("Upload successfully registered")
    else:
        print("Error registering upload:", register_response.text)
else:
    print("Error uploading file:", upload_response.text)

