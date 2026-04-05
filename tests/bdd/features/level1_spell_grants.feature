Feature: Level 1 spell grants integrate with character creation
  Extra spells from class features, species, and feats should appear in the
  spellbook without consuming base class spell picks, while choice-driven
  sources should still report the right follow-up requirements.

  Scenario: Artificer fixed cantrips stay outside the class cantrip quota
    Given a fully completed level 1 artificer character
    Then the spellbook includes Mending granted by Tinker's Magic
    And Mending is not a selectable base cantrip for that character
    And the spellbook includes 3 cantrips total

  Scenario Outline: Fixed class spell grants stay out of base level 1 spell picks
    Given a fully completed level 1 <class_slug> character
    Then the spellbook includes <spell_name> granted by <source_label>
    And <spell_name> is not a selectable base level 1 spell for that character

    Examples:
      | class_slug | spell_name          | source_label   |
      | druid      | Speak with Animals  | Druidic        |
      | ranger     | Hunter's Mark       | Favored Enemy  |

  Scenario: A non-caster with magical species traits still gets the spells step
    Given a level 1 rogue character
    And the character is the species Aasimar
    When spell grant defaults are applied
    Then the character has spell step content
    And the spellbook includes Light granted by Aasimar

  Scenario: Magic Initiate remains chooser-driven on the spells step
    Given a level 1 rogue character
    And the character has the species origin feat Magic Initiate
    Then the Magic Initiate source requires a spell list choice
    When the Magic Initiate source spell list is set to Cleric
    Then the Magic Initiate source requires 2 cantrip choices and 1 spell choices

  Scenario: Aberrant Dragonmark remains chooser-driven until both spell picks are made
    Given a level 1 rogue character
    And the character has the species origin feat Aberrant Dragonmark
    Then the Aberrant Dragonmark source requires 1 cantrip choices and 1 spell choices

  Scenario: Caster spell-grant abilities default to the class spellcasting ability
    Given a level 1 wizard character
    And the character has the species origin feat Mark Of Detection
    When spell grant defaults are applied
    Then the Mark Of Detection source uses Intelligence as its spellcasting ability

  Scenario: Confirmed non-class spellcasting abilities are preserved
    Given a level 1 wizard character
    And the character has the species origin feat Mark Of Detection
    And the Mark Of Detection source uses Wisdom as its spellcasting ability
    When spell grant defaults are applied
    Then the Mark Of Detection source uses Wisdom as its spellcasting ability

  Scenario: Cold Caster becomes a chooser when Ray of Frost is already known
    Given a level 1 rogue character
    And the character is the species Rimekin
    And the character has the species origin feat Cold Caster
    When spell grant defaults are applied
    Then the Cold Caster source offers 1 cantrip choice instead of a fixed cantrip

  Scenario: Mark feats expand the class spell list without auto-preparing those spells
    Given a level 1 wizard character
    And the character has the species origin feat Mark Of Detection
    When spell grant defaults are applied
    Then Identify is a selectable base level 1 spell for that character
    And the spellbook does not include Identify

  Scenario: Free spell summary entries stay separate by source and resolve proficiency bonus
    Given a level 1 rogue character
    And the character is the species Gnome with the Forest Gnome lineage
    And the character has the species origin feat Mark Of Handling
    When spell grant defaults are applied
    Then the free spell summary includes Speak with Animals (Forest Gnome) - 2 / Long Rest
    And the free spell summary includes Speak with Animals (Mark Of Handling) - 1 / Long Rest

  Scenario: Potent Dragonmark tags mark spells and adds the dragonmark slot summary
    Given a level 1 wizard character
    And the character has the species origin feat Mark Of Detection
    And the character has the background feat Potent Dragonmark
    When spell grant defaults are applied
    Then the spellbook includes Detect Magic granted by Mark Of Detection
    And the spellbook includes Identify granted by Mark Of Detection
    And Detect Magic is tagged as a Dragonmark spell
    And Identify is tagged as a Dragonmark spell
    And the free spell summary includes 1 Dragonmark spell - 1 / Short or Long Rest
