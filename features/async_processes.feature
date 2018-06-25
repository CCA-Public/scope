Feature: Asynchronous processes
  The CCA DIP access application will use an asynchronous worker to execute long
  running processes in the background. This worker will be implemented using Celery
  and it will be initially used to extract and parse the METS file in the Folder
  creation process after the DIP zip file is uploaded.

  Scenario: Folder creation
    Given an instance running with the asynchronous worker setup
    When a user access the interface
    And creates a new Folder attached to a Collection and with a DIP ZIP file
    Then the instance will start the METS parsing process after the file is uploaded
    And the instance will redirect the user without waiting for that process to end
    And the instance will show a notification to indicate the process is running
    And the process will update the Folder and will create the new Digital Files
    And the work made by the process will appear in the interface while it's running
      But only when the interface is reloaded
