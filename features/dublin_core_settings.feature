Feature: Dublin Core settings
  SCOPE will include a settings page, initially with the ability to configure
  the Dublin Core metadata fields used for Collections and Folders.

  Scenario: Settings page
    Given an instance running
    When an application user logs in the application
    Then the user menu drop-down will show a link to go to a settings page
      But only if the user is an Administrator

  Scenario: Dublin Core settings
    Given an instance running
    When an administrator user goes to the settings page
    Then the settings page will show a form with two fields to configure the DC settings
    And the first field will be called "Optional Dublin Core fields"
      And this field will use a multi-select input
      And this field will include a list with the following optional DC fields:
        | fields:     |
        | title       |
        | creator     |
        | subject     |
        | description |
        | publisher   |
        | contributor |
        | date        |
        | type        |
        | format      |
        | source      |
        | language    |
        | coverage    |
        | rights      |
        | isPartOf    |
      And all the DC fields will be selected by default
    And the second field will be called "Hide empty Dublin Core fields"
      And this field will use a check-box input
      And this check-box will be checked by default

  Scenario: Optional DC fields settings behavior
    Given an instance running
    When a user with enough permissions goes to one of the following pages:
      | pages:          |
      | New Collection  |
      | Edit Collection |
      | View Collection |
      | Edit Folder     |
      | View Folder     |
    Then the new and edit forms will only include the fields selected in the setting
    And the view pages will only show the fields selected in the setting

  Scenario: Hide empty DC fields settings behavior
    Given an instance running
    When a user with enough permissions goes to one of the following pages:
      | pages:          |
      | View Collection |
      | View Folder     |
    Then the page will only show the DC fields configured to be shown in the "Optional Dublin Core fields" setting that have data if the "Hide empty DC fields" setting is checked
    And the page will show all optional DC fields configured to be shown in the "Optional Dublin Core fields" setting if the "Hide empty DC fields" setting is not checked
