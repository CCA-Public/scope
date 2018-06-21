Feature: Data tables
  The CCA DIP access application uses four types of tables to display its metadata:
    - Collections: used in the home page.
    - Folders: used in the Collection page.
    - All Digital Files: used in the search page.
    - Folder Digital Files: used in the Folder page.

  Scenario: All tables
    Given an instance running
    And with some Collections, Folders and/or Digital Files created
    When a user visits one of the pages with data tables
    Then the page will use the Elasticsearch indexes to fetch the table data
    And the table will show a search field and button on top to filter the results
    And the table will show ten results
      And the total results and the range being shown will appear at the botton
      And a pager will be shown at the bottom to go to a different range of results
    And some of the table headers will have the option to sort in both directions
    And the table will have a column with a button to view each result

  Scenario: Collections table
    Given an instance running with some Collections created
    When a user visits the home page
    Then the page will use the Collections Elasticsearch index
    And the table will show the following columns and fields
      | column_name | es_field       |
      | Identifier  | identifier     |
      | Title       | dc.title       |
      | Description | dc.description |
    And the search form will query over the following fields
      | es_field       |
      | identifier     |
      | dc.title       |
      | dc.description |
    And the table header will show sort options for the following columns
      | column_name |
      | Identifier  |
      | Title       |

  Scenario: Folders table
    Given an instance running with some Folders created
    When a user visits a Collection page with some child folders
    Then the page will use the Folders Elasticsearch index
    And the table will show only Folders from that Collection
    And the table will show the following columns and fields
      | column_name | es_field       |
      | Identifier  | identifier     |
      | Title       | dc.title       |
      | Date        | dc.date        |
      | Description | dc.description |
    And the search form will query over the following fields
      | es_field       |
      | identifier     |
      | dc.title       |
      | dc.date        |
      | dc.description |
    And the table header will show sort options for the following columns
      | column_name |
      | Identifier  |
      | Title       |

  Scenario: All Digital Files table
    Given an instance running with some Digital Files created
    When a user visits the search page
    Then the page will use the Digital Files Elasticsearch index
    And the table will show the following columns and fields
      | column_name   | es_field       |
      | Filepath      | filepath       |
      | Format        | fileformat     |
      | Size (bytes)  | size_bytes     |
      | Last modified | datemodified   |
      | Folder        | dip.identifier | # link to Folder
    And the search form will query over the following fields
      | es_field       |
      | filepath       |
      | fileformat     |
      | datemodified   |
      | dip.identifier |
    And the table header will show sort options for the following columns
      | column_name  |
      | Filepath     |
      | Format       |
      | Size (bytes) |

  Scenario: Folder Digital Files table
    Given an instance running with some Digital Files created
    When a user visits a Folder page with some child Digital Files
    Then the page will use the Digital Files Elasticsearch index
    And the table will show only Digital Files from that Folder
    And the table will show the following columns and fields
      | column_name   | es_field     |
      | Filepath      | filepath     |
      | Format        | fileformat   |
      | Size (bytes)  | size_bytes   |
      | Last modified | datemodified |
    And the search form will query over the following fields
      | es_field     |
      | filepath     |
      | fileformat   |
      | datemodified |
    And the table header will show sort options for the following columns
      | column_name  |
      | Filepath     |
      | Format       |
      | Size (bytes) |
