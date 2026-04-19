Feature: All rest-based features are rigorously tracked or deliberately excluded
  To prevent new subclasses or species from silently introducing untracked
  mechanics, all game data entries possessing "Short Rest" or "Long Rest" 
  descriptions must be validated against the feature tracking engine or placed
  on the strict skip-list for future resolution.

  Scenario: Game data rest limits are comprehensively tracked
    Given the core game data is loaded
    Then all class features mentioning rests are either tracked or legitimately excluded
    And all subclass features mentioning rests are either tracked or legitimately excluded
    And all species traits mentioning rests are either tracked or legitimately excluded
    And all feats mentioning rests are either tracked or legitimately excluded
