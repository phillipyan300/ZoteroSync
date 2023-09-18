# ZoteroSync
A Python program for users to bulk download files with annotations from Zotero to a local repository and then upload their edits. Features include customizability with a user-specified directory, duplication control, and automatic detection and implementation of uploading new or edited files via a PDFDictionary log to keep track of changes on your local repository compared to Zotero's file repository.

```mermaid
flowchart TD;
    A[init SingleUploadZoteroAPI] --> B(upload);
    B --> C{_searchForPdfKeyInUserLibrary};
    C -->|Key Exists| D[_delete];
    C -->|Key Does Not Exist| E[_getZoteroDocumentTemplate];
    subgraph _updateItem ;
    D --> E;
    subgraph _uploadNewItem;
    E --> F[_sendTemplate];
    F --> G[_addToDictionary];
    G --> H{_uploadCheck};
    H --> |Zotero Allows Upload| I[_fileUpload];
    end;
    end;
    H --> |Zotero Does Not Allow Upload, return False| return;
    I --> |return True| return;
```