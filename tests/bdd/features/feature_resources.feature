Feature: Limited-use feature resources are tracked on the Features tab
  Non-spell class features, traits, feats, and subclass features with limited
  uses should expose spendable counters that restore on the correct rest.

  # ─── Fighter ────────────────────────────────────────────────────────────

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

  # ─── Barbarian ──────────────────────────────────────────────────────────

  Scenario: Barbarian Rage restores one use on a short rest and all on a long rest
    Given a level 3 barbarian character
    When the feature resource Rage is spent
    And the feature resource Rage is spent
    Then the feature resource Rage shows 1/3 uses (1 on Short Rest, full on Long Rest)
    When the character restores feature resources on a short rest
    Then the feature resource Rage shows 2/3 uses (1 on Short Rest, full on Long Rest)
    When the character restores feature resources on a long rest
    Then the feature resource Rage shows 3/3 uses (1 on Short Rest, full on Long Rest)

  # ─── Paladin ────────────────────────────────────────────────────────────

  Scenario: Paladin Lay On Hands spends from a pool and restores on a long rest
    Given a level 3 paladin character
    When 7 points of the feature resource Lay On Hands are spent
    Then the feature resource Lay On Hands shows 8/15 pool (Long Rest resets)
    When the character restores feature resources on a long rest
    Then the feature resource Lay On Hands shows 15/15 pool (Long Rest resets)

  Scenario: Paladin Lay On Hands pool does not restore on a short rest
    Given a level 3 paladin character
    When 5 points of the feature resource Lay On Hands are spent
    And the character takes a short rest without full feature restore
    Then the feature resource Lay On Hands shows 10/15 pool (Long Rest resets)

  # ─── Monk ────────────────────────────────────────────────────────────────

  Scenario: Monk Focus Points restore on a short rest
    Given a level 2 monk character
    When 2 points of the feature resource Focus Points are spent
    Then the feature resource Focus Points shows 0/2 pool (Short or Long Rest resets)
    When the character restores feature resources on a short rest
    Then the feature resource Focus Points shows 2/2 pool (Short or Long Rest resets)

  # ─── Bard ────────────────────────────────────────────────────────────────

  Scenario: Bard Bardic Inspiration uses are based on Charisma modifier
    Given a level 1 bard character
    Then the feature resource Bardic Inspiration shows 3/3 uses (Long Rest resets)
    When the feature resource Bardic Inspiration is spent
    Then the feature resource Bardic Inspiration shows 2/3 uses (Long Rest resets)
    When the character restores feature resources on a long rest
    Then the feature resource Bardic Inspiration shows 3/3 uses (Long Rest resets)

  Scenario: Bard Bardic Inspiration does not restore on a short rest at level 1
    Given a level 1 bard character
    When the feature resource Bardic Inspiration is spent
    And the character takes a short rest without full feature restore
    Then the feature resource Bardic Inspiration shows 2/3 uses (Long Rest resets)

  # ─── Cleric ──────────────────────────────────────────────────────────────

  Scenario: Cleric Channel Divinity tracks partial short-rest recovery
    Given a level 2 cleric character
    Then the feature resource Channel Divinity shows 2/2 uses (1 on Short Rest, full on Long Rest)
    When the feature resource Channel Divinity is spent
    And the feature resource Channel Divinity is spent
    Then the feature resource Channel Divinity shows 0/2 uses (1 on Short Rest, full on Long Rest)
    When the character restores feature resources on a short rest
    Then the feature resource Channel Divinity shows 1/2 uses (1 on Short Rest, full on Long Rest)
    When the character restores feature resources on a long rest
    Then the feature resource Channel Divinity shows 2/2 uses (1 on Short Rest, full on Long Rest)

  # ─── Druid ───────────────────────────────────────────────────────────────

  Scenario: Druid Wild Shape tracks partial short-rest recovery
    Given a level 2 druid character
    Then the feature resource Wild Shape shows 2/2 uses (1 on Short Rest, full on Long Rest)
    When the feature resource Wild Shape is spent
    And the feature resource Wild Shape is spent
    Then the feature resource Wild Shape shows 0/2 uses (1 on Short Rest, full on Long Rest)
    When the character restores feature resources on a short rest
    Then the feature resource Wild Shape shows 1/2 uses (1 on Short Rest, full on Long Rest)

  # ─── Sorcerer ────────────────────────────────────────────────────────────

  Scenario: Sorcerer Innate Sorcery has 2 uses restoring on a long rest
    Given a level 1 sorcerer character
    Then the feature resource Innate Sorcery shows 2/2 uses (Long Rest resets)
    When the feature resource Innate Sorcery is spent
    Then the feature resource Innate Sorcery shows 1/2 uses (Long Rest resets)
    When the character restores feature resources on a long rest
    Then the feature resource Innate Sorcery shows 2/2 uses (Long Rest resets)

  Scenario: Sorcerer Sorcery Points pool appears at level 2
    Given a level 2 sorcerer character
    Then the feature resource Sorcery Points shows 2/2 pool (Long Rest resets)
    When 2 points of the feature resource Sorcery Points are spent
    Then the feature resource Sorcery Points shows 0/2 pool (Long Rest resets)
    When the character restores feature resources on a long rest
    Then the feature resource Sorcery Points shows 2/2 pool (Long Rest resets)



  Scenario: Warding Flare exposes a spendable limit based on Wisdom modifier dynamically
    Given a level 3 cleric character
    And the character has the subclass Light Domain
    Then the feature resource Warding Flare shows 3/3 uses (Long Rest resets)
    When the feature resource Warding Flare is spent
    Then the feature resource Warding Flare shows 2/3 uses (Long Rest resets)
    When the character restores feature resources on a long rest
    Then the feature resource Warding Flare shows 3/3 uses (Long Rest resets)

  # ─── Species traits ─────────────────────────────────────────────────────

  Scenario: Species trait counters are tracked separately from class features
    Given a level 1 rogue character
    And the character is the species Orc
    Then the species trait Adrenaline Rush shows 2/2 uses (Short or Long Rest resets)
    When the feature resource Adrenaline Rush is spent
    Then the species trait Adrenaline Rush shows 1/2 uses (Short or Long Rest resets)

  # ─── Feats ──────────────────────────────────────────────────────────────

  Scenario: Lucky feat exposes a spendable pool on the feat card
    Given a level 1 rogue character
    And the character has the background feat Lucky
    Then the feat Lucky shows 2/2 pool (Long Rest resets)
    When 2 points of the feature resource Luck Points are spent
    Then the feat Lucky shows 0/2 pool (Long Rest resets)

  # ─── Subclass linked resources ──────────────────────────────────────────

  Scenario: Subclass cards can show linked shared resources
    Given a level 3 paladin character
    And the character has the subclass Oath Of The Spellguard
    Then the subclass feature Guardian Bond links Channel Divinity as 2/2 uses (1 on Short Rest, full on Long Rest)

  # ─── Pool scaling on level-up ───────────────────────────────────────────

  Scenario: Paladin Lay On Hands pool scales with level
    Given a level 1 paladin character
    Then the feature resource Lay On Hands shows 5/5 pool (Long Rest resets)
    When the paladin levels up to 2
    Then the feature resource Lay On Hands shows 10/10 pool (Long Rest resets)
    When the paladin levels up to 3
    Then the feature resource Lay On Hands shows 15/15 pool (Long Rest resets)

  Scenario: Sorcery Points pool scales with level
    Given a level 2 sorcerer character
    Then the feature resource Sorcery Points shows 2/2 pool (Long Rest resets)
    When the sorcerer levels up to 3
    Then the feature resource Sorcery Points shows 3/3 pool (Long Rest resets)

  Scenario: Spent pool values are clamped when the maximum changes on level-up
    Given a level 1 paladin character
    When 5 points of the feature resource Lay On Hands are spent
    Then the feature resource Lay On Hands shows 0/5 pool (Long Rest resets)
    When the paladin levels up to 2
    Then the feature resource Lay On Hands shows 5/10 pool (Long Rest resets)

  # ─── Overspend protection ───────────────────────────────────────────────

  Scenario: Spending more than remaining uses is rejected
    Given a level 2 fighter character
    When the feature resource Action Surge is spent
    Then spending the feature resource Action Surge again is rejected

  Scenario: Spending more pool points than remaining is rejected
    Given a level 1 paladin character
    Then spending 6 points of the feature resource Lay On Hands is rejected

  # ─── Restorable resource listing ────────────────────────────────────────

  Scenario: Long rest lists all restorable resources
    Given a level 2 fighter character
    When the feature resource Second Wind is spent
    And the feature resource Action Surge is spent
    Then long rest restorable resources include Second Wind
    And long rest restorable resources include Action Surge

  Scenario: Short rest lists only short-rest restorable resources
    Given a level 1 sorcerer character
    Then short rest restorable resources do not include Innate Sorcery

  # ─── No-resource classes (negative coverage) ────────────────────────────

  Scenario: Artificer Tinker's Magic uses are based on Intelligence modifier
    Given a level 1 artificer character
    Then the feature resource Tinker's Magic shows 3/3 uses (Long Rest resets)
    When the feature resource Tinker's Magic is spent
    Then the feature resource Tinker's Magic shows 2/3 uses (Long Rest resets)
    When the character restores feature resources on a long rest
    Then the feature resource Tinker's Magic shows 3/3 uses (Long Rest resets)

  Scenario: Rogue has no feature resources through level 3
    Given a level 3 rogue character
    Then the character has no active feature resources

  Scenario: Wizard Arcane Recovery has 1 use restoring on a long rest
    Given a level 1 wizard character
    Then the feature resource Arcane Recovery shows 1/1 uses (Long Rest resets)
    When the feature resource Arcane Recovery is spent
    Then spending the feature resource Arcane Recovery again is rejected
    When the character restores feature resources on a long rest
    Then the feature resource Arcane Recovery shows 1/1 uses (Long Rest resets)

  Scenario: Warlock Magical Cunning has 1 use restoring on a long rest
    Given a level 2 warlock character
    Then the feature resource Magical Cunning shows 1/1 uses (Long Rest resets)
    When the feature resource Magical Cunning is spent
    Then spending the feature resource Magical Cunning again is rejected
    When the character restores feature resources on a long rest
    Then the feature resource Magical Cunning shows 1/1 uses (Long Rest resets)

  # ─── Scrubbing ──────────────────────────────────────────────────────────

  Scenario: Spent feature resources are scrubbed when the owning card disappears
    Given a level 1 rogue character
    And the character is the species Orc
    When the feature resource Adrenaline Rush is spent
    And the character changes species to Aasimar
    Then the species trait Adrenaline Rush is no longer tracked
    And no feature resources are marked as spent
