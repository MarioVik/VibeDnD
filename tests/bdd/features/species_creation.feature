Feature: Species selection during character creation
  Species selection sets traits, sub-choices, size, and optionally grants an
  origin feat.  All species traits must be accessible on the character sheet.

  Scenario: The species catalog contains all expected species
    Given the species catalog
    Then the catalog contains 22 species
    And every species has at least one trait

  Scenario Outline: Species requiring a lineage sub-choice block completion without one
    Given a character with the species <species_name>
    When no sub-choice has been made
    Then the species step is invalid

    Examples:
      | species_name |
      | Elf          |
      | Tiefling     |

  Scenario Outline: Species requiring a trait-option sub-choice block completion without one
    Given a character with the species <species_name>
    When no sub-choice has been made
    Then the species step is invalid

    Examples:
      | species_name |
      | Gnome        |
      | Goliath      |
      | Shifter      |

  Scenario Outline: Species with a sub-choice are valid once a choice is made
    Given a character with the species <species_name>
    When the sub-choice <sub_choice> is selected
    Then the species step is valid

    Examples:
      | species_name | sub_choice                       |
      | Elf          | Drow                             |
      | Elf          | High Elf                         |
      | Tiefling     | Infernal                         |
      | Gnome        | Forest Gnome                     |
      | Goliath      | Stone's Endurance (Stone Giant)   |
      | Shifter      | Beasthide                        |

  Scenario Outline: Species with size options default to the first option
    Given a character with the species <species_name>
    Then the character size is <default_size>

    Examples:
      | species_name | default_size |
      | Aasimar      | Medium       |
      | Human        | Medium       |
      | Tiefling     | Medium       |

  Scenario: Species without sub-choices are immediately valid
    Given a character with the species Dwarf
    Then the species step is valid

  Scenario: Human grants an origin feat via the Versatile trait
    Given a character with the species Human
    Then the species grants an origin feat

  Scenario Outline: Non-Human species do not grant an origin feat
    Given a character with the species <species_name>
    Then the species does not grant an origin feat

    Examples:
      | species_name |
      | Dwarf        |
      | Elf          |
      | Gnome        |
      | Dragonborn   |
      | Halfling     |

  Scenario: Species traits produce non-empty trait cards
    Given a character with the species Dragonborn
    Then the species trait cards are not empty

  Scenario Outline: Trait-option species exclude radio options from general trait cards
    Given a character with the species <species_name>
    Then the trait cards exclude <excluded_trait>

    Examples:
      | species_name | excluded_trait                    |
      | Gnome        | Forest Gnome                     |
      | Gnome        | Rock Gnome                       |
      | Goliath      | Stone's Endurance (Stone Giant)   |
      | Shifter      | Beasthide                        |

  Scenario: Species speed is set on the character
    Given a character with the species Dwarf
    Then the character speed is 30

  Scenario: Selecting a new species clears the previous origin feat
    Given a character with the species Human
    And the character has origin feat Alert
    When the species is changed to Dwarf
    Then the character has no species origin feat
