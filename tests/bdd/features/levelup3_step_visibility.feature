Feature: Level-up wizard step visibility (level 2→3)
  At level 3 every class gains a subclass. No class gets ASI, proficiency, or
  language steps.

  Scenario Outline: Every class shows class, hp, features, and subclass steps
    Given a level-2 <class_name> character ready to level up to 3
    When the level-3 visible steps are computed
    Then the level-3 visible steps include lu_class
    And the level-3 visible steps include lu_hp
    And the level-3 visible steps include lu_features
    And the level-3 visible steps include lu_subclass

    Examples:
      | class_name |
      | Artificer  |
      | Barbarian  |
      | Bard       |
      | Cleric     |
      | Druid      |
      | Fighter    |
      | Monk       |
      | Paladin    |
      | Ranger     |
      | Rogue      |
      | Sorcerer   |
      | Warlock    |
      | Wizard     |

  Scenario Outline: Casters show the spells step at level 3
    Given a level-2 <class_name> character ready to level up to 3
    When the level-3 visible steps are computed
    Then the level-3 visible steps include lu_spells

    Examples:
      | class_name |
      | Artificer  |
      | Bard       |
      | Cleric     |
      | Druid      |
      | Paladin    |
      | Ranger     |
      | Sorcerer   |
      | Warlock    |
      | Wizard     |

  Scenario Outline: Non-casters do not show the spells step at level 3
    Given a level-2 <class_name> character ready to level up to 3
    When the level-3 visible steps are computed
    Then the level-3 visible steps do not include lu_spells

    Examples:
      | class_name |
      | Barbarian  |
      | Fighter    |
      | Monk       |
      | Rogue      |

  Scenario Outline: Swap-eligible classes show the swap step at level 3
    Given a level-2 <class_name> character ready to level up to 3
    And the level-3 character has existing spells
    When the level-3 visible steps are computed
    Then the level-3 visible steps include lu_swap

    Examples:
      | class_name |
      | Bard       |
      | Sorcerer   |
      | Warlock    |

  Scenario Outline: No class gets ASI, proficiencies, or languages at level 3
    Given a level-2 <class_name> character ready to level up to 3
    When the level-3 visible steps are computed
    Then the level-3 visible steps do not include lu_asi
    And the level-3 visible steps do not include lu_proficiencies
    And the level-3 visible steps do not include lu_languages

    Examples:
      | class_name |
      | Artificer  |
      | Barbarian  |
      | Bard       |
      | Cleric     |
      | Druid      |
      | Fighter    |
      | Monk       |
      | Paladin    |
      | Ranger     |
      | Rogue      |
      | Sorcerer   |
      | Warlock    |
      | Wizard     |
