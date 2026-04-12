Feature: Level-up spell swap (level 1→2)
  Bard, Sorcerer, and Warlock can swap one cantrip and/or one spell during
  level-up if they have existing selections.

  Scenario Outline: Swap-eligible classes can swap when they have spells
    Given a level-1 <class_name> character ready to level up
    And the character has existing spells
    Then spell swap is available

    Examples:
      | class_name |
      | Bard       |
      | Sorcerer   |
      | Warlock    |

  Scenario Outline: Non-swap classes cannot swap
    Given a level-1 <class_name> character ready to level up
    Then spell swap is not available

    Examples:
      | class_name |
      | Artificer  |
      | Barbarian  |
      | Cleric     |
      | Druid      |
      | Fighter    |
      | Monk       |
      | Paladin    |
      | Ranger     |
      | Rogue      |
      | Wizard     |

  Scenario: Swap step is valid when no swap is in progress
    Given a level-1 Bard character ready to level up
    Then the swap step is valid

  Scenario: Swap step is invalid when cantrip out selected but no cantrip in
    Given a level-1 Bard character ready to level up
    When a cantrip swap out is selected without a swap in
    Then the swap step is invalid

  Scenario: Swap step is invalid when spell out selected but no spell in
    Given a level-1 Bard character ready to level up
    When a spell swap out is selected without a swap in
    Then the swap step is invalid
