Feature: Background selection during character creation
  Background selection grants skill proficiencies, a tool proficiency, an origin
  feat, ability score bonuses, and equipment options.

  Scenario: The background catalog contains all expected backgrounds
    Given the background catalog
    Then the catalog contains 56 backgrounds
    And every background has exactly 2 skill proficiencies
    And every background has a feat
    And every background has equipment options

  Scenario: Selecting a background grants skill proficiencies
    Given a character with the background Acolyte
    Then the character is proficient in Insight
    And the character is proficient in Religion

  Scenario: Selecting a background sets the background feat
    Given a character with the background Acolyte
    Then the character background feat is Magic Initiate

  Scenario: Background feat has non-empty benefits
    Given a character with the background Acolyte
    Then the background feat has at least one benefit

  Scenario: Ability bonus mode 2/1 applies correct bonuses
    Given a character with the background Acolyte
    When ability bonus mode is set to 2/1
    Then one ability has a +2 bonus
    And one other ability has a +1 bonus

  Scenario: Ability bonus mode 1/1/1 applies correct bonuses
    Given a character with the background Acolyte
    When ability bonus mode is set to 1/1/1
    Then three abilities each have a +1 bonus

  Scenario: Background with no ability scores clears all bonuses
    Given a character with the background Shadowmasters Exile
    Then no ability has any bonus

  Scenario: Background and species origin feats are both tracked as owned
    Given a character with the background Acolyte
    And the character has origin feat Alert
    Then the owned feat names include Magic Initiate
    And the owned feat names include Alert

  Scenario: Changing background updates the feat
    Given a character with the background Acolyte
    When the background is changed to Sailor
    Then the character background feat is Tavern Brawler

  Scenario Outline: Background skill proficiencies come from the background data
    Given a character with the background <bg_name>
    Then the character is proficient in <skill>

    Examples:
      | bg_name     | skill          |
      | Soldier     | Athletics      |
      | Soldier     | Intimidation   |
      | Criminal    | Sleight of Hand|
      | Criminal    | Stealth        |
      | Sage        | Arcana         |
      | Sage        | History        |
