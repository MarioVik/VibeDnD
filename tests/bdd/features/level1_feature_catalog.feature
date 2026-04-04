Feature: Level 1 class feature catalog
  The repository keeps a human-readable and executable catalog of every class
  feature granted at level 1.

  Scenario: Markdown documentation covers every level 1 class feature
    Given the level 1 class feature catalog
    Then the markdown specification documents every level 1 class feature

  Scenario: The code catalog classifies every level 1 class feature
    Given the level 1 class feature catalog
    Then every catalog entry has a valid category and wizard surface
