Feature: Level-up wizard step visibility (level 1→2)
  The level-up wizard shows different steps depending on the class being levelled.
  At level 2 no class gets subclass, ASI, or proficiency steps.

  Scenario Outline: Every class always shows class, hp, and features steps
    Given a level-1 <class_name> character ready to level up
    When the visible level-up steps are computed
    Then the visible steps include lu_class
    And the visible steps include lu_hp
    And the visible steps include lu_features

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

  Scenario Outline: Casters with new spells show the spells step
    Given a level-1 <class_name> character ready to level up
    When the visible level-up steps are computed
    Then the visible steps include lu_spells

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

  Scenario Outline: Non-casters do not show the spells step at level 2
    Given a level-1 <class_name> character ready to level up
    When the visible level-up steps are computed
    Then the visible steps do not include lu_spells

    Examples:
      | class_name |
      | Barbarian  |
      | Fighter    |
      | Monk       |
      | Rogue      |

  Scenario Outline: Classes with class choices at level 2 show the choices step
    Given a level-1 <class_name> character ready to level up
    When the visible level-up steps are computed
    Then the visible steps include lu_choices

    Examples:
      | class_name |
      | Artificer  |
      | Sorcerer   |
      | Warlock    |

  Scenario Outline: Classes without class choices at level 2 do not show the choices step
    Given a level-1 <class_name> character ready to level up
    When the visible level-up steps are computed
    Then the visible steps do not include lu_choices

    Examples:
      | class_name |
      | Barbarian  |
      | Bard       |
      | Cleric     |
      | Druid      |
      | Fighter    |
      | Monk       |
      | Paladin    |
      | Ranger     |
      | Rogue      |
      | Wizard     |

  Scenario Outline: Swap-eligible classes show the swap step when they have spells
    Given a level-1 <class_name> character ready to level up
    And the character has existing spells
    When the visible level-up steps are computed
    Then the visible steps include lu_swap

    Examples:
      | class_name |
      | Bard       |
      | Sorcerer   |
      | Warlock    |

  Scenario: Ranger shows the language step at level 2
    Given a level-1 Ranger character ready to level up
    When the visible level-up steps are computed
    Then the visible steps include lu_languages

  Scenario Outline: Non-ranger classes do not show the language step
    Given a level-1 <class_name> character ready to level up
    When the visible level-up steps are computed
    Then the visible steps do not include lu_languages

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
      | Rogue      |
      | Sorcerer   |
      | Warlock    |
      | Wizard     |

  Scenario Outline: No class gets subclass or ASI at level 2
    Given a level-1 <class_name> character ready to level up
    When the visible level-up steps are computed
    Then the visible steps do not include lu_subclass
    And the visible steps do not include lu_asi

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
