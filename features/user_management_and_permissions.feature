Feature: User management and permissions
  The CCA DIP access application has five major user types:
    - Administrators: Administrators in user stories.
    - Managers: Reference librarians in user stories.
    - Editors: Processing Archivist in user stories.
    - Viewer: Researchers in user stories.
    - Unauthenticated: Not mentioned in the user stories.
  This user types have different permission over the application:

  Scenario: Administrators
    Given an instance running
    And a superuser created in the database with the Django task
    When an administrator logs in the app with that superuser credentials
    Then the administrator is able to view, create and edit users
    And the administrator can make users administrators
    And the administrator can add and remove users to the "Editors" and/or "Managers" groups
    And the administrator can deactivate (delete?) users
    And the administrator can access the setting page
    And the administrator has access to all the parts of the application

  Scenario: Managers
    Given an instance running
    And a user that belongs to the "Managers" group created in the application
    When a manager logs in the application with that user credentials
    Then the manager is able to view, create and edit users
    And the manager can add and remove users to the "Editors" and/or "Managers" groups
    And the manager can deactivate (delete?) users
    And the manager cannot create, edit, or delete Collections and Folders
    And the manager cannot access the setting page
    And the manager has access to all the view parts of the application

  Scenario: Editors
    Given an instance running
    And a user that belongs to the "Editors" group created in the application
    When an editor logs in the application with that user credentials
    Then the editor can't view or manage users
    And the editor can't access the setting page
    And the editor can create and edit Collections and Folders but not delete them
    And the editor has access to all the view parts of the application

  Scenario: Viewer
    Given an instance running
    And a user that is not an administrator and doesn't belongs to any group created in the application
    When a viewer logs in the application with that user credentials
    Then the viewer can browse and view Collections
    And the viewer can browse and view Folders
    And the viewer can browse and view Digital Files
    And the viewer can download the Folders ZIP files
    And the viewer cannot manage users
    And the viewer cannot access the setting page
    And the viewer cannot create, edit or delete Collections or Folders

  Scenario: Unauthenticated
    Given an instance running
    When a user without credentials tries to access the application
    Then the unauthenticated user can only see the FAQ and the login pages
    And all the other pages will redirect the unauthenticated user to the login page
