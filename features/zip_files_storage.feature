Feature: Storage of DIP ZIP files
  SCOPE will have the option to split the storage of the uploaded DIPs into different
  locations of the local filesystem. Each location will store a configurable amount of data.
  This configuration will be made via two environment variables:
    - STORAGE_LOCATIONS: list of locations paths separated by comma.
    - STORAGE_LOCATION_SIZE: maximum size of each location.

  Scenario: Default configuration
    Given an instance running
    When the STORAGE_LOCATIONS and STORAGE_LOCATION_SIZE variables are not configured in the environment
    Then the instance will use the "media" folder inside the instance directory to store the ZIP files
    And the instance won't check the size used by ZIP files on that folder

  Scenario: Custom configuration
    Given an instance running
    When the STORAGE_LOCATIONS and/or STORAGE_LOCATION_SIZE variables are configured in the environment
    Then the instance will use the locations indicated in STORAGE_LOCATIONS to store the ZIP files
    And the instance will limit each location size to the STORAGE_LOCATION_SIZE env. var. value

  Scenario: Behavior
    Given an instance running
    When a user with permissions creates a new Folder
    And the ZIP file is uploaded
    Then the instance will check the list of storage locations from the STORAGE_LOCATIONS env. var.
    And the instance will save the ZIP on the first location with enough free space to hold the ZIP without passing the STORAGE_LOCATION_SIZE env. var. value
    And the instance will fail to create the Folder and it will show an error message if there is not enough space in any location
