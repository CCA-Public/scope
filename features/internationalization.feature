Feature: Internationalization
  SCOPE will have an interface that can be shown in different languages,
  with English as the default language. On this first iteration of the feature,
  the translation process won't include configuration/tasks to integrate with
  translation web services like Transifex or Pootle and it will only include English
  and French languages. This feature only defines the internationalization of the interface,
  it doesn't add the ability to translate the Collection, Folder and DigitalFile metadata
  in the database and Elasticseach indexes.

  Scenario: Application user
    Given an instance running with the internationalization system setup
    When an application user accesses the interface
    Then the interface will appear in the user's browser default language
      But the language will default to English if the user browser's default language is not available
    And a drop-down menu will be shown in the header with the available languages
    And the user will be able to switch the interface to a different language

  Scenario: Developer
    Given a developer working on the source code of the application
    When the developer adds, modifies or edits translation strings
    Then the developer must run a Django task in the command line
    And those string changes will be available in the translation files
    And the developer will commit all the changes to the source code

  Scenario: Translator
    Given a translator notified that new strings are available for translation
    When the translator makes changes to the translation files
    And those changes are added to the source code of the application
    And they are deployed to a running instance
    Then the interface will display the translator changes
