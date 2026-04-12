Feature: Level-up features display (level 1→2)
  The Features step shows new class features and extra progression columns.
  It is always valid (informational only).

  Scenario Outline: Each class has the expected features at level 2
    Given a level-1 <class_name> character ready to level up
    Then the level 2 features include <feature_name>

    Examples:
      | class_name | feature_name              |
      | Artificer  | Replicate Magic Item      |
      | Barbarian  | Danger Sense              |
      | Barbarian  | Reckless Attack           |
      | Bard       | Expertise                 |
      | Bard       | Jack of all Trades        |
      | Cleric     | Channel Divinity          |
      | Druid      | Wild Shape                |
      | Druid      | Wild Companion            |
      | Fighter    | Action Surge (One Use)    |
      | Fighter    | Tactical Mind             |
      | Monk       | Monk's Focus              |
      | Monk       | Unarmored Movement        |
      | Monk       | Uncanny Metabolism        |
      | Paladin    | Fighting Style            |
      | Paladin    | Paladin's Smite           |
      | Ranger     | Deft Explorer             |
      | Ranger     | Fighting Style            |
      | Rogue      | Cunning Action            |
      | Sorcerer   | Font of Magic             |
      | Sorcerer   | Metamagic                 |
      | Warlock    | Magical Cunning           |
      | Wizard     | Scholar                   |

  Scenario Outline: Feature descriptions are available for level 2 features
    Given a level-1 <class_name> character ready to level up
    Then the level 2 feature <feature_name> has a description

    Examples:
      | class_name | feature_name              |
      | Barbarian  | Danger Sense              |
      | Bard       | Expertise                 |
      | Cleric     | Channel Divinity          |
      | Fighter    | Action Surge              |
      | Rogue      | Cunning Action            |
      | Wizard     | Scholar                   |

  Scenario: The features step is always valid
    Given a level-1 Fighter character ready to level up
    Then the features step is valid
