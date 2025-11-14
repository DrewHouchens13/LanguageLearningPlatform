Feature: User Leveling System
  As a learner
  I want to advance through levels
  So that I can see my progression and unlock new content

  Background:
    Given I am logged in as "learner@example.com"

  Scenario: View current level on profile
    Given I am level 5 with 250 XP
    When I view my profile page
    Then I should see my current level is 5
    And I should see my current XP is 250
    And I should see XP needed for next level

  Scenario: Level progression display
    Given I am level 3 with 180 XP
    And level 4 requires 200 XP
    When I view my progress
    Then I should see a progress bar showing 90% complete
    And I should see "20 XP to Level 4"

  Scenario: Multiple level ups in one achievement
    Given I am level 1 with 50 XP
    And I complete a challenge worth 200 XP
    When the XP is awarded
    Then I should level up to level 3
    And I should see notifications for both level 2 and level 3

  Scenario: Level milestone rewards
    Given I am level 4 with 450 XP
    When I reach level 5
    Then I should receive a "Level 5 Achiever" badge
    And I should see a congratulations message

  Scenario: Leaderboard ranking
    Given multiple users exist with different XP levels
    When I view the leaderboard
    Then I should see users ranked by total XP
    And I should see my current rank
