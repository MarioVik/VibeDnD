Feature: Level-up features display (level 2→3)
  The Features step shows new class features. At level 3 every class gets a
  subclass (handled by its own step) plus some classes get additional features.

  Scenario Outline: Each class has its subclass feature listed at level 3
    Given a level-2 <class_name> character ready to level up to 3
    Then the level 3 features include <subclass_feature>

    Examples:
      | class_name | subclass_feature      |
      | Artificer  | Artificer Subclass    |
      | Barbarian  | Barbarian Subclass    |
      | Bard       | Bard Subclass         |
      | Cleric     | Cleric Subclass       |
      | Druid      | Druid Subclass        |
      | Fighter    | Fighter Subclass      |
      | Monk       | Monk Subclass         |
      | Paladin    | Paladin Subclass      |
      | Ranger     | Ranger Subclass       |
      | Rogue      | Rogue Subclass        |
      | Sorcerer   | Sorcerer Subclass     |
      | Warlock    | Warlock Subclass      |
      | Wizard     | Wizard Subclass       |

  Scenario Outline: Classes with additional features at level 3
    Given a level-2 <class_name> character ready to level up to 3
    Then the level 3 features include <feature_name>

    Examples:
      | class_name | feature_name       |
      | Barbarian  | Primal Knowledge   |
      | Monk       | Deflect Attacks    |
      | Paladin    | Channel Divinity   |
      | Rogue      | Steady Aim         |
