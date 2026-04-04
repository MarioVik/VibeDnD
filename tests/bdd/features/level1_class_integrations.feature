Feature: Level 1 class creation rule integrations
  Class-specific rules can alter spell counts, proficiencies, skill bonuses,
  language counts, and nested creation requirements.

  Scenario: Cleric orders change level 1 creation grants
    Given a level 1 cleric character
    When the cleric chooses the Thaumaturge order
    Then the cleric gains 1 extra cantrip choice
    And the cleric gains a Wisdom bonus to Arcana and Religion
    When the cleric chooses the Protector order
    Then the cleric gains heavy armor and martial weapon proficiency

  Scenario: Druid orders change level 1 creation grants
    Given a level 1 druid character
    When the druid chooses the Magician order
    Then the druid gains 1 extra cantrip choice
    And the druid gains a Wisdom bonus to Arcana and Nature
    When the druid chooses the Warden order
    Then the druid gains medium armor and martial weapon proficiency

  Scenario Outline: Martial classes expose the correct weapon mastery counts
    Given a level 1 <class_slug> character
    Then the <class_slug> requires <count> weapon mastery choices

    Examples:
      | class_slug | count |
      | barbarian  | 2     |
      | fighter    | 3     |
      | paladin    | 2     |
      | ranger     | 2     |
      | rogue      | 2     |

  Scenario: Rogue expertise must come from proficient skills
    Given a fully completed level 1 rogue character
    When the rogue selects a non-proficient expertise skill
    Then the rogue-expertise blocker is reported for that character
    And the rogue receives 3 total level 1 language choices

  Scenario: Rogue weapon mastery options stay within the rogue pool
    Given a level 1 rogue character
    Then the rogue weapon mastery pool includes Dagger
    And the rogue weapon mastery pool includes Shortsword
    And the rogue weapon mastery pool excludes Greatsword

  Scenario: Druid feature text includes the selected order
    Given a fully completed level 1 druid character
    Then the Primal Order feature annotation shows Warden

  Scenario: Barbarian feature text includes the selected mastery weapons
    Given a fully completed level 1 barbarian character
    Then the Weapon Mastery feature annotation shows the selected weapons

  Scenario: The level 1 creation summary includes non-feature choices
    Given a fully completed level 1 rogue character
    Then the level 1 creation choice summary lists skills, expertise, languages, and equipment

  Scenario: Warlock feature text includes the selected invocation details
    Given a fully completed level 1 warlock character with the Pact of the Tome invocation
    Then the Eldritch Invocations feature annotation shows Pact of the Tome details

  Scenario: Warlock blast invocations require a cantrip binding
    Given a fully completed level 1 warlock character with the Agonizing Blast invocation
    When the invocation cantrip binding is removed from that character
    Then the warlock-invocation-cantrip blocker is reported for that character

  Scenario: Pact of the Tome requires nested cantrip choices
    Given a fully completed level 1 warlock character with the Pact of the Tome invocation
    When one Pact of the Tome cantrip is removed from that character
    Then the warlock-tome-cantrips blocker is reported for that character

  Scenario: Pact of the Tome requires nested ritual choices
    Given a fully completed level 1 warlock character with the Pact of the Tome invocation
    When one Pact of the Tome ritual is removed from that character
    Then the warlock-tome-rituals blocker is reported for that character

  Scenario: Lessons of the First Ones requires an origin feat choice
    Given a fully completed level 1 warlock character with the Lessons of the First Ones invocation
    When the granted origin feat choice is removed from that character
    Then the warlock-lessons-feat blocker is reported for that character
