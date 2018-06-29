Feature: Asynchronous processes
  SCOPE will use an asynchronous worker to execute long running processes in the
  background. This worker will be implemented using Celery and it will be initially
  used to extract and parse the METS file in the Folder creation process after the
  DIP ZIP file is uploaded.

  Scenario: Folder creation
    Given an instance running with the asynchronous worker setup
    When an application user with enough permissions goes to the Folder creation page
    And the user enters the Folder identifier and the parent Collection
    And the user attaches a DIP ZIP file and submits the form
    Then the DIP ZIP file will be uploaded to the instance
    And the instance will create the Folder with the given identifier and Collection
    And the instance will launch a background process to extract and parse the METS file
    And the instance will show the home page to the user right after the background process is launched
    And the instance will show a notification to indicate the background process is running
    And the background process will update the Folder with the Dublin Core metadata from the METS
    And the background process will create the Folder's Digital Files and their PREMIS events
      And these changes made by the background process will appear in the interface while the process is running
        But only when the interface is reloaded
