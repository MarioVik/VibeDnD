Feature: Feat selection during character creation
  The feat step handles the optional species origin feat (granted by Human
  Versatile).  Background feats and species origin feats are tracked together
  to prevent duplicates.

  Scenario: Origin feat catalog contains 23 feats
    Given the origin feat catalog
    Then the catalog contains 23 origin feats

  Scenario: Human triggers the species origin feat step
    Given a character with the species Human
    Then the feat step requires a selection

  Scenario: Non-Human species hides the origin feat step
    Given a character with the species Dwarf
    Then the feat step does not require a selection

  Scenario: Selecting a species origin feat sets it on the character
    Given a character with the species Human
    When the species origin feat Alert is selected
    Then the character species origin feat is Alert

  Scenario: Owned feat names include background feat
    Given a character with the background Acolyte
    Then the owned feat names include Magic Initiate

  Scenario: Owned feat names include species origin feat
    Given a character with the species Human
    When the species origin feat Lucky is selected
    Then the owned feat names include Lucky

  Scenario: Owned feat names include warlock lessons feat
    Given a warlock character with Lessons of the First Ones
    Then the character owns the warlock lessons feat

  Scenario: Duplicate feat between background and species origin is detected
    Given a character with the background Acolyte
    And the character has origin feat Magic Initiate
    Then Magic Initiate appears in owned feat names

  Scenario: Feat benefits are present for background feat on the sheet
    Given a character with the background Acolyte
    Then the background feat has benefits with names and descriptions

  Scenario: Feat benefits are present for species origin feat on the sheet
    Given a character with the species Human
    When the species origin feat Alert is selected
    Then the species origin feat has benefits with names and descriptions
