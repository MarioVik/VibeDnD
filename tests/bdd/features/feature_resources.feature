Feature: Limited-use feature resources are tracked on the Features tab
  Non-spell class features, traits, feats, and subclass features with limited
  uses should expose spendable counters that restore on the correct rest.

  Scenario: Fighter Second Wind tracks partial short-rest recovery and Tactical Mind links it
    Given a level 2 fighter character
    Then the feature resource Second Wind shows 2/2 uses (1 on Short Rest, full on Long Rest)
    And the class feature Tactical Mind links Second Wind as 2/2 uses (1 on Short Rest, full on Long Rest)
    When the feature resource Second Wind is spent
    Then the feature resource Second Wind shows 1/2 uses (1 on Short Rest, full on Long Rest)
    When the character restores feature resources on a short rest
    Then the feature resource Second Wind shows 2/2 uses (1 on Short Rest, full on Long Rest)

  Scenario: Fighter Action Surge restores fully on a short rest
    Given a level 2 fighter character
    When the feature resource Action Surge is spent
    Then the feature resource Action Surge shows 0/1 uses (Short or Long Rest resets)
    When the character restores feature resources on a short rest
    Then the feature resource Action Surge shows 1/1 uses (Short or Long Rest resets)

  Scenario: Barbarian Rage restores one use on a short rest and all on a long rest
    Given a level 3 barbarian character
    When the feature resource Rage is spent
    And the feature resource Rage is spent
    Then the feature resource Rage shows 1/3 uses (1 on Short Rest, full on Long Rest)
    When the character restores feature resources on a short rest
    Then the feature resource Rage shows 2/3 uses (1 on Short Rest, full on Long Rest)
    When the character restores feature resources on a long rest
    Then the feature resource Rage shows 3/3 uses (1 on Short Rest, full on Long Rest)

  Scenario: Paladin Lay On Hands spends from a pool and restores on a long rest
    Given a level 3 paladin character
    When 7 points of the feature resource Lay On Hands are spent
    Then the feature resource Lay On Hands shows 8/15 pool (Long Rest resets)
    When the character restores feature resources on a long rest
    Then the feature resource Lay On Hands shows 15/15 pool (Long Rest resets)

  Scenario: Monk Focus Points restore on a short rest
    Given a level 2 monk character
    When 2 points of the feature resource Focus Points are spent
    Then the feature resource Focus Points shows 0/2 pool (Short or Long Rest resets)
    When the character restores feature resources on a short rest
    Then the feature resource Focus Points shows 2/2 pool (Short or Long Rest resets)

  Scenario: Species trait counters are tracked separately from class features
    Given a level 1 rogue character
    And the character is the species Orc
    Then the species trait Adrenaline Rush shows 2/2 uses (Short or Long Rest resets)
    When the feature resource Adrenaline Rush is spent
    Then the species trait Adrenaline Rush shows 1/2 uses (Short or Long Rest resets)

  Scenario: Lucky feat exposes a spendable pool on the feat card
    Given a level 1 rogue character
    And the character has the background feat Lucky
    Then the feat Lucky shows 2/2 pool (Long Rest resets)
    When 2 points of the feature resource Luck Points are spent
    Then the feat Lucky shows 0/2 pool (Long Rest resets)

  Scenario: Subclass cards can show linked shared resources
    Given a level 3 paladin character
    And the character has the subclass Oath Of The Spellguard
    Then the subclass feature Guardian Bond links Channel Divinity as 2/2 uses (1 on Short Rest, full on Long Rest)

  Scenario: Spent feature resources are scrubbed when the owning card disappears
    Given a level 1 rogue character
    And the character is the species Orc
    When the feature resource Adrenaline Rush is spent
    And the character changes species to Aasimar
    Then the species trait Adrenaline Rush is no longer tracked
    And no feature resources are marked as spent
