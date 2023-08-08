import requests
import json
import os
import subprocess

#How to stop it from accessing trash

def main():

    #These three things I need to get from the user
    userID = ""
    api_key = ""
    directory_name = "ZoteroImports"
    full_directory_path = ""

    #Dictionary where the PDF key is the key and the value is another dictionary which contains the relevant information for the dictionary
    PDFDictionary = {}
    makeFolder("ZoteroImports", full_directory_path)
    extract(userID, api_key, PDFDictionary, full_directory_path)

    doneViewing = False
    while not doneViewing:
        doneViewing = openPDF(PDFDictionary, directory_name)

#Multiple API calls needed bc limits on each + need to do pdfs first then annotations
def extract(userID: str, api_key: str, PDFDictionary: dict, full_directory_path: str) -> None:
    start = 0
    itemsLeft = True
    while itemsLeft:
        itemsLeft = getPDFS(userID, api_key, PDFDictionary, full_directory_path, start)
        start += 25

    # Annotations
    start = 0
    itemsLeft = True
    while itemsLeft:
        itemsLeft = getAnnotations(userID, api_key, PDFDictionary, full_directory_path, start)
        start += 25

def makeFolder(directory_name: str, full_directory_path: str) -> None:
    if not os.path.exists(full_directory_path):
        os.mkdir(directory_name)

#Generic API get function, with generic error checking
def APIrequest(link: str, api_key: str) -> requests.models.Response:
    headers = {
        "Zotero-API-Version": "3",
        "Zotero-API-Key": api_key,

    }
    try:
        response = requests.get(link, headers = headers)
        if response.status_code == 200:
            return response
        else:
            print(f"API call failed. Status code: {response.status_code}. ")
            exit()
    except Exception as e:
       print(f"API request error: {e}")


def openPDF(PDFDictionary: dict, directoryname: str) -> bool:
    print(f"\nYour Zotero library has the following files: ")
    counter = 0
    for key, value in PDFDictionary.items():
        counter += 1
        print(f"{counter}. {value['pdf_name']}")
        #Assign an ordering to the Dictionary
        PDFDictionary[key]["Order"] = counter

    fileno = int(input("Enter -1 to quit. Choose a file to open by its number: (i.e. 1)  "))-1

    if fileno == -2:
        return True
    elif fileno >= len(PDFDictionary) or fileno < 0:
        print("Not a valid number!")
        return False
    else:
        for key, value in PDFDictionary.items():
            if value["Order"] == (fileno + 1):
                subprocess.run(["open", f"{directoryname}/{PDFDictionary[key]['pdf_name']}"])
        return False

#TODO: When the user specifies a specific directory, wll need to change the os.path.join
def getPDFS(userID: str, api_key: str, PDFDictionary: dict, full_directory_path: str, start: int) -> bool:
    response = APIrequest(f"https://api.zotero.org/users/{userID}/items?limit=25&start={start}", api_key)

    items = response.json()

    #Commented code below lists all json data extracted from all the items of the library
    #print(json.dumps(items, indent=4))
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
            pdf_url = f"https://api.zotero.org/users/{userID}/items/{item['data']['key']}/file/view"
            #pdf_url = item["links"]["enclosure"]["href"]

            # Get the PDF and store it in the drive
            response = APIrequest(pdf_url, api_key)
            file_path = os.path.join(full_directory_path, pdf_name)
            with open(file_path, "wb") as f:
                f.write(response.content)

            #Add to the dictionary of pdfs
            PDFDictionary[pdf_key] = {"pdf_name": pdf_name, "pdf_url": pdf_url}
    return True

#TODO: Redo the same repetition as for getPDFS
def getAnnotations(userID: str, api_key: str, PDFDictionary: dict, full_directory_path: str, start: int) -> bool:
    response = APIrequest(f"https://api.zotero.org/users/{userID}/items?limit=25&start={start}", api_key)

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


            #Get Annotation and store in local repo
            response = APIrequest(annotation_url, api_key)
            file_path = os.path.join(full_directory_path, annotation_title)
            with open(file_path, "wb") as f:
                f.write(response.content)
            #Add to dictionary
            PDFDictionary[annotation_parent_key]["annotation_url"] = annotation_url



            #TODO call antother function to clip the annotation on to the parent function, pikepdf?






if __name__ == "__main__":
    main()



# JournalArticle - Like a wrapper class (Not sure if this is useful, maybe we might need the metadata?)
        #Lets comment this out for now, it just clogs up the run time
        # elif item["data"]["itemType"] == "journalArticle":
        #     wrapper_title = item["data"]["title"]
        #     wrapper_url = item["links"]["attachment"]["href"]
        #     print(f"Exporting journalArticle wrapper: {wrapper_title}")
        #     response = APIrequest(wrapper_url, api_key)
        #     file_path = os.path.join(full_directory_path, wrapper_title)
        #     with open(file_path, "wb") as f:
        #         f.write(response.content)
