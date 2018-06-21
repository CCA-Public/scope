Feature: Elasticsearch integration
  The CCA DIP access application uses Elasticsearch 6.x to improve the search capabilities
  of the application. The database is the persistent data storage service and a CLI task is
  defined to index the data in three different indexes for Collections, Folders and Digital
  Files. The configuration for the connection between the application and Elasticsearch is
  defined by the following environment variables:
    - ES_HOSTS: (REQUIRED) List of Elasticsearch hosts separated by comma. RFC-1738 formatted
      URLs can be used. E.g.: https://user:secret@host:443/.
    - ES_TIMEOUT: Timeout in seconds for Elasticsearch requests. Default: 10.
    - ES_POOL_SIZE: Elasticsearch requests pool size. Default: 10.
    - ES_INDEXES_SHARDS: Number of shards for Elasticsearch indexes. Default: 1.
    - ES_INDEXES_REPLICAS: Number of replicas for Elasticsearch indexes. Default: 0.

  Scenario: Installation
    Given an instance being installed after the database has been initialized
    And at least the required variable "ES_HOSTS" has been defined in the environment
    When a system administrator installing the application runs the "inde_data" CLI task
    Then the task will create three indexes in the configured Elasticsearch instance
    And the task will show that there are no Collections, Folders or Digital Tiles to index

  Scenario: Upgrade and/or re-index data
    Given an instance installed
    And with Collection, Folder or Digital File data in the database
    And at least the required variable "ES_HOSTS" defined in the environment
    When a system administrator runs the "inde_data" CLI task
    Then the task will re-create the three indexes in the configured Elasticsearch instance
    And the task will add all Collections, Folders and Digital Tiles to their indexes
    And the task will show indication of the progress

  Scenario: Model changes
    Given an instance running
    When a user creates, edits or deletes a resource in the interface
    Then the instance will update the Elasticsearch indexes to keep them in sync. with the database

  Scenario: Data tables
    Given an instance running with some data
    When a data table for Collections, Folders or Digital Files is displayed in the interface
    Then the search indexes are used to query, sort, paginate and fetch the data
    And the values shown in the table will come from the Elasticsearch index
    # See the data_tables.feature file for more info about the data indexed
    # in Elasticsearch for display, sort and search
